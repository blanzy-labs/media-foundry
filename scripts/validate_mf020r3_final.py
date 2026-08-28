#!/usr/bin/env python3
"""Final fail-closed media gate for MF-020R3."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    art = root / "artifacts/mf-020r3"
    focus_path = root / "config/mf-020r3-dormant-lighting.json"
    base_path = root / "config/mf-bench-001.json"
    builder_path = root / "scripts/blender/build_mf_bench_001.py"
    template_path = root / "templates/blender/pulp-reactor-v1.blend"
    focus = json.loads(focus_path.read_text())
    base = json.loads(base_path.read_text())
    lighting_gate = json.loads((art / "validation/lighting-and-invariants.json").read_text())
    composition_gate = json.loads((art / "validation/composition.json").read_text())
    performance = json.loads((art / "validation/final-render-performance.json").read_text())
    final_contract = json.loads((art / "frames/scene-contract.json").read_text())
    baseline_contract = json.loads((root / "artifacts/mf-020r2/proof/scene-contract.json").read_text())
    video = art / "final-test.mp4"
    checks: list[dict] = []

    def check(name: str, passed: bool, evidence: object) -> None:
        checks.append({"name": name, "passed": bool(passed), "evidence": evidence})

    check("pre_render_gates", lighting_gate["result"] == "PASS" and lighting_gate["checks_passed"] == lighting_gate["checks_total"] and composition_gate["result"] == "STATIC_TECHNICAL_PASS" and composition_gate["passed"] == composition_gate["total"], {"lighting": {"result": lighting_gate["result"], "passed": lighting_gate["checks_passed"], "total": lighting_gate["checks_total"]}, "composition": {"result": composition_gate["result"], "state": composition_gate["state"], "passed": composition_gate["passed"], "total": composition_gate["total"]}})

    expected_fingerprint = {"config_sha256": sha256(focus_path), "base_config_sha256": sha256(base_path), "builder_sha256": sha256(builder_path), "template_sha256": sha256(template_path)}
    observed = [performance["render_fingerprint"], final_contract["render_fingerprint"]]
    fingerprint_ok = all(all(item.get(key) == value for key, value in expected_fingerprint.items()) for item in observed)
    check("immutable_render_fingerprint", fingerprint_ok and focus["frozen_invariants"]["base_manifest_sha256"] == sha256(base_path), {"expected": expected_fingerprint, "performance": observed[0], "scene_contract": observed[1]})

    lamp_keys = ("placement", "hierarchy", "master_geometry", "records", "spacing", "maximum_radial_deviation", "overlap_count", "protected_detail_intersection_count", "maximum_glow_anchor_delta", "position_samples", "maximum_position_drift", "placement_animation_channels", "screen_space_offsets", "per_lamp_manual_offsets")
    lamp_differences = [key for key in lamp_keys if baseline_contract["upper_ring_lamps"][key] != final_contract["upper_ring_lamps"][key]]
    check("final_r2_lamp_alignment_preserved", not lamp_differences, {"differences": lamp_differences})
    check("final_camera_text_causality_preserved", baseline_contract["camera"] == final_contract["camera"] and baseline_contract["text"] == final_contract["text"] and baseline_contract["causality"] == final_contract["causality"], {"camera": final_contract["camera"], "text": final_contract["text"], "causality": final_contract["causality"]})

    frames = sorted((art / "frames").glob("frame-*.png"))
    indices = [int(path.stem.split("-")[-1]) for path in frames]
    dimensions_ok = len(frames) == 600
    if dimensions_ok:
        for path in frames:
            with Image.open(path) as image:
                if list(image.size) != base["shot"]["resolution"]:
                    dimensions_ok = False
                    break
    check("complete_frame_sequence", dimensions_ok and indices == list(range(600)) and performance["rendered"] == 600, {"count": len(frames), "first": indices[0] if indices else None, "last": indices[-1] if indices else None, "rendered": performance["rendered"]})

    probe_process = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], capture_output=True, text=True)
    probe = json.loads(probe_process.stdout) if probe_process.returncode == 0 else {}
    video_stream = next((item for item in probe.get("streams", []) if item.get("codec_type") == "video"), {})
    audio_stream = next((item for item in probe.get("streams", []) if item.get("codec_type") == "audio"), {})
    duration = float(probe.get("format", {}).get("duration", 0))
    media_ok = video_stream.get("codec_name") == "h264" and [video_stream.get("width"), video_stream.get("height")] == base["shot"]["resolution"] and video_stream.get("r_frame_rate") == "30/1" and int(video_stream.get("nb_frames", 0)) == 600 and abs(duration - 20.0) <= 0.01
    check("final_video_contract", media_ok, {"duration_seconds": duration, "codec": video_stream.get("codec_name"), "resolution": [video_stream.get("width"), video_stream.get("height")], "fps": video_stream.get("r_frame_rate"), "frames": video_stream.get("nb_frames")})
    audio_ok = audio_stream.get("codec_name") == "aac" and audio_stream.get("sample_rate") == "48000" and audio_stream.get("channels") == 2 and abs(float(audio_stream.get("duration", 0)) - 20.0) <= 0.01
    baseline_audio = (art / "validation/baseline-audio-essence.md5").read_text().strip()
    refined_audio = (art / "validation/refined-audio-essence.md5").read_text().strip()
    check("audio_unchanged", audio_ok and baseline_audio == refined_audio, {"codec": audio_stream.get("codec_name"), "sample_rate": audio_stream.get("sample_rate"), "channels": audio_stream.get("channels"), "baseline_essence": baseline_audio, "refined_essence": refined_audio})
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
    check("full_decode", decode.returncode == 0 and not decode.stderr.strip(), {"returncode": decode.returncode, "stderr": decode.stderr.strip()})

    loudness_text = (art / "validation/loudness.log").read_text()
    matches = re.findall(r'\{\s*"input_i".*?\}', loudness_text, re.S)
    loudness = json.loads(matches[-1]) if matches else {}
    integrated = float(loudness.get("input_i", 999))
    true_peak = float(loudness.get("input_tp", 999))
    check("audio_loudness_preserved", -18.0 <= integrated <= -15.5 and true_peak <= -1.5, {"integrated_lufs": integrated, "true_peak_db": true_peak})

    evidence_paths = [art / "proof/dormant.png", art / "proof/startup.png", art / "proof/mid-active.png", art / "proof/peak.png", art / "comparison/before-dormant.png", art / "comparison/after-dormant.png", art / "comparison/before-after-dormant.png", art / "representative-frames/contact-sheet.png"]
    check("review_evidence_complete", all(path.is_file() and path.stat().st_size > 1024 for path in evidence_paths), [{"path": str(path.relative_to(root)), "sha256": sha256(path) if path.is_file() else None} for path in evidence_paths])

    passed = all(item["passed"] for item in checks)
    result = {
        "slice": "MF-020R3",
        "result": "PASS" if passed else "FAIL",
        "technical_state": "READY_FOR_HUMAN_REVIEW" if passed else "TECHNICAL_FAILURE",
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_total": len(checks),
        "checks": checks,
        "artifact": {"path": str(video.relative_to(root)), "sha256": sha256(video) if video.is_file() else None, "bytes": video.stat().st_size if video.is_file() else None},
        "human_review": "PENDING_HUMAN",
        "release_ready": False,
        "published": False
    }
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
