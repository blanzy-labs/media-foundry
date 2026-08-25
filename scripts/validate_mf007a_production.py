#!/usr/bin/env python3
"""Independently validate the MF-007A frozen-picture audio experiment."""

import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
import wave
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command(args, error):
    run = subprocess.run(args, capture_output=True, text=True)
    if run.returncode != 0:
        raise ValueError(f"{error}: {run.stderr[-240:]}")
    return run.stdout, run.stderr


def probe(path):
    stdout, _ = command([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=index,codec_type,codec_name,sample_rate,channels,duration,width,height,r_frame_rate:format=duration",
        "-of", "json", str(path)
    ], "MEDIA_PROBE_FAILED")
    return json.loads(stdout)


def stream_hash(path, selector):
    stdout, _ = command(["ffmpeg", "-v", "error", "-i", str(path), "-map", selector, "-c", "copy", "-f", "hash", "-hash", "sha256", "-"], "STREAM_HASH_FAILED")
    return stdout.strip().split("=", 1)[-1]


def loudness(path):
    _, stderr = command([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-"
    ], "LOUDNESS_MEASUREMENT_FAILED")
    blocks = re.findall(r'\{\s*"input_i".*?\}', stderr, re.DOTALL)
    if not blocks:
        raise ValueError("LOUDNESS_MEASUREMENT_FAILED: no measurement block")
    data = json.loads(blocks[-1])
    return {"integrated_lufs": float(data["input_i"]), "true_peak_db": float(data["input_tp"]), "loudness_range": float(data["input_lra"])}


def decode(path):
    run = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    return run.returncode == 0


def wav_rms_windows(path, windows):
    with wave.open(str(path), "rb") as source:
        if source.getframerate() != 48000 or source.getnchannels() != 2 or source.getsampwidth() != 2:
            raise ValueError("AMBIENT_MIX_FORMAT_FAILED")
        frames = source.readframes(source.getnframes())
    values = [sample[0] / 32768.0 for sample in struct.iter_unpack("<h", frames)]
    results = {}
    for name, start, end in windows:
        first = round(start * 48000) * 2
        last = round(end * 48000) * 2
        selected = values[first:last]
        rms = math.sqrt(sum(value * value for value in selected) / max(1, len(selected)))
        results[name] = round(20 * math.log10(max(rms, 1e-9)), 3)
    return results


