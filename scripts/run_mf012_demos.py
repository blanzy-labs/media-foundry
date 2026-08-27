#!/usr/bin/env python3
"""Render, encode, and validate the five MF-012 activity demonstrations."""

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(command, root: Path, log: Path, timeout=300) -> int:
    started = time.monotonic()
    process = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(process.stdout + ("\n" if process.stdout and process.stderr else "") + process.stderr)
    if process.returncode:
        raise RuntimeError(f"command failed ({process.returncode}): {' '.join(command)}; see {log}")
    return round((time.monotonic() - started) * 1000)


def renderer_state(root: Path) -> dict:
    files = ["godot/mf002.gd", "godot/lofi_book_stage.gd", "godot/extended_data_window_stage.gd",
             "godot/indicator_pulse_stage.gd", "godot/activity_vocabulary_stage.gd", "config/visual-grammar.json"]
    return {name: sha256(root / name) for name in files}


def encode(root: Path, frames: Path, duration: float, output: Path, log: Path) -> int:
    return run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-start_number", "0",
        "-i", str(frames / "frame_%06d.png"), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
        "-map", "0:v:0", "-map", "1:a:0", "-t", str(duration),
        "-vf", "scale=1080:1920:flags=neighbor,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-threads", "1", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-movflags", "+faststart",
        "-metadata", "creation_time=1970-01-01T00:00:00Z", str(output)
    ], root, log, 360)


