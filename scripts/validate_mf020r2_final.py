#!/usr/bin/env python3
"""Final independent media and provenance gate for MF-020R2."""
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
    art = root / "artifacts/mf-020r2"
    config_path = root / "config/mf-bench-001.json"
    builder_path = root / "scripts/blender/build_mf_bench_001.py"
    template_path = root / "templates/blender/pulp-reactor-v1.blend"
    config = json.loads(config_path.read_text())
    alignment = json.loads((art / "validation/alignment.json").read_text())
    performance = json.loads((art / "validation/final-render-performance.json").read_text())
    contract = json.loads((art / "frames/scene-contract.json").read_text())
    video = art / "final-test.mp4"
    checks: list[dict] = []

    def check(name: str, passed: bool, evidence: object) -> None:
        checks.append({"name": name, "passed": bool(passed), "evidence": evidence})

    expected_fingerprint = {
        "config_sha256": sha256(config_path),
        "builder_sha256": sha256(builder_path),
        "template_sha256": sha256(template_path),
    }
    observed_fingerprints = [performance["render_fingerprint"], contract["render_fingerprint"]]
    fingerprint_ok = all(all(item.get(key) == value for key, value in expected_fingerprint.items()) for item in observed_fingerprints)
    check("immutable_render_fingerprint", fingerprint_ok, {"expected": expected_fingerprint, "performance": observed_fingerprints[0], "scene_contract": observed_fingerprints[1]})
    check("alignment_gate_precedes_final", alignment["result"] == "PASS" and alignment["checks_passed"] == alignment["checks_total"], {"result": alignment["result"], "passed": alignment["checks_passed"], "total": alignment["checks_total"]})

    frames = sorted((art / "frames").glob("frame-*.png"))
    frame_indices = [int(path.stem.split("-")[-1]) for path in frames]
    dimensions_ok = len(frames) == 600
    if dimensions_ok:
        for path in frames:
            with Image.open(path) as image:
                if list(image.size) != config["shot"]["resolution"]:
                    dimensions_ok = False
                    break
    check("complete_frame_sequence", dimensions_ok and frame_indices == list(range(600)) and performance["rendered"] == 600, {"count": len(frames), "first": frame_indices[0] if frame_indices else None, "last": frame_indices[-1] if frame_indices else None, "rendered": performance["rendered"]})

    probe_process = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], capture_output=True, text=True)
    probe = json.loads(probe_process.stdout) if probe_process.returncode == 0 else {}
    video_stream = next((item for item in probe.get("streams", []) if item.get("codec_type") == "video"), {})
    audio_stream = next((item for item in probe.get("streams", []) if item.get("codec_type") == "audio"), {})
    duration = float(probe.get("format", {}).get("duration", 0))
    media_ok = video_stream.get("codec_name") == "h264" and [video_stream.get("width"), video_stream.get("height")] == config["shot"]["resolution"] and video_stream.get("r_frame_rate") == "30/1" and int(video_stream.get("nb_frames", 0)) == 600 and abs(duration - 20.0) <= 0.01
    check("final_video_contract", media_ok, {"duration_seconds": duration, "codec": video_stream.get("codec_name"), "resolution": [video_stream.get("width"), video_stream.get("height")], "fps": video_stream.get("r_frame_rate"), "frames": video_stream.get("nb_frames")})
    audio_ok = audio_stream.get("codec_name") == "aac" and audio_stream.get("sample_rate") == "48000" and audio_stream.get("channels") == 2 and abs(float(audio_stream.get("duration", 0)) - 20.0) <= 0.01
    check("final_audio_stream", audio_ok, {"codec": audio_stream.get("codec_name"), "sample_rate": audio_stream.get("sample_rate"), "channels": audio_stream.get("channels"), "duration_seconds": audio_stream.get("duration")})
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
    check("full_decode", decode.returncode == 0 and not decode.stderr.strip(), {"returncode": decode.returncode, "stderr": decode.stderr.strip()})

    catalog = json.loads((root / config["audio"]["catalog"]).read_text())
    track = next((item for item in catalog["tracks"] if item["qualified_id"] == config["audio"]["qualified_id"]), None)
    cue = next((item for item in track["cue_regions"] if item["id"] == config["audio"]["cue_region"]), None) if track else None
    source = root / config["audio"]["source"]
    music_ok = bool(track and cue and track["approval"]["status"] == cue["approval"]["status"] == "APPROVED" and sha256(source) == config["audio"]["source_sha256"] == track["approval"]["approved_sha256"] and cue["usable_start"] <= config["audio"]["start_seconds"] < config["audio"]["end_seconds"] <= cue["usable_end"])
    check("approved_music_unchanged", music_ok, {"qualified_id": config["audio"]["qualified_id"], "cue": config["audio"]["cue_region"], "source_sha256": sha256(source), "offset": [config["audio"]["start_seconds"], config["audio"]["end_seconds"]]})

    loudness_text = (art / "validation/loudness.log").read_text()
    matches = re.findall(r'\{\s*"input_i".*?\}', loudness_text, re.S)
    loudness = json.loads(matches[-1]) if matches else {}
    integrated = float(loudness.get("input_i", 999))
    true_peak = float(loudness.get("input_tp", 999))
    check("bounded_audio_loudness", -18.0 <= integrated <= -15.5 and true_peak <= -1.5, {"integrated_lufs": integrated, "true_peak_db": true_peak})

    required_evidence = [art / "debug/lamp-arc-overlay.png", art / "debug/anchor-closeup.png", art / "proof/lamps-off.png", art / "proof/lamps-half.png", art / "proof/lamps-all.png", art / "comparison/before.png", art / "comparison/after.png"]
    evidence_ok = all(path.is_file() and path.stat().st_size > 1024 for path in required_evidence)
    check("review_evidence_complete", evidence_ok, [{"path": str(path.relative_to(root)), "sha256": sha256(path) if path.is_file() else None} for path in required_evidence])

    passed = all(item["passed"] for item in checks)
    result = {
        "slice": "MF-020R2",
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
