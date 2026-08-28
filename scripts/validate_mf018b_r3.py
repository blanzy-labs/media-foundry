#!/usr/bin/env python3
"""Independent validation for MF-018B-R3 display and cleanup refinement."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from composition_contract import validate_manifest
from playable_scene_contract import sha256, validate_package


def image(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def media_probe(path: Path) -> dict:
    process = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    data = json.loads(process.stdout) if process.returncode == 0 else {}
    video = next((item for item in data.get("streams", []) if item.get("codec_type") == "video"), {})
    audio = next((item for item in data.get("streams", []) if item.get("codec_type") == "audio"), {})
    return {"video": video.get("codec_name"), "audio": audio.get("codec_name"), "width": video.get("width"), "height": video.get("height"), "fps": video.get("avg_frame_rate"), "frames": int(video.get("nb_read_frames", 0)), "duration": float(data.get("format", {}).get("duration", 0)), "sample_rate": int(audio.get("sample_rate", 0)) if audio else 0}


def audio_md5(path: Path) -> str:
    process = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-c", "copy", "-f", "md5", "-"], capture_output=True, text=True)
    return process.stdout.strip() if process.returncode == 0 else process.stderr.strip()


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve(); art = root / "artifacts/mf-018b-r3"
    config = json.loads((root / "config/mf018b-r3-display-cleanup.json").read_text()); manifest = json.loads((art / "render-manifest.json").read_text()); checks = {}
    def check(name, passed, detail): checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    baseline = config["baseline"]
    actual_baseline = {key: sha256(root / baseline[key]) for key in ("artifact", "scene", "script", "config", "manifest", "evidence", "handoff")}
    expected_baseline = {key: baseline[f"{key}_sha256"] for key in actual_baseline}
    check("r2_baseline_preserved", actual_baseline == expected_baseline, actual_baseline)

    composition = validate_manifest(json.loads((root / config["composition_manifest"]).read_text()))
    check("composition_preserved", composition["result"] == "PASS" and all(value == "PASS" for value in composition["checks"].values()), composition)
    handoff = validate_package(root, json.loads((root / config["handoff_manifest"]).read_text()))
    check("playable_ready_interface_preserved", handoff["result"] == "PASS" and manifest["inherited_handoff"]["interface_changed"] is False, handoff)

    log = (art / "logs/base-scene-probe.log").read_text()
    marker = "MF018B_R3_PROBE_OK preserved_nodes=4 information_display=true copy=3 outline=complete l_artifact=false signals=3 driver_loaded=false"
    check("standalone_scene_contract", marker in log and "ERROR:" not in log and "SCRIPT ERROR:" not in log, log.strip())

    source = (root / config["base_script"]).read_text(); scene = (root / config["scene"]).read_text(); display = config["display_contract"]; cleanup = config["cleanup_contract"]
    metadata = json.loads((root / display["metadata_source"]).read_text())
    metadata_values = {"title": metadata["subject"]["title"], "display_url": metadata["cta"]["display_url"], "canonical_url": metadata["cta"]["canonical_url"]}
    check("approved_title_and_url", metadata_values == {"title": "Unknown Process", "display_url": display["display_url"], "canonical_url": display["canonical_url"]}, metadata_values)
    check("required_copy_declared", display["title"] == "UNKNOWN PROCESS" and display["cta"] == "TRY A WEB GAME" and display["display_url"] == "rcblanzy.com/books/unknown-process" and all(value in source for value in ("UNKNOWN PROCESS", "TRY A WEB GAME", "rcblanzy.com/books/unknown-process")), display)
    check("in_world_display_node_and_style", "InformationDisplay" in scene and "r3_information_display" in source and "_pixel_text" in source and display["style"] == "in_world_monospaced_machine_display", {"node": display["node"], "bounds": display["panel_bounds"], "style": display["style"]})
    timing = [display[key] for key in ("title_start", "cta_start", "url_start")]
    check("readable_display_timing", timing == sorted(timing) and len(set(timing)) == 3 and display["minimum_full_copy_hold_seconds"] >= 3.5, {"starts": timing, "full_hold_seconds": display["minimum_full_copy_hold_seconds"]})

    frames = {name: image(art / "representative-frames" / f"{name}.png") for _, name in config["representative_frames"]}
    panel_roi = (slice(150, 420), slice(25, 255)); dormant = frames["clean-dormant-scene"]
    stage_deltas = {name: int(np.any(frames[name][panel_roi] != dormant[panel_roi], axis=2).sum()) for name in ("book-title-reveal", "web-game-cta-reveal", "full-panel-active")}
    check("sequential_panel_reveal", stage_deltas["book-title-reveal"] < stage_deltas["web-game-cta-reveal"] < stage_deltas["full-panel-active"], stage_deltas)
    active = frames["full-panel-active"]
    readable_counts = {}
    for name, roi in {"title": (slice(195, 275), slice(45, 240)), "cta": (slice(285, 320), slice(45, 240)), "url": (slice(320, 370), slice(45, 240))}.items():
        pixels = active[roi]; mask = (pixels.max(axis=2) > 130) & ((pixels.max(axis=2) - pixels.min(axis=2)) > 20); readable_counts[name] = int(mask.sum())
    check("panel_copy_has_readable_contrast", readable_counts["title"] > 2000 and readable_counts["cta"] > 600 and readable_counts["url"] > 900, readable_counts)

    outline_path = "M51 613 L228 575 L245 625 L240 946 L52 982 Z"
    check("control_panel_outline_complete", "r3_complete_control_outline" in source and outline_path in source and cleanup["overall_sloped_control_outline_complete"] is True and cleanup["r2_lower_rectangular_outline_restored"] is False, {"path": outline_path, "closed": True, "lower_r2_rectangle_restored": False})
    l_tokens = ("M398 389 H356 Q334 389 334 367 V315", "M398 384 H356 Q340 384 340 367 V315")
    check("l_shaped_artifact_removed", all(token in source for token in l_tokens) and cleanup["l_shaped_reactor_pipe_present"] is False and cleanup["replacement_props_added"] == 0, {"removed_paths": list(l_tokens), "replacements": cleanup["replacement_props_added"]})

    r2_dormant = image(root / "artifacts/mf-018b-r2/representative-frames/full-scene-cleanup.png"); r2_active = image(root / "artifacts/mf-018b-r2/representative-frames/final-active-machine.png")
    localizations = {}; localized = True
    for label, old, new in (("dormant", r2_dormant, dormant), ("active", r2_active, active)):
        changed = np.any(old != new, axis=2); allowed = np.zeros(changed.shape, dtype=bool)
        allowed[130:440, 15:270] = True; allowed[540:1010, 35:270] = True; allowed[280:440, 300:425] = True
        detail = {"total": int(changed.sum()), "display": int(changed[130:440, 15:270].sum()), "control_outline": int(changed[540:1010, 35:270].sum()), "artifact_zone": int(changed[280:440, 300:425].sum()), "outside_allowed_regions": int((changed & ~allowed).sum())}
        localizations[label] = detail; localized = localized and detail["outside_allowed_regions"] == 0 and min(detail["display"], detail["control_outline"], detail["artifact_zone"]) > 500
    check("visual_changes_localized_to_requested_regions", localized, localizations)

    preserved_rois = {"gauges": (slice(620, 735), slice(55, 230)), "dials": (slice(775, 835), slice(60, 205)), "startup_lever": (slice(830, 895), slice(145, 225)), "chamber": (slice(430, 810), slice(430, 625)), "upper_ring": (slice(160, 300), slice(420, 740))}
    preserved_deltas = {name: int(np.any(r2_active[roi] != active[roi], axis=2).sum()) for name, roi in preserved_rois.items()}
    yy, xx = np.ogrid[:1152, :768]; changed_active = np.any(r2_active != active, axis=2)
    dot_deltas = [int(changed_active[((xx - center) ** 2 + (yy - 921) ** 2) <= 12 ** 2].sum()) for center in (70, 116, 162, 208)]
    check("approved_machine_content_pixel_preserved", all(value == 0 for value in preserved_deltas.values()) and dot_deltas == [0, 0, 0, 0], {"regions": preserved_deltas, "four_dots": dot_deltas})
    driver_hash = sha256(root / config["promo_driver"])
    check("startup_indicator_and_motion_logic_preserved", driver_hash == "1a4f744aebd1e660ea3bd1cc41874c5d0f9d9651f7e22fe7a04cd248773040a7" and all(cleanup[key] is False for key in ("startup_logic_changed", "indicator_logic_changed")), {"driver_sha256": driver_hash, "cleanup": cleanup})

    outputs_ok = True; output_hashes = {}
    for relative, expected in manifest["outputs"].items():
        path = art / relative; actual_hash = sha256(path) if path.is_file() else None; actual_size = path.stat().st_size if path.is_file() else None
        output_hashes[relative] = actual_hash; outputs_ok = outputs_ok and actual_hash == expected["sha256"] and actual_size == expected["bytes"]
    check("artifact_integrity", outputs_ok, output_hashes)
    media = media_probe(art / "final-test.mp4")
    check("promo_media_contract", media == {"video": "h264", "audio": "aac", "width": 768, "height": 1152, "fps": "30/1", "frames": 420, "duration": 14.0, "sample_rate": 48000}, media)
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(art / "final-test.mp4"), "-f", "null", "-"], capture_output=True)
    check("full_decode", decode.returncode == 0, decode.stderr.decode()[-1000:])
    comparison = media_probe(art / "comparison/r2-vs-r3.mp4")
    check("comparison_media", comparison["video"] == "h264" and comparison["width"] == 1536 and comparison["height"] == 1152 and comparison["frames"] == 240 and comparison["duration"] == 8.0, comparison)
    evidence = {"representative": len(frames), "closeups": len(list((art / "closeups").glob("*.png"))), "contact_sheet": (art / "representative-frames/contact-sheet.png").is_file(), "static_comparison": (art / "comparison/r2-vs-r3.png").is_file()}
    check("representative_evidence_complete", evidence == {"representative": 5, "closeups": 3, "contact_sheet": True, "static_comparison": True}, evidence)

    audio = manifest["audio"]; audio_hashes = {"r2": audio_md5(root / baseline["artifact"]), "r3": audio_md5(art / "final-test.mp4")}
    check("approved_audio_unchanged", audio["track_approval"] == audio["cue_approval"] == "APPROVED" and audio["changed_from_r2"] is False and audio["additional_cue_added"] is False and audio_hashes["r2"] == audio_hashes["r3"], audio_hashes)
    levels = audio["loudness"]; check("audio_levels", abs(levels["integrated_lufs"] + 16) <= .75 and levels["true_peak_db"] <= -1.4, levels)
    render_log = (art / "logs/godot-render.log").read_text(); check("clean_native_render", "MF018B_R3_NATIVE_OK frames=420" in render_log and "ERROR:" not in render_log and "SCRIPT ERROR:" not in render_log, render_log.strip())
    check("no_gameplay_publication_or_release_claim", manifest["gameplay_implemented"] is False and manifest["published"] is False and manifest["release_ready"] is False and manifest["human_review"] == "PENDING_HUMAN", {key: manifest[key] for key in ("gameplay_implemented", "published", "release_ready", "human_review")})

    result = "TECHNICAL_PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"
    report = {"slice": "MF-018B-R3", "result": result, "passed": sum(item["status"] == "PASS" for item in checks.values()), "total": len(checks), "release_ready": False, "human_review": "PENDING_HUMAN", "checks": checks, "published": False}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n"); print(json.dumps(report, indent=2))
    return 0 if result == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
