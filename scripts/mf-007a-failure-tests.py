#!/usr/bin/env python3
"""Prove MF-007A rejects invalid baseline, music, timing, and audio contracts."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    for name in ("repo_root", "fixture", "candidate_a", "candidate_b", "ambient", "sfx", "final_mix", "ambient_report", "narration", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root)
    fixture = json.loads(Path(args.fixture).read_text())
    cases = [
        ("baseline_hash", lambda data: data["frozen_visual"].update(sha256="0" * 64)),
        ("video_stream_hash", lambda data: data["frozen_visual"].update(video_stream_sha256="1" * 64)),
        ("music_enabled", lambda data: data["candidate_b"].update(music_enabled=True)),
        ("music_source", lambda data: data["candidate_b"].update(music_sources=["forbidden.wav"])),
        ("missing_event", lambda data: data["events"].pop()),
        ("narration_hash", lambda data: data["narration"].update(source_manifest_sha256="2" * 64)),
        ("narration_state", lambda data: data["narration"].update(segment_count=1)),
        ("loudness_target", lambda data: data["candidate_b"].update(target_integrated_lufs=-20.0)),
    ]
    results = []
    with tempfile.TemporaryDirectory(prefix="mf007a-failure-") as directory:
        temporary = Path(directory)
        for ordinal, (name, mutate) in enumerate(cases):
            changed = json.loads(json.dumps(fixture))
            mutate(changed)
            fixture_path = temporary / f"{ordinal}.json"
            output_path = temporary / f"{ordinal}-result.json"
            timeline_path = temporary / f"{ordinal}-timeline.json"
            fixture_path.write_text(json.dumps(changed))
            command = [
                "python3", str(root / "scripts/validate_mf007a_production.py"),
                "--project-root", str(root), "--fixture", str(fixture_path),
                "--candidate-a", args.candidate_a, "--candidate-b", args.candidate_b,
                "--ambient", args.ambient, "--sfx", args.sfx, "--final-mix", args.final_mix,
                "--ambient-report", args.ambient_report, "--narration", args.narration,
                "--output", str(output_path), "--audio-timeline", str(timeline_path)
            ]
            run = subprocess.run(command, capture_output=True, text=True)
            result = json.loads(output_path.read_text()) if output_path.is_file() else {}
            passed = run.returncode != 0 and result.get("result") == "FAIL"
            results.append({"case": name, "expected": "FAIL", "actual": result.get("result", "NO_RESULT"), "validator_exit": run.returncode, "result": "PASS" if passed else "FAIL"})
    report = {"slice": "MF-007A", "case_count": len(results), "cases": results, "result": "PASS" if all(item["result"] == "PASS" for item in results) else "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
