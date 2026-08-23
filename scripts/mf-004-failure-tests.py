#!/usr/bin/env python3
"""Run controlled MF-004 timeline failures without invoking the renderer."""

import argparse
import copy
import json
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root)
    base = json.loads((root / "content/fixtures/mf004-turd-burglar.json").read_text())
    cases = {}

    def add(name, mutate):
        fixture = copy.deepcopy(base)
        mutate(fixture)
        cases[name] = fixture

    add("unknown_beat_type", lambda f: f["beats"][1].update(type="mystery"))
    add("zero_duration", lambda f: f["beats"][1].update(duration=0))
    add("negative_duration", lambda f: f["beats"][1].update(duration=-1))
    add("total_too_long", lambda f: f["beats"][1].update(duration=3))
    add("total_too_short", lambda f: f["beats"][1].update(duration=1.5))
    add("invalid_media_ref", lambda f: f["beats"][2].update(media_ref="missing"))
    add("invalid_audio_cue", lambda f: f["beats"][1].update(audio_cue="kaboom"))
    add("impossible_text_density", lambda f: f["beats"][1].update(text="WORD " * 100))
    add("malformed_timeline", lambda f: f.update(beats={"not": "an array"}))
    add("explicit_timing_rejected", lambda f: f["beats"][1].update(start=1.4, end=4.0))
    results = {}
    with tempfile.TemporaryDirectory(prefix="mf004-failures-") as temporary:
        directory = Path(temporary)
        for name, fixture in cases.items():
            fixture_path, report_path = directory / f"{name}.json", directory / f"{name}-result.json"
            fixture_path.write_text(json.dumps(fixture))
            process = subprocess.run([
                "python3", str(root / "scripts/preflight_mf004.py"), "--fixture", str(fixture_path),
                "--grammar", str(root / "config/visual-grammar.json"), "--project-root", str(root), "--output", str(report_path)
            ], capture_output=True, text=True)
            report = json.loads(report_path.read_text())
            passed = process.returncode != 0 and report.get("result") == "FAIL"
            results[name] = {"result": "PASS" if passed else "FAIL", "preflight_exit": process.returncode, "error": report.get("error", "")}
    result = {"slice": "MF-004", "tests": results, "result": "PASS" if all(item["result"] == "PASS" for item in results.values()) else "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
