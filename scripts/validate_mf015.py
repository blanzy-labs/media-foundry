#!/usr/bin/env python3
"""Independent fail-closed validation for MF-015."""

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

from pulp_trailer_stage import PulpTrailerStage


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(checks: dict, name: str, passed: bool, detail: object) -> None:
    checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def fit_font(path: str, text: str, maximum: int, start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size > 16:
        font = ImageFont.truetype(path, size)
        if font.getbbox(text)[2] <= maximum:
            return font
        size -= 2
    return ImageFont.truetype(path, size)


def text_metrics(image: Image.Image, text: str, position: tuple[int, int], size: int, font_path: str,
                 maximum: int, anchor: str = "mm") -> dict:
    raw = Image.new("L", image.size, 0)
    font = fit_font(font_path, text, maximum, size)
    ImageDraw.Draw(raw).text(position, text, font=font, fill=255, anchor=anchor, stroke_width=1)
    # One-pixel film weave is accepted by dilating the independently reconstructed mask.
    glyph = np.asarray(raw.filter(ImageFilter.MaxFilter(5))) > 0
    ring = (np.asarray(raw.filter(ImageFilter.MaxFilter(17))) > 0) & ~glyph
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    ys, xs = np.where(glyph)
    return {"bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "contrast": round(float(gray[glyph].mean() - gray[ring].mean()), 3),
            "glyph_p90": round(float(np.percentile(gray[glyph], 90)), 3),
            "edge_margin": int(min(xs.min(), ys.min(), image.width - 1 - xs.max(), image.height - 1 - ys.max()))}


def red_lamp_pixels(rgb: np.ndarray) -> int:
    roi = rgb[700:900, 30:280]
    return int(((roi[:, :, 0] > 95) & (roi[:, :, 0] > roi[:, :, 1] * 1.7)
                & (roi[:, :, 0] > roi[:, :, 2] * 1.5)).sum())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf015-pulp-trailer.json")
    parser.add_argument("--artifacts", default="artifacts/mf-015")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, output = Path(args.project_root).resolve(), Path(args.output).resolve()
    config_path, artifacts = root / args.config, root / args.artifacts
    checks, metrics = {}, {}
    try:
        definition = json.loads(config_path.read_text())
        manifest = json.loads((artifacts / "render-manifest.json").read_text())
        video = artifacts / "final-test.mp4"
        source = Path(definition["source_reference"]["path"])
        check(checks, "source_reference_verified", source.is_file()
              and sha256(source) == definition["source_reference"]["sha256"]
              and definition["source_reference"]["usage"] == "art_direction_reference",
              definition["source_reference"])
        check(checks, "config_identity", manifest.get("config_sha256") == sha256(config_path), manifest.get("config_sha256"))
        check(checks, "deterministic_seed_recorded", isinstance(definition.get("seed"), int)
              and manifest.get("seed") == definition["seed"], definition.get("seed"))

        timeline = definition["timeline"]
        expected_ids = ["black", "opening", "wake", "unknown", "charge", "uncontrolled", "escalation",
                        "undiscovered", "peak", "final"]
        contiguous = all(abs(timeline[index]["end"] - timeline[index + 1]["start"]) < 1e-9
                         for index in range(len(timeline) - 1))
        check(checks, "timeline_and_hard_cut_order", [scene["id"] for scene in timeline] == expected_ids
              and contiguous and timeline[0]["start"] == 0 and timeline[-1]["end"] == definition["video"]["duration_seconds"],
              [{"id": scene["id"], "kind": scene["kind"], "start": scene["start"], "end": scene["end"]} for scene in timeline])
        words = {scene["id"]: scene.get("lines") for scene in timeline if scene["kind"] == "card"}
        final_scene = timeline[-1]
        check(checks, "required_cards_exact", words == {"opening": ["A PROCESS", "NO ONE WAS MEANT", "TO DISCOVER"],
              "unknown": ["UNKNOWN"], "uncontrolled": ["UNCONTROLLED"], "undiscovered": ["UNDISCOVERED"]}
              and final_scene["title"] == ["UNKNOWN", "PROCESS"] and final_scene["book"] == "BOOK ONE"
              and final_scene["cta"] == "rcblanzy.com/books/unknown-process",
              {"cards": words, "final": {key: final_scene[key] for key in ("title", "book", "cta")}})
        serialized = json.dumps(definition).lower()
        banned = [term for term in ("hud", "hologram", "modern ui", "digital display", "cta button") if term in serialized]
        check(checks, "no_modern_ui_contract", not banned, banned)

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
        check(checks, "full_audio_video_decode", decode.returncode == 0, "succeeded" if decode.returncode == 0 else decode.stderr[-300:])
        audio = manifest.get("audio", {})
        levels = audio.get("levels", {})
        score = Path(audio.get("path", ""))
        check(checks, "temporary_audio_explicit", audio.get("status") == "MUSIC_PENDING_APPROVAL"
              and audio.get("source") == "locally_generated_temporary_score" and audio.get("generated") is True
              and audio.get("narration") is False and score.is_file() and sha256(score) == audio.get("sha256"), audio)
        check(checks, "audio_levels", -17 <= levels.get("integrated_lufs", 99) <= -15
              and levels.get("true_peak_db", 99) <= -1.0, levels)

        names = [name for _, name in definition["representative_frames"]]
        frame_paths = {name: artifacts / "representative-frames" / f"{name}.png" for name in names}
        check(checks, "evidence_complete", len(frame_paths) == 12 and all(path.is_file() for path in frame_paths.values())
              and (artifacts / "motion-evidence/trailer-sequence.png").is_file(),
              {"representative_frames": len(frame_paths), "motion_evidence": str(artifacts / "motion-evidence/trailer-sequence.png")})
        if all(path.is_file() for path in frame_paths.values()):
            images = {name: Image.open(path).convert("RGB") for name, path in frame_paths.items()}
            arrays = {name: np.asarray(image) for name, image in images.items()}
            stage = PulpTrailerStage(definition)
            deterministic = {}
            for timestamp, name in definition["representative_frames"]:
                rerendered = np.asarray(stage.render_frame(min(stage.frame_count - 1, round(timestamp * stage.fps))))
                deterministic[name] = bool(np.array_equal(rerendered, arrays[name]))
            check(checks, "representative_frames_deterministic", all(deterministic.values()), deterministic)

            card_specs = {
                "unknown-card": ("UNKNOWN", (384, 576), 180, 676),
                "uncontrolled-card": ("UNCONTROLLED", (384, 576), 180, 676),
                "undiscovered-card": ("UNDISCOVERED", (384, 576), 180, 676),
                "final-title": ("UNKNOWN", (384, 370), 184, 692),
                "final-cta": ("rcblanzy.com/books/unknown-process", (384, 1015), 36, 688),
            }
            card_readability = {}
            for name, (text, position, size, maximum) in card_specs.items():
                card_readability[name] = text_metrics(images[name], text, position, size,
                                                      definition["fonts"]["display"], maximum)
            metrics["card_readability"] = card_readability
            check(checks, "cards_present_readable_unclipped", all(item["contrast"] > 35 and item["glyph_p90"] > 100
                  and item["edge_margin"] > 20 for item in card_readability.values()), card_readability)

            machine_names = ["machine-dormant", "machine-waking", "reactor-charging", "escalation", "reactor-peak"]
            reactor = {}
            for name in machine_names:
                gray = np.asarray(images[name].convert("L"), dtype=np.float32)
                roi = gray[340:845, 430:622]
                reactor[name] = {"mean_luma": round(float(roi.mean()), 3),
                                 "bright_ratio": round(float((roi > 150).mean()), 5)}
            metrics["reactor"] = reactor
            means = [reactor[name]["mean_luma"] for name in machine_names]
            check(checks, "reactor_escalation_progresses", all(b > a for a, b in zip(means, means[1:]))
                  and means[-1] > means[0] * 2, reactor)
            lamps = {name: red_lamp_pixels(arrays[name]) for name in machine_names[:-1]}
            metrics["warning_lamps"] = lamps
            check(checks, "warning_lights_activate", lamps["machine-dormant"] < lamps["machine-waking"]
                  < lamps["reactor-charging"] < lamps["escalation"] and lamps["escalation"] > 700, lamps)
            gauge_roi = arrays["machine-dormant"][560:690, 35:270]
            gauge_faces = int(((gauge_roi[:, :, 0] > 120) & (gauge_roi[:, :, 1] > 110) & (gauge_roi[:, :, 2] < 130)).sum())
            gauge_delta = np.abs(arrays["escalation"].astype(np.int16) - arrays["machine-dormant"].astype(np.int16)).max(axis=2)
            check(checks, "analog_gauges_present_and_move", gauge_faces > 5000
                  and float((gauge_delta[560:690, 35:270] > 12).mean()) > .04,
                  {"cream_gauge_pixels": gauge_faces,
                   "changed_ratio": round(float((gauge_delta[560:690, 35:270] > 12).mean()), 5)})
            silhouette_roi = arrays["reactor-charging"][730:1070, 175:425]
            silhouette_delta = np.abs(arrays["escalation"].astype(np.int16) - arrays["reactor-charging"].astype(np.int16)).max(axis=2)
            check(checks, "silhouette_present_and_reacts", float((silhouette_roi.mean(axis=2) < 25).mean()) > .35
                  and float((silhouette_delta[730:1070, 175:425] > 12).mean()) > .12,
                  {"dark_silhouette_ratio": round(float((silhouette_roi.mean(axis=2) < 25).mean()), 5),
                   "reaction_changed_ratio": round(float((silhouette_delta[730:1070, 175:425] > 12).mean()), 5)})
            source_gray = np.asarray(Image.open(source).convert("L").resize((768, 1152)), dtype=np.float32).ravel()
            machine_gray = np.asarray(images["machine-waking"].convert("L"), dtype=np.float32).ravel()
            correlation = float(np.corrcoef(source_gray, machine_gray)[0, 1])
            wake_delta = np.abs(arrays["machine-waking"].astype(np.int16) - arrays["machine-dormant"].astype(np.int16)).max(axis=2)
            check(checks, "new_scene_not_static_cover_pan", abs(correlation) < .25 and .02 < float((wake_delta > 12).mean()) < .25,
                  {"cover_machine_correlation": round(correlation, 5),
                   "dormant_to_waking_changed_ratio": round(float((wake_delta > 12).mean()), 5)})
        film = definition["film"]
        check(checks, "vintage_print_film_controls", film["grain_strength"] > 0 and film["jitter_pixels"] in (1, 2)
              and film["dust_count"] > 0 and film["registration_peak_pixels"] in (1, 2, 3) and film["edge_wear"] > 0, film)
        check(checks, "not_published", manifest.get("published") is False, manifest.get("published"))
        passed = all(value["status"] == "PASS" for value in checks.values())
        result = {"slice": "MF-015", "checks": checks, "visual_metrics": metrics,
                  "audio_status": audio.get("status"), "human_review": "PENDING_HUMAN", "published": False,
                  "result": "TECHNICAL_PASS" if passed else "FAIL"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result = {"slice": "MF-015", "checks": checks, "visual_metrics": metrics, "errors": [str(error)],
                  "human_review": "PENDING_HUMAN", "published": False, "result": "FAIL"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
