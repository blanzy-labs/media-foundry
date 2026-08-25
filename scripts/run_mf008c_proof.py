#!/usr/bin/env python3
"""Run the bounded supervised MF-008C fixture-only engineering proof."""

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command, root, log, timeout=300):
    started = time.monotonic()
    process = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(process.stdout + ("\n" if process.stdout and process.stderr else "") + process.stderr)
    if process.returncode:
        raise RuntimeError(f"command failed ({process.returncode}): {' '.join(command)}; see {log}")
    return round((time.monotonic() - started) * 1000)


def render(root, fixture, job_dir):
    validation, logs, audio, frames = (job_dir / name for name in ["validation", "logs", "audio", "work/frames"])
    for path in [validation, logs, audio, frames]:
        path.mkdir(parents=True, exist_ok=True)
    fixture_copy = job_dir / "fixture.json"
    shutil.copy2(fixture, fixture_copy)
    commands = [
        (["python3", "scripts/validate_mf008c_creative.py", "--project-root", ".", "--fixture", str(fixture_copy), "--output", str(validation / "creative-preflight.json")], "creative-preflight"),
        (["python3", "scripts/preflight_mf004.py", "--fixture", str(fixture_copy), "--grammar", "config/visual-grammar.json", "--project-root", ".", "--output", str(validation / "timeline-preflight.json")], "timeline-preflight"),
        (["python3", "scripts/prepare_mf005r1_music.py", "--fixture", str(fixture_copy), "--project-root", ".", "--duration", "28", "--output-audio", str(audio / "music.wav"), "--output-report", str(validation / "music.json")], "music"),
        (["python3", "scripts/generate_mf006_sfx.py", "--fixture", str(fixture_copy), "--output", str(audio / "sfx.wav"), "--report", str(validation / "sfx.json")], "sfx"),
    ]
    metrics = {}
    for command, name in commands:
        metrics[name + "_ms"] = run(command, root, logs / f"{name}.log", 180)
    narration = validation / "narration.json"
    narration.write_text(json.dumps({"slice": "MF-008C", "segments": [], "voice_status": "PROHIBITED_FOR_PROOF", "result": "PASS"}, indent=2) + "\n")
    metrics["render_ms"] = run([
        "godot", "--path", "godot", "--fixed-fps", "30", "res://mf002.tscn", "--",
        "--fixture", str(fixture_copy), "--grammar", str(root / "config/visual-grammar.json"),
        "--output-dir", str(frames), "--layout-report", str(validation / "layout.json"),
        "--timeline-report", str(validation / "execution.json")
    ], root, logs / "render.log", 300)
    if len(list(frames.glob("frame_*.png"))) != 840:
        raise RuntimeError(f"expected 840 frames for {fixture.stem}")
    metrics["mix_ms"] = run([
        "python3", "scripts/mix_mf005_audio.py", "--base", str(audio / "sfx.wav"), "--manifest", str(narration),
        "--music-manifest", str(validation / "music.json"), "--duck-db", "-3", "--slice", "MF-008C",
        "--final-lufs", "-15.5", "--final-true-peak", "-2.0", "--output", str(audio / "final.wav"),
        "--report", str(validation / "mix.json")
    ], root, logs / "mix.log", 180)
    media = job_dir / "final.mp4"
    metrics["encode_ms"] = run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-start_number", "0",
        "-i", str(frames / "frame_%06d.png"), "-i", str(audio / "final.wav"), "-map", "0:v:0", "-map", "1:a:0",
        "-t", "28", "-vf", "scale=1080:1920:flags=neighbor,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-threads", "1", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-c:a", "aac",
        "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z", str(media)
    ], root, logs / "encode.log", 300)
    metrics["media_validation_ms"] = run([
        "python3", "scripts/validate_media.py", str(media), "--slice", "MF-008C", "--duration-min", "27.95",
        "--duration-max", "28.05", "--ffprobe-json", str(validation / "ffprobe.json"),
        "--result-json", str(validation / "media.json")
    ], root, logs / "media-validation.log", 180)
    metrics["creative_validation_ms"] = run([
        "python3", "scripts/validate_mf008c_output.py", "--fixture", str(fixture_copy),
        "--creative-preflight", str(validation / "creative-preflight.json"), "--layout", str(validation / "layout.json"),
        "--execution", str(validation / "execution.json"), "--media", str(validation / "media.json"),
        "--music", str(validation / "music.json"), "--output", str(validation / "creative-output.json")
    ], root, logs / "creative-validation.log", 60)
    creative = json.loads(fixture_copy.read_text())["creative"]
    intro = creative["timing"]["intro_seconds"]
    investigation = creative["timing"]["investigation_seconds"]
    evidence = job_dir / "representative-frames"
    motion = job_dir / "motion-evidence"
    evidence.mkdir(); motion.mkdir()
    stamps = [(intro + investigation * .12, "phase-1"), (intro + investigation * .48, "phase-2"),
              (intro + investigation * .82, "phase-3"), (24.8, "cta")]
    for stamp, label in stamps:
        frame = min(839, round(stamp * 30))
        shutil.copy2(frames / f"frame_{frame:06d}.png", evidence / f"{label}.png")
    for index in range(12):
        stamp = intro + investigation * (.05 + index * .075)
        frame = min(839, round(stamp * 30))
        shutil.copy2(frames / f"frame_{frame:06d}.png", motion / f"{index:02d}-{frame:06d}.png")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", str(motion / "*.png"),
         "-vf", "scale=180:320,tile=4x3:padding=4:margin=4:color=0x070b0f", "-frames:v", "1", str(motion / "sequence.png")], root, logs / "motion-sheet.log", 90)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", str(evidence / "*.png"),
         "-vf", "scale=180:320,tile=4x1:padding=4:margin=4:color=0x070b0f", "-frames:v", "1", str(job_dir / "contact-sheet.png")], root, logs / "contact-sheet.log", 90)
    result = {"fixture": fixture.stem, "state": "READY_FOR_REVIEW", "technical": "PASS", "editorial": "PENDING_HUMAN",
              "release": "PENDING_HUMAN", "mechanism": creative["mechanism"], "profiles": {key: creative[key] for key in
              ["palette_profile", "camera_profile", "node_profile", "projection_profile", "cta_profile"]},
              "audio_cue": "baseline_full", "artifact": {"path": str(media), "bytes": media.stat().st_size, "sha256": sha256(media)},
              "renderer_source_state": None, "metrics": metrics, "result": "PASS"}
    (job_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    shutil.rmtree(job_dir / "work")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--archive", default="/home/blanzy/media-foundry-output/mf008c/supervised-proof-001")
    args = parser.parse_args()
    root, archive = Path(args.project_root).resolve(), Path(args.archive).resolve()
    if archive.exists():
        raise SystemExit(f"refusing to overwrite existing proof archive: {archive}")
    archive.mkdir(parents=True)
    renderer_files = [root / "godot/indicator_pulse_stage.gd", root / "godot/lofi_book_stage.gd", root / "godot/mf002.gd"]
    source_state = {str(path.relative_to(root)): sha256(path) for path in renderer_files}
    results = []
    for fixture in sorted((root / "content/fixtures/mf008c").glob("*.json")):
        result = render(root, fixture, archive / fixture.stem)
        current = {str(path.relative_to(root)): sha256(path) for path in renderer_files}
        if current != source_state:
            raise RuntimeError("renderer source changed between fixture-only runs")
        result["renderer_source_state"] = source_state
        (archive / fixture.stem / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
    inputs = []
    for result in results:
        inputs += ["-i", str(archive / result["fixture"] / "representative-frames/phase-3.png")]
    filters = [f"[{index}:v]scale=270:480[v{index}]" for index in range(3)]
    filters.append("[v0][v1][v2]hstack=inputs=3")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters),
         "-frames:v", "1", str(archive / "contact-sheet.png")], root, archive / "contact-sheet.log", 90)
    summary = {"slice": "MF-008C", "run": "supervised-proof-001", "state": "COMPLETE", "jobs": results,
               "renderer_source_state": source_state, "renderer_changes_between_jobs": 0,
               "ready_for_review": 3, "published": 0, "human_review": "PENDING_HUMAN", "result": "PASS_WITH_HUMAN_GATE"}
    (archive / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
