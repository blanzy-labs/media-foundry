#!/usr/bin/env python3
"""Independently validate final MF-005 narration activity and mix evidence."""

import argparse
import json
import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path


def window_rms_db(samples, start, end, rate=48000):
    values = samples[max(0, round(start * rate)):min(len(samples), round(end * rate))]
    if not values:
        return -120.0
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    return 20 * math.log10(max(rms, 1e-6))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--mix-report", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--grammar", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--expected-content-duck-db", type=float, default=-6.0)
    parser.add_argument("--media", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    errors = []
    try:
        manifest = json.loads(Path(args.manifest).read_text())
        mix = json.loads(Path(args.mix_report).read_text())
        fixture = json.loads(Path(args.fixture).read_text())
        grammar = json.loads(Path(args.grammar).read_text())
        if manifest.get("result") != "PASS" or mix.get("result") != "PASS":
            errors.append("narration preparation or mix did not pass")
        with tempfile.TemporaryDirectory(prefix="mf005-validation-") as temporary:
            decoded = Path(temporary) / "decoded.wav"
            process = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", args.media, "-vn", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(decoded)], capture_output=True, text=True)
            if process.returncode != 0:
                raise ValueError(f"final audio decode failed: {process.stderr[-300:]}")
            with wave.open(str(decoded), "rb") as wav:
                raw = wav.readframes(wav.getnframes())
            samples = [value[0] / 32768.0 for value in struct.iter_unpack("<h", raw)]
        with wave.open(args.base, "rb") as wav:
            base_raw = wav.readframes(wav.getnframes())
        base_samples = [value[0] / 32768.0 for value in struct.iter_unpack("<h", base_raw)]
        activity = []
        previous_end = 0.0
        mix_beats = {item["beat"] for item in mix.get("segments", [])}
        for segment in manifest.get("segments", []):
            if float(segment["start"]) < previous_end or float(segment["end"]) > float(segment["beat_end"]) - float(segment["tail_out"]) + 0.002:
                errors.append(f"narration interval for {segment['beat']} overlaps or escapes beat")
            previous_end = float(segment["end"])
            level = window_rms_db(samples, float(segment["start"]), float(segment["end"]))
            status = "PASS" if level > -45.0 and segment["beat"] in mix_beats else "FAIL"
            if status == "FAIL":
                errors.append(f"expected narration activity missing for {segment['beat']}")
            activity.append({"beat": segment["beat"], "start": segment["start"], "end": segment["end"], "decoded_rms_dbfs": round(level, 3), "status": status})
        if not activity:
            errors.append("no narration segments were validated")
        if mix.get("clipped_samples") != 0 or mix.get("duck_db") != args.expected_content_duck_db:
            errors.append("mix clipping or ducking policy failed")
        vocabulary = {item["name"].lower(): item for item in grammar.get("audio", {}).get("events", [])}
        cue_activity, cursor = [], 0.0
        for beat in fixture.get("beats", []):
            cue = beat.get("audio_cue")
            if cue:
                event = vocabulary.get(cue)
                if event is None:
                    errors.append(f"configured cue {cue} is absent from audio grammar")
                else:
                    start = cursor + min(0.12, float(beat["duration"]) * 0.1)
                    level = window_rms_db(base_samples, start, start + float(event["duration"]))
                    status = "PASS" if level > -35.0 else "FAIL"
                    if status == "FAIL": errors.append(f"expected cue activity missing for {beat['id']}")
                    cue_activity.append({"beat": beat["id"], "cue": cue, "start": round(start, 6), "rms_dbfs": round(level, 3), "status": status})
            cursor += float(beat["duration"])
        result = {"slice": "MF-005", "checks": {"normalized_assets": "PASS" if manifest.get("result") == "PASS" else "FAIL", "beat_fit": "PASS" if not any("overlap" in item or "escapes" in item for item in errors) else "FAIL", "final_audio_activity": "PASS" if activity and all(item["status"] == "PASS" for item in activity) else "FAIL", "existing_cues": "PASS" if cue_activity and all(item["status"] == "PASS" for item in cue_activity) else "FAIL", "ducking": "PASS" if mix.get("duck_db") == args.expected_content_duck_db else "FAIL", "clipping": "PASS" if mix.get("clipped_samples") == 0 else "FAIL", "decode": "PASS"}, "activity": activity, "cue_activity": cue_activity, "errors": errors, "result": "PASS" if not errors else "FAIL"}
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, wave.Error) as error:
        result = {"slice": "MF-005", "checks": {"decode": "FAIL"}, "errors": [str(error)], "result": "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
