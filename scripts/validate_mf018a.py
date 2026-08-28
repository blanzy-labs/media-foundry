#!/usr/bin/env python3
"""Independent fail-closed validation for the MF-018A native Godot proof."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from composition_contract import validate_manifest
from run_mf018a import sha256


FROZEN = {
    "artifacts/mf-015/final-test.mp4": "f145f0b089f54e6db32a4ab907f53ae8eb4b6dbbe7ebcb7eed50bec8034b7d7c",
    "artifacts/mf-015r1/final-test.mp4": "4945abbb49965b1132fa99be45e2d9019e5214ef0ccf23905936da0077f113a6",
    "artifacts/mf-015r2/final-test.mp4": "3c3d570d9c8d33a0942373937beefef49809b46f2e7a256008c3b9c2de9dc080",
    "config/mf016-pulp-composition.json": "53971df4c454268eb09c5d9715fae7fab6defd8979484888d318d643355b26ef",
    "artifacts/mf-017/hybrid/motion-proof.mp4": "f6b18c9b9b97c3e12bb25b538e1d351e974ceec8d114dfce2b3d9461869f7859",
}


def probe(path: Path) -> dict:
    process = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    data = json.loads(process.stdout) if process.returncode == 0 else {}
    video = next((item for item in data.get("streams", []) if item.get("codec_type") == "video"), {})
    audio = next((item for item in data.get("streams", []) if item.get("codec_type") == "audio"), {})
    return {"video_codec": video.get("codec_name"), "audio_codec": audio.get("codec_name"),
            "width": video.get("width"), "height": video.get("height"), "fps": video.get("avg_frame_rate"),
            "frames": int(video.get("nb_read_frames", 0)), "duration": float(data.get("format", {}).get("duration", 0)),
            "sample_rate": int(audio.get("sample_rate", 0))}


def frame(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def luma(values: np.ndarray) -> np.ndarray:
    return .2126 * values[:, :, 0] + .7152 * values[:, :, 1] + .0722 * values[:, :, 2]


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve(); artifacts = root / "artifacts/mf-018a"
    config_path = root / "config/mf018a-native-pulp-scene.json"; composition_path = root / "config/mf018a-native-composition.json"
    config = json.loads(config_path.read_text()); composition = json.loads(composition_path.read_text())
    manifest = json.loads((artifacts / "render-manifest.json").read_text()); audio = json.loads((artifacts / "validation/audio-selection.json").read_text())
    checks = {}

    def check(name: str, passed: bool, detail) -> None:
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    frozen_actual = {relative: sha256(root / relative) if (root / relative).is_file() else None for relative in FROZEN}
    check("prior_slices_frozen", frozen_actual == FROZEN, frozen_actual)
    check("config_and_source_integrity", manifest["config_sha256"] == sha256(config_path)
          and manifest["composition_sha256"] == sha256(composition_path)
          and manifest["godot_script_sha256"] == sha256(root / manifest["godot_script"]),
          {"config": sha256(config_path), "composition": sha256(composition_path), "godot": sha256(root / manifest["godot_script"])})
    composition_result = validate_manifest(composition)
    check("semantic_composition_contract", composition_result["result"] == "PASS"
          and len(composition_result["checks"]) == 17 and all(value == "PASS" for value in composition_result["checks"].values()), composition_result)
    check("composition_human_gate_preserved", manifest["composition_gate"] == "COMPOSITION_PENDING"
          and manifest["composition_human_status"] == "PENDING_HUMAN" and not manifest["release_ready"],
          {"gate": manifest["composition_gate"], "human": manifest["composition_human_status"], "release_ready": manifest["release_ready"]})
    reference = Path(config["art_direction_reference"]["path"])
    check("art_direction_reference_bound", reference.is_file() and sha256(reference) == config["art_direction_reference"]["sha256"],
          {"path": str(reference), "sha256": sha256(reference) if reference.is_file() else None})
    catalog = json.loads((root / config["audio"]["catalog"]).read_text())
    track = next((item for item in catalog["tracks"] if item["qualified_id"] == config["audio"]["qualified_id"]), None)
    cue = next((item for item in track.get("cue_regions", []) if item["id"] == config["audio"]["cue_region"]), None) if track else None
    source = root / config["audio"]["source"]
    audio_ok = bool(track and cue and source.is_file() and sha256(source) == config["audio"]["source_sha256"]
                    and track["approval"]["status"] == cue["approval"]["status"] == "APPROVED"
                    and track["approval"]["approved_sha256"] == cue["approval"]["approved_sha256"] == sha256(source)
                    and cue["usable_start"] <= audio["actual_start"] < audio["actual_end"] <= cue["usable_end"])
    check("approved_local_audio", audio_ok, audio)
    loudness = audio["loudness"]
    check("audio_delivery_levels", abs(loudness["integrated_lufs"] - config["audio"]["target_lufs"]) <= .75
          and loudness["true_peak_db"] <= config["audio"]["true_peak_db"] + .1,
          {"measured": loudness, "target_lufs": config["audio"]["target_lufs"], "true_peak_ceiling": config["audio"]["true_peak_db"]})
    output_integrity, actual_outputs = True, {}
    for relative, expected in manifest["outputs"].items():
        path = artifacts / relative; actual = sha256(path) if path.is_file() else None
        actual_outputs[relative] = actual; output_integrity = output_integrity and actual == expected["sha256"] and path.stat().st_size == expected["bytes"]
    check("artifact_integrity", output_integrity, actual_outputs)
    final = artifacts / "godot-native-pulp-scene.mp4"; final_probe = probe(final)
    check("candidate_media_contract", final_probe == {"video_codec": "h264", "audio_codec": "aac", "width": 768, "height": 1152,
          "fps": "30/1", "frames": 360, "duration": 12.0, "sample_rate": 48000}, final_probe)
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"], capture_output=True)
    check("full_candidate_decode", decode.returncode == 0, decode.stderr.decode()[-1000:])
    comparison = artifacts / "comparison/hybrid-vs-native.mp4"; comparison_probe = probe(comparison)
    comparison_decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(comparison), "-f", "null", "-"], capture_output=True)
    check("matched_hybrid_comparison", comparison_probe["video_codec"] == "h264" and comparison_probe["width"] == 1536
          and comparison_probe["height"] == 1152 and comparison_probe["frames"] == 120 and comparison_probe["duration"] == 4.0
          and comparison_decode.returncode == 0, comparison_probe)
    expected_stills = [artifacts / "representative-frames" / f"{name}.png" for _, name in config["representative_frames"]]
    expected_stills += [artifacts / "static-keyframes" / f"{name}.png" for name in ("dormant", "activation", "peak")]
    stills_ok = all(path.is_file() and Image.open(path).size == (768, 1152) for path in expected_stills)
    check("static_and_representative_evidence", stills_ok and (artifacts / "representative-frames/contact-sheet.png").is_file(),
          [str(path.relative_to(root)) for path in expected_stills])
    godot_log = (artifacts / "logs/godot-native.log").read_text()
    check("godot_native_render_clean", "MF018A_NATIVE_SCENE_OK frames=360 seed=1801957" in godot_log
          and "ERROR:" not in godot_log and "SCRIPT ERROR:" not in godot_log, godot_log.strip())
    source_text = (root / manifest["godot_script"]).read_text()
    required_tokens = ["clipPath id='chamber'", "for gauge in range(3)", "Attached ring lamps",
                       "steam valve", "camera transform", "load_svg_from_string", "Native console"]
    forbidden_tokens = ["--base", "load_png_from_buffer", "Image.load(", "plate_path"]
    check("native_scene_construction", all(token in source_text for token in required_tokens)
          and all(token not in source_text for token in forbidden_tokens) and manifest["native_scene"],
          {"required": required_tokens, "forbidden_absent": forbidden_tokens})
    dormant = frame(artifacts / "static-keyframes/dormant.png").astype(float)
    activation = frame(artifacts / "static-keyframes/activation.png").astype(float)
    peak = frame(artifacts / "static-keyframes/peak.png").astype(float)
    motion = {"dormant_to_activation_mean": float(np.abs(activation - dormant).mean()),
              "activation_to_peak_mean": float(np.abs(peak - activation).mean()),
              "changed_ratio": float(np.mean(np.any(np.abs(peak - dormant) > 8, axis=2)))}
    check("meaningful_machine_state_motion", motion["dormant_to_activation_mean"] > .4
          and motion["activation_to_peak_mean"] > .7 and motion["changed_ratio"] > .02, motion)
    reactor = (slice(210, 1010), slice(340, 690)); support = (slice(500, 1010), slice(15, 280))
    hierarchy = {"dormant": float(luma(dormant[reactor]).mean() / max(luma(dormant[support]).mean(), 1)),
                 "activation": float(luma(activation[reactor]).mean() / max(luma(activation[support]).mean(), 1)),
                 "peak": float(luma(peak[reactor]).mean() / max(luma(peak[support]).mean(), 1))}
    check("reactor_visual_dominance", min(hierarchy.values()) > 1.08, hierarchy)
    chamber = (slice(330, 820), slice(420, 635)); outside = (slice(330, 820), slice(635, 768))
    def yellow(values: np.ndarray) -> np.ndarray:
        return ((values[:, :, 0] > 120) & (values[:, :, 1] > 85) & (values[:, :, 2] < 125)
                & ((values[:, :, 0] + values[:, :, 1]) > values[:, :, 2] * 2.5))
    chamber_growth = int(yellow(peak[chamber]).sum() - yellow(dormant[chamber]).sum())
    outside_growth = int(yellow(peak[outside]).sum() - yellow(dormant[outside]).sum())
    energy_delta = {"inside_new_yellow_pixels": chamber_growth, "adjacent_new_yellow_pixels": outside_growth,
                    "binding_ratio": round(chamber_growth / max(outside_growth, 1), 3)}
    check("energy_bound_to_chamber", chamber_growth > 2000 and chamber_growth > max(outside_growth, 1) * 5, energy_delta)
    red = (peak[:, :, 0] > 105) & (peak[:, :, 0] > peak[:, :, 1] * 1.45) & (peak[:, :, 1] < 90)
    ring_red = int(red[180:370, 340:700].sum()); console_red = int(red[720:930, 30:260].sum())
    total_red = int(red.sum())
    check("warning_lamps_seated_in_machine_regions", ring_red > 100 and console_red > 40
          and (ring_red + console_red) / max(total_red, 1) > .72,
          {"ring_pixels": ring_red, "console_pixels": console_red, "total_red_pixels": total_red})
    gauge_delta = float(np.abs(peak[610:735, 45:245] - dormant[610:735, 45:245]).mean())
    check("native_gauge_response", gauge_delta > .3 and "var angle:=deg_to_rad" in source_text, {"gauge_region_mean_delta": gauge_delta})
    check("deterministic_seed_and_schedule", manifest["seed"] == config["seed"] == composition["seed"] == 1801957
          and manifest["raw_frames_retained"] is False and config["motion"]["lamp_count"] == 10
          and config["motion"]["gauge_count"] == 3 and config["motion"]["steam_sources"] == 1,
          {"seed": manifest["seed"], "motion": config["motion"], "raw_frames_retained": manifest["raw_frames_retained"]})
    check("practical_render_performance", manifest["elapsed_ms"] < 120000,
          {"native_elapsed_ms": manifest["elapsed_ms"], "mf017_reference_elapsed_ms": 89310,
           "native_to_mf017_ratio": round(manifest["elapsed_ms"] / 89310, 3)})
    check("no_publication", manifest["published"] is False and manifest["human_review"] == "PENDING_HUMAN",
          {"published": manifest["published"], "human_review": manifest["human_review"]})
    result = "TECHNICAL_PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"
    report = {"slice": "MF-018A", "result": result, "mode": "PULP_GAME_WORLD", "release_ready": False,
              "composition_status": "COMPOSITION_PENDING", "human_review": "PENDING_HUMAN", "checks": checks,
              "metrics": {"motion": motion, "hierarchy": hierarchy, "energy_binding": energy_delta,
                          "gauge_delta": gauge_delta, "performance_ms": manifest["elapsed_ms"]}, "published": False}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2)); return 0 if result == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
