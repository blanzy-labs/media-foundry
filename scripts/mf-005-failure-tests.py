#!/usr/bin/env python3
"""Controlled fail-closed tests for MF-005 narration preparation."""

import argparse
import copy
import json
import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path


def write_wav(path, seconds):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(48000)
        wav.writeframes(b"".join(struct.pack("<h", round(math.sin(index / 20) * 8000)) for index in range(round(seconds * 48000))))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root)
    base = json.loads((root / "content/fixtures/mf005-turd-burglar.json").read_text())
    results = {}
    with tempfile.TemporaryDirectory(prefix="mf005-failures-") as temporary:
        temp = Path(temporary)
        unreadable = temp / "unreadable.wav"; unreadable.write_bytes(b"not audio")
        invalid = temp / "invalid.txt"; invalid.write_text("not audio")
        long_audio = temp / "long.wav"; write_wav(long_audio, 4.0)
        cases = {}

        def add(name, mutate):
            fixture = copy.deepcopy(base); mutate(fixture); cases[name] = fixture

        add("missing_narration_file", lambda f: f["beats"][1]["narration"].update(source=str(temp / "missing.wav")))
        add("unreadable_audio", lambda f: f["beats"][1]["narration"].update(source=str(unreadable)))
        add("narration_longer_than_beat", lambda f: f["beats"][1]["narration"].update(source=str(long_audio)))
        add("invalid_audio_format", lambda f: f["beats"][1]["narration"].update(source=str(invalid)))
        add("missing_provider", lambda f: f["beats"][1].update(narration={"generate": True, "text": "Hi.", "provider": "missing", "voice": "slt"}))
        add("invalid_voice", lambda f: f["beats"][1].update(narration={"generate": True, "text": "Hi.", "provider": "local_ffmpeg_flite", "voice": "unknown"}))
        add("malformed_narration", lambda f: f["beats"][1].update(narration="speak this"))
        add("nonexistent_beat_reference", lambda f: f.update(narration_required_beats=["not-a-beat"]))

        def run_case(name, fixture, cache_dir=None):
            fixture_path = temp / f"{name}.json"; timeline_path = temp / f"{name}-timeline.json"; report_path = temp / f"{name}-report.json"
            fixture_path.write_text(json.dumps(fixture))
            preflight = subprocess.run(["python3", str(root / "scripts/preflight_mf004.py"), "--fixture", str(fixture_path), "--grammar", str(root / "config/visual-grammar.json"), "--project-root", str(root), "--output", str(timeline_path)], capture_output=True, text=True)
            if preflight.returncode != 0:
                return preflight.returncode, {"result": "FAIL", "error": "fixture timeline unexpectedly failed"}
            process = subprocess.run(["python3", str(root / "scripts/prepare_mf005_narration.py"), "--fixture", str(fixture_path), "--timeline", str(timeline_path), "--project-root", str(root), "--normalized-dir", str(temp / f"{name}-normalized"), "--cache-dir", str(cache_dir or temp / f"{name}-cache"), "--output", str(report_path)], capture_output=True, text=True)
            return process.returncode, json.loads(report_path.read_text())

        for name, fixture in cases.items():
            returncode, report = run_case(name, fixture)
            passed = returncode != 0 and report.get("result") == "FAIL"
            results[name] = {"result": "PASS" if passed else "FAIL", "error": report.get("error", "")}

        corrupt_fixture = copy.deepcopy(base)
        corrupt_fixture["narration_required_beats"] = ["setup"]
        corrupt_fixture["beats"][1]["narration"] = {"generate": True, "text": "Cache test.", "provider": "local_ffmpeg_flite", "voice": "slt", "lead_in": 0.15, "tail_out": 0.15}
        for beat in corrupt_fixture["beats"][2:]:
            beat["narration"] = None
        cache = temp / "corrupt-cache"
        first_code, first_report = run_case("cache_seed", corrupt_fixture, cache)
        if first_code == 0:
            next(cache.glob("*.wav")).write_bytes(b"corrupt")
        second_code, second_report = run_case("cache_corruption", corrupt_fixture, cache)
        passed = first_code == 0 and second_code != 0 and "NARRATION_CACHE_FAILED" in second_report.get("error", "")
        results["cache_corruption"] = {"result": "PASS" if passed else "FAIL", "error": second_report.get("error", "")}
    result = {"slice": "MF-005", "tests": results, "result": "PASS" if all(item["result"] == "PASS" for item in results.values()) else "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
