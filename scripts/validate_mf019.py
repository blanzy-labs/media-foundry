#!/usr/bin/env python3
"""Independent technical validation for the MF-019 optional Blender backend proof."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from playable_scene_contract import sha256
from render_backend_contract import load_contract, select_backend, validate_portable_paths
from run_mf019 import audio_md5, probe


def im(path: Path) -> np.ndarray: return np.asarray(Image.open(path).convert("RGB"))


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve(); art = root / "artifacts/mf-019"; config = json.loads((root / "config/mf019-ab-render.json").read_text()); manifest = json.loads((art / "render-manifest.json").read_text()); checks = {}
    def check(name, passed, detail): checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    contract = load_contract(root / "config/render-backends.json"); check("bounded_backend_vocabulary", set(contract["backends"]) == {"GODOT", "BLENDER", "COMPARE"}, list(contract["backends"]))
    default = select_backend({}, contract); selected = select_backend(config, contract); check("godot_default_and_explicit_compare", default == "GODOT" and selected == "COMPARE", {"undeclared": default, "mf019": selected})
    validate_portable_paths(config); config_text = (root / "config/mf019-ab-render.json").read_text(); check("portable_backend_configuration", "/home/" not in config_text and config["render"]["fallback"]["allowed"] is False, config["render"])
    capabilities = contract["backends"]; check("backend_capability_declarations", "native_interactivity" in capabilities["GODOT"]["capabilities"] and "complex_materials" in capabilities["BLENDER"]["capabilities"] and "semantic_ab_comparison" in capabilities["COMPARE"]["capabilities"], capabilities)

    preflight = json.loads((art / "validation/blender-preflight.json").read_text()); check("blender_preflight", preflight["result"] == "PASS" and all(preflight["checks"].values()), preflight)
    check("blender_version_engine_recorded", preflight["blender"]["version"] == "5.2.0 LTS" and preflight["blender"]["python"] and preflight["blender"]["selected_engine"] == "BLENDER_EEVEE", preflight["blender"])
    template = root / config["render"]["blender"]["template"]; builder = root / config["render"]["blender"]["builder_script"]
    check("template_and_builder_integrity", template.is_file() and builder.is_file() and sha256(template) == manifest["template"]["sha256"] and sha256(builder) == manifest["builder"]["sha256"], {"template_sha256": sha256(template), "builder_sha256": sha256(builder)})
    source_assets = {"font": root / "godot/fonts/Lato-Heavy.ttf", "music": root / config["audio"]["source"]}; check("local_source_assets_resolve", all(path.is_file() for path in source_assets.values()) and sha256(source_assets["music"]) == config["audio"]["source_sha256"], {key: {"path": str(path.relative_to(root)), "sha256": sha256(path)} for key, path in source_assets.items()})

    candidate_a = art / "godot/candidate-a.mp4"; candidate_b = art / "blender/candidate-b.mp4"; comparison = art / "comparison/side-by-side.mp4"
    check("godot_baseline_preserved", sha256(root / config["candidate_a"]["artifact"]) == config["candidate_a"]["artifact_sha256"] == sha256(candidate_a), {"source": sha256(root / config["candidate_a"]["artifact"]), "copy": sha256(candidate_a)})
    static = json.loads((art / "validation/blender-composition.json").read_text()); check("static_composition_gate", static["result"] == "PASS" and all(item["status"] == "PASS" for item in static["checks"].values()), static)

    expected_count = round(config["shared"]["runtime_seconds"] * config["shared"]["fps"]); frames = art / "blender/frames"; paths = [frames / f"frame-{index:04d}.png" for index in range(expected_count)]
    complete = len(list(frames.glob("frame-*.png"))) == expected_count and all(path.is_file() and path.stat().st_size > 1024 for path in paths); dimensions = {Image.open(path).size for path in paths} if complete else set()
    check("complete_png_frame_sequence", complete and dimensions == {(768, 1152)}, {"expected": expected_count, "actual": len(list(frames.glob("frame-*.png"))), "dimensions": [list(item) for item in dimensions]})
    scene_contract = json.loads((frames / "scene-contract.json").read_text()); check("deterministic_scene_contract", scene_contract["seed"] == config["seed"] and scene_contract["engine"] == "BLENDER_EEVEE" and scene_contract["samples"] == 16 and scene_contract["frames"] == 420, {key: scene_contract[key] for key in ("seed", "engine", "samples", "resolution", "fps", "frames")})
    check("physically_attached_motion_contract", all(scene_contract["attached_motion"].values()) and scene_contract["objects"]["gauges"] == 3 and scene_contract["objects"]["indicators"] == 4 and scene_contract["objects"]["ring_lights"] == 8, {"objects": scene_contract["objects"], "attached": scene_contract["attached_motion"]})
    static_pairs = [("dormant", 15), ("startup", 72), ("active", 198), ("peak-final", 375)]; repro = {}
    for label, index in static_pairs:
        a, b = im(art / "blender/static-keyframes" / f"{label}.png"), im(paths[index]); repro[label] = int(np.any(a != b, axis=2).sum())
    check("cross_invocation_pixel_determinism", all(value == 0 for value in repro.values()), repro)
    resume = json.loads((art / "validation/blender-resume-performance.json").read_text()); check("resume_recovery", resume["rendered"] == 0 and resume["resumed_frames"] == 420, resume)

    before_lever, after_lever = im(paths[34]), im(paths[68]); roi_before = before_lever[500:1050, :300]; roi_after = after_lever[500:1050, :300]
    def red_centroid(pixels):
        mask = (pixels[:, :, 0] > 60) & (pixels[:, :, 0] > pixels[:, :, 1] * 1.5) & (pixels[:, :, 0] > pixels[:, :, 2] * 1.5); yy, xx = np.where(mask); return [float(xx.mean()), float(yy.mean())]
    lever_before, lever_after = red_centroid(roi_before), red_centroid(roi_after); check("lever_rotates_right_on_hinge", lever_after[0] - lever_before[0] > 50 and lever_after[1] - lever_before[1] > 40, {"before": lever_before, "after": lever_after, "delta": [lever_after[0] - lever_before[0], lever_after[1] - lever_before[1]]})
    gauge_roi = (slice(620, 760), slice(30, 285)); gauge_delta = float(np.abs(im(paths[52])[gauge_roi].astype(int) - im(paths[120])[gauge_roi].astype(int)).mean()); check("gauge_needles_respond", gauge_delta > .3, {"mean_region_delta": gauge_delta})
    def color_count(path, color):
        pixels = im(path)[900:1000, 20:285]
        if color == "blue": mask = (pixels[:, :, 2] > 70) & (pixels[:, :, 2] > pixels[:, :, 0] * 1.4)
        elif color == "green": mask = (pixels[:, :, 1] > 70) & (pixels[:, :, 1] > pixels[:, :, 0] * 1.3) & (pixels[:, :, 1] > pixels[:, :, 2] * 1.1)
        else: mask = (pixels[:, :, 0] > 100) & (pixels[:, :, 1] > 70) & (pixels[:, :, 2] < 90)
        return int(mask.sum())
    colors = {"blue": color_count(paths[108], "blue"), "green": color_count(paths[125], "green"), "yellow": color_count(paths[168], "yellow")}; check("blue_green_yellow_sequence", colors["blue"] > 200 and colors["green"] > 500 and colors["yellow"] > 250, colors)
    def bright_ring(path): return int((im(path)[280:430, 330:700].max(axis=2) > 130).sum())
    ring = {"pre": bright_ring(paths[171]), "post": bright_ring(paths[198])}; check("yellow_triggers_mounted_ring", ring["post"] > ring["pre"] + 2000, ring)
    def core_luma(path): return float(im(path)[450:850, 420:610].mean())
    energy = {"dormant": core_luma(paths[15]), "active": core_luma(paths[198]), "final": core_luma(paths[375])}; check("reactor_energy_intensifies_in_chamber", energy["dormant"] < energy["active"] < energy["final"] and energy["final"] > energy["dormant"] * 2, energy)
    def display_pixels(path): return int((im(path)[200:470, :285].max(axis=2) > 100).sum())
    display = {"before": display_pixels(paths[210]), "title": display_pixels(paths[240]), "cta": display_pixels(paths[270]), "url": display_pixels(paths[315])}; check("title_cta_url_reveal_sequence", display["before"] < display["title"] < display["cta"] < display["url"], display)

    expected_text = {"title": config["shared"]["title"], "cta": config["shared"]["cta"], "url": config["shared"]["display_url"]}; check("ab_content_identity", scene_contract["text"] == expected_text and manifest["ab_integrity"]["text"] == expected_text, expected_text)
    timing = json.loads((art / "validation/backend-timing.json").read_text()); check("semantic_timing_parity", timing["result"] == "PASS" and timing["maximum_delta_frames"] <= timing["tolerance_frames"] and timing["semantic_order_equal"] is True, timing)
    audio = json.loads((art / "validation/audio-selection.json").read_text()); check("ab_audio_identity", audio["result"] == "PASS" and audio["candidate_a_md5"] == audio["candidate_b_md5"] == audio_md5(candidate_a) == audio_md5(candidate_b) and audio["track_approval"] == audio["cue_approval"] == "APPROVED", audio)

    expected_media = {"video": "h264", "audio": "aac", "width": 768, "height": 1152, "fps": "30/1", "frames": 420, "duration": 14.0, "sample_rate": 48000}; media = {"candidate_a": probe(candidate_a), "candidate_b": probe(candidate_b), "comparison": probe(comparison)}
    check("candidate_media_parity", media["candidate_a"] == expected_media and media["candidate_b"] == expected_media, media)
    check("comparison_media_contract", media["comparison"] == {**expected_media, "width": 1536}, media["comparison"])
    decodes = {}; decode_ok = True
    for name, path in (("candidate_a", candidate_a), ("candidate_b", candidate_b), ("comparison", comparison)):
        process = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True); decodes[name] = process.returncode; decode_ok = decode_ok and process.returncode == 0
    check("full_media_decode", decode_ok, decodes)

    outputs_ok = True; output_hashes = {}
    for relative, expected in manifest["outputs"].items():
        path = art / relative; actual = sha256(path) if path.is_file() else None; output_hashes[relative] = actual; outputs_ok = outputs_ok and actual == expected["sha256"] and path.stat().st_size == expected["bytes"]
    check("artifact_integrity", outputs_ok, output_hashes)
    performance = json.loads((art / "validation/performance.json").read_text()); blender_perf = performance["candidate_b_blender"]; check("performance_evidence", performance["candidate_a_godot"]["recorded_total_ms"] > 0 and all(blender_perf[key] is not None and blender_perf[key] > 0 for key in ("preflight_ms", "scene_build_ms", "frame_render_ms", "finalization_ms", "recorded_total_ms", "artifact_bytes", "frame_storage_bytes", "peak_memory_kb")), performance)
    failures = json.loads((root / "reports/mf-019/failure-tests.json").read_text()); check("failure_tests", failures["result"] == "PASS" and failures["passed"] == failures["total"] == 13, failures)
    states = [json.loads(line)["state"] for line in (art / "logs/backend-status.jsonl").read_text().splitlines()]; expected_states = ["BACKEND_PREFLIGHT", "BUILDING_SCENE", "RENDERING_FRAMES", "VALIDATING_FRAMES", "FINALIZING", "READY_FOR_REVIEW"]; check("actionable_backend_status_model", states == expected_states, states)
    check("scope_and_human_gate", manifest["published"] is False and manifest["release_ready"] is False and manifest["human_backend_preference"] == "PENDING_HUMAN" and manifest["blender_to_godot_export_implemented"] is False and manifest["gameplay_implemented"] is False, {key: manifest[key] for key in ("published", "release_ready", "human_backend_preference", "blender_to_godot_export_implemented", "gameplay_implemented")})

    result = "TECHNICAL_PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"; report = {"slice": "MF-019", "result": result, "passed": sum(item["status"] == "PASS" for item in checks.values()), "total": len(checks), "human_backend_preference": "PENDING_HUMAN", "release_ready": False, "checks": checks, "published": False}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n"); print(json.dumps(report, indent=2)); return 0 if result == "TECHNICAL_PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
