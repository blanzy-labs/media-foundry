#!/usr/bin/env python3
"""Independently validate the MF-005R2 final mix and audiovisual evidence."""

import argparse
import json
import re
import subprocess
from pathlib import Path


def loudness(path):
    process = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-"
    ], capture_output=True, text=True)
    blocks = re.findall(r"\{\s*\"input_i\".*?\}", process.stderr, re.DOTALL)
    if process.returncode != 0 or not blocks:
        raise ValueError("FINAL_MIX_VALIDATION_FAILED: loudness analysis unavailable")
    data = json.loads(blocks[-1])
    return {"integrated_lufs": float(data["input_i"]), "true_peak_db": float(data["input_tp"]), "loudness_range": float(data["input_lra"])}


def main():
    parser = argparse.ArgumentParser()
    for name in ("fixture", "timeline", "execution", "narration", "music", "mix", "audio_validation", "editorial", "media", "output", "audio_timeline"):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    args = parser.parse_args(); errors = []
    try:
        fixture = json.loads(Path(args.fixture).read_text()); timeline = json.loads(Path(args.timeline).read_text()); execution = json.loads(Path(args.execution).read_text())
        narration = json.loads(Path(args.narration).read_text()); music = json.loads(Path(args.music).read_text()); mix = json.loads(Path(args.mix).read_text()); audio = json.loads(Path(args.audio_validation).read_text()); editorial = json.loads(Path(args.editorial).read_text())
        if any(item.get("result") != "PASS" for item in (timeline, execution, narration, music, mix, audio, editorial)):
            errors.append("one or more required production inputs did not pass")
        duration = float(timeline.get("duration", 0)); segments = narration.get("segments", []); ducks = mix.get("ducking_windows", [])
        if duration != 15.0 or music.get("activity") != {"start": 0.0, "end": 15.0} or music.get("continuous") is not True:
            errors.append("music activity does not continuously span the production")
        if music.get("fade_in", 0) <= 0 or music.get("fade_out", 0) <= 0:
            errors.append("music fade-in or fade-out is absent")
        if len(ducks) != len(segments):
            errors.append("ducking windows do not derive one-for-one from narration")
        else:
            for segment, duck in zip(segments, ducks):
                if duck.get("beat") != segment.get("beat") or float(duck.get("start", -1)) != float(segment.get("start", -2)) or float(duck.get("end", 16)) != float(segment.get("end", 17)):
                    errors.append("ducking windows differ from narration timing")
                if float(duck.get("start", -1)) < 0 or float(duck.get("end", 16)) > duration or float(duck.get("start", 0)) >= float(duck.get("end", 0)):
                    errors.append("ducking window is outside video bounds")
        reveal = next((item for item in segments if item.get("beat") == "reveal"), None)
        reveal_beat = next((item for item in timeline.get("beats", []) if item.get("id") == "reveal"), None)
        if reveal is None or reveal_beat is None or not (float(reveal_beat["start"]) <= float(reveal["start"]) < float(reveal["end"]) <= float(reveal_beat["end"])):
            errors.append("spoken product name is not aligned with visual reveal")
        expected_hash = fixture.get("music", {}).get("provenance", {}).get("sha256")
        if expected_hash != music.get("source_sha256") or music.get("selected_offset") != fixture.get("music", {}).get("selected_offset"):
            errors.append("supplied music hash or deterministic offset differs from fixture")
        if mix.get("music", {}).get("narration_duck_db") != fixture.get("music", {}).get("narration_duck_db"):
            errors.append("music ducking gain differs from fixture")
        measured = loudness(Path(args.media)); target = fixture.get("final_mix", {})
        if abs(measured["integrated_lufs"] - float(target.get("integrated_lufs", -16))) > 1.0:
            errors.append("final integrated loudness is outside tolerance")
        if measured["true_peak_db"] > float(target.get("true_peak_db", -1.5)) + 0.5 or mix.get("clipped_samples") != 0:
            errors.append("final true peak or pre-normalization clipping exceeds threshold")
        timeline_evidence = {
            "slice": "MF-005R2", "duration": duration,
            "music": {"start": 0.0, "end": duration, "source_offset": music.get("selected_offset"), "fade_in_seconds": music.get("fade_in"), "fade_out_seconds": music.get("fade_out"), "gain_db": music.get("gain_db")},
            "narration": [{"beat": item["beat"], "start": item["start"], "end": item["end"], "text": item["text"]} for item in segments],
            "ducking": ducks, "sfx": audio.get("cue_activity", []), "result": "PASS" if not errors else "FAIL"
        }
        Path(args.audio_timeline).parent.mkdir(parents=True, exist_ok=True); Path(args.audio_timeline).write_text(json.dumps(timeline_evidence, indent=2) + "\n")
        checks = {
            "music_source_valid": "PASS" if expected_hash == music.get("source_sha256") else "FAIL",
            "narration_source_valid": audio.get("checks", {}).get("normalized_assets", "FAIL"),
            "sfx_sources_valid": audio.get("checks", {}).get("existing_cues", "FAIL"),
            "continuous_music": "PASS" if not any("continuously" in item for item in errors) else "FAIL",
            "narration_windows": audio.get("checks", {}).get("beat_fit", "FAIL"),
            "ducking_windows": "PASS" if not any("ducking window" in item for item in errors) else "FAIL",
            "fade_in": "PASS" if music.get("fade_in", 0) > 0 else "FAIL", "fade_out": "PASS" if music.get("fade_out", 0) > 0 else "FAIL",
            "spoken_name_alignment": "PASS" if not any("spoken product" in item for item in errors) else "FAIL",
            "final_audio_stream": "PASS", "full_decode": audio.get("checks", {}).get("decode", "FAIL"),
            "clipping": "PASS" if not any("peak" in item or "clipping" in item for item in errors) else "FAIL",
        }
        result = {"slice": "MF-005R2", "fixture": fixture.get("id"), "checks": checks, "loudness": measured, "errors": errors, "result": "PASS" if not errors and all(value == "PASS" for value in checks.values()) else "FAIL"}
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        result = {"slice": "MF-005R2", "checks": {}, "errors": [str(error)], "result": "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2)); return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
