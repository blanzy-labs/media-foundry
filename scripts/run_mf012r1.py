#!/usr/bin/env python3
"""Produce and independently validate two MF-012R1 original/refined A/B pairs."""

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


JOBS = [
    {
        "id": "video-01",
        "variant": "restrained",
        "fixture": "content/fixtures/mf012r1/video-01-restrained.json",
        "source_fixture": "content/fixtures/mf011/02-leo-living-data-bridge.json",
        "source_job": "02-leo-living-data-bridge",
    },
    {
        "id": "video-02",
        "variant": "reactive",
        "fixture": "content/fixtures/mf012r1/video-02-reactive.json",
        "source_fixture": "content/fixtures/mf011/06-the-kill-switch.json",
        "source_job": "06-the-kill-switch",
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_hash(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.glob("frame_*.png")):
        digest.update(path.name.encode())
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(command, root: Path, log: Path, timeout=600) -> int:
    started = time.monotonic()
    process = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(process.stdout + ("\n" if process.stdout and process.stderr else "") + process.stderr)
    if process.returncode:
        raise RuntimeError(f"command failed ({process.returncode}): {' '.join(command)}; see {log}")
    return round((time.monotonic() - started) * 1000)


def renderer_state(root: Path) -> dict:
    files = ["godot/mf002.gd", "godot/indicator_pulse_stage.gd", "godot/integrated_lower_right_stage.gd",
             "godot/final_polish_stage.gd", "godot/live_investigation_stage.gd", "godot/extended_data_window_stage.gd",
             "godot/projected_data_window_stage.gd", "godot/lofi_book_stage.gd", "config/visual-grammar.json"]
    return {name: sha256(root / name) for name in files}


def render(root: Path, fixture: Path, frames: Path, validation: Path, log: Path) -> int:
    frames.mkdir(parents=True)
    return run([
        "godot", "--path", "godot", "--fixed-fps", "30", "res://mf002.tscn", "--",
        "--fixture", str(fixture), "--grammar", str(root / "config/visual-grammar.json"),
        "--output-dir", str(frames), "--layout-report", str(validation / "layout.json"),
        "--timeline-report", str(validation / "execution.json"),
    ], root, log, 600)


def encode_with_original_audio(root: Path, frames: Path, source_video: Path, runtime: float, output: Path, log: Path) -> int:
    return run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-start_number", "0",
        "-i", str(frames / "frame_%06d.png"), "-i", str(source_video), "-map", "0:v:0", "-map", "1:a:0",
        "-t", str(runtime), "-vf", "scale=1080:1920:flags=neighbor,format=yuv420p", "-c:v", "libx264",
        "-preset", "medium", "-crf", "20", "-threads", "1", "-g", "60", "-keyint_min", "60",
        "-sc_threshold", "0", "-c:a", "copy", "-movflags", "+faststart",
        "-metadata", "creation_time=1970-01-01T00:00:00Z", str(output),
    ], root, log, 420)


def copy_motion_evidence(root: Path, source_job: Path, frames: Path, job_dir: Path, fixture: dict) -> None:
    original_motion = source_job / "motion-evidence"
    refined_motion = job_dir / "motion-evidence/refined-frames"
    comparison = job_dir / "motion-evidence/comparison-frames"
    refined_motion.mkdir(parents=True)
    comparison.mkdir(parents=True)
    source_frames = sorted(original_motion.glob("[0-9][0-9]-*.png"))
    for index, source_frame in enumerate(source_frames):
        frame_number = int(source_frame.stem.split("-")[-1])
        refined = frames / f"frame_{frame_number:06d}.png"
        copy_name = f"{index:02d}-{frame_number:06d}.png"
        shutil.copy2(refined, refined_motion / copy_name)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source_frame), "-i", str(refined),
             "-filter_complex", "[0:v]scale=270:480[a];[1:v]scale=270:480[b];[a][b]hstack=inputs=2",
             "-frames:v", "1", str(comparison / copy_name)], root, job_dir / f"logs/comparison-frame-{index:02d}.log", 60)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", str(refined_motion / "*.png"),
         "-vf", "scale=180:320,tile=4x3:padding=4:margin=4:color=0x070b0f", "-frames:v", "1", str(job_dir / "motion-evidence/refined-sequence.png")],
        root, job_dir / "logs/refined-sequence.log", 90)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", str(comparison / "*.png"),
         "-vf", "scale=360:320,tile=4x3:padding=4:margin=4:color=0x070b0f", "-frames:v", "1", str(job_dir / "motion-evidence/comparison-sequence.png")],
        root, job_dir / "logs/comparison-sequence.log", 90)
    shutil.copy2(original_motion / "sequence.png", job_dir / "motion-evidence/original-sequence.png")
    for name in ["phase-1.png", "phase-2.png", "phase-3.png", "cta.png"]:
        shutil.copy2(source_job / "representative-frames" / name, job_dir / "original-reference/representative-frames" / name)
    creative = fixture["creative"]
    intro, investigation, runtime = creative["timing"]["intro_seconds"], creative["timing"]["investigation_seconds"], fixture["format"]["duration_seconds"]
    evidence = job_dir / "refined/representative-frames"
    evidence.mkdir(parents=True)
    for stamp, label in [(intro + investigation * .12, "phase-1"), (intro + investigation * .48, "phase-2"),
                         (intro + investigation * .82, "phase-3"), (runtime - 3.0, "cta")]:
        frame = min(round(runtime * 30) - 1, round(stamp * 30))
        shutil.copy2(frames / f"frame_{frame:06d}.png", evidence / f"{label}.png")


