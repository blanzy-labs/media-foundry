#!/usr/bin/env python3
"""Run the unattended manifest-driven MF-011 ten-video campaign."""

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


PROFILE_NAMES = ["palette_profile", "camera_profile", "node_profile", "projection_profile", "cta_profile"]


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def object_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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


def renderer_state(root: Path, grammar: dict) -> dict:
    return {relative: sha256(root / relative) for relative in grammar["files"] if relative.startswith("godot/")}


def transition_campaign(state: dict, state_path: Path, value: str, detail=None) -> None:
    state["state"] = value
    event = {"state": value, "at": now()}
    if detail:
        event["detail"] = detail
    state["transitions"].append(event)
    write_json(state_path, state)


def transition_job(state: dict, state_path: Path, job_state: dict, value: str, detail=None) -> None:
    job_state["state"] = value
    event = {"state": value, "at": now()}
    if detail:
        event["detail"] = detail
    job_state["transitions"].append(event)
    write_json(state_path, state)


def render_job(root: Path, job: dict, run_dir: Path) -> dict:
    job_dir = run_dir / job["id"]
    validation = job_dir / "validation"
    logs = job_dir / "logs"
    audio = job_dir / "audio"
    frames = job_dir / "work/frames"
    for path in [validation, logs, audio, frames]:
        path.mkdir(parents=True, exist_ok=True)
    fixture = root / job["fixture"]
    fixture_copy = job_dir / "resolved-config.json"
    shutil.copy2(fixture, fixture_copy)
    job_path = job_dir / "job-brief.json"
    write_json(job_path, job)
    write_json(job_dir / "resolved-creative-profile.json", job["creative"])
    runtime = float(job["music"]["video_duration"])
    selection = job["music"]
    catalog = json.loads((root / "config/music/catalog.json").read_text())
    track_record = next(track for track in catalog["tracks"] if track["id"] == selection["track_id"])
    region_record = next(region for region in track_record["cue_regions"] if region["id"] == selection["region_id"])
    metrics = {}
    selection_command = [
        "python3", "scripts/music_cue.py", "--root", str(root), "--catalog", str(root / "config/music/catalog.json"),
        "select", "unknown-process", selection["track_id"], selection["region_id"],
        "--actual-start", str(selection["actual_start"]), "--actual-end", str(selection["actual_end"]),
        "--video-duration", str(runtime), "--fade-in", str(selection["fade_in"]), "--fade-out", str(selection["fade_out"]),
        "--output", str(validation / "music-selection.json"), "--json",
    ]
    metrics["selection_ms"] = run(selection_command, root, logs / "music-selection.log", 60)
    commands = [
        (["python3", "scripts/validate_mf008c_creative.py", "--project-root", ".", "--fixture", str(fixture_copy),
          "--output", str(validation / "creative-preflight.json")], "creative-preflight", 60),
        (["python3", "scripts/preflight_mf004.py", "--fixture", str(fixture_copy), "--grammar", "config/visual-grammar.json",
          "--project-root", ".", "--output", str(validation / "timeline-preflight.json")], "timeline-preflight", 60),
        (["python3", "scripts/prepare_mf005r1_music.py", "--fixture", str(fixture_copy), "--project-root", ".",
          "--duration", str(runtime), "--output-audio", str(audio / "music.wav"),
          "--output-report", str(validation / "music.json")], "music", 180),
        (["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
          "-t", str(runtime), "-c:a", "pcm_s16le", str(audio / "silence.wav")], "silence", 90),
    ]
    for command, name, timeout in commands:
        metrics[name + "_ms"] = run(command, root, logs / f"{name}.log", timeout)
    write_json(validation / "sfx.json", {
        "slice": "MF-011", "policy": "disabled", "event_count": 0,
        "ambient_machine_audio": False, "generated_audio": False, "result": "PASS"
    })
    write_json(validation / "narration.json", {
        "slice": "MF-011", "policy": "off", "segments": [],
        "voice_status": "NOT_REQUESTED", "result": "PASS"
    })
    metrics["render_ms"] = run([
        "godot", "--path", "godot", "--fixed-fps", "30", "res://mf002.tscn", "--",
        "--fixture", str(fixture_copy), "--grammar", str(root / "config/visual-grammar.json"),
        "--output-dir", str(frames), "--layout-report", str(validation / "layout.json"),
        "--timeline-report", str(validation / "execution.json")
    ], root, logs / "render.log", 1200)
    expected_frames = round(runtime * 30)
    frame_count = len(list(frames.glob("frame_*.png")))
    if frame_count != expected_frames:
        raise RuntimeError(f"GODOT_FRAME_COUNT_INVALID expected={expected_frames} actual={frame_count}")
    metrics["mix_ms"] = run([
        "python3", "scripts/mix_mf005_audio.py", "--base", str(audio / "silence.wav"),
        "--manifest", str(validation / "narration.json"), "--music-manifest", str(validation / "music.json"),
        "--duck-db", "-3", "--slice", "MF-011", "--final-lufs", "-15.5", "--final-true-peak", "-2.0",
        "--output", str(audio / "final.wav"), "--report", str(validation / "mix.json")
    ], root, logs / "mix.log", 180)
    media = job_dir / "final.mp4"
    metrics["encode_ms"] = run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-start_number", "0",
        "-i", str(frames / "frame_%06d.png"), "-i", str(audio / "final.wav"), "-map", "0:v:0", "-map", "1:a:0",
        "-t", str(runtime), "-vf", "scale=1080:1920:flags=neighbor,format=yuv420p", "-c:v", "libx264",
        "-preset", "medium", "-crf", "20", "-threads", "1", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart",
        "-metadata", "creation_time=1970-01-01T00:00:00Z", str(media)
    ], root, logs / "encode.log", 420)
    metrics["media_validation_ms"] = run([
        "python3", "scripts/validate_media.py", str(media), "--slice", "MF-011",
        "--duration-min", str(runtime - .05), "--duration-max", str(runtime + .05),
        "--ffprobe-json", str(validation / "ffprobe.json"), "--result-json", str(validation / "media.json")
    ], root, logs / "media-validation.log", 180)
    metrics["output_validation_ms"] = run([
        "python3", "scripts/validate_mf011.py", "--mode", "job-output", "--job", str(job_path),
        "--fixture", str(fixture_copy), "--layout", str(validation / "layout.json"),
        "--execution", str(validation / "execution.json"), "--media", str(validation / "media.json"),
        "--music", str(validation / "music.json"), "--mix", str(validation / "mix.json"),
        "--selection", str(validation / "music-selection.json"), "--sfx", str(validation / "sfx.json"),
        "--narration", str(validation / "narration.json"), "--output", str(validation / "output.json")
    ], root, logs / "output-validation.log", 60)
    creative = job["creative"]
    intro = creative["timing"]["intro_seconds"]
    investigation = creative["timing"]["investigation_seconds"]
    evidence = job_dir / "representative-frames"
    motion = job_dir / "motion-evidence"
    evidence.mkdir()
    motion.mkdir()
    for stamp, label in [
        (intro + investigation * .12, "phase-1"), (intro + investigation * .48, "phase-2"),
        (intro + investigation * .82, "phase-3"), (runtime - 3.0, "cta")
    ]:
        frame = min(expected_frames - 1, round(stamp * 30))
        shutil.copy2(frames / f"frame_{frame:06d}.png", evidence / f"{label}.png")
    for index in range(12):
        stamp = intro + investigation * (.05 + index * .075)
        frame = min(expected_frames - 1, round(stamp * 30))
        shutil.copy2(frames / f"frame_{frame:06d}.png", motion / f"{index:02d}-{frame:06d}.png")
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", str(motion / "*.png"),
        "-vf", "scale=180:320,tile=4x3:padding=4:margin=4:color=0x070b0f", "-frames:v", "1", str(motion / "sequence.png")
    ], root, logs / "motion-sheet.log", 90)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", str(evidence / "*.png"),
        "-vf", "scale=180:320,tile=4x1:padding=4:margin=4:color=0x070b0f", "-frames:v", "1", str(job_dir / "contact-sheet.png")
    ], root, logs / "contact-sheet.log", 90)
    validation_result = json.loads((validation / "output.json").read_text())
    selection_result = validation_result["music_selection"]
    result = {
        "job_id": job["id"], "title": job["title"], "state": "READY_FOR_REVIEW", "technical": "PASS",
        "editorial": "PENDING_HUMAN", "release": "PENDING_HUMAN", "runtime_seconds": runtime,
        "frame_count": frame_count, "mechanism": creative["mechanism"],
        "profiles": {key: creative[key] for key in PROFILE_NAMES}, "distinguishing_features": job["distinguishing_features"],
        "music": {**selection, "track_title": Path(track_record["source"]).stem.replace("_", " "),
                  "cue_tags": region_record["mood_tags"],
                  "usable_start": selection_result["usable_start"], "usable_end": selection_result["usable_end"],
                  "source_sha256": selection_result["track_sha256"]},
        "audio_policy": {"presentation": "music_only", "sfx_count": 0, "ambient_machine_audio": False, "narration": "off"},
        "artifact": {"path": str(media), "bytes": media.stat().st_size, "sha256": sha256(media)},
        "evidence": {"contact_sheet": str(job_dir / "contact-sheet.png"),
                     "motion_sequence": str(motion / "sequence.png"), "representative_frames": str(evidence)},
        "metrics": metrics, "publish": False, "result": "PASS"
    }
    write_json(job_dir / "result.json", result)
    shutil.rmtree(job_dir / "work")
    return result


