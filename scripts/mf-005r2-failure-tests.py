#!/usr/bin/env python3
"""Run controlled MF-005R2 music, ducking, and editorial failures."""

import argparse
import copy
import json
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--repo-root", required=True); parser.add_argument("--artifacts", required=True); parser.add_argument("--output", required=True); args = parser.parse_args()
    root = Path(args.repo_root); artifacts = Path(args.artifacts); fixture = json.loads((root / "content/fixtures/mf005r2-turd-burglar.json").read_text()); results = {}
    with tempfile.TemporaryDirectory(prefix="mf005r2-failures-") as directory:
        temp = Path(directory); corrupt = temp / "corrupt.mp3"; corrupt.write_bytes(b"not an audio stream")
        def prepare_case(name, mutate, expected):
            candidate = copy.deepcopy(fixture); mutate(candidate); fixture_path = temp / f"{name}.json"; fixture_path.write_text(json.dumps(candidate)); report = temp / f"{name}-music.json"
            process = subprocess.run(["python3", str(root / "scripts/prepare_mf005r1_music.py"), "--fixture", str(fixture_path), "--project-root", str(root), "--duration", "15", "--output-audio", str(temp / f"{name}.wav"), "--output-report", str(report)], capture_output=True, text=True)
            payload = json.loads(report.read_text()); passed = process.returncode != 0 and expected in payload.get("error", "")
            results[name] = {"result": "PASS" if passed else "FAIL", "expected": expected, "observed": payload.get("error", "")}
        prepare_case("missing_supplied_music", lambda item: item["music"].update(source=str(temp / "missing.mp3")), "MUSIC_SOURCE_MISSING")
        prepare_case("corrupt_music_source", lambda item: item["music"].update(source=str(corrupt)), "MUSIC_AUDIO_FAILED")
        prepare_case("unsupported_audio_stream", lambda item: item["music"].update(source="media/images/venus-magellan-pia00271.jpg"), "MUSIC_AUDIO_FAILED")
        prepare_case("invalid_selected_offset", lambda item: item["music"].update(selected_offset=-1), "MUSIC_OFFSET_FAILED")
        prepare_case("invalid_loop_duration", lambda item: item["music"].update(selected_offset=150, loop=False), "MUSIC_DURATION_FAILED")
        prepare_case("invalid_fade_configuration", lambda item: item["music"].update(fade_in=8, fade_out=8), "MUSIC_DUCKING_CONFIG_FAILED")

        editorial_fixture = copy.deepcopy(fixture); next(beat for beat in editorial_fixture["beats"] if beat["id"] == "reveal")["narration"]["text"] = "It is called the game."
        editorial_path = temp / "missing-product-name.json"; editorial_path.write_text(json.dumps(editorial_fixture)); editorial_report = temp / "missing-product-name-report.json"
        editorial_process = subprocess.run(["python3", str(root / "scripts/validate_mf005r2_editorial.py"), "--fixture", str(editorial_path), "--output", str(editorial_report)], capture_output=True, text=True)
        editorial_payload = json.loads(editorial_report.read_text()); passed = editorial_process.returncode != 0 and any("required_spoken" in item for item in editorial_payload.get("errors", []))
        results["required_narration_missing_product_name"] = {"result": "PASS" if passed else "FAIL", "expected": "EDITORIAL_REQUIREMENT_FAILED", "observed": editorial_payload.get("errors", [])}

        bad_mix = json.loads((artifacts / "validation/turd-burglar-mix.json").read_text()); bad_mix["ducking_windows"][0]["start"] = -0.1
        bad_mix_path = temp / "bad-duck.json"; bad_mix_path.write_text(json.dumps(bad_mix)); validation = temp / "bad-duck-validation.json"
        command = ["python3", str(root / "scripts/validate_mf005r2_mix.py"), "--fixture", str(root / "content/fixtures/mf005r2-turd-burglar.json"), "--timeline", str(artifacts / "timelines/turd-burglar.json"), "--execution", str(artifacts / "timelines/turd-burglar-execution.json"), "--narration", str(artifacts / "timelines/turd-burglar-narration.json"), "--music", str(artifacts / "timelines/turd-burglar-music.json"), "--mix", str(bad_mix_path), "--audio-validation", str(artifacts / "validation/turd-burglar-audio.json"), "--editorial", str(artifacts / "validation/turd-burglar-editorial.json"), "--media", str(artifacts / "turd-burglar.mp4"), "--output", str(validation), "--audio-timeline", str(temp / "bad-duck-timeline.json")]
        process = subprocess.run(command, capture_output=True, text=True); payload = json.loads(validation.read_text()); passed = process.returncode != 0 and any("outside video bounds" in item for item in payload.get("errors", []))
        results["ducking_window_outside_bounds"] = {"result": "PASS" if passed else "FAIL", "expected": "outside video bounds", "observed": payload.get("errors", [])}
    result = {"slice": "MF-005R2", "cases": results, "count": len(results), "result": "PASS" if results and all(item["result"] == "PASS" for item in results.values()) else "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2) + "\n"); print(json.dumps(result, indent=2)); return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
