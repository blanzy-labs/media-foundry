#!/usr/bin/env python3
"""Independent technical validation for the MF-020 Blender-only hero shot."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from playable_scene_contract import sha256
from render_backend_contract import load_contract, select_backend, validate_portable_paths
from run_mf019 import probe


def image(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    art = root / "artifacts/mf-020"
    config = json.loads((root / "config/mf020-cinematic-reactor.json").read_text())
    manifest = json.loads((art / "render-manifest.json").read_text())
    checks = {}

    def check(name, passed, detail):
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    contract = load_contract(root / "config/render-backends.json")
    validate_portable_paths(config)
    check("explicit_blender_only_backend", select_backend(config, contract) == "BLENDER" and manifest["backend"] == "BLENDER" and manifest["compare_mode"] is False, {"selected": select_backend(config, contract), "compare_mode": manifest["compare_mode"]})
    check("godot_architecture_untouched_and_not_required", manifest["godot_dependency"] is False and manifest["scene_contract"]["godot_dependency"] is False and manifest["gameplay_ready"] is False, {"godot_dependency": manifest["godot_dependency"], "gameplay_ready": manifest["gameplay_ready"]})
    check("portable_fail_closed_configuration", config["render"]["fallback"]["allowed"] is False and not any(str(value).startswith("/home/") for value in (config["render"]["blender"]["template"], config["render"]["blender"]["builder_script"], config["render"]["blender"]["scene_output"], config["audio"]["source"])), config["render"])

    preflight = json.loads((art / "validation/blender-preflight.json").read_text())
    check("blender_preflight", preflight["result"] == "PASS" and all(preflight["checks"].values()), preflight)
    check("version_engine_device_recorded", preflight["blender"]["version"] == "5.2.0 LTS" and preflight["blender"]["python"] and preflight["blender"]["selected_engine"] == "BLENDER_EEVEE" and preflight["blender"]["device"], preflight["blender"])
    template = root / manifest["template"]["path"]
    builder = root / manifest["builder"]["path"]
    scene = root / manifest["scene"]["path"]
    check("template_builder_scene_integrity", all(path.is_file() for path in (template, builder, scene)) and sha256(template) == manifest["template"]["sha256"] and sha256(builder) == manifest["builder"]["sha256"] and sha256(scene) == manifest["scene"]["sha256"], {"template": sha256(template), "builder": sha256(builder), "scene": sha256(scene)})

    expected_stage_order = ["CONCEPT", "BLOCKOUT", "DETAIL", "LIGHTING", "ANIMATION_FX", "FINAL_RENDER", "FINALIZATION"]
    status_states = [json.loads(line)["state"] for line in (art / "logs/production-status.jsonl").read_text().splitlines()]
    runtime_stage_order = ["BACKEND_PREFLIGHT", "BLOCKOUT", "BLOCKOUT_GATE", "DETAIL_PASS", "LIGHTING_PASS", "ANIMATION_FX_PASS", "FINAL_RENDER", "VALIDATING_FRAMES", "FINALIZATION", "READY_FOR_REVIEW"]
    check("proper_production_stage_contract", config["stages"]["order"] == expected_stage_order and manifest["stage_order"] == expected_stage_order, manifest["stage_order"])
    check("runtime_stage_order_and_gate", status_states == runtime_stage_order and status_states.index("BLOCKOUT_GATE") < status_states.index("DETAIL_PASS"), status_states)
    gate = json.loads((art / "validation/blockout-gate.json").read_text())
    check("blockout_gate", gate["result"] == "PASS" and gate["detail_render_authorized"] is True and all(value["status"] == "PASS" for value in gate["checks"].values()), gate)

    stage_paths = {
        "blockout": [art / "blockout/dormant.png", art / "blockout/escalation.png", art / "blockout/final.png"],
        "detail": [art / "previews/detail/detail-pass.png"],
        "lighting": [art / "previews/lighting/lighting-pass.png"],
        "fx": [art / "previews/fx/pressure-release.png", art / "previews/fx/full-power.png", art / "previews/fx/final-hold.png"],
    }
    stage_files = [path for values in stage_paths.values() for path in values]
    stage_dimensions = {Image.open(path).size for path in stage_files if path.is_file()}
    check("evidence_for_each_visual_stage", all(path.is_file() and path.stat().st_size > 1024 for path in stage_files) and stage_dimensions == {(768, 1152)}, {key: [str(path.relative_to(root)) for path in values] for key, values in stage_paths.items()})
    detail = image(stage_paths["detail"][0])
    lighting = image(stage_paths["lighting"][0])
    fx_full = image(stage_paths["fx"][1])
    stage_deltas = {"detail_to_lighting": int(np.any(detail != lighting, axis=2).sum()), "lighting_to_fx": int(np.any(lighting != fx_full, axis=2).sum())}
    check("detail_lighting_fx_are_distinct_passes", min(stage_deltas.values()) > 10000, stage_deltas)

    frames_dir = art / "frames"
    frame_paths = [frames_dir / f"frame-{index:04d}.png" for index in range(300)]
    complete = len(list(frames_dir.glob("frame-*.png"))) == 300 and all(path.is_file() and path.stat().st_size > 1024 for path in frame_paths)
    dimensions = {Image.open(path).size for path in frame_paths} if complete else set()
    check("complete_png_frame_sequence", complete and dimensions == {(768, 1152)}, {"expected": 300, "actual": len(list(frames_dir.glob("frame-*.png"))), "dimensions": [list(value) for value in dimensions]})
    resume = json.loads((art / "validation/resume-performance.json").read_text())
    check("frame_resume_recovery", resume["rendered"] == 0 and resume["resumed_frames"] == 300, resume)
    scene_contract = json.loads((frames_dir / "scene-contract.json").read_text())
    check("deterministic_render_contract", scene_contract["seed"] == 200020 and scene_contract["engine"] == "BLENDER_EEVEE" and scene_contract["samples"] == 16 and scene_contract["fps"] == 30 and scene_contract["frames"] == 300, {key: scene_contract[key] for key in ("seed", "engine", "samples", "resolution", "fps", "frames")})
    camera = scene_contract["camera"]
    check("single_cinematic_perspective_move", camera == {"name": "CinematicHeroCamera", "lens_mm": 46.0, "move": "slow_push_with_subtle_rightward_orbit", "single_shot": True}, camera)
    mechanical = scene_contract["mechanical_logic"]
    check("physical_causal_machine_logic", all(mechanical.values()) and scene_contract["objects"]["gauges"] == 3 and scene_contract["objects"]["ring_lamps"] == 7, {"logic": mechanical, "objects": scene_contract["objects"]})
    fx = scene_contract["fx"]
    check("restrained_native_fx_contract", fx == {"steam_volumes": 4, "contained_sparks": 9, "bounded_compositor_glow": True}, fx)

    cross = {"pressure_release": int(np.any(image(stage_paths["fx"][0]) != image(frame_paths[150]), axis=2).sum()), "full_power": int(np.any(image(stage_paths["fx"][1]) != image(frame_paths[219]), axis=2).sum()), "final_hold": int(np.any(image(stage_paths["fx"][2]) != image(frame_paths[282]), axis=2).sum())}
    check("cross_invocation_pixel_determinism", max(cross.values()) <= 2 and cross["full_power"] == 0 and cross["final_hold"] == 0, {**cross, "practical_volumetric_tolerance_pixels": 2})
    dormant = image(frame_paths[15])
    pressure = image(frame_paths[138])
    powered = image(frame_paths[219])
    final_frame = image(frame_paths[282])
    core_roi = (slice(180, 980), slice(210, 690))
    energy_metrics = {"dormant_luma": float(dormant[core_roi].mean()), "pressure_luma": float(pressure[core_roi].mean()), "powered_luma": float(powered[core_roi].mean()), "powered_bright_pixels": int((powered[core_roi].max(axis=2) > 180).sum())}
    check("readable_reactor_escalation", energy_metrics["powered_luma"] > energy_metrics["dormant_luma"] * 1.8 and energy_metrics["powered_bright_pixels"] > 8000, energy_metrics)
    camera_change = {"dormant_to_final_changed_pixels": int(np.any(dormant != final_frame, axis=2).sum())}
    check("camera_and_end_state_visually_change", camera_change["dormant_to_final_changed_pixels"] > 300000, camera_change)

    final = art / "final-test.mp4"
    expected_media = {"video": "h264", "audio": "aac", "width": 768, "height": 1152, "fps": "30/1", "frames": 300, "duration": 10.0, "sample_rate": 48000}
    media = probe(final)
    check("final_media_contract", media == expected_media, media)
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"], capture_output=True)
    check("full_final_decode", decode.returncode == 0, {"returncode": decode.returncode, "stderr": decode.stderr.decode(errors="replace")})
    finalization = json.loads((art / "validation/finalization.json").read_text())
    audio = finalization["audio"]
    check("approved_audio_finalization", finalization["result"] == "PASS" and audio["track_approval"] == audio["cue_approval"] == "APPROVED" and audio["source_offsets_seconds"] == [5.0, 15.0] and audio["sfx_policy"] == "NONE_FOR_FIRST_PROOF", audio)
    with tempfile.TemporaryDirectory(prefix="mf020-title-") as temp:
        title_path = Path(temp) / "title.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "9.4", "-i", str(final), "-frames:v", "1", str(title_path)], check=True)
        title_image = image(title_path)
    title_roi = title_image[930:1100]
    yellow = (title_roi[:, :, 0] > 170) & (title_roi[:, :, 1] > 110) & (title_roi[:, :, 2] < 130)
    check("media_foundry_title_present", int(yellow.sum()) > 1500 and finalization["title"]["owner"] == "MEDIA_FOUNDRY" and finalization["title"]["text"] == "UNKNOWN PROCESS", {"yellow_title_pixels": int(yellow.sum()), **finalization["title"]})

    outputs_ok = True
    actual_hashes = {}
    for relative, expected in manifest["outputs"].items():
        path = art / relative
        actual = sha256(path) if path.is_file() else None
        actual_hashes[relative] = actual
        outputs_ok = outputs_ok and actual == expected["sha256"] and path.stat().st_size == expected["bytes"]
    check("evidence_artifact_integrity", outputs_ok, actual_hashes)
    performance = manifest["performance"]
    check("performance_evidence", performance["final_render"]["rendered"] == 300 and performance["final_render"]["render_ms"] > 0 and performance["finalization_ms"] > 0 and performance["peak_memory_kb"] > 0 and performance["frame_storage_bytes"] > 0, performance)
    check("human_and_publication_gates", manifest["human_review"] == "PENDING_HUMAN" and manifest["release_ready"] is False and manifest["published"] is False and manifest["blender_to_godot_export"] is False, {key: manifest[key] for key in ("human_review", "release_ready", "published", "blender_to_godot_export")})

    result = "TECHNICAL_PASS" if all(value["status"] == "PASS" for value in checks.values()) else "FAIL"
    report = {"slice": "MF-020", "result": result, "passed": sum(value["status"] == "PASS" for value in checks.values()), "total": len(checks), "creative_review": "PENDING_HUMAN", "release_ready": False, "published": False, "checks": checks}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if result == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