def build_campaign_contact_sheet(root: Path, run_dir: Path, successful: list) -> Path | None:
    if not successful:
        return None
    inputs = []
    filters = []
    for index, item in enumerate(successful):
        inputs += ["-i", str(run_dir / item["job_id"] / "representative-frames/phase-3.png")]
        filters.append(f"[{index}:v]scale=270:480[v{index}]")
    columns = min(5, len(successful))
    layout = "|".join(f"{(index % columns) * 270}_{(index // columns) * 480}" for index in range(len(successful)))
    filters.append("".join(f"[v{index}]" for index in range(len(successful))) + f"xstack=inputs={len(successful)}:layout={layout}:fill=0x070b0f")
    output = run_dir / "campaign-contact-sheet.png"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters),
         "-frames:v", "1", str(output)], root, run_dir / "campaign-contact-sheet.log", 120)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--trigger-kind", choices=["scheduled", "supervised"], default="scheduled")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text())
    archive = Path(manifest["campaign"]["output_archive"]).resolve()
    run_dir = archive / args.run_id
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite existing run: {run_dir}")
    run_dir.mkdir(parents=True)
    shutil.copy2(manifest_path, run_dir / "campaign-manifest.json")
    grammar_path = root / manifest["campaign"]["production_grammar_file"]
    grammar = json.loads(grammar_path.read_text())
    renderer_before = renderer_state(root, grammar)
    catalog_before = sha256(root / manifest["music_catalog"])
    started = time.monotonic()
    started_at = now()
    state = {
        "campaign_id": manifest["campaign"]["id"], "run_id": args.run_id, "trigger_kind": args.trigger_kind,
        "state": "PENDING", "started_at": started_at, "transitions": [{"state": "PENDING", "at": started_at}],
        "jobs": [{"id": job["id"], "state": "PENDING", "attempts": 0,
                  "transitions": [{"state": "PENDING", "at": started_at}]} for job in manifest["jobs"]]
    }
    state_path = run_dir / "campaign-state.json"
    write_json(state_path, state)
    transition_campaign(state, state_path, "PREFLIGHT")
    health = subprocess.run(["openclaw", "health"], cwd=root, capture_output=True, text=True)
    (run_dir / "openclaw-health.log").write_text(health.stdout + health.stderr)
    if health.returncode:
        transition_campaign(state, state_path, "FAILED", "OPENCLAW_CONTEXT_INVALID")
        raise SystemExit("OPENCLAW_CONTEXT_INVALID")
    try:
        run(["python3", "scripts/validate_mf011.py", "--mode", "shared", "--project-root", str(root),
             "--manifest", str(manifest_path), "--output", str(run_dir / "shared-preflight.json")],
            root, run_dir / "shared-preflight.log", 180)
    except RuntimeError as error:
        transition_campaign(state, state_path, "FAILED", str(error))
        raise
    transition_campaign(state, state_path, "RUNNING")
    results = []
    attempted = 0
    for index, job in enumerate(manifest["jobs"]):
        attempted += 1
        job_state = state["jobs"][index]
        result = None
        errors = []
        for attempt in range(1, manifest["policy"]["max_technical_retries"] + 2):
            job_state["attempts"] = attempt
            job_dir = run_dir / job["id"]
            if job_dir.exists():
                shutil.rmtree(job_dir)
            try:
                transition_job(state, state_path, job_state, "PREFLIGHT", f"attempt {attempt}")
                transition_job(state, state_path, job_state, "READY")
                transition_job(state, state_path, job_state, "RENDERING")
                result = render_job(root, job, run_dir)
                transition_job(state, state_path, job_state, "VALIDATING")
                if renderer_state(root, grammar) != renderer_before:
                    raise RuntimeError("RENDERER_SOURCE_CHANGED")
                transition_job(state, state_path, job_state, "READY_FOR_REVIEW")
                break
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                errors.append({"attempt": attempt, "detail": str(error)})
                if attempt <= manifest["policy"]["max_technical_retries"]:
                    continue
                transition_job(state, state_path, job_state, "FAILED", str(error))
                result = {"job_id": job["id"], "state": "FAILED", "technical": "FAIL",
                          "attempt_errors": errors, "publish": False, "result": "FAIL"}
                write_json(job_dir / "result.json", result)
        result["attempts"] = job_state["attempts"]
        result["attempt_errors"] = errors
        write_json(run_dir / job["id"] / "result.json", result)
        results.append(result)
    successful = [item for item in results if item["state"] == "READY_FOR_REVIEW"]
    contact_sheet = build_campaign_contact_sheet(root, run_dir, successful)
    run(["python3", "scripts/validate_mf011.py", "--mode", "shared", "--project-root", str(root),
         "--manifest", str(manifest_path), "--output", str(run_dir / "final-shared-preflight.json")],
        root, run_dir / "final-catalog-integrity.log", 180)
    renderer_after = renderer_state(root, grammar)
    catalog_after = sha256(root / manifest["music_catalog"])
    final_state = "COMPLETE" if len(successful) == len(manifest["jobs"]) else "PARTIAL" if successful else "FAILED"
    transition_campaign(state, state_path, final_state)
    state["ended_at"] = now()
    write_json(state_path, state)
    result = {
        "slice": "MF-011", "campaign_id": manifest["campaign"]["id"], "run_id": args.run_id,
        "trigger_kind": args.trigger_kind, "execution_authority": "OpenClaw orchestration with Codex bounded execution",
        "start_state": "PENDING", "state": final_state, "started_at": started_at, "ended_at": state["ended_at"],
        "elapsed_ms": round((time.monotonic() - started) * 1000), "jobs_attempted": attempted,
        "jobs": results, "ready_for_review": len(successful), "grammar_id": grammar["id"],
        "grammar_source_git_ref": grammar["source_git_ref"], "grammar_sha256": sha256(grammar_path),
        "baseline_git_ref": manifest["campaign"]["baseline_git_ref"], "manifest_sha256": sha256(manifest_path),
        "renderer_state_before": renderer_before, "renderer_state_after": renderer_after,
        "renderer_source_hash_before": object_hash(renderer_before), "renderer_source_hash_after": object_hash(renderer_after),
        "renderer_changes": 0 if renderer_before == renderer_after else 1,
        "catalog_sha256_before": catalog_before, "catalog_sha256_after": catalog_after,
        "catalog_changes": 0 if catalog_before == catalog_after else 1,
        "audio_policy": manifest["audio_policy"], "published": 0, "human_review": "PENDING_HUMAN",
        "useful_candidate_percentage": None, "campaign_contact_sheet": str(contact_sheet) if contact_sheet else None,
        "result": "PASS" if len(successful) == 10 and renderer_before == renderer_after and catalog_before == catalog_after else "FAIL"
    }
    write_json(run_dir / "campaign-result.json", result)
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
