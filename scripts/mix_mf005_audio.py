#!/usr/bin/env python3
"""Deterministically mix normalized beat narration over the existing cue/bed track."""

import argparse
import json
import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path


def read_pcm(path):
    with wave.open(str(path), "rb") as wav:
        if wav.getframerate() != 48000 or wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError(f"AUDIO_MIX_FAILED: {path} must be 48 kHz mono PCM16")
        raw = wav.readframes(wav.getnframes())
    return [value[0] / 32768.0 for value in struct.iter_unpack("<h", raw)]


def rms_db(samples):
    if not samples:
        return -120.0
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    return 20.0 * math.log10(max(rms, 1e-6))


def write_pcm(path, samples, rate=48000):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate)
        wav.writeframes(b"".join(struct.pack("<h", round(value * 32767)) for value in samples))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--duck-db", type=float, default=-6.0)
    parser.add_argument("--music-manifest")
    parser.add_argument("--slice", default=None)
    parser.add_argument("--final-lufs", type=float)
    parser.add_argument("--final-true-peak", type=float, default=-1.5)
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    base = read_pcm(Path(args.base))
    rate, attack = 48000, round(0.03 * 48000)
    duck_gain = 10.0 ** (args.duck_db / 20.0)
    gains = [1.0] * len(base)
    narration = [0.0] * len(base)
    music = [0.0] * len(base)
    music_gains = [1.0] * len(base)
    music_state = {"status": "NOT_PRESENT"}
    music_attack = music_release = attack
    music_duck_gain = 1.0
    if args.music_manifest:
        music_manifest = json.loads(Path(args.music_manifest).read_text())
        if music_manifest.get("result") != "PASS": raise ValueError("AUDIO_MIX_FAILED: music preparation did not pass")
        if music_manifest.get("status") == "PASS":
            music = read_pcm(Path(music_manifest["audio_path"]))
            if len(music) != len(base): raise ValueError("AUDIO_MIX_FAILED: music bed duration differs from production")
            music_attack = round(float(music_manifest["attack_ms"]) * rate / 1000.0)
            music_release = round(float(music_manifest["release_ms"]) * rate / 1000.0)
            music_duck_gain = 10.0 ** (float(music_manifest["narration_duck_db"]) / 20.0)
            music_state = {"status": "PASS", "start": 0.0, "end": len(music) / rate, "gain_db": music_manifest["gain_db"], "narration_duck_db": music_manifest["narration_duck_db"], "attack_ms": music_manifest["attack_ms"], "release_ms": music_manifest["release_ms"]}
    evidence = []
    for segment in manifest.get("segments", []):
        voice = read_pcm(Path(segment["audio_path"]))
        start = round(float(segment["start"]) * rate)
        end = min(len(base), start + len(voice))
        if end - start != len(voice):
            raise ValueError(f"AUDIO_MIX_FAILED: narration {segment['beat']} escapes final duration")
        for index, value in enumerate(voice):
            narration[start + index] += value
        for index in range(max(0, start - attack), min(len(base), end + attack)):
            if index < start:
                fraction = (index - (start - attack)) / attack
                gain = 1.0 + (duck_gain - 1.0) * fraction
            elif index >= end:
                fraction = (index - end) / attack
                gain = duck_gain + (1.0 - duck_gain) * fraction
            else:
                gain = duck_gain
            gains[index] = min(gains[index], gain)
        if music_state["status"] == "PASS":
            for index in range(max(0, start - music_attack), min(len(base), end + music_release)):
                if index < start:
                    fraction = (index - (start - music_attack)) / max(1, music_attack)
                    gain = 1.0 + (music_duck_gain - 1.0) * fraction
                elif index >= end:
                    fraction = (index - end) / max(1, music_release)
                    gain = music_duck_gain + (1.0 - music_duck_gain) * fraction
                else:
                    gain = music_duck_gain
                music_gains[index] = min(music_gains[index], gain)
        evidence.append({"beat": segment["beat"], "start": segment["start"], "end": segment["end"], "narration_rms_dbfs": round(rms_db(voice), 3), "status": "PASS"})
    mixed, clipped = [], 0
    for index in range(len(base)):
        value = base[index] * gains[index] + music[index] * music_gains[index] + narration[index]
        if abs(value) > 1.0:
            clipped += 1
        mixed.append(max(-1.0, min(1.0, value)))
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    pre_normalization_peak = max(abs(value) for value in mixed)
    normalization = {"enabled": False}
    if args.final_lufs is None:
        write_pcm(output, mixed)
    else:
        if not -24 <= args.final_lufs <= -12 or not -3 <= args.final_true_peak <= -1:
            raise ValueError("AUDIO_NORMALIZATION_FAILED: final loudness target is outside supported limits")
        with tempfile.TemporaryDirectory(prefix="mf005-mix-") as directory:
            raw = Path(directory) / "pre-normalized.wav"; write_pcm(raw, mixed)
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw), "-af", f"loudnorm=I={args.final_lufs}:TP={args.final_true_peak}:LRA=7", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(output)]
            process = subprocess.run(command, capture_output=True, text=True)
            if process.returncode != 0:
                raise ValueError(f"AUDIO_NORMALIZATION_FAILED: {process.stderr[-300:]}")
        mixed = read_pcm(output)
        normalization = {"enabled": True, "integrated_lufs_target": args.final_lufs, "true_peak_db_target": args.final_true_peak, "implementation": "ffmpeg_loudnorm_single_pass"}
    final_peak = max(abs(value) for value in mixed)
    report = {"slice": args.slice or ("MF-005R1" if args.music_manifest else "MF-005"), "result": "PASS" if clipped == 0 and final_peak < 1.0 else "FAIL", "priority": ["narration", "content_cues", "ambient_music"], "base_audio": str(Path(args.base)), "duck_db": args.duck_db, "content_duck_db": args.duck_db, "attack_release_seconds": 0.03, "music": music_state, "ducking_windows": [{"beat": item["beat"], "start": item["start"], "end": item["end"], "music_gain_db": music_state.get("narration_duck_db")} for item in evidence] if music_state["status"] == "PASS" else [], "clipped_samples": clipped, "segments": evidence, "normalization": normalization, "pre_normalization_peak": round(pre_normalization_peak, 6), "final_peak": round(final_peak, 6), "final_rms_dbfs": round(rms_db(mixed), 3)}
    report_path = Path(args.report); report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if clipped == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
