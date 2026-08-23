#!/usr/bin/env python3
"""Validate and prepare a deterministic continuous MF-005R1 ambient music bed."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


ALLOWED = {"source", "required", "loop", "gain_db", "narration_duck_db", "attack_ms", "release_ms", "fade_in", "fade_out", "provenance"}


def fail(code, message):
    raise ValueError(f"{code}: {message}")


def probe(path):
    process = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    try: data = json.loads(process.stdout) if process.returncode == 0 else {}
    except json.JSONDecodeError: data = {}
    audio = next((item for item in data.get("streams", []) if item.get("codec_type") == "audio"), None)
    if audio is None: fail("MUSIC_AUDIO_FAILED", "music source has no readable audio stream")
    duration = float(audio.get("duration") or data.get("format", {}).get("duration") or 0)
    if duration <= 0: fail("MUSIC_AUDIO_FAILED", "music source duration is invalid")
    return {"duration": duration, "sample_rate": int(audio.get("sample_rate", 0)), "channels": int(audio.get("channels", 0))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--duration", required=True, type=float)
    parser.add_argument("--output-audio", required=True)
    parser.add_argument("--output-report", required=True)
    args = parser.parse_args()
    started = time.perf_counter(); report_path = Path(args.output_report); report_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fixture = json.loads(Path(args.fixture).read_text()); music = fixture.get("music")
        if music is None:
            result = {"slice": "MF-005R1", "fixture": fixture.get("id"), "status": "NOT_PRESENT", "result": "PASS"}
        else:
            if not isinstance(music, dict) or not set(music).issubset(ALLOWED): fail("MUSIC_CONFIG_FAILED", "music configuration is malformed")
            required = music.get("required", False)
            source_value = music.get("source", "")
            source = Path(source_value); source = source if source.is_absolute() else Path(args.project_root) / source
            if not source.is_file():
                if required: fail("MUSIC_SOURCE_MISSING", "required music source does not exist")
                result = {"slice": "MF-005R1", "fixture": fixture.get("id"), "status": "OPTIONAL_MISSING", "result": "PASS"}
            else:
                metadata = probe(source)
                loop = music.get("loop", True); gain = float(music.get("gain_db", -22)); duck = float(music.get("narration_duck_db", -8)); attack = float(music.get("attack_ms", 60)); release = float(music.get("release_ms", 180)); fade_in = float(music.get("fade_in", 0.35)); fade_out = float(music.get("fade_out", 0.6))
                if not isinstance(loop, bool) or not -40 <= gain <= -6 or not -18 <= duck <= 0 or not 10 <= attack <= 500 or not 10 <= release <= 1000 or fade_in < 0 or fade_out < 0 or fade_in > args.duration / 2 or fade_out > args.duration / 2:
                    fail("MUSIC_DUCKING_CONFIG_FAILED", "gain, ducking, fade, attack, or release is outside supported limits")
                if metadata["duration"] < args.duration and loop is not True: fail("MUSIC_DURATION_FAILED", "short music source must enable deterministic looping")
                output = Path(args.output_audio); output.parent.mkdir(parents=True, exist_ok=True)
                filters = f"volume={gain}dB,afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0,args.duration-fade_out)}:d={fade_out}"
                command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
                if loop: command += ["-stream_loop", "-1"]
                command += ["-i", str(source), "-t", str(args.duration), "-af", filters, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(output)]
                process = subprocess.run(command, capture_output=True, text=True)
                if process.returncode != 0: fail("MUSIC_PREPARATION_FAILED", process.stderr[-300:])
                prepared = probe(output)
                if abs(prepared["duration"] - args.duration) > 0.002: fail("MUSIC_DURATION_FAILED", "prepared bed does not span production duration")
                result = {"slice": "MF-005R1", "fixture": fixture.get("id"), "status": "PASS", "source": str(source), "audio_path": str(output), "source_duration": metadata["duration"], "duration": prepared["duration"], "loop": loop, "gain_db": gain, "narration_duck_db": duck, "attack_ms": attack, "release_ms": release, "fade_in": fade_in, "fade_out": fade_out, "activity": {"start": 0.0, "end": args.duration}, "provenance": music.get("provenance", {}), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "prepared_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "preparation_seconds": round(time.perf_counter()-started,6), "result": "PASS"}
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        result = {"slice": "MF-005R1", "result": "FAIL", "error": str(error)}; report_path.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 1
    report_path.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
