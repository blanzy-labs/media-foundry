#!/usr/bin/env python3
"""Render and package the bounded MF-014 circuit burn capability test."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

from metal_circuit_burn_stage import BurnConfig, MetalCircuitBurnStage


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def encode(stage: MetalCircuitBurnStage, output: Path, log: Path) -> str:
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{stage.size[0]}x{stage.size[1]}", "-r", str(stage.config.fps), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-threads", "1", "-pix_fmt", "yuv420p",
        "-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-movflags", "+faststart",
        "-metadata", "creation_time=1970-01-01T00:00:00Z", str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdin is not None
    frame_digest = hashlib.sha256()
    try:
        for index in range(stage.frame_count):
            raw = stage.render_frame(index).tobytes()
            frame_digest.update(raw)
            process.stdin.write(raw)
        process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        returncode = process.wait()
    except BaseException:
        process.kill()
        raise
    log.write_text(stderr, encoding="utf-8")
    if returncode:
        raise RuntimeError(f"ffmpeg failed ({returncode}); see {log}")
    return frame_digest.hexdigest()


def make_contact_sheet(frames: list[Path], labels: list[str], output: Path) -> None:
    thumb_width = 256
    opened = [Image.open(path).convert("RGB") for path in frames]
    thumbs = [image.resize((thumb_width, round(image.height * thumb_width / image.width)), Image.Resampling.LANCZOS) for image in opened]
    margin, gap, label_height = 5, 5, 22
    canvas = Image.new("RGB", (margin * 2 + thumb_width * len(thumbs) + gap * (len(thumbs) - 1),
                               margin * 2 + label_height + max(image.height for image in thumbs)), (8, 7, 6))
    draw = ImageDraw.Draw(canvas)
    for index, (thumb, label) in enumerate(zip(thumbs, labels)):
        x = margin + index * (thumb_width + gap)
        draw.text((x + 4, margin + 4), label.upper(), fill=(211, 129, 61))
        canvas.paste(thumb, (x, margin + label_height))
    canvas.save(output, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--artifacts", default="artifacts/mf-014")
    parser.add_argument("--reports", default="reports/mf-014")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    source = Path(args.source).resolve()
    artifacts = (root / args.artifacts).resolve()
    reports = (root / args.reports).resolve()
    if not source.is_file():
        raise SystemExit(f"source image missing: {source}")
    if artifacts.exists() or reports.exists():
        raise SystemExit("refusing to overwrite existing MF-014 artifacts or reports")
    artifacts.mkdir(parents=True)
    reports.mkdir(parents=True)
    (artifacts / "representative-frames").mkdir()
    (artifacts / "motion-evidence").mkdir()
    (artifacts / "validation").mkdir()
    (artifacts / "logs").mkdir()
    config = BurnConfig()
    stage = MetalCircuitBurnStage(source, config)
    source_copy = artifacts / "source-reference.png"
    shutil.copy2(source, source_copy)
    started = time.monotonic()
    video = artifacts / "final-test.mp4"
    frame_tree_hash = encode(stage, video, artifacts / "logs/encode.log")
    stamps = ((0.4, "idle"), (1.35, "ignition"), (3.65, "active-burn"), (6.65, "title-interaction"), (8.65, "settled"))
    evidence_frames = []
    for timestamp, name in stamps:
        index = min(stage.frame_count - 1, round(timestamp * config.fps))
        destination = artifacts / "representative-frames" / f"{name}.png"
        stage.render_frame(index).save(destination, optimize=True)
        evidence_frames.append(destination)
    make_contact_sheet(evidence_frames, [name for _, name in stamps], artifacts / "motion-evidence/burn-sequence.png")
    manifest = {
        "slice": "MF-014",
        "source": {"path": str(source), "preserved_copy": str(source_copy), "sha256": sha256(source), "bytes": source.stat().st_size},
        "effect": {"module": "metal_circuit_burn_stage", "path_count": len(stage.paths), "duration_seconds": config.duration_seconds,
                   "fps": config.fps, "frame_count": stage.frame_count, "width": stage.size[0], "height": stage.size[1]},
        "video": {"path": str(video), "sha256": sha256(video), "bytes": video.stat().st_size},
        "raw_frame_sequence_sha256": frame_tree_hash,
        "representative_frames": [str(path) for path in evidence_frames],
        "motion_evidence": str(artifacts / "motion-evidence/burn-sequence.png"),
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "published": False,
    }
    write_json(artifacts / "render-manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
