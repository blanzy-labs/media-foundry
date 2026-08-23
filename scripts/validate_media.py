#!/usr/bin/env python3
"""Independent FFprobe/FFmpeg validation for MF-001."""

import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def add_check(state, key, passed, detail):
    state[key] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("media")
    parser.add_argument("--ffprobe-json", required=True)
    parser.add_argument("--result-json", required=True)
    args = parser.parse_args()
    media = Path(args.media)
    probe_path = Path(args.ffprobe_json)
    result_path = Path(args.result_json)
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    validation = {}
    probe = {}

    file_ok = media.is_file() and media.stat().st_size > 0
    add_check(validation, "file", file_ok, str(media))
    if file_ok:
        proc = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(media)], capture_output=True, text=True)
        try:
            probe = json.loads(proc.stdout) if proc.returncode == 0 else {}
        except json.JSONDecodeError:
            probe = {}
        probe["_command_returncode"] = proc.returncode
        if proc.stderr:
            probe["_stderr"] = proc.stderr.strip()
    else:
        probe = {"_error": "file missing or empty"}
    probe_path.write_text(json.dumps(probe, indent=2) + "\n", encoding="utf-8")

    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    container = probe.get("format", {}).get("format_name", "")
    add_check(validation, "container", "mp4" in container, container or "unreadable")
    add_check(validation, "video_stream", video is not None, video.get("codec_name", "") if video else "missing")
    add_check(validation, "audio_stream", audio is not None, audio.get("codec_name", "") if audio else "missing")
    add_check(validation, "resolution", bool(video and video.get("width") == 1080 and video.get("height") == 1920), f"{video.get('width')}x{video.get('height')}" if video else "missing")
    add_check(validation, "orientation", bool(video and video.get("height", 0) > video.get("width", 0)), "vertical" if video and video.get("height", 0) > video.get("width", 0) else "not vertical")
    duration = float(probe.get("format", {}).get("duration", 0) or 0)
    add_check(validation, "duration", 14.8 <= duration <= 15.2, f"{duration:.3f} seconds")
    try:
        rate = float(Fraction(video.get("avg_frame_rate", "0/1"))) if video else 0.0
    except (ValueError, ZeroDivisionError):
        rate = 0.0
    add_check(validation, "frame_rate", 29.0 <= rate <= 31.0, f"{rate:.3f} fps")
    add_check(validation, "video_codec", bool(video and video.get("codec_name") == "h264"), video.get("codec_name", "missing") if video else "missing")
    add_check(validation, "audio_codec", bool(audio and audio.get("codec_name") == "aac"), audio.get("codec_name", "missing") if audio else "missing")

    decode_ok = False
    decode_detail = "media unavailable"
    if file_ok:
        decoded = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-f", "null", "-"], capture_output=True, text=True)
        decode_ok = decoded.returncode == 0
        decode_detail = "full decode succeeded" if decode_ok else (decoded.stderr.strip()[-500:] or "decode failed")
    add_check(validation, "decode", decode_ok, decode_detail)
    passed = all(item["status"] == "PASS" for item in validation.values())
    result = {"slice":"MF-001", "render":"PASS" if file_ok else "FAIL", "validation":validation, "result":"PASS" if passed else "FAIL"}
    if file_ok:
        result["artifact"] = {"path":str(media), "bytes":media.stat().st_size, "sha256":hashlib.sha256(media.read_bytes()).hexdigest()}
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
