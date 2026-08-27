#!/usr/bin/env python3
"""Independent validation for the MF-015R2 characterless atmosphere A/B variant."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from pulp_trailer_stage_r2 import CharacterlessPulpTrailerStage
from validate_mf015 import text_metrics


R1_VIDEO_SHA256 = "4945abbb49965b1132fa99be45e2d9019e5214ef0ccf23905936da0077f113a6"
R1_CONFIG_SHA256 = "7c3b80471e2b8189118c44f6c3e7f9d9d29efd3a7caaeabfa7d682ce1316372e"
EXPECTED_PCM_SHA256 = "416f77e922a303a27207b0d39c1823490678509815aa2ba3a6f05faf5bfe8bb9"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(checks: dict, name: str, passed: bool, detail: object) -> None:
    checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def pcm_hash(video: Path) -> str:
    run = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a:0",
                          "-f", "s16le", "-acodec", "pcm_s16le", "-"], capture_output=True)
    return hashlib.sha256(run.stdout).hexdigest() if run.returncode == 0 else "decode-failed"


def gradient(rgb: np.ndarray, roi: tuple[int, int, int, int]) -> float:
    gray = np.asarray(Image.fromarray(rgb).convert("L"), dtype=np.float32)
    y1, y2, x1, x2 = roi
    region = gray[y1:y2, x1:x2]
    return float((np.abs(np.diff(region, axis=0)).mean() + np.abs(np.diff(region, axis=1)).mean()) / 2)


def head_gold_pixels(rgb: np.ndarray) -> int:
    region = rgb[710:835, 220:335]
    return int(((region[:, :, 0] > 95) & (region[:, :, 0] > region[:, :, 1] * 1.18)
                & (region[:, :, 2] < 80)).sum())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf015r2-characterless-atmosphere.json")
    parser.add_argument("--artifacts", default="artifacts/mf-015r2")
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
        check(checks, "character_candidate_frozen", prior_video.is_file() and sha256(prior_video) == R1_VIDEO_SHA256,
              sha256(prior_video) if prior_video.is_file() else "missing")
        check(checks, "character_config_frozen", prior_config_path.is_file() and sha256(prior_config_path) == R1_CONFIG_SHA256,
              sha256(prior_config_path) if prior_config_path.is_file() else "missing")
        check(checks, "config_identity", manifest.get("config_sha256") == sha256(config_path), manifest.get("config_sha256"))
        preserved = {key: current[key] == prior[key] for key in
                     ("seed", "source_reference", "video", "palette", "fonts", "timeline", "film", "machine", "audio")}
        check(checks, "ab_structure_and_style_integrity", all(preserved.values()), preserved)
        cards = {scene["id"]: scene.get("lines") for scene in current["timeline"] if scene["kind"] == "card"}
        check(checks, "intertitle_order_preserved", [scene["id"] for scene in current["timeline"]]
              == ["black", "opening", "wake", "unknown", "charge", "uncontrolled", "escalation", "undiscovered", "peak", "final"]
              and cards["unknown"] == ["UNKNOWN"] and cards["uncontrolled"] == ["UNCONTROLLED"]
              and cards["undiscovered"] == ["UNDISCOVERED"], cards)

        stage_source = (root / "scripts/pulp_trailer_stage_r2.py").read_text()
        tree = ast.parse(stage_source)
        figure_functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_draw_figure"]
        no_op = len(figure_functions) == 1 and len(figure_functions[0].body) == 1 and isinstance(figure_functions[0].body[0], ast.Return)
        check(checks, "human_renderer_removed", current.get("human_character") is False and no_op,
              {"human_character": current.get("human_character"), "draw_figure_ast": "single return" if no_op else "not no-op"})
        effects = current["environmental_effects"]
        budget = effects["effect_budget"]
        check(checks, "bounded_environmental_effect_budget", budget == {"dominant": 1, "supporting_max": 3}
              and len(effects["steam_sources"]) == 2 and len(effects["arc_events_seconds"]) == 3
              and effects["dust_particles"] <= 20 and effects["ring_vibration_max_pixels"] <= 2
              and effects["cable_sway_pixels"] <= 5,
              {"budget": budget, "steam_sources": len(effects["steam_sources"]),
               "arc_events": effects["arc_events_seconds"], "dust_particles": effects["dust_particles"],
               "ring_vibration_max_pixels": effects["ring_vibration_max_pixels"], "cable_sway_pixels": effects["cable_sway_pixels"]})
        check(checks, "composition_rebalance_declared", effects["foreground_instrument_bank"] is True
              and effects["automatic_lever"] is True and effects["moving_shadow_strength"] <= .3,
              {key: effects[key] for key in ("foreground_instrument_bank", "automatic_lever", "moving_shadow_strength")})

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
        r1_pcm, r2_pcm = pcm_hash(prior_video), pcm_hash(video)
        check(checks, "audio_bit_exact_to_character_version", r1_pcm == r2_pcm == EXPECTED_PCM_SHA256,
              {"mf015r1_pcm_sha256": r1_pcm, "mf015r2_pcm_sha256": r2_pcm})

        names = [name for _, name in current["representative_frames"]]
        frames = {name: artifacts / "representative-frames" / f"{name}.png" for name in names}
        comparisons = [artifacts / "before-after-comparison/charge-composition.png",
                       artifacts / "before-after-comparison/escalation-composition.png",
                       artifacts / "before-after-comparison/character-vs-characterless.mp4"]
        check(checks, "motion_and_comparison_evidence", len(frames) == 12 and all(path.is_file() for path in frames.values())
              and all(path.is_file() for path in comparisons) and (artifacts / "motion-evidence/trailer-sequence.png").is_file(),
              {"representative_frames": len(frames), "comparison_files": [str(path) for path in comparisons]})
        if all(path.is_file() for path in frames.values()):
            images = {name: Image.open(path).convert("RGB") for name, path in frames.items()}
            arrays = {name: np.asarray(image) for name, image in images.items()}
            stage = CharacterlessPulpTrailerStage(current)
            deterministic = {}
            for timestamp, name in current["representative_frames"]:
                rerendered = np.asarray(stage.render_frame(min(stage.frame_count - 1, round(timestamp * stage.fps))))
                deterministic[name] = bool(np.array_equal(rerendered, arrays[name]))
            check(checks, "environmental_frames_deterministic", all(deterministic.values()), deterministic)

            machine_names = ["dark-machine-room", "initial-activation", "first-reactor-escalation",
                             "steam-light-gauges", "stronger-machine-instability"]
            head_counts = {name: head_gold_pixels(arrays[name]) for name in machine_names}
            prior_head = head_gold_pixels(np.asarray(Image.open(root / "artifacts/mf-015r1/representative-frames/reactor-charging.png").convert("RGB")))
            metrics["human_absence"] = {"prior_character_head_pixels": prior_head, "r2_head_pixels": head_counts}
            check(checks, "human_visually_absent_all_sampled_machine_states", prior_head > 300
                  and all(value < prior_head * .1 for value in head_counts.values()), metrics["human_absence"])

            gray_states = {}
            reactor_names = ["dark-machine-room", "initial-activation", "first-reactor-escalation",
                             "stronger-machine-instability", "maximum-reactor-state"]
            for name in reactor_names:
                gray = np.asarray(images[name].convert("L"), dtype=np.float32)
                reactor = gray[340:845, 430:622]
                gray_states[name] = {"reactor_mean": round(float(reactor.mean()), 3),
                                     "reactor_bright_ratio": round(float((reactor > 150).mean()), 5),
                                     "frame_mean": round(float(gray.mean()), 3)}
            metrics["reactor"] = gray_states
            reactor_means = [gray_states[name]["reactor_mean"] for name in reactor_names]
            check(checks, "reactor_escalation_strengthened", all(b > a for a, b in zip(reactor_means, reactor_means[1:]))
                  and reactor_means[-1] > reactor_means[0] * 2, gray_states)
            dominance = {}
            for name in reactor_names[:-1]:
                gray = np.asarray(images[name].convert("L"), dtype=np.float32)
                reactor_mean = float(gray[340:845, 430:622].mean())
                rest_mean = float(gray[160:1040, 20:400].mean())
                dominance[name] = round(reactor_mean / max(rest_mean, 1), 3)
            check(checks, "reactor_remains_visual_hero", all(value > 1.55 for value in dominance.values()), dominance)

            early = np.asarray(images["first-reactor-escalation"])
            former_gray = np.asarray(images["first-reactor-escalation"].convert("L"), dtype=np.float32)[710:1110, 140:410]
            left_mean = float(np.asarray(images["first-reactor-escalation"].convert("L"), dtype=np.float32)[:, :384].mean())
            right_mean = float(np.asarray(images["first-reactor-escalation"].convert("L"), dtype=np.float32)[:, 384:].mean())
            balance = {"former_character_region_mean": round(float(former_gray.mean()), 3),
                       "former_character_region_std": round(float(former_gray.std()), 3),
                       "right_to_left_luma_ratio": round(right_mean / max(left_mean, 1), 3)}
            metrics["composition"] = balance
            check(checks, "composition_rebalanced_without_empty_hole", balance["former_character_region_mean"] > 30
                  and balance["former_character_region_std"] > 20 and 1.2 < balance["right_to_left_luma_ratio"] < 1.8, balance)

            # Execute effect helpers into independent alpha plates at configured evidence times.
            steam_plate = Image.new("RGBA", stage.size, (0, 0, 0, 0))
            steam_state = stage._steam(steam_plate, .58, 11.8, round(11.8 * stage.fps))
            steam_alpha = np.asarray(steam_plate)[:, :, 3]
            arc_plate = Image.new("RGBA", stage.size, (0, 0, 0, 0))
            arc_state = stage._arcs(arc_plate, .8, 16.75, round(16.75 * stage.fps))
            arc_alpha = np.asarray(arc_plate)[:, :, 3]
            check(checks, "steam_vapor_executes_bounded", steam_state["active"] is True
                  and 0 < int((steam_alpha > 0).sum()) < stage.size[0] * stage.size[1] * .08,
                  {"state": steam_state, "alpha_pixels": int((steam_alpha > 0).sum())})
            check(checks, "electrical_arc_executes_briefly", arc_state["active"] is True
                  and arc_state["level"] == 1.0 and 0 < int((arc_alpha > 0).sum()) < 4000,
                  {"state": arc_state, "alpha_pixels": int((arc_alpha > 0).sum())})
            steam_delta = np.abs(arrays["steam-light-gauges"].astype(np.int16)
                                 - arrays["first-reactor-escalation"].astype(np.int16)).max(axis=2)[700:950, 230:530]
            check(checks, "environment_light_pressure_motion_visible", .05 < float((steam_delta > 10).mean()) < .3,
                  {"changed_ratio": round(float((steam_delta > 10).mean()), 5), "mean_delta": round(float(steam_delta.mean()), 3)})

            prior_charge = np.asarray(Image.open(root / "artifacts/mf-015r1/representative-frames/reactor-charging.png").convert("RGB"))
            rois = {"background": (80, 700, 280, 740), "machine_room": (500, 1040, 25, 720)}
            material = {}
            for key, roi in rois.items():
                before, after = gradient(prior_charge, roi), gradient(early, roi)
                material[key] = {"character_version": round(before, 5), "characterless": round(after, 5),
                                 "retention_ratio": round(after / before, 5)}
            metrics["materiality"] = material
            check(checks, "pulp_materiality_preserved", all(item["retention_ratio"] > .95 for item in material.values()), material)

            card_pairs = {"unknown-card": ("UNKNOWN", (384, 576), 180, 676),
                          "uncontrolled-card": ("UNCONTROLLED", (384, 576), 180, 676),
                          "undiscovered-card": ("UNDISCOVERED", (384, 576), 180, 676),
                          "final-title": ("UNKNOWN", (384, 370), 184, 692),
                          "final-cta": ("rcblanzy.com/books/unknown-process", (384, 1015), 36, 688)}
            readable = {}
            for name, (text, position, size, maximum) in card_pairs.items():
                readable[name] = text_metrics(images[name], text, position, size, current["fonts"]["display"], maximum)
            metrics["readability"] = readable
            check(checks, "cards_final_title_cta_readable", all(item["contrast"] > 35 and item["glyph_p90"] > 100
                  and item["edge_margin"] > 20 for item in readable.values()), readable)

        r1_elapsed = json.loads((root / "artifacts/mf-015r1/render-manifest.json").read_text())["elapsed_ms"]
        r2_elapsed = manifest["elapsed_ms"]
        performance = {"mf015r1_elapsed_ms": r1_elapsed, "mf015r2_elapsed_ms": r2_elapsed,
                       "ratio": round(r2_elapsed / r1_elapsed, 4), "increase_percent": round((r2_elapsed / r1_elapsed - 1) * 100, 2)}
        check(checks, "render_cost_practical", performance["ratio"] < 1.5, performance)
        check(checks, "not_published", manifest.get("published") is False, manifest.get("published"))
        passed = all(value["status"] == "PASS" for value in checks.values())
        result = {"slice": "MF-015R2", "checks": checks, "environmental_metrics": metrics,
                  "performance": performance, "audio_status": manifest.get("audio", {}).get("status"),
                  "human_ab_review": "PENDING_HUMAN", "published": False,
                  "result": "TECHNICAL_PASS" if passed else "FAIL"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result = {"slice": "MF-015R2", "checks": checks, "environmental_metrics": metrics,
                  "errors": [str(error)], "human_ab_review": "PENDING_HUMAN", "published": False, "result": "FAIL"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
