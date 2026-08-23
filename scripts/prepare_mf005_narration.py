#!/usr/bin/env python3
"""Preflight, normalize, and materialize beat-linked MF-005 narration."""

import argparse
import hashlib
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

from narration_provider import generate


ALLOWED_KEYS = {"enabled", "source", "generate", "text", "voice", "provider", "lead_in", "tail_out", "pause_after", "semantic_target", "required", "provenance", "beat_id", "speech_settings"}
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}


def fail(code, message):
    raise ValueError(f"{code}: {message}")


def probe(path):
    process = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    try:
        data = json.loads(process.stdout) if process.returncode == 0 else {}
    except json.JSONDecodeError:
        data = {}
    audio = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"), None)
    if audio is None:
        fail("NARRATION_AUDIO_FAILED", f"{path} has no readable audio stream")
    duration = float(audio.get("duration") or data.get("format", {}).get("duration") or 0)
    if duration <= 0:
        fail("NARRATION_AUDIO_FAILED", f"{path} has invalid duration")
    return {"duration": duration, "sample_rate": int(audio.get("sample_rate", 0)), "channels": int(audio.get("channels", 0)), "codec": audio.get("codec_name")}


def peak_pcm(path):
    with wave.open(str(path), "rb") as wav:
        if wav.getsampwidth() != 2:
            fail("NARRATION_NORMALIZATION_FAILED", "normalized PCM must be 16-bit")
        frames = wav.readframes(wav.getnframes())
    maximum = max((abs(int.from_bytes(frames[index:index + 2], "little", signed=True)) for index in range(0, len(frames), 2)), default=0)
    return maximum / 32768.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--grammar")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--normalized-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        fixture = json.loads(Path(args.fixture).read_text())
        timeline = json.loads(Path(args.timeline).read_text())
        grammar = json.loads(Path(args.grammar).read_text()) if args.grammar else {}
        root = Path(args.project_root)
        normalized_dir = Path(args.normalized_dir)
        normalized_dir.mkdir(parents=True, exist_ok=True)
        beat_map = {beat["id"]: beat for beat in timeline.get("beats", [])}
        strict_sync = fixture.get("narration_sync_policy") == "semantic_beat"
        if fixture.get("production_media_required") is True:
            media = fixture.get("media")
            if not isinstance(media, dict) or "source" not in media or media.get("required") is not True:
                fail("PRODUCTION_MEDIA_MISSING", "production fixture requires one explicit required media asset")
            media_path = Path(media["source"]); media_path = media_path if media_path.is_absolute() else root / media_path
            capability_names = {"mf003-still.png", "mf003-wide.png", "mf003-clip.mp4"}
            if not media_path.is_file() or media_path.name in capability_names or media.get("provenance", {}).get("type") == "deterministic_fixture":
                fail("PRODUCTION_MEDIA_MISSING", "approved production media is missing or resolves to a capability-test asset")
        required = fixture.get("narration_required_beats", [])
        if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
            fail("NARRATION_CONFIG_FAILED", "narration_required_beats must be an array of beat IDs")
        if any(item not in beat_map for item in required):
            fail("NARRATION_BEAT_FAILED", "required narration references a nonexistent beat")
        segments = []
        generated_seconds = 0.0
        normalization_seconds = 0.0
        for fixture_beat in fixture.get("beats", []):
            beat_id = fixture_beat.get("id")
            narration = fixture_beat.get("narration")
            if narration is None or narration == {"enabled": False}:
                if beat_id in required:
                    fail("NARRATION_REQUIRED_FAILED", f"beat {beat_id} requires narration")
                continue
            if not isinstance(narration, dict) or not set(narration).issubset(ALLOWED_KEYS):
                fail("NARRATION_CONFIG_FAILED", f"beat {beat_id} narration is malformed")
            if narration.get("enabled", True) is not True:
                if beat_id in required:
                    fail("NARRATION_REQUIRED_FAILED", f"beat {beat_id} requires narration")
                continue
            if narration.get("beat_id", beat_id) != beat_id or beat_id not in beat_map:
                fail("NARRATION_BEAT_FAILED", f"narration linkage for beat {beat_id} is invalid")
            has_source = isinstance(narration.get("source"), str) and bool(narration.get("source"))
            has_generate = narration.get("generate") is True
            if has_source == has_generate:
                fail("NARRATION_CONFIG_FAILED", f"beat {beat_id} must select exactly one narration mode")
            text = narration.get("text", "")
            generation = {"cache": "NOT_APPLICABLE", "provider": "fixture", "voice": None}
            if has_source:
                source = Path(narration["source"])
                source = source if source.is_absolute() else root / source
                if source.suffix.lower() not in ALLOWED_EXTENSIONS:
                    fail("NARRATION_FORMAT_FAILED", f"unsupported narration extension for beat {beat_id}")
                if not source.is_file():
                    fail("NARRATION_MISSING_FAILED", f"narration source for beat {beat_id} does not exist")
                source_type = "fixture"
            else:
                generation_started = time.perf_counter()
                generation = generate(narration, args.cache_dir)
                generated_seconds += time.perf_counter() - generation_started
                source = Path(generation["path"])
                source_type = "generated"
            source_metadata = probe(source)
            normalized = normalized_dir / f"{beat_id}.wav"
            normalization_started = time.perf_counter()
            process = subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-vn",
                "-af", "loudnorm=I=-18:TP=-2:LRA=7", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(normalized)
            ], capture_output=True, text=True)
            normalization_seconds += time.perf_counter() - normalization_started
            if process.returncode != 0:
                fail("NARRATION_NORMALIZATION_FAILED", f"beat {beat_id}: {process.stderr[-300:]}")
            metadata = probe(normalized)
            peak = peak_pcm(normalized)
            if metadata["sample_rate"] != 48000 or metadata["channels"] != 1 or peak >= 0.9999:
                fail("NARRATION_NORMALIZATION_FAILED", f"beat {beat_id} normalization or peak validation failed")
            lead = float(narration.get("lead_in", 0.15))
            tail = float(narration.get("tail_out", 0.15))
            pause_after = float(narration.get("pause_after", 0.0))
            if lead < 0 or tail < 0 or pause_after < 0:
                fail("NARRATION_BEAT_SYNC_FAILED" if strict_sync else "NARRATION_CONFIG_FAILED", f"beat {beat_id} padding cannot be negative")
            beat = beat_map[beat_id]
            transition = str(beat.get("transition", "cut"))
            beat_duration = float(beat["end"]) - float(beat["start"])
            entrance = min(float(grammar.get("motion", {}).get("ENTER", {}).get("seconds", 0.65)), beat_duration * 0.25) if strict_sync and transition != "cut" else 0.0
            exit_duration = min(float(grammar.get("motion", {}).get("EXIT", {}).get("seconds", 0.32)), beat_duration * 0.2) if strict_sync and transition != "cut" else 0.0
            active_start = float(beat["start"]) + entrance
            active_end = float(beat["end"]) - exit_duration
            narration_start = active_start + lead
            narration_limit = active_end - tail - pause_after
            available = narration_limit - narration_start
            semantic_target = narration.get("semantic_target", "media" if beat.get("type") == "media" else "text")
            text_active = semantic_target == "text" and beat.get("type") in {"intro", "statement", "emphasis", "reveal", "outro"} and isinstance(beat.get("text"), str) and bool(beat.get("text", "").strip())
            media_active = semantic_target == "media" and beat.get("type") == "media" and bool(beat.get("media_ref"))
            if strict_sync and semantic_target == "text" and not text_active:
                fail("NARRATION_TEXT_SYNC_FAILED", f"beat {beat_id} narration requires active visible text")
            if strict_sync and semantic_target == "media" and not media_active:
                fail("NARRATION_MEDIA_SYNC_FAILED", f"beat {beat_id} narration requires its media state to be active")
            if metadata["duration"] > available + 0.001:
                fail("NARRATION_BEAT_SYNC_FAILED" if strict_sync else "NARRATION_DURATION_FAILED", f"beat {beat_id} narration {metadata['duration']:.3f}s exceeds {available:.3f}s semantic speech window")
            narration_end = narration_start + metadata["duration"]
            segments.append({
                "beat": beat_id, "beat_start": beat["start"], "beat_end": beat["end"], "entrance_seconds": entrance, "active_start": round(active_start, 6), "active_end": round(active_end, 6), "start": round(narration_start, 6), "end": round(narration_end, 6),
                "speech_window_end": round(narration_limit, 6), "lead_in": lead, "tail_out": tail, "pause_after": pause_after, "semantic_target": semantic_target, "text_active": text_active, "media_active": media_active, "source_type": source_type,
                "source_path": str(source), "audio_path": str(normalized), "duration_seconds": metadata["duration"], "sample_rate": metadata["sample_rate"],
                "channels": metadata["channels"], "peak": round(peak, 6), "text": text, "provenance": narration.get("provenance", {}),
                "provider": generation.get("provider"), "voice": generation.get("voice"), "cache": generation.get("cache"), "cache_key": generation.get("cache_key"),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "normalized_sha256": hashlib.sha256(normalized.read_bytes()).hexdigest(), "status": "PASS"
            })
        if any(item not in {segment["beat"] for segment in segments} for item in required):
            fail("NARRATION_REQUIRED_FAILED", "one or more required narration beats are absent")
        for first, second in zip(segments, segments[1:]):
            if first["end"] > second["start"]:
                fail("NARRATION_OVERLAP_FAILED", f"narration overlaps between {first['beat']} and {second['beat']}")
        result = {"slice": "MF-005", "fixture": fixture.get("id"), "sync_policy": "semantic_beat" if strict_sync else "legacy_window", "result": "PASS", "normalization": {"sample_rate": 48000, "channels": 1, "codec": "pcm_s16le", "integrated_lufs_target": -18, "true_peak_db": -2}, "segments": segments, "metrics": {"preflight_total_seconds": round(time.perf_counter() - started, 6), "generation_seconds": round(generated_seconds, 6), "normalization_seconds": round(normalization_seconds, 6), "cache_hits": sum(item["cache"] == "HIT" for item in segments), "cache_misses": sum(item["cache"] == "MISS" for item in segments)}}
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, wave.Error) as error:
        result = {"slice": "MF-005", "result": "FAIL", "error": str(error)}
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 1
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