def run_job(root: Path, archive: Path, run_dir: Path, definition: dict) -> dict:
    job_dir = run_dir / definition["id"]
    source_job = archive / definition["source_job"]
    source_video = source_job / "final.mp4"
    fixture_path = root / definition["fixture"]
    source_fixture_path = root / definition["source_fixture"]
    fixture = json.loads(fixture_path.read_text())
    runtime = float(fixture["format"]["duration_seconds"])
    frames = job_dir / "work/frames"
    validation = job_dir / "validation"
    logs = job_dir / "logs"
    for path in [validation, logs, job_dir / "original-reference/representative-frames", job_dir / "refined"]:
        path.mkdir(parents=True, exist_ok=True)
    original_copy = job_dir / "original-reference/video-original.mp4"
    shutil.copy2(source_video, original_copy)
    shutil.copy2(source_fixture_path, job_dir / "original-reference/fixture.json")
    shutil.copy2(fixture_path, job_dir / "refined/fixture.json")
    for relative in ["result.json", "job-brief.json", "resolved-config.json", "validation/music-selection.json",
                     "validation/music.json", "validation/mix.json", "validation/sfx.json", "validation/narration.json"]:
        destination = job_dir / "original-reference" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_job / relative, destination)
    metrics = {}
    metrics["config_validation_ms"] = run([
        "python3", "scripts/validate_mf012r1.py", "--mode", "config", "--project-root", str(root),
        "--fixture", str(fixture_path), "--source-fixture", str(source_fixture_path), "--output", str(validation / "config.json")
    ], root, logs / "config-validation.log", 60)
    metrics["timeline_preflight_ms"] = run([
        "python3", "scripts/preflight_mf004.py", "--fixture", str(fixture_path), "--grammar", "config/visual-grammar.json",
        "--project-root", ".", "--output", str(validation / "timeline.json")
    ], root, logs / "timeline-preflight.log", 60)
    metrics["render_ms"] = render(root, fixture_path, frames, validation, logs / "render.log")
    expected_frames = round(runtime * 30)
    if len(list(frames.glob("frame_*.png"))) != expected_frames:
        raise RuntimeError("refined frame count mismatch")
    refined_video = job_dir / "refined/video-micro-variation.mp4"
    metrics["encode_ms"] = encode_with_original_audio(root, frames, source_video, runtime, refined_video, logs / "encode.log")
    metrics["media_validation_ms"] = run([
        "python3", "scripts/validate_media.py", str(refined_video), "--slice", "MF-012R1",
        "--duration-min", str(runtime - .01), "--duration-max", str(runtime + .01),
        "--ffprobe-json", str(validation / "ffprobe.json"), "--result-json", str(validation / "media.json")
    ], root, logs / "media-validation.log", 180)
    metrics["output_validation_ms"] = run([
        "python3", "scripts/validate_mf012r1.py", "--mode", "output", "--project-root", str(root),
        "--fixture", str(fixture_path), "--source-fixture", str(source_fixture_path), "--source-video", str(source_video),
        "--refined-video", str(refined_video), "--source-job-dir", str(source_job), "--layout", str(validation / "layout.json"),
        "--media", str(validation / "media.json"), "--output", str(validation / "output.json")
    ], root, logs / "output-validation.log", 180)
    copy_motion_evidence(root, source_job, frames, job_dir, fixture)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source_video), "-i", str(refined_video),
         "-filter_complex", "[0:v]scale=270:480[a];[1:v]scale=270:480[b];[a][b]hstack=inputs=2[v]",
         "-map", "[v]", "-map", "0:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-threads", "1",
         "-c:a", "copy", "-t", str(runtime), "-metadata", "creation_time=1970-01-01T00:00:00Z",
         str(job_dir / "motion-evidence/original-vs-refined.mp4")], root, logs / "comparison-video.log", 360)
    first_tree_hash = tree_hash(frames)
    proof_frames = job_dir / "work/determinism-frames"
    proof_validation = job_dir / "work/determinism-validation"
    metrics["determinism_render_ms"] = render(root, fixture_path, proof_frames, proof_validation, logs / "determinism-render.log")
    second_tree_hash = tree_hash(proof_frames)
    deterministic = first_tree_hash == second_tree_hash
    write_json(validation / "determinism.json", {"first_frame_tree_sha256": first_tree_hash, "second_frame_tree_sha256": second_tree_hash,
                                                  "byte_identical": deterministic, "result": "PASS" if deterministic else "FAIL"})
    legacy_frames = job_dir / "work/legacy-frames"
    legacy_validation = job_dir / "work/legacy-validation"
    metrics["legacy_render_ms"] = render(root, source_fixture_path, legacy_frames, legacy_validation, logs / "legacy-render.log")
    creative = fixture["creative"]
    phase_frame = round((creative["timing"]["intro_seconds"] + creative["timing"]["investigation_seconds"] * .82) * 30)
    archived_phase = source_job / "representative-frames/phase-3.png"
    legacy_phase = legacy_frames / f"frame_{phase_frame:06d}.png"
    legacy_equal = sha256(archived_phase) == sha256(legacy_phase)
    write_json(validation / "legacy-default.json", {"frame": phase_frame, "archived_sha256": sha256(archived_phase),
                                                      "rerendered_sha256": sha256(legacy_phase), "byte_identical": legacy_equal,
                                                      "result": "PASS" if legacy_equal else "FAIL"})
    output_validation = json.loads((validation / "output.json").read_text())
    result = {
        "id": definition["id"], "variant": definition["variant"], "source_job": definition["source_job"],
        "source": {"path": str(source_video), "preserved_path": str(original_copy), "sha256": sha256(source_video), "bytes": source_video.stat().st_size},
        "refined": {"path": str(refined_video), "sha256": sha256(refined_video), "bytes": refined_video.stat().st_size},
        "runtime_seconds": runtime, "frame_count": expected_frames, "micro_variation": fixture["micro_variation"],
        "audio_packet_sha256": output_validation["audio"]["source_packet_sha256"],
        "audio_packet_identical": output_validation["checks"]["audio_packet_identity"] == "PASS",
        "text_identical": output_validation["checks"]["text_equivalence"] == "PASS",
        "cue_identical": output_validation["checks"]["cue_identity"] == "PASS",
        "safe_zone": output_validation["checks"]["safe_zone"], "motion_budget": output_validation["checks"]["motion_budget"],
        "determinism": "PASS" if deterministic else "FAIL", "legacy_default": "PASS" if legacy_equal else "FAIL",
        "motion_evidence": str(job_dir / "motion-evidence/original-vs-refined.mp4"), "metrics": metrics,
        "human_review": "PENDING_HUMAN", "published": False,
        "result": "PASS" if output_validation["result"] == "PASS" and deterministic and legacy_equal else "FAIL",
    }
    write_json(job_dir / "result.json", result)
    shutil.rmtree(job_dir / "work")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--source-archive", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    root, archive, run_dir = Path(args.project_root).resolve(), Path(args.source_archive).resolve(), Path(args.run_dir).resolve()
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite: {run_dir}")
    run_dir.mkdir(parents=True)
    before, started = renderer_state(root), time.monotonic()
    results = [run_job(root, archive, run_dir, job) for job in JOBS]
    after = renderer_state(root)
    failures_path = run_dir / "failure-tests.json"
    run(["python3", "scripts/test_mf012r1_failures.py", "--project-root", str(root), "--output", str(failures_path)], root, run_dir / "failure-tests.log", 60)
    failures = json.loads(failures_path.read_text())
    result = {
        "slice": "MF-012R1", "source_archive": str(archive), "run_dir": str(run_dir), "jobs": results,
        "job_count": len(results), "ready_for_review": sum(job["result"] == "PASS" for job in results),
        "renderer_state_before": before, "renderer_state_after": after, "renderer_changes_during_run": 0 if before == after else 1,
        "failure_tests": failures["result"], "human_review": "PENDING_HUMAN", "approved_micro_variations": [],
        "published": 0, "elapsed_ms": round((time.monotonic() - started) * 1000),
        "result": "PASS" if len(results) == 2 and all(job["result"] == "PASS" for job in results) and before == after and failures["result"] == "PASS" else "FAIL",
    }
    write_json(run_dir / "result.json", result)
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
