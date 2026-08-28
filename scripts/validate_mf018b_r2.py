#!/usr/bin/env python3
"""Independent validation for the two-change MF-018B-R2 cleanup."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from composition_contract import validate_manifest
from playable_scene_contract import sha256, validate_package


def media_probe(path: Path) -> dict:
    process = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        text=True,
    )
    data = json.loads(process.stdout) if process.returncode == 0 else {}
    video = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
    audio = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"), {})
    return {
        "video": video.get("codec_name"),
        "audio": audio.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": video.get("avg_frame_rate"),
        "frames": int(video.get("nb_read_frames", 0)),
        "duration": float(data.get("format", {}).get("duration", 0)),
        "sample_rate": int(audio.get("sample_rate", 0)) if audio else 0,
    }


def image(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def audio_md5(path: Path) -> str:
    process = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-c", "copy", "-f", "md5", "-"],
        capture_output=True,
        text=True,
    )
    return process.stdout.strip() if process.returncode == 0 else process.stderr.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    art = root / "artifacts/mf-018b-r2"
    config = json.loads((root / "config/mf018b-r2-cleanup.json").read_text())
    manifest = json.loads((art / "render-manifest.json").read_text())
    checks: dict[str, dict] = {}

    def check(name: str, passed: bool, detail) -> None:
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    baseline = config["baseline"]
    actual_baseline = {key: sha256(root / baseline[key]) for key in ("artifact", "scene", "config", "handoff")}
    expected_baseline = {key: baseline[f"{key}_sha256"] for key in actual_baseline}
    check("r1_baseline_preserved", actual_baseline == expected_baseline, actual_baseline)

    composition = validate_manifest(json.loads((root / config["composition_manifest"]).read_text()))
    check("composition_preserved", composition["result"] == "PASS" and all(value == "PASS" for value in composition["checks"].values()), composition)
    handoff_data = json.loads((root / config["handoff_manifest"]).read_text())
    handoff = validate_package(root, handoff_data)
    check("inherited_playable_handoff", handoff["result"] == "PASS" and manifest["inherited_handoff"]["interface_changed"] is False, handoff)

    probe_log = (art / "logs/base-scene-probe.log").read_text()
    expected_probe = "MF018B_R2_PROBE_OK preserved_nodes=4 removed_steam_lever=true signals=3 driver_loaded=false"
    check("standalone_scene_contract", expected_probe in probe_log and "ERROR:" not in probe_log and "SCRIPT ERROR:" not in probe_log, probe_log.strip())

    scene_text = (root / config["scene"]).read_text()
    source = (root / config["base_script"]).read_text()
    cleanup = config["cleanup_contract"]
    removal_tokens = ("M654 854 H710 V927", "M654 848 H710 V927", "cx='710' cy='931'")
    check(
        "right_machine_lever_removed",
        "SteamVent" not in scene_text and all(token in source for token in removal_tokens)
        and cleanup["right_machine_lever_present"] is False
        and cleanup["right_machine_steam_from_removed_lever_present"] is False,
        {"steam_vent_node": "SteamVent" in scene_text, "removal_tokens": list(removal_tokens)},
    )
    check(
        "panel_inner_outline_removed",
        "id='r2_control_panel_clean'" in source and "stroke='none'" in source and "M68 752 H219" in source
        and cleanup["control_panel_inner_outline_present"] is False,
        {"fill_preserved": True, "inner_outline": False, "redundant_top_border": False},
    )
    check(
        "no_replacement_props",
        cleanup["replacement_props_added"] == 0 and "No replacement prop is added" in source,
        cleanup["replacement_props_added"],
    )
    driver_hash = sha256(root / config["promo_driver"])
    check(
        "r1_driver_and_logic_unchanged",
        driver_hash == "1a4f744aebd1e660ea3bd1cc41874c5d0f9d9651f7e22fe7a04cd248773040a7"
        and cleanup["r1_promo_driver_reused"] is True
        and cleanup["r1_startup_timeline_changed"] is False
        and cleanup["r1_indicator_logic_changed"] is False
        and cleanup["r1_audio_logic_changed"] is False,
        {"driver_sha256": driver_hash, "cleanup_contract": cleanup},
    )

    pairs = [
        ("four-dot-blue", "startup-panel-active"),
        ("four-dot-yellow-trigger", "yellow-trigger-preserved"),
        ("linked-ring-activating", "linked-ring-preserved"),
        ("strong-active-machine", "final-active-machine"),
    ]
    localization = {}
    all_localized = True
    both_targets_changed = True
    for r1_name, r2_name in pairs:
        r1 = image(root / "artifacts/mf-018b-r1/representative-frames" / f"{r1_name}.png")
        r2 = image(art / "representative-frames" / f"{r2_name}.png")
        changed = np.any(r1 != r2, axis=2)
        allowed = np.zeros(changed.shape, dtype=bool)
        allowed[700:1005, 40:270] = True
        allowed[680:1010, 610:768] = True
        outside = int((changed & ~allowed).sum())
        panel = int(changed[700:1005, 40:270].sum())
        right = int(changed[680:1010, 610:768].sum())
        localization[f"{r1_name}_to_{r2_name}"] = {"changed_pixels": int(changed.sum()), "panel": panel, "right_machine": right, "outside_allowed_regions": outside}
        all_localized = all_localized and outside == 0
        both_targets_changed = both_targets_changed and panel > 500 and right > 500
    check("pixel_changes_localized_to_two_cleanup_zones", all_localized, localization)
    check("both_requested_cleanup_zones_materially_changed", both_targets_changed, localization)

    # These preserved regions sit wholly outside the two allowed edit zones.
    r1_blue = image(root / "artifacts/mf-018b-r1/representative-frames/four-dot-blue.png")
    r2_blue = image(art / "representative-frames/startup-panel-active.png")
    r1_yellow = image(root / "artifacts/mf-018b-r1/representative-frames/four-dot-yellow-trigger.png")
    r2_yellow = image(art / "representative-frames/yellow-trigger-preserved.png")
    r1_linked = image(root / "artifacts/mf-018b-r1/representative-frames/linked-ring-activating.png")
    r2_linked = image(art / "representative-frames/linked-ring-preserved.png")
    gauges = (slice(580, 735), slice(35, 270))
    ring = (slice(160, 390), slice(320, 740))
    preserved_deltas = {
        "gauges_blue_stage": int(np.any(r1_blue[gauges] != r2_blue[gauges], axis=2).sum()),
        "upper_ring_yellow_trigger": int(np.any(r1_yellow[ring] != r2_yellow[ring], axis=2).sum()),
        "upper_ring_linked_stage": int(np.any(r1_linked[ring] != r2_linked[ring], axis=2).sum()),
    }
    check("gauges_and_linked_ring_pixels_preserved", all(value == 0 for value in preserved_deltas.values()), preserved_deltas)

    outputs_ok = True
    hashes = {}
    for relative, expected in manifest["outputs"].items():
        path = art / relative
        actual_hash = sha256(path) if path.is_file() else None
        actual_bytes = path.stat().st_size if path.is_file() else None
        hashes[relative] = actual_hash
        outputs_ok = outputs_ok and actual_hash == expected["sha256"] and actual_bytes == expected["bytes"]
    check("artifact_integrity", outputs_ok, hashes)

    media = media_probe(art / "final-test.mp4")
    expected_media = {"video": "h264", "audio": "aac", "width": 768, "height": 1152, "fps": "30/1", "frames": 420, "duration": 14.0, "sample_rate": 48000}
    check("promo_media_contract", media == expected_media, media)
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(art / "final-test.mp4"), "-f", "null", "-"], capture_output=True)
    check("full_decode", decode.returncode == 0, decode.stderr.decode()[-1000:])
    comparison = media_probe(art / "comparison/r1-vs-r2.mp4")
    check("comparison_media", comparison["video"] == "h264" and comparison["width"] == 1536 and comparison["height"] == 1152 and comparison["frames"] == 240 and comparison["duration"] == 8.0, comparison)

    evidence = {
        "representative_frames": len(list((art / "representative-frames").glob("*.png"))) - 1,
        "closeups": len(list((art / "closeups").glob("*.png"))),
        "contact_sheet": (art / "representative-frames/contact-sheet.png").is_file(),
        "static_comparison": (art / "comparison/r1-vs-r2.png").is_file(),
    }
    check("evidence_complete", evidence == {"representative_frames": 5, "closeups": 3, "contact_sheet": True, "static_comparison": True}, evidence)

    audio = manifest["audio"]
    audio_hashes = {"r1": audio_md5(root / baseline["artifact"]), "r2": audio_md5(art / "final-test.mp4")}
    check(
        "approved_audio_bitstream_unchanged",
        audio["track_approval"] == audio["cue_approval"] == "APPROVED"
        and audio["changed_from_r1"] is False
        and audio["track_sha256"] == config["audio"]["source_sha256"]
        and audio_hashes["r1"] == audio_hashes["r2"],
        audio_hashes,
    )
    levels = audio["loudness"]
    check("audio_levels", abs(levels["integrated_lufs"] + 16) <= 0.75 and levels["true_peak_db"] <= -1.4, levels)

    render_log = (art / "logs/godot-render.log").read_text()
    check("clean_native_render", "MF018B_R2_NATIVE_OK frames=420" in render_log and "ERROR:" not in render_log and "SCRIPT ERROR:" not in render_log, render_log.strip())
    check(
        "no_gameplay_publication_or_release_claim",
        manifest["gameplay_implemented"] is False and manifest["published"] is False
        and manifest["release_ready"] is False and manifest["human_review"] == "PENDING_HUMAN",
        {key: manifest[key] for key in ("gameplay_implemented", "published", "release_ready", "human_review")},
    )

    result = "TECHNICAL_PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"
    report = {
        "slice": "MF-018B-R2",
        "result": result,
        "passed": sum(item["status"] == "PASS" for item in checks.values()),
        "total": len(checks),
        "release_ready": False,
        "human_review": "PENDING_HUMAN",
        "checks": checks,
        "published": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if result == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
