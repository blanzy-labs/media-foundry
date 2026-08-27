#!/usr/bin/env python3
"""Independent A/B validation for MF-015R1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from pulp_trailer_stage_r1 import PulpTrailerRefinementStage
from validate_mf015 import text_metrics


BASELINE_VIDEO_SHA256 = "f145f0b089f54e6db32a4ab907f53ae8eb4b6dbbe7ebcb7eed50bec8034b7d7c"
BASELINE_CONFIG_SHA256 = "d553d675a689b8478e6be60525d51ac579f4e91a3c0150275cf777e9024cf803"
EXPECTED_PCM_SHA256 = "416f77e922a303a27207b0d39c1823490678509815aa2ba3a6f05faf5bfe8bb9"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(checks: dict, name: str, passed: bool, detail: object) -> None:
    checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def decoded_pcm_hash(video: Path) -> str:
    run = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a:0",
                          "-f", "s16le", "-acodec", "pcm_s16le", "-"], capture_output=True)
    return hashlib.sha256(run.stdout).hexdigest() if run.returncode == 0 else "decode-failed"


def texture_gradient(rgb: np.ndarray, roi: tuple[int, int, int, int]) -> float:
    gray = np.asarray(Image.fromarray(rgb).convert("L"), dtype=np.float32)
    y1, y2, x1, x2 = roi
    region = gray[y1:y2, x1:x2]
    return float((np.abs(np.diff(region, axis=0)).mean() + np.abs(np.diff(region, axis=1)).mean()) / 2)


def anatomical_metrics(rgb: np.ndarray) -> dict:
    regions = {"head": (710, 835, 220, 335), "torso": (805, 990, 180, 350),
               "hand": (780, 910, 360, 455), "legs": (945, 1110, 190, 380)}
    result = {}
    for key, (y1, y2, x1, x2) in regions.items():
        region = rgb[y1:y2, x1:x2]
        mean = region.mean(axis=2)
        gold = ((region[:, :, 0] > 95) & (region[:, :, 0] > region[:, :, 1] * 1.18)
                & (region[:, :, 2] < 80))
        result[key] = {"midtone_ratio": round(float(((mean > 30) & (mean < 140)).mean()), 5),
                       "gold_rim_pixels": int(gold.sum())}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf015r1-pulp-material-refinement.json")
    parser.add_argument("--artifacts", default="artifacts/mf-015r1")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, output = Path(args.project_root).resolve(), Path(args.output).resolve()
    config_path, artifacts = root / args.config, root / args.artifacts
    checks, metrics = {}, {}
    try:
        current = json.loads(config_path.read_text())
        prior_config_path = root / current["prior_artifact"]["config_path"]
        prior = json.loads(prior_config_path.read_text())
        prior_video = root / current["prior_artifact"]["path"]
        video = artifacts / "final-test.mp4"
        manifest = json.loads((artifacts / "render-manifest.json").read_text())
        check(checks, "mf015_baseline_frozen", prior_video.is_file() and sha256(prior_video) == BASELINE_VIDEO_SHA256,
              sha256(prior_video) if prior_video.is_file() else "missing")
        check(checks, "mf015_config_frozen", prior_config_path.is_file() and sha256(prior_config_path) == BASELINE_CONFIG_SHA256,
              sha256(prior_config_path) if prior_config_path.is_file() else "missing")
        check(checks, "config_identity", manifest.get("config_sha256") == sha256(config_path), manifest.get("config_sha256"))
        preserved = {key: current[key] == prior[key] for key in
                     ("seed", "source_reference", "video", "palette", "fonts", "timeline", "audio")}
        check(checks, "structure_pacing_content_audio_preserved", all(preserved.values()), preserved)
        check(checks, "refinement_stage_declared", current.get("stage") == "pulp_trailer_stage_r1:PulpTrailerRefinementStage",
              current.get("stage"))
        film, base_film = current["film"], prior["film"]
        check(checks, "stronger_print_film_controls", film["grain_strength"] > base_film["grain_strength"]
              and film["jitter_pixels"] > base_film["jitter_pixels"]
              and film["dust_count"] > base_film["dust_count"]
              and film["registration_peak_pixels"] > base_film["registration_peak_pixels"]
              and film["edge_wear"] > base_film["edge_wear"] and film["paper_fiber_strength"] > 0,
              {"baseline": base_film, "refined": film})
        machine = current["machine"]
        check(checks, "depth_material_reactor_controls", machine.get("depth_layers", 0) >= 3
              and machine.get("grime_marks", 0) >= 60 and machine.get("plasma_blobs", 0) >= 5
              and machine.get("character_rim_level", 0) > .5,
              {key: machine[key] for key in ("depth_layers", "grime_marks", "plasma_blobs", "character_rim_level")})

        probe_run = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
                                   capture_output=True, text=True)
        probe = json.loads(probe_run.stdout) if probe_run.returncode == 0 else {}
        streams = probe.get("streams", [])
        video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
        audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})
        duration = float(probe.get("format", {}).get("duration", 0) or 0)
        try:
            fps = float(Fraction(video_stream.get("avg_frame_rate", "0/1")))
        except (ValueError, ZeroDivisionError):
            fps = 0
        check(checks, "video_contract", video_stream.get("codec_name") == "h264" and 29.99 <= duration <= 30.01
              and 29.9 <= fps <= 30.1 and int(video_stream.get("nb_frames", 0)) == 900
              and [video_stream.get("width"), video_stream.get("height")] == [768, 1152],
              {"codec": video_stream.get("codec_name"), "duration": duration, "fps": fps,
               "frames": video_stream.get("nb_frames"), "size": [video_stream.get("width"), video_stream.get("height")]})
        check(checks, "audio_stream", audio_stream.get("codec_name") == "aac", audio_stream.get("codec_name"))
        decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
        check(checks, "full_decode", decode.returncode == 0, "succeeded" if decode.returncode == 0 else decode.stderr[-300:])
        prior_pcm, current_pcm = decoded_pcm_hash(prior_video), decoded_pcm_hash(video)
        check(checks, "audio_bit_exact_to_mf015", prior_pcm == current_pcm == EXPECTED_PCM_SHA256,
              {"mf015_pcm_sha256": prior_pcm, "mf015r1_pcm_sha256": current_pcm})
        audio = manifest.get("audio", {})
        levels = audio.get("levels", {})
        check(checks, "temporary_audio_status_preserved", audio.get("status") == "MUSIC_PENDING_APPROVAL"
              and audio.get("sha256") == "eb7397b4d6901effc10ccca72ba438f0588ec9c58c5af17321f1b5b33e7f7e71"
              and -17 <= levels.get("integrated_lufs", 99) <= -15 and levels.get("true_peak_db", 99) <= -1,
              audio)

        names = [name for _, name in current["representative_frames"]]
        frames = {name: artifacts / "representative-frames" / f"{name}.png" for name in names}
        comparisons = [artifacts / "before-after-comparison/character-materiality.png",
                       artifacts / "before-after-comparison/character-reaction.png",
                       artifacts / "before-after-comparison/final-card.png",
                       artifacts / "before-after-comparison/mf015-vs-mf015r1.mp4"]
        check(checks, "evidence_and_comparisons_complete", len(frames) == 12 and all(path.is_file() for path in frames.values())
              and all(path.is_file() for path in comparisons) and (artifacts / "motion-evidence/trailer-sequence.png").is_file(),
              {"representative_frames": len(frames), "comparison_files": [str(path) for path in comparisons]})
        if all(path.is_file() for path in frames.values()):
            images = {name: Image.open(path).convert("RGB") for name, path in frames.items()}
            arrays = {name: np.asarray(image) for name, image in images.items()}
            stage = PulpTrailerRefinementStage(current)
            deterministic = {}
            for timestamp, name in current["representative_frames"]:
                rendered = np.asarray(stage.render_frame(min(stage.frame_count - 1, round(timestamp * stage.fps))))
                deterministic[name] = bool(np.array_equal(rendered, arrays[name]))
            check(checks, "representative_frames_deterministic", all(deterministic.values()), deterministic)

            prior_dir = root / "artifacts/mf-015/representative-frames"
            prior_images = {name: Image.open(prior_dir / f"{name}.png").convert("RGB") for name in
                            ("opening-intertitle", "unknown-card", "uncontrolled-card", "undiscovered-card", "final-title", "final-cta",
                             "reactor-charging", "escalation", "machine-dormant", "machine-waking", "reactor-peak")}
            card_specs = {"unknown-card": ("UNKNOWN", (384, 576), 180, 676),
                          "uncontrolled-card": ("UNCONTROLLED", (384, 576), 180, 676),
                          "undiscovered-card": ("UNDISCOVERED", (384, 576), 180, 676),
                          "final-title": ("UNKNOWN", (384, 370), 184, 692),
                          "final-cta": ("rcblanzy.com/books/unknown-process", (384, 1015), 36, 688)}
            readability = {}
            readable = True
            for name, (text, position, size, maximum) in card_specs.items():
                before = text_metrics(prior_images[name], text, position, size, prior["fonts"]["display"], maximum)
                after = text_metrics(images[name], text, position, size, current["fonts"]["display"], maximum)
                readability[name] = {"before": before, "after": after}
                readable &= after["contrast"] > 35 and after["contrast"] >= before["contrast"] * .72
                readable &= after["glyph_p90"] > 100 and after["edge_margin"] > 20
            metrics["readability"] = readability
            check(checks, "intertitles_final_title_cta_readable", readable, readability)

            before_charge = np.asarray(prior_images["reactor-charging"])
            before_reaction = np.asarray(prior_images["escalation"])
            after_charge = arrays["reactor-charging"]
            after_reaction = arrays["character-reaction"]
            anatomy_before = anatomical_metrics(before_charge)
            anatomy_after = anatomical_metrics(after_charge)
            metrics["character_anatomy"] = {"before": anatomy_before, "after": anatomy_after}
            anatomy_pass = (anatomy_after["head"]["midtone_ratio"] > .65
                            and anatomy_after["torso"]["midtone_ratio"] > .65
                            and anatomy_after["hand"]["gold_rim_pixels"] > anatomy_before["hand"]["gold_rim_pixels"] * 1.3
                            and anatomy_after["legs"]["gold_rim_pixels"] > anatomy_before["legs"]["gold_rim_pixels"] * 1.3)
            check(checks, "character_anatomy_readability_improved", anatomy_pass, metrics["character_anatomy"])
            before_motion = np.abs(before_reaction.astype(np.int16) - before_charge.astype(np.int16)).max(axis=2)[710:1110, 170:460]
            after_motion = np.abs(after_reaction.astype(np.int16) - after_charge.astype(np.int16)).max(axis=2)[710:1110, 170:460]
            motion = {"before_changed_ratio": round(float((before_motion > 12).mean()), 5),
                      "after_changed_ratio": round(float((after_motion > 12).mean()), 5)}
            metrics["character_motion"] = motion
            check(checks, "character_reaction_refined", motion["after_changed_ratio"] > motion["before_changed_ratio"] * 1.6
                  and motion["after_changed_ratio"] < .45, motion)

            material_rois = {"background": (80, 700, 280, 740), "machine_room": (500, 1040, 25, 720)}
            material = {}
            for key, roi in material_rois.items():
                before_value = texture_gradient(before_charge, roi)
                after_value = texture_gradient(after_charge, roi)
                material[key] = {"before_gradient": round(before_value, 5), "after_gradient": round(after_value, 5),
                                 "ratio": round(after_value / before_value, 5)}
            metrics["materiality"] = material
            check(checks, "pulp_materiality_measurably_stronger", all(item["ratio"] > 1.08 for item in material.values()), material)

            reactor_names = ["machine-dormant", "machine-waking", "reactor-charging", "character-reaction", "reactor-peak"]
            reactor = {}
            for name in reactor_names:
                gray = np.asarray(images[name].convert("L"), dtype=np.float32)[340:845, 430:622]
                left, right = gray[:, :96], np.fliplr(gray[:, 96:])
                reactor[name] = {"mean_luma": round(float(gray.mean()), 3),
                                 "bright_ratio": round(float((gray > 150).mean()), 5),
                                 "asymmetry": round(float(np.abs(left - right).mean()), 3)}
            metrics["reactor"] = reactor
            means = [reactor[name]["mean_luma"] for name in reactor_names]
            base_charge_gray = np.asarray(prior_images["reactor-charging"].convert("L"), dtype=np.float32)[340:845, 430:622]
            base_asymmetry = float(np.abs(base_charge_gray[:, :96] - np.fliplr(base_charge_gray[:, 96:])).mean())
            check(checks, "reactor_stranger_and_escalates", all(b > a for a, b in zip(means, means[1:]))
                  and means[-1] > means[0] * 2 and reactor["reactor-charging"]["asymmetry"] > base_asymmetry * 1.15,
                  {"baseline_charge_asymmetry": round(base_asymmetry, 3), "refined": reactor})
        check(checks, "not_published", manifest.get("published") is False, manifest.get("published"))
        passed = all(value["status"] == "PASS" for value in checks.values())
        result = {"slice": "MF-015R1", "checks": checks, "comparison_metrics": metrics,
                  "audio_status": audio.get("status"), "human_review": "PENDING_HUMAN", "published": False,
                  "result": "TECHNICAL_PASS" if passed else "FAIL"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result = {"slice": "MF-015R1", "checks": checks, "comparison_metrics": metrics, "errors": [str(error)],
                  "human_review": "PENDING_HUMAN", "published": False, "result": "FAIL"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