def render_demo(root: Path, fixture: Path, run_dir: Path) -> dict:
    source = json.loads(fixture.read_text())
    demo_id = fixture.stem
    demo_dir = run_dir / demo_id
    frames = demo_dir / "work/frames"
    validation = demo_dir / "validation"
    logs = demo_dir / "logs"
    evidence = demo_dir / "representative-frames"
    motion = demo_dir / "motion-evidence"
    for path in [frames, validation, logs, evidence, motion]:
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fixture, demo_dir / "fixture.json")
    metrics = {}
    metrics["config_validation_ms"] = run([
        "python3", "scripts/validate_mf012_activity.py", "--mode", "config", "--project-root", str(root),
        "--fixture", str(fixture), "--output", str(validation / "config.json")
    ], root, logs / "config-validation.log", 60)
    metrics["timeline_preflight_ms"] = run([
        "python3", "scripts/preflight_mf004.py", "--fixture", str(fixture), "--grammar", "config/visual-grammar.json",
        "--project-root", ".", "--output", str(validation / "timeline.json")
    ], root, logs / "timeline-preflight.log", 60)
    started = time.monotonic()
    metrics["render_ms"] = run([
        "godot", "--path", "godot", "--fixed-fps", "30", "res://mf002.tscn", "--",
        "--fixture", str(fixture), "--grammar", str(root / "config/visual-grammar.json"),
        "--output-dir", str(frames), "--layout-report", str(validation / "layout.json"),
        "--timeline-report", str(validation / "execution.json")
    ], root, logs / "render.log", 600)
    duration = float(source["format"]["duration_seconds"])
    expected_frames = round(duration * 30)
    frame_count = len(list(frames.glob("frame_*.png")))
    if frame_count != expected_frames:
        raise RuntimeError(f"FRAME_COUNT_INVALID expected={expected_frames} actual={frame_count}")
    media = demo_dir / "demo.mp4"
    metrics["encode_ms"] = encode(root, frames, duration, media, logs / "encode.log")
    metrics["media_validation_ms"] = run([
        "python3", "scripts/validate_media.py", str(media), "--slice", "MF-012",
        "--duration-min", str(duration - .05), "--duration-max", str(duration + .05),
        "--ffprobe-json", str(validation / "ffprobe.json"), "--result-json", str(validation / "media.json")
    ], root, logs / "media-validation.log", 120)
    metrics["output_validation_ms"] = run([
        "python3", "scripts/validate_mf012_activity.py", "--mode", "output", "--project-root", str(root),
        "--fixture", str(fixture), "--layout", str(validation / "layout.json"),
        "--media", str(validation / "media.json"), "--output", str(validation / "output.json")
    ], root, logs / "output-validation.log", 60)
    for fraction, label in [(0.18, "opening"), (0.42, "development"), (0.68, "dominant"), (0.86, "resolution")]:
        frame = min(frame_count - 1, round(duration * fraction * 30))
        shutil.copy2(frames / f"frame_{frame:06d}.png", evidence / f"{label}.png")
    for index in range(12):
        frame = min(frame_count - 1, round(duration * (.05 + index * .075) * 30))
        shutil.copy2(frames / f"frame_{frame:06d}.png", motion / f"{index:02d}-{frame:06d}.png")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", str(motion / "*.png"),
         "-vf", "scale=180:320,tile=4x3:padding=4:margin=4:color=0x070b0f", "-frames:v", "1", str(motion / "sequence.png")],
        root, logs / "motion-sheet.log", 90)
    activity = source["activity"]
    result = {
        "demo_id": demo_id, "state": "READY_FOR_REVIEW", "runtime_seconds": duration, "frame_count": frame_count,
        "dominant_activity": activity["dominant_activity"], "supporting_activities": activity["supporting_activities"],
        "opening_choreography": activity["opening_choreography"], "camera_choreography": activity["camera_choreography"],
        "spatial_behavior": activity["spatial_behavior"], "text_behavior": activity["text_behavior"],
        "activity_sequence": activity["sequence"], "artifact": {"path": str(media), "bytes": media.stat().st_size, "sha256": sha256(media)},
        "motion_evidence": str(motion / "sequence.png"), "representative_frames": str(evidence),
        "render_ms": metrics["render_ms"], "render_ms_per_frame": round(metrics["render_ms"] / frame_count, 3),
        "metrics": metrics, "result": "PASS"
    }
    write_json(demo_dir / "result.json", result)
    shutil.rmtree(demo_dir / "work")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    run_dir = Path(args.run_dir).resolve()
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite: {run_dir}")
    run_dir.mkdir(parents=True)
    before = renderer_state(root)
    results = []
    started = time.monotonic()
    for fixture in sorted((root / "content/fixtures/mf012").glob("*.json")):
        results.append(render_demo(root, fixture, run_dir))
    contact_inputs, filters = [], []
    for index, item in enumerate(results):
        contact_inputs += ["-i", str(run_dir / item["demo_id"] / "representative-frames/dominant.png")]
        filters.append(f"[{index}:v]scale=270:480[v{index}]")
    filters.append("".join(f"[v{index}]" for index in range(len(results))) + f"hstack=inputs={len(results)}")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *contact_inputs,
         "-filter_complex", ";".join(filters), "-frames:v", "1", str(run_dir / "demo-contact-sheet.png")],
        root, run_dir / "demo-contact-sheet.log", 90)
    proof = results[0]
    proof_fixture = root / "content/fixtures/mf012" / f"{proof['demo_id']}.json"
    proof_dir = run_dir / "determinism-proof"
    proof_frames = proof_dir / "frames"
    proof_frames.mkdir(parents=True)
    run(["godot", "--path", "godot", "--fixed-fps", "30", "res://mf002.tscn", "--",
         "--fixture", str(proof_fixture), "--grammar", str(root / "config/visual-grammar.json"),
         "--output-dir", str(proof_frames), "--layout-report", str(proof_dir / "layout.json"),
         "--timeline-report", str(proof_dir / "execution.json")], root, proof_dir / "render.log", 600)
    proof_media = proof_dir / "demo.mp4"
    encode(root, proof_frames, proof["runtime_seconds"], proof_media, proof_dir / "encode.log")
    deterministic = sha256(proof_media) == proof["artifact"]["sha256"]
    write_json(proof_dir / "result.json", {"demo_id": proof["demo_id"], "first_sha256": proof["artifact"]["sha256"],
                                            "second_sha256": sha256(proof_media), "byte_identical": deterministic,
                                            "result": "PASS" if deterministic else "FAIL"})
    shutil.rmtree(proof_frames)
    after = renderer_state(root)
    result = {"slice": "MF-012", "run_dir": str(run_dir), "demos": results, "demo_count": len(results),
              "ready_for_review": sum(item["state"] == "READY_FOR_REVIEW" for item in results),
              "renderer_state_before": before, "renderer_state_after": after,
              "renderer_changes_during_run": 0 if before == after else 1,
              "determinism": "PASS" if deterministic else "FAIL", "elapsed_ms": round((time.monotonic() - started) * 1000),
              "human_review": "PENDING_HUMAN", "published": 0,
              "result": "PASS" if len(results) == 5 and all(item["result"] == "PASS" for item in results) and before == after and deterministic else "FAIL"}
    write_json(run_dir / "result.json", result)
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
