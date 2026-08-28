#!/usr/bin/env python3
"""Build matched procedural and hybrid source-strategy proofs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from composition_contract import validate_manifest
from visual_source_contract import sha256, validate_visual_source


FONT = "/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Bold.otf"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2) + "\n")


def run_checked(command: list[str], log: Path) -> None:
    process = subprocess.run(command, capture_output=True, text=True)
    rendered = process.stdout + process.stderr
    log.parent.mkdir(parents=True, exist_ok=True); log.write_text(rendered)
    if process.returncode or "SCRIPT ERROR:" in rendered or "ERROR:" in rendered:
        raise RuntimeError(f"command failed ({process.returncode}); see {log}")


def encode(sequence: Path, output: Path, log: Path) -> None:
    run_checked(["ffmpeg", "-y", "-v", "error", "-framerate", "30", "-i", str(sequence / "frame-%04d.png"),
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                 "-t", "4", str(output)], log)


def labeled_comparison(left: Path, right: Path, output: Path) -> None:
    a = Image.open(left).convert("RGB"); b = Image.open(right).convert("RGB")
    a.thumbnail((360, 540), Image.Resampling.LANCZOS); b.thumbnail((360, 540), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (768, 620), (8, 12, 11)); draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 30)
    draw.text((20, 18), "PROCEDURAL", font=font, fill=(224, 201, 139))
    draw.text((398, 18), "HYBRID", font=font, fill=(230, 185, 5))
    canvas.paste(a, (20, 62)); canvas.paste(b, (388, 62)); canvas.save(output, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf017-pulp-visual-source.json")
    parser.add_argument("--artifacts", default="artifacts/mf-017")
    args = parser.parse_args(); root = Path(args.project_root).resolve(); artifacts = root / args.artifacts
    if artifacts.exists():
        raise SystemExit(f"refusing to overwrite: {artifacts}")
    definition = json.loads((root / args.config).read_text())
    source_result = validate_visual_source(root, definition)
    if source_result["result"] != "PASS":
        raise SystemExit(json.dumps(source_result, indent=2))
    composition_path = root / definition["visual_source"]["composition_gate"]["manifest_path"]
    composition = json.loads(composition_path.read_text()); composition_result = validate_manifest(composition)
    if composition_result["result"] != "PASS":
        raise SystemExit("MF-016 composition validation failed")
    for directory in (artifacts / "procedural", artifacts / "hybrid", artifacts / "comparison", artifacts / "validation", artifacts / "logs"):
        directory.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    procedural_base = root / "artifacts/mf-016/pulp-keyframes/escalation.png"
    plate = root / definition["visual_source"]["plate"]["source_path"]
    with tempfile.TemporaryDirectory(prefix="mf017-") as temporary:
        temporary = Path(temporary)
        bases = temporary / "bases"; bases.mkdir()
        procedural_image = Image.open(procedural_base).convert("RGB")
        procedural_image.save(bases / "procedural.png")
        hybrid_image = Image.open(plate).convert("RGB").resize((768, 1152), Image.Resampling.LANCZOS)
        hybrid_image.save(bases / "hybrid.png")
        for mode in ("procedural", "hybrid"):
            frames = temporary / mode
            run_checked(["godot", "--headless", "--path", str(root / "godot"), "--script", "mf017_visual_source_proof.gd", "--",
                         "--base", str(bases / f"{mode}.png"), "--output", str(frames), "--mode", mode],
                        artifacts / "logs" / f"godot-{mode}.log")
            static = artifacts / mode / "static-proof.png"
            shutil.copy2(frames / "frame-0060.png", static)
            encode(frames, artifacts / mode / "motion-proof.mp4", artifacts / "logs" / f"encode-{mode}.log")
    labeled_comparison(artifacts / "procedural/static-proof.png", artifacts / "hybrid/static-proof.png",
                       artifacts / "comparison/side-by-side.png")
    run_checked(["ffmpeg", "-y", "-v", "error", "-i", str(artifacts / "procedural/motion-proof.mp4"),
                 "-i", str(artifacts / "hybrid/motion-proof.mp4"), "-filter_complex",
                 "[0:v]drawtext=fontfile=" + FONT + ":text=PROCEDURAL:x=24:y=24:fontsize=34:fontcolor=0xE0C98B[v0];"
                 "[1:v]drawtext=fontfile=" + FONT + ":text=HYBRID:x=24:y=24:fontsize=34:fontcolor=0xE6B905[v1];"
                 "[v0][v1]hstack=inputs=2[v]", "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(artifacts / "comparison/side-by-side.mp4")],
                artifacts / "logs/comparison-encode.log")
    outputs = {}
    for relative in ("procedural/static-proof.png", "procedural/motion-proof.mp4", "hybrid/static-proof.png",
                     "hybrid/motion-proof.mp4", "comparison/side-by-side.png", "comparison/side-by-side.mp4"):
        path = artifacts / relative; outputs[relative] = {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
    manifest = {"slice": "MF-017", "strategy": "HYBRID", "source_status": "PRODUCTION_PLATE_PENDING",
                "config": str(root / args.config), "config_sha256": sha256(root / args.config),
                "plate": {"path": str(plate), "sha256": sha256(plate), "approval": "REVIEW_REQUIRED", "provenance": "generated"},
                "source_validation": source_result, "composition_validation": composition_result["result"],
                "composition_human_status": definition["visual_source"]["composition_gate"]["human_status"],
                "godot_overlay": {"script": "godot/mf017_visual_source_proof.gd", "reactor": True, "warning_lamps": True,
                                  "local_light_reaction": True, "environmental_steam": True},
                "outputs": outputs, "duration_seconds": 4.0, "fps": 30, "full_trailer_rendered": False,
                "elapsed_ms": round((time.monotonic() - started) * 1000), "human_review": "PENDING_HUMAN", "published": False}
    write_json(artifacts / "proof-manifest.json", manifest)
    write_json(artifacts / "validation/source-validation.json", source_result)
    print(json.dumps(manifest, indent=2)); return 0


if __name__ == "__main__":
    sys.exit(main())
