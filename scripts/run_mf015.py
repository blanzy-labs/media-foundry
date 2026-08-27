#!/usr/bin/env python3
"""Render and package the deterministic MF-015 pulp-trailer capability test."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

from pulp_trailer_stage import PulpTrailerStage
from run_mf014 import make_contact_sheet, sha256, write_json
from run_mf014r1 import measure_audio


def generate_temporary_score(path: Path, definition: dict) -> str:
    sample_rate = definition["audio"]["sample_rate"]
    duration = definition["video"]["duration_seconds"]
    count = round(sample_rate * duration)
    t = np.arange(count, dtype=np.float64) / sample_rate
    rng = np.random.default_rng(definition["seed"] + 7000)
    score = np.zeros(count, dtype=np.float64)
    # Low orchestral/oscillator bed with slowly opening harmonics.
    score += .20 * np.sin(2 * np.pi * 55 * t + .20 * np.sin(2 * np.pi * .11 * t))
    score += .095 * np.sin(2 * np.pi * 82.5 * t)
    escalation = np.clip((t - 3.6) / 20.0, 0, 1)
    score += escalation * .075 * np.sin(2 * np.pi * 110 * t + .7 * np.sin(2 * np.pi * .23 * t))
    # Restrained theremin-like line; serious and low in the mix.
    theremin_frequency = 285 + 44 * np.sin(2 * np.pi * .071 * t) + 22 * escalation
    theremin_phase = np.cumsum(2 * np.pi * theremin_frequency / sample_rate)
    theremin_gate = np.clip((t - 4.2) / 1.2, 0, 1) * np.clip((25.0 - t) / 1.1, 0, 1)
    score += .07 * theremin_gate * np.sin(theremin_phase + .35 * np.sin(2 * np.pi * 4.6 * t))
    # Primitive mechanical pulse rises with the machine.
    pulse_rate = 1.15 + 1.3 * escalation
    pulse_phase = np.cumsum(pulse_rate / sample_rate) % 1
    score += (.018 + .055 * escalation) * np.where(pulse_phase < .10, np.exp(-pulse_phase * 38), 0)
    # Editorial brass/percussion impacts at hard cuts.
    cuts = (1.0, 3.6, 7.0, 8.15, 12.5, 13.65, 18.0, 19.15, 24.6)
    for index, cut in enumerate(cuts):
        local = t - cut
        active = (local >= 0) & (local < 1.25)
        envelope = np.exp(-local[active] * (3.0 if index < 5 else 2.2))
        score[active] += envelope * (.19 * np.sin(2 * np.pi * (47 + index % 3 * 7) * local[active])
                                      + .08 * np.sin(2 * np.pi * 94 * local[active]))
    # Reactor rise and short peak, plus very quiet projector texture.
    peak = np.clip((t - 19.15) / 4.5, 0, 1) * np.clip((24.65 - t) / .8, 0, 1)
    score += peak * .12 * np.sin(2 * np.pi * (145 + 35 * peak) * t)
    noise = rng.normal(0, 1, count)
    projector = noise - np.concatenate(([0], noise[:-1]))
    score += .006 * projector
    for click in np.arange(.12, duration, 1 / 18):
        index = int(click * sample_rate)
        if index + 55 < count:
            score[index:index + 55] += np.hanning(110)[:55] * rng.uniform(.035, .07)
    fade_in = np.clip(t / definition["audio"]["fade_in_seconds"], 0, 1)
    fade_out = np.clip((duration - t) / definition["audio"]["fade_out_seconds"], 0, 1)
    score *= fade_in * fade_out
    score /= max(np.max(np.abs(score)), 1e-9)
    pcm = np.int16(np.clip(score * .78, -1, 1) * 32767)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(sample_rate); output.writeframes(pcm.tobytes())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(stage: PulpTrailerStage, output: Path, log_path: Path) -> str:
    command = ["ffmpeg", "-y", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size",
               f"{stage.size[0]}x{stage.size[1]}", "-framerate", str(stage.fps), "-i", "-", "-an",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    digest = hashlib.sha256()
    with log_path.open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=log, stderr=log)
        try:
            assert process.stdin is not None
            for frame_index in range(stage.frame_count):
                raw = stage.render_frame(frame_index).tobytes()
                digest.update(raw)
                process.stdin.write(raw)
            process.stdin.close()
            code = process.wait()
        except BrokenPipeError:
            code = process.wait()
        if code != 0:
            raise RuntimeError(f"video encoding failed; see {log_path}")
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf015-pulp-trailer.json")
    parser.add_argument("--artifacts", default="artifacts/mf-015")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    config_path, artifacts = root / args.config, root / args.artifacts
    if artifacts.exists():
        raise SystemExit(f"refusing to overwrite: {artifacts}")
    definition = json.loads(config_path.read_text())
    if "prior_artifact" in definition:
        prior = root / definition["prior_artifact"]["path"]
        if not prior.is_file() or sha256(prior) != definition["prior_artifact"]["sha256"]:
            raise SystemExit("declared prior artifact is missing or changed")
    source = Path(definition["source_reference"]["path"])
    if not source.is_file() or sha256(source) != definition["source_reference"]["sha256"]:
        raise SystemExit("source cover is missing or changed")
    for font in definition["fonts"].values():
        if not Path(font).is_file():
            raise SystemExit(f"font missing: {font}")
    stage_class = PulpTrailerStage
    if "stage" in definition:
        module_name, class_name = definition["stage"].split(":", 1)
        stage_class = getattr(importlib.import_module(module_name), class_name)
    stage = stage_class(definition)
    for directory in (artifacts, artifacts / "representative-frames", artifacts / "motion-evidence",
                      artifacts / "validation", artifacts / "logs", artifacts / "audio"):
        directory.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=".work-", dir=artifacts) as temporary:
        temporary = Path(temporary)
        video_only = temporary / "video-only.mp4"
        score = artifacts / "audio/temporary-retro-futurist-score.wav"
        score_sha = generate_temporary_score(score, definition)
        raw_hash = encode(stage, video_only, artifacts / "logs/video-encode.log")
        final = artifacts / "final-test.mp4"
        audio = definition["audio"]
        filter_value = (f"highpass=f=42,lowpass=f=9600,loudnorm=I={audio['target_lufs']}:"
                        f"TP={audio['true_peak_limit_db']}:LRA=8")
        command = ["ffmpeg", "-y", "-v", "error", "-i", str(video_only), "-i", str(score),
                   "-filter:a", filter_value, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                   "-b:a", "192k", "-t", str(definition["video"]["duration_seconds"]), "-movflags", "+faststart", str(final)]
        mux = subprocess.run(command, capture_output=True, text=True)
        (artifacts / "logs/audio-mux.log").write_text(mux.stdout + mux.stderr)
        if mux.returncode != 0:
            raise RuntimeError("audio mux failed")
    frame_paths = []
    for timestamp, name in definition["representative_frames"]:
        path = artifacts / "representative-frames" / f"{name}.png"
        stage.render_frame(min(stage.frame_count - 1, round(timestamp * stage.fps))).save(path, optimize=True)
        frame_paths.append(path)
    make_contact_sheet(frame_paths, [name for _, name in definition["representative_frames"]],
                       artifacts / "motion-evidence/trailer-sequence.png")
    levels = measure_audio(final)
    audio_summary = {"status": definition["audio"]["status"], "source": definition["audio"]["source"],
                     "path": str(artifacts / "audio/temporary-retro-futurist-score.wav"), "sha256": score_sha,
                     "generated": True, "copyright": "locally generated temporary test score", "narration": False,
                     "processing": filter_value, "levels": levels}
    write_json(artifacts / "validation/audio-summary.json", audio_summary)
    manifest = {"slice": definition["slice"], "config": str(config_path), "config_sha256": sha256(config_path),
                "seed": definition["seed"], "source_reference": {**definition["source_reference"], "verified": True},
                "output": {"path": str(final), "sha256": sha256(final), "bytes": final.stat().st_size},
                "video": {**definition["video"], "frame_count": stage.frame_count, "raw_frame_sequence_sha256": raw_hash},
                "timeline": definition["timeline"], "machine": definition["machine"], "film": definition["film"],
                "audio": audio_summary, "representative_frames": [str(path) for path in frame_paths],
                "motion_evidence": str(artifacts / "motion-evidence/trailer-sequence.png"),
                "elapsed_ms": round((time.monotonic() - started) * 1000), "human_review": "PENDING_HUMAN",
                "published": False}
    if "prior_artifact" in definition:
        manifest["prior_artifact"] = definition["prior_artifact"]
    write_json(artifacts / "render-manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