def main():
    parser = argparse.ArgumentParser()
    for name in ("project_root", "fixture", "candidate_a", "candidate_b", "ambient", "sfx", "final_mix", "ambient_report", "narration", "output", "audio_timeline"):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    args = parser.parse_args()
    errors = []
    try:
        root = Path(args.project_root)
        fixture = json.loads(Path(args.fixture).read_text())
        source = root / fixture["frozen_visual"]["source"]
        candidate_a = Path(args.candidate_a)
        candidate_b = Path(args.candidate_b)
        narration_path = Path(args.narration)
        narration = json.loads(narration_path.read_text())
        ambient_report = json.loads(Path(args.ambient_report).read_text())
        expected_file_hash = fixture["frozen_visual"]["sha256"]
        source_hash = sha256(source)
        a_hash = sha256(candidate_a)
        b_hash = sha256(candidate_b)
        if source_hash != expected_file_hash or a_hash != expected_file_hash:
            errors.append("CANDIDATE_A_PRESERVATION_FAILED")
        if sha256(narration_path) != fixture["narration"]["source_manifest_sha256"]:
            errors.append("NARRATION_SOURCE_PRESERVATION_FAILED")
        if len(narration.get("segments", [])) != fixture["narration"]["segment_count"] or narration.get("voice_status") != fixture["narration"]["status"]:
            errors.append("NARRATION_STATE_FAILED")
        a_video_hash = stream_hash(candidate_a, "0:v:0")
        b_video_hash = stream_hash(candidate_b, "0:v:0")
        expected_video_hash = fixture["frozen_visual"]["video_stream_sha256"]
        if a_video_hash != expected_video_hash or b_video_hash != expected_video_hash:
            errors.append("VISUAL_STREAM_IDENTITY_FAILED")
        if stream_hash(candidate_a, "0:a:0") == stream_hash(candidate_b, "0:a:0"):
            errors.append("AUDIO_DIRECTION_DIFFERENCE_FAILED")
        for label, media in (("A", candidate_a), ("B", candidate_b)):
            media_probe = probe(media)
            streams = media_probe.get("streams", [])
            video = next((item for item in streams if item.get("codec_type") == "video"), {})
            audio = next((item for item in streams if item.get("codec_type") == "audio"), {})
            if video.get("width") != 1080 or video.get("height") != 1920 or video.get("r_frame_rate") != "30/1":
                errors.append(f"CANDIDATE_{label}_VIDEO_FORMAT_FAILED")
            if abs(float(media_probe.get("format", {}).get("duration", 0)) - 28.0) > 0.05 or audio.get("codec_name") != "aac":
                errors.append(f"CANDIDATE_{label}_MEDIA_FORMAT_FAILED")
            if not decode(media):
                errors.append(f"CANDIDATE_{label}_FULL_DECODE_FAILED")
        if fixture["candidate_b"].get("music_enabled") is not False or fixture["candidate_b"].get("music_sources") != []:
            errors.append("NO_MUSIC_CONTRACT_FAILED")
        if ambient_report.get("music_enabled") is not False or ambient_report.get("music_sources") != []:
            errors.append("NO_MUSIC_EVIDENCE_FAILED")
        if ambient_report.get("no_constant_beeps") is not True or ambient_report.get("no_melodic_or_rhythmic_program") is not True:
            errors.append("NON_MUSICAL_DESIGN_FAILED")
        expected_events = fixture.get("events", [])
        actual_events = ambient_report.get("events", [])
        if [(item.get("id"), item.get("time"), item.get("family")) for item in actual_events] != [(item.get("id"), item.get("time"), item.get("family")) for item in expected_events]:
            errors.append("EVENT_TIMELINE_FAILED")
        if ambient_report.get("ambient", {}).get("start") != 0.0 or ambient_report.get("ambient", {}).get("end") != 28.0:
            errors.append("CONTINUOUS_AMBIENCE_FAILED")
        if ambient_report.get("silent_visuals") != ["orange_indicator_pulses", "powered_wall_cells"]:
            errors.append("SILENT_VISUALS_FAILED")
        for stem in (Path(args.ambient), Path(args.sfx), Path(args.final_mix)):
            if not stem.is_file() or stem.stat().st_size < 100000:
                errors.append("AUDIO_STEM_FAILED")
        window_rms = wav_rms_windows(Path(args.final_mix), [("opening", 0.0, 0.35), ("active", 4.0, 18.5), ("ending", 27.65, 28.0)])
        if not (window_rms["opening"] < window_rms["active"] - 4.0 and window_rms["ending"] < window_rms["active"] - 5.0):
            errors.append("WAKE_POWER_DOWN_ARC_FAILED")
        a_loudness = loudness(candidate_a)
        b_loudness = loudness(candidate_b)
        if abs(a_loudness["integrated_lufs"] - b_loudness["integrated_lufs"]) > 0.5:
            errors.append("LOUDNESS_MATCH_FAILED")
        if abs(b_loudness["integrated_lufs"] - fixture["candidate_b"]["target_integrated_lufs"]) > 0.7 or b_loudness["true_peak_db"] > -1.0:
            errors.append("CANDIDATE_B_LEVEL_FAILED")
        technical = "PASS" if not errors else "FAIL"
        voice = "BLOCKED_PRODUCTION_VOICE" if not narration.get("segments") else "PASS"
        checks = {
            "frozen_visual_baseline": "FAIL" if "CANDIDATE_A_PRESERVATION_FAILED" in errors else "PASS",
            "candidate_a_unchanged": "FAIL" if "CANDIDATE_A_PRESERVATION_FAILED" in errors else "PASS",
            "identical_visual_stream": "FAIL" if "VISUAL_STREAM_IDENTITY_FAILED" in errors else "PASS",
            "audio_only_difference": "FAIL" if "AUDIO_DIRECTION_DIFFERENCE_FAILED" in errors else "PASS",
            "candidate_b_no_music": "PASS" if not any(item.startswith("NO_MUSIC") for item in errors) else "FAIL",
            "continuous_ambient_tech": "FAIL" if "CONTINUOUS_AMBIENCE_FAILED" in errors else "PASS",
            "event_sfx_timeline": "FAIL" if "EVENT_TIMELINE_FAILED" in errors else "PASS",
            "silent_indicator_and_wall_cells": "FAIL" if "SILENT_VISUALS_FAILED" in errors else "PASS",
            "non_musical_no_beep_design": "FAIL" if "NON_MUSICAL_DESIGN_FAILED" in errors else "PASS",
            "wake_and_power_down": "FAIL" if "WAKE_POWER_DOWN_ARC_FAILED" in errors else "PASS",
            "loudness_match": "FAIL" if "LOUDNESS_MATCH_FAILED" in errors else "PASS",
            "valid_streams_and_full_decode": "PASS" if not any("FORMAT_FAILED" in item or "DECODE_FAILED" in item for item in errors) else "FAIL"
        }
        timeline = {
            "slice": "MF-007A", "duration": 28.0, "visual_timeline": "UNCHANGED_MF006R9",
            "candidate_a": {"music_enabled": True, "video_stream_sha256": a_video_hash},
            "candidate_b": {"music_enabled": False, "video_stream_sha256": b_video_hash, "ambient": ambient_report.get("ambient"), "events": actual_events},
            "narration": narration, "result": technical
        }
        Path(args.audio_timeline).parent.mkdir(parents=True, exist_ok=True)
        Path(args.audio_timeline).write_text(json.dumps(timeline, indent=2) + "\n")
        result = {
            "slice": "MF-007A", "checks": checks,
            "baseline": {"path": str(source), "sha256": source_hash, "video_stream_sha256": expected_video_hash},
            "candidate_a": {"path": str(candidate_a), "sha256": a_hash, "video_stream_sha256": a_video_hash, "loudness": a_loudness},
            "candidate_b": {"path": str(candidate_b), "sha256": b_hash, "video_stream_sha256": b_video_hash, "loudness": b_loudness, "music_enabled": False},
            "loudness_delta_lu": round(abs(a_loudness["integrated_lufs"] - b_loudness["integrated_lufs"]), 2),
            "mix_window_rms_dbfs": window_rms,
            "errors": errors,
            "gates": {"audio_visual_technical": technical, "production_voice": voice, "human_ab_review": "PENDING_HUMAN", "winner": "NO_WINNER_PENDING_HUMAN", "release": "RELEASE_ELIGIBLE_NO"},
            "result": "PASS_WITH_BLOCKER" if not errors else "FAIL"
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        result = {"slice": "MF-007A", "errors": [str(error)], "result": "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result.get("result") == "PASS_WITH_BLOCKER" else 1


if __name__ == "__main__":
    raise SystemExit(main())
