#!/usr/bin/env python3
"""Independent fail-closed validation for the MF-014 rendered candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def check(state: dict, name: str, passed: bool, detail: object) -> None:
    state[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source, artifacts, output = Path(args.source).resolve(), Path(args.artifacts).resolve(), Path(args.output).resolve()
    video = artifacts / "final-test.mp4"
    manifest_path = artifacts / "render-manifest.json"
    checks: dict = {}
    check(checks, "source_present", source.is_file(), str(source))
    check(checks, "video_present", video.is_file() and video.stat().st_size > 0, str(video))
    check(checks, "manifest_present", manifest_path.is_file(), str(manifest_path))
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    check(checks, "source_identity", bool(source.is_file() and manifest.get("source", {}).get("sha256") == sha256(source)), manifest.get("source", {}).get("sha256"))
    probe_process = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], capture_output=True, text=True)
    probe = json.loads(probe_process.stdout) if probe_process.returncode == 0 else {}
    streams = probe.get("streams", [])
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
    duration = float(probe.get("format", {}).get("duration", 0.0) or 0.0)
    check(checks, "duration", 8.99 <= duration <= 9.01, duration)
    check(checks, "codec", video_stream.get("codec_name") == "h264", video_stream.get("codec_name", "missing"))
    check(checks, "portrait", int(video_stream.get("height", 0)) > int(video_stream.get("width", 0)), f"{video_stream.get('width')}x{video_stream.get('height')}")
    check(checks, "frame_count", int(video_stream.get("nb_frames", 0)) == 270, int(video_stream.get("nb_frames", 0)))
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
    check(checks, "full_decode", decode.returncode == 0, "full decode succeeded" if decode.returncode == 0 else decode.stderr[-300:])
    names = ("idle", "ignition", "active-burn", "title-interaction", "settled")
    frames = {name: artifacts / "representative-frames" / f"{name}.png" for name in names}
    check(checks, "representative_frames", all(path.is_file() for path in frames.values()), [str(path) for path in frames.values()])
    metrics = {}
    if all(path.is_file() for path in frames.values()):
        arrays = {name: np.asarray(Image.open(path).convert("RGB"), dtype=np.int16) for name, path in frames.items()}
        idle = arrays["idle"]
        source_image = Image.open(source).convert("RGB")
        expected_height = round(source_image.height * idle.shape[1] / source_image.width)
        if expected_height % 2:
            expected_height += 1
        expected_idle = np.asarray(source_image.resize((idle.shape[1], expected_height), Image.Resampling.LANCZOS), dtype=np.int16)
        check(checks, "idle_base_pixel_identity", expected_idle.shape == idle.shape and np.array_equal(expected_idle, idle),
              {"expected_shape": list(expected_idle.shape), "actual_shape": list(idle.shape)})
        for name in names[1:]:
            delta = np.abs(arrays[name] - idle)
            metrics[name] = {"mean_absolute_delta": round(float(delta.mean()), 4), "changed_pixel_ratio": round(float((delta.max(axis=2) > 8).mean()), 5)}
        check(checks, "visible_active_change", metrics["active-burn"]["changed_pixel_ratio"] > 0.004, metrics["active-burn"])
        check(checks, "aftermath_remains", metrics["settled"]["changed_pixel_ratio"] > 0.003, metrics["settled"])
        check(checks, "controlled_coverage", metrics["active-burn"]["changed_pixel_ratio"] < 0.18 and metrics["settled"]["changed_pixel_ratio"] < 0.12, metrics)
    check(checks, "path_count", manifest.get("effect", {}).get("path_count") in (2, 3, 4, 5), manifest.get("effect", {}).get("path_count"))
    check(checks, "not_published", manifest.get("published") is False, manifest.get("published"))
    passed = all(item["status"] == "PASS" for item in checks.values())
    result = {"slice": "MF-014", "checks": checks, "visual_metrics": metrics, "human_review": "PENDING_HUMAN", "published": False,
              "result": "TECHNICAL_PASS" if passed else "FAIL"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
