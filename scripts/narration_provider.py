#!/usr/bin/env python3
"""Small provider boundary for optional generated MF-005 narration."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


PROVIDER = "local_ffmpeg_flite"
PROVIDER_VERSION = "ffmpeg-flite-v1"
VOICES = {"slt", "kal", "kal16", "awb", "rms"}


def cache_key(request):
    relevant = {
        "provider": request.get("provider", PROVIDER),
        "provider_version": PROVIDER_VERSION,
        "voice": request.get("voice", "slt"),
        "text": request.get("text", ""),
        "speech_settings": request.get("speech_settings", {}),
    }
    return hashlib.sha256(json.dumps(relevant, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def generate(request, cache_dir):
    provider = request.get("provider", PROVIDER)
    voice = request.get("voice", "slt")
    text = request.get("text", "")
    if provider != PROVIDER or shutil.which("ffmpeg") is None:
        raise ValueError("NARRATION_PROVIDER_FAILED: required local_ffmpeg_flite provider is unavailable")
    if voice not in VOICES:
        raise ValueError(f"NARRATION_VOICE_FAILED: unsupported voice {voice!r}")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("NARRATION_PROVIDER_FAILED: generated narration requires text")
    key = cache_key(request)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio = cache_dir / f"{key}.wav"
    metadata = cache_dir / f"{key}.json"
    if audio.exists() or metadata.exists():
        if not audio.is_file() or not metadata.is_file():
            raise ValueError("NARRATION_CACHE_FAILED: incomplete cache entry")
        try:
            record = json.loads(metadata.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"NARRATION_CACHE_FAILED: corrupt metadata: {error}") from error
        digest = hashlib.sha256(audio.read_bytes()).hexdigest()
        if record.get("cache_key") != key or record.get("sha256") != digest:
            raise ValueError("NARRATION_CACHE_FAILED: cache hash or request key mismatch")
        return {"path": str(audio), "cache": "HIT", "cache_key": key, "provider": provider, "provider_version": PROVIDER_VERSION, "voice": voice, "sha256": digest}
    expression = f"flite=text={json.dumps(text)}:voice={voice}"
    process = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", expression, str(audio)], capture_output=True, text=True)
    if process.returncode != 0 or not audio.is_file():
        raise ValueError(f"NARRATION_PROVIDER_FAILED: Flite generation failed: {process.stderr[-300:]}")
    digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    record = {"cache_key": key, "provider": provider, "provider_version": PROVIDER_VERSION, "voice": voice, "text": text, "sha256": digest}
    metadata.write_text(json.dumps(record, indent=2) + "\n")
    return {"path": str(audio), "cache": "MISS", "cache_key": key, "provider": provider, "provider_version": PROVIDER_VERSION, "voice": voice, "sha256": digest}
