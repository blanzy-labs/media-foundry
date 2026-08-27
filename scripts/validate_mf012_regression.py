#!/usr/bin/env python3
"""Render legacy fixtures and compare archived representative frames byte-for-byte."""

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


CASES = [
    {
        "slice": "MF-011",
        "fixture": "content/fixtures/mf011/01-simon-target-acquired.json",
        "frame": 461,
        "expected": "artifacts/mf-011/representative-frames/01-simon-target-acquired/phase-3.png",
    },
    {
        "slice": "MF-008B-R1",
        "fixture": "content/fixtures/mf008b-r1/leo-zeph-investigation.json",
        "frame": 481,
        "expected": "artifacts/mf-008b-r1/representative-frames/leo-zeph-investigation/phase-3.png",
    },
    {
        "slice": "MF-006R9",
        "fixture": "content/fixtures/mf006r9-unknown-process.json",
        "frame": 349,
        "expected": "artifacts/mf-006r9/motion-evidence/08-000349.png",
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    work = Path(args.work_dir).resolve()
    if work.exists():
        raise SystemExit(f"refusing to overwrite: {work}")
    work.mkdir(parents=True)
    cases, errors = [], []
    for definition in CASES:
        case_dir = work / definition["slice"].lower()
        frames = case_dir / "frames"
        frames.mkdir(parents=True)
        fixture = root / definition["fixture"]
        expected = root / definition["expected"]
        layout = case_dir / "layout.json"
        execution = case_dir / "execution.json"
        started = time.monotonic()
        process = subprocess.run([
            "godot", "--path", "godot", "--fixed-fps", "30", "res://mf002.tscn", "--",
            "--fixture", str(fixture), "--grammar", str(root / "config/visual-grammar.json"),
            "--output-dir", str(frames), "--layout-report", str(layout),
            "--timeline-report", str(execution),
        ], cwd=root, capture_output=True, text=True, timeout=600)
        render_ms = round((time.monotonic() - started) * 1000)
        (case_dir / "render.log").write_text(process.stdout + process.stderr)
        actual = frames / f"frame_{definition['frame']:06d}.png"
        expected_hash = sha256(expected) if expected.is_file() else None
        actual_hash = sha256(actual) if actual.is_file() else None
        passed = process.returncode == 0 and expected_hash is not None and expected_hash == actual_hash
        if not passed:
            errors.append({"slice": definition["slice"], "code": "LEGACY_FRAME_IDENTITY_FAILED"})
        cases.append({
            **definition,
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
            "render_ms": render_ms,
            "frame_count": len(list(frames.glob("frame_*.png"))),
            "layout_result": json.loads(layout.read_text()).get("result") if layout.is_file() else None,
            "timeline_result": json.loads(execution.read_text()).get("result") if execution.is_file() else None,
            "result": "PASS" if passed else "FAIL",
        })
        if actual.is_file():
            shutil.copy2(actual, case_dir / "actual.png")
        shutil.rmtree(frames)
    result = {
        "slice": "MF-012",
        "type": "legacy_pixel_regression",
        "cases": cases,
        "errors": errors,
        "result": "PASS" if not errors else "FAIL",
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
