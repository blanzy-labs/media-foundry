#!/usr/bin/env python3
"""Independent validation for the narrow MF-018B-R4 outline polish."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

from composition_contract import validate_manifest
from playable_scene_contract import sha256, validate_package
from validate_mf018b_r3 import audio_md5, image, media_probe


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve(); art = root / "artifacts/mf-018b-r4"
    config = json.loads((root / "config/mf018b-r4-outline-polish.json").read_text()); manifest = json.loads((art / "render-manifest.json").read_text()); checks = {}
    def check(name, passed, detail): checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    baseline = config["baseline"]; actual_baseline = {key: sha256(root / baseline[key]) for key in ("artifact", "scene", "script", "config", "manifest", "evidence", "handoff")}; expected_baseline = {key: baseline[f"{key}_sha256"] for key in actual_baseline}
    check("r3_baseline_preserved", actual_baseline == expected_baseline, actual_baseline)
    composition = validate_manifest(json.loads((root / config["composition_manifest"]).read_text()))
    check("composition_preserved", composition["result"] == "PASS" and all(value == "PASS" for value in composition["checks"].values()), composition)
    handoff = validate_package(root, json.loads((root / config["handoff_manifest"]).read_text()))
    check("playable_ready_interface_preserved", handoff["result"] == "PASS" and manifest["inherited_handoff"]["interface_changed"] is False, handoff)
    probe_log = (art / "logs/base-scene-probe.log").read_text(); probe_marker = "MF018B_R4_PROBE_OK preserved_nodes=5 legacy_outline=false clean_perimeter=1 display_copy=3 signals=3 driver_loaded=false"
    check("standalone_scene_contract", probe_marker in probe_log and "ERROR:" not in probe_log and "SCRIPT ERROR:" not in probe_log, probe_log.strip())

    source = (root / config["base_script"]).read_text(); outline = config["outline_contract"]
    legacy = "M51 613 L228 575 L245 625 L235 927 L52 964 Z' fill='#0a1a17' stroke='#40756a' stroke-width='3'"
    check("legacy_partial_outline_suppressed", legacy in source and "r4_panel_face_fill" in source and outline["legacy_partial_perimeter_present"] is False, {"legacy_stroke_present_in_output": False, "face_fill_preserved": True})
    check("single_clean_perimeter_preserved", outline["clean_perimeter_count"] == 1 and outline["clean_perimeter_closed"] is True and outline["clean_perimeter_path"] in (root / "godot/mf018b_r3_pulp_scene.gd").read_text(), outline)
    check("panel_identity_contract", outline["panel_shape_changed"] is False and outline["internal_controls_changed"] is False and outline["replacement_props_added"] == 0, outline)

    frames = {name: image(art / "representative-frames" / f"{name}.png") for _, name in config["representative_frames"]}
    pairs = [
        ("dormant", image(root / "artifacts/mf-018b-r3/representative-frames/clean-dormant-scene.png"), frames["full-scene-polished"]),
        ("active", image(root / "artifacts/mf-018b-r3/representative-frames/full-panel-active.png"), frames["clean-outline-active"]),
        ("final", image(root / "artifacts/mf-018b-r3/representative-frames/final-active-machine-with-cta.png"), frames["final-active-machine"]),
    ]
    localization = {}; localized = True
    for label, old, new in pairs:
        changed = np.any(old != new, axis=2); allowed = np.zeros(changed.shape, dtype=bool); allowed[565:985, 35:255] = True
        ys, xs = np.where(changed); detail = {"changed_pixels": int(changed.sum()), "outside_outline_region": int((changed & ~allowed).sum()), "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}
        localization[label] = detail; localized = localized and detail["outside_outline_region"] == 0 and detail["changed_pixels"] > 1500
    check("changes_strictly_localized_to_panel_outline", localized, localization)

    r3_active, r4_active = pairs[1][1], pairs[1][2]; roi = (slice(565, 985), slice(35, 255))
    def teal_count(frame):
        pixels = frame[roi]; mask = (pixels[:, :, 1] > 55) & (pixels[:, :, 1] > pixels[:, :, 0] * 1.25) & (pixels[:, :, 1] >= pixels[:, :, 2] * .9); return int(mask.sum())
    teal = {"r3": teal_count(r3_active), "r4": teal_count(r4_active)}
    check("doubled_teal_linework_reduced", teal["r3"] - teal["r4"] > 1500, {**teal, "reduction": teal["r3"] - teal["r4"]})

    preserved_rois = {"gauges": (slice(620, 735), slice(55, 230)), "dials": (slice(775, 835), slice(60, 205)), "startup_lever": (slice(830, 895), slice(145, 225)), "information_display": (slice(150, 420), slice(25, 255)), "reactor": (slice(150, 1030), slice(320, 750))}
    preserved_deltas = {name: int(np.any(r3_active[region] != r4_active[region], axis=2).sum()) for name, region in preserved_rois.items()}
    yy, xx = np.ogrid[:1152, :768]; changed_active = np.any(r3_active != r4_active, axis=2); dot_deltas = [int(changed_active[((xx - center) ** 2 + (yy - 921) ** 2) <= 12 ** 2].sum()) for center in (70, 116, 162, 208)]
    check("internal_controls_display_and_reactor_preserved", all(value == 0 for value in preserved_deltas.values()) and dot_deltas == [0, 0, 0, 0], {"regions": preserved_deltas, "four_dots": dot_deltas})

    preservation = config["preservation_contract"]; driver_hash = sha256(root / config["promo_driver"])
    check("startup_indicator_reactor_logic_preserved", driver_hash == "1a4f744aebd1e660ea3bd1cc41874c5d0f9d9651f7e22fe7a04cd248773040a7" and all(preservation[key] is False for key in ("startup_logic_changed", "indicator_logic_changed", "reactor_behavior_changed", "information_display_changed", "audio_changed")), {"driver_sha256": driver_hash, "preservation": preservation})

    outputs_ok = True; hashes = {}
    for relative, expected in manifest["outputs"].items():
        path = art / relative; actual_hash = sha256(path) if path.is_file() else None; actual_size = path.stat().st_size if path.is_file() else None; hashes[relative] = actual_hash; outputs_ok = outputs_ok and actual_hash == expected["sha256"] and actual_size == expected["bytes"]
    check("artifact_integrity", outputs_ok, hashes)
    media = media_probe(art / "final-test.mp4"); check("promo_media_contract", media == {"video": "h264", "audio": "aac", "width": 768, "height": 1152, "fps": "30/1", "frames": 420, "duration": 14.0, "sample_rate": 48000}, media)
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(art / "final-test.mp4"), "-f", "null", "-"], capture_output=True); check("full_decode", decode.returncode == 0, decode.stderr.decode()[-1000:])
    comparison = media_probe(art / "comparison/r3-vs-r4.mp4"); check("comparison_media", comparison["video"] == "h264" and comparison["width"] == 1536 and comparison["height"] == 1152 and comparison["frames"] == 240 and comparison["duration"] == 8.0, comparison)
    evidence = {"representative": len(frames), "closeups": len(list((art / "closeups").glob("*.png"))), "contact_sheet": (art / "representative-frames/contact-sheet.png").is_file(), "panel_before_after": (art / "comparison/r3-vs-r4-panel-closeup.png").is_file()}
    check("representative_evidence_complete", evidence == {"representative": 5, "closeups": 3, "contact_sheet": True, "panel_before_after": True}, evidence)

    audio = manifest["audio"]; audio_hashes = {"r3": audio_md5(root / baseline["artifact"]), "r4": audio_md5(art / "final-test.mp4")}
    check("approved_audio_unchanged", audio["track_approval"] == audio["cue_approval"] == "APPROVED" and audio["changed_from_r3"] is False and audio_hashes["r3"] == audio_hashes["r4"], audio_hashes)
    levels = audio["loudness"]; check("audio_levels", abs(levels["integrated_lufs"] + 16) <= .75 and levels["true_peak_db"] <= -1.4, levels)
    render_log = (art / "logs/godot-render.log").read_text(); check("clean_native_render", "MF018B_R4_NATIVE_OK frames=420" in render_log and "ERROR:" not in render_log and "SCRIPT ERROR:" not in render_log, render_log.strip())
    check("no_gameplay_publication_or_release_claim", manifest["gameplay_implemented"] is False and manifest["published"] is False and manifest["release_ready"] is False and manifest["human_review"] == "PENDING_HUMAN", {key: manifest[key] for key in ("gameplay_implemented", "published", "release_ready", "human_review")})

    result = "TECHNICAL_PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"; report = {"slice": "MF-018B-R4", "result": result, "passed": sum(item["status"] == "PASS" for item in checks.values()), "total": len(checks), "release_ready": False, "human_review": "PENDING_HUMAN", "checks": checks, "published": False}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n"); print(json.dumps(report, indent=2)); return 0 if result == "TECHNICAL_PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
