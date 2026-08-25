#!/usr/bin/env python3
"""Run one bounded, sequential MF-008 batch into the external output archive."""

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


TERMINAL_JOB_STATES = {"READY_FOR_REVIEW", "BLOCKED_CONTENT", "MISSING_ASSET", "FAILED_RENDER", "FAILED_VALIDATION", "NEEDS_ENGINEERING", "CANCELLED"}
FAILURE_STATES = TERMINAL_JOB_STATES - {"READY_FOR_REVIEW"}


class JobFailure(Exception):
    def __init__(self, state, reason, retryable=False):
        super().__init__(reason)
        self.state = state
        self.reason = reason
        self.retryable = retryable


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def directory_bytes(path):
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def run_command(command, cwd, log_path, timeout=600, stdin=None):
    started = time.monotonic()
    try:
        process = subprocess.run(command, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text((error.stdout or "") + "\n" + (error.stderr or "") + "\nTIMEOUT\n")
        return 124, round((time.monotonic() - started) * 1000), "timeout"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(process.stdout + ("\n" if process.stdout and process.stderr else "") + process.stderr)
    return process.returncode, round((time.monotonic() - started) * 1000), process.stderr[-400:]


def transition(batch_state, state_path, job_state, state, detail=None):
    job_state["state"] = state
    event = {"state": state, "at": now()}
    if detail:
        event["detail"] = detail
    job_state["transitions"].append(event)
    write_json(state_path, batch_state)


def validate_content_package(package, job, source_id):
    if package.get("job_id") != job["id"] or package.get("status") != "APPROVED_AS_PROVIDED":
        raise JobFailure("BLOCKED_CONTENT", "CODEX_CONTENT_PACKAGE_NOT_APPROVED", True)
    if package.get("objective") != job["objective"] or package.get("selected_phrases") != job["approved_phrases"]:
        raise JobFailure("BLOCKED_CONTENT", "CODEX_CONTENT_DRIFT", True)
    if package.get("cta") != job["cta"] or package.get("source_id") != source_id:
        raise JobFailure("BLOCKED_CONTENT", "CODEX_SOURCE_OR_CTA_DRIFT", True)
    if package.get("renderer_changes_required") is not False or package.get("requested_changes") != []:
        raise JobFailure("NEEDS_ENGINEERING", "CODEX_REQUESTED_PROHIBITED_CHANGE", False)


def invoke_codex(root, schema_path, job, source_id, output_path, log_path):
    exact = {
        "job_id": job["id"], "status": "APPROVED_AS_PROVIDED", "objective": job["objective"],
        "selected_phrases": job["approved_phrases"], "cta": job["cta"], "source_id": source_id,
        "renderer_changes_required": False, "requested_changes": []
    }
    prompt = (
        "You are the constrained Codex content-package worker for MF-008. The human-approved batch has already selected all copy. "
        "Do not edit files, call tools, paraphrase, add facts, or request renderer changes. Return exactly the JSON object below, "
        "conforming to the supplied schema, with no commentary.\n" + json.dumps(exact, indent=2)
    )
    command = [
        "codex", "exec", "--ephemeral", "--color", "never", "--sandbox", "read-only", "--cd", str(root),
        "--output-schema", str(schema_path), "--output-last-message", str(output_path), "-"
    ]
    code, elapsed, tail = run_command(command, root, log_path, timeout=600, stdin=prompt)
    if code != 0 or not output_path.is_file():
        raise JobFailure("BLOCKED_CONTENT", f"CODEX_INVOCATION_FAILED: {tail}", True)
    try:
        package = json.loads(output_path.read_text())
    except json.JSONDecodeError as error:
        raise JobFailure("BLOCKED_CONTENT", f"CODEX_PACKAGE_MALFORMED: {error}", True) from error
    validate_content_package(package, job, source_id)
    return package, elapsed


def materialize_fixture(root, job, output):
    base = json.loads((root / "content/fixtures/mf006r9-unknown-process.json").read_text())
    base["id"] = job["id"]
    base["page_phrases"] = job["approved_phrases"]
    page_beats = [beat for beat in base["beats"] if beat["id"] in {"page_1", "page_2", "page_3"}]
    for beat, phrase in zip(page_beats, job["approved_phrases"]):
        beat["text"] = phrase
    cue = job["resolved_audio_cue"]
    base["music"]["selected_offset"] = cue["start"]
    for beat in base["beats"]:
        beat["narration"] = None
    output.write_text(json.dumps(base, indent=2) + "\n")
    return base


def per_job_preflight(root, manifest, cue_map, job, controlled_failure, controlled_engineering):
    if controlled_engineering == job["id"]:
        raise JobFailure("NEEDS_ENGINEERING", "CONTROLLED_RENDERER_CHANGE_REQUIRED", False)
    local = copy.deepcopy(job)
    if controlled_failure == job["id"]:
        local["audio"]["cue_id"] = "controlled-invalid-cue"
    if local.get("renderer_changes_required") is not False:
        raise JobFailure("NEEDS_ENGINEERING", "RENDERER_CHANGE_REQUIRED", False)
    if local.get("source_id") != manifest["approved_source"]["id"]:
        raise JobFailure("BLOCKED_CONTENT", "UNAPPROVED_CONTENT_SOURCE", False)
    if set(local.get("approved_phrases", [])) - set(manifest["approved_phrase_allowlist"]):
        raise JobFailure("BLOCKED_CONTENT", "UNAPPROVED_COPY", False)
    if local.get("cta") != "Continue the adventure":
        raise JobFailure("BLOCKED_CONTENT", "UNAPPROVED_CTA", False)
    if local.get("audio", {}).get("track_id") != cue_map.get("track_id"):
        raise JobFailure("MISSING_ASSET", "UNAPPROVED_AUDIO_TRACK", False)
    cue_id = local.get("audio", {}).get("cue_id")
    if cue_id not in cue_map.get("sections", {}):
        raise JobFailure("FAILED_VALIDATION", "UNAPPROVED_AUDIO_CUE", True)
    cue = cue_map["sections"][cue_id]
    if float(cue["duration"]) != 28.0 or float(cue["start"]) < 0:
        raise JobFailure("FAILED_VALIDATION", "INVALID_AUDIO_CUE_BOUNDS", True)
    local["resolved_audio_cue"] = cue
    return local


def validate_job_outputs(job_dir, fixture, package, media_result):
    required = [
        job_dir / "validation/preflight.json", job_dir / "validation/layout.json", job_dir / "validation/execution.json",
        job_dir / "validation/sfx.json", job_dir / "validation/music.json", job_dir / "validation/mix.json"
    ]
    documents = [json.loads(path.read_text()) for path in required]
    if any(document.get("result") not in {"PASS", "PASS_WITH_BLOCKER"} for document in documents):
        raise JobFailure("FAILED_VALIDATION", "PRODUCTION_STAGE_VALIDATION_FAILED", True)
    layout = documents[1]
    scene = layout.get("generated_scene", {})
    pulse = scene.get("indicator_pulse", {})
    if scene.get("strategy") != "godot_indicator_pulse_refinement" or pulse.get("approved_indicator_count") != 4:
        raise JobFailure("FAILED_VALIDATION", "FROZEN_VISUAL_GRAMMAR_NOT_OBSERVED", False)
    execution = documents[2]
    if execution.get("total_frames") != 840 or abs(float(execution.get("duration", 0)) - 28.0) > 1e-6:
        raise JobFailure("FAILED_VALIDATION", "TIMELINE_EXECUTION_FAILED", True)
    validate_content_package(package, fixture, fixture["source_id"])
    if media_result.get("result") != "PASS":
        raise JobFailure("FAILED_VALIDATION", "FINAL_MEDIA_VALIDATION_FAILED", True)


def render_job(root, grammar_path, job, job_dir):
    frames = job_dir / "work/frames"
    frames.mkdir(parents=True, exist_ok=True)
    fixture_path = job_dir / "fixture.json"
    materialize_fixture(root, job, fixture_path)
    validation = job_dir / "validation"
    logs = job_dir / "logs"
    audio = job_dir / "audio"
    validation.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)
    audio.mkdir(exist_ok=True)
    commands = [
        (["python3", str(root / "scripts/preflight_mf004.py"), "--fixture", str(fixture_path), "--grammar", str(grammar_path), "--project-root", str(root), "--output", str(validation / "preflight.json")], logs / "preflight.log", 60),
        (["python3", str(root / "scripts/prepare_mf005r1_music.py"), "--fixture", str(fixture_path), "--project-root", str(root), "--duration", "28", "--output-audio", str(audio / "music.wav"), "--output-report", str(validation / "music.json")], logs / "music.log", 120),
        (["python3", str(root / "scripts/generate_mf006_sfx.py"), "--fixture", str(fixture_path), "--output", str(audio / "sfx.wav"), "--report", str(validation / "sfx.json")], logs / "sfx.log", 120)
    ]
    for command, log, timeout in commands:
        code, _, tail = run_command(command, root, log, timeout=timeout)
        if code != 0:
            raise JobFailure("FAILED_VALIDATION", f"FIXTURE_AUDIO_PREFLIGHT_FAILED: {tail}", True)
    narration = job_dir / "validation/narration.json"
    write_json(narration, {"slice": "MF-008", "segments": [], "voice_status": "PROHIBITED_FOR_BATCH", "result": "PASS"})
    render_metrics = job_dir / "validation/render-metrics.txt"
    render_command = [
        "/usr/bin/time", "-f", "elapsed_seconds=%e\npeak_kib=%M", "-o", str(render_metrics),
        "timeout", "240", "godot", "--path", str(root / "godot"), "--fixed-fps", "30", "res://mf002.tscn", "--",
        "--fixture", str(fixture_path), "--grammar", str(grammar_path), "--output-dir", str(frames),
        "--layout-report", str(validation / "layout.json"), "--timeline-report", str(validation / "execution.json")
    ]
    code, render_ms, tail = run_command(render_command, root, logs / "render.log", timeout=270)
    frame_count = len(list(frames.glob("frame_*.png")))
    if code != 0 or frame_count != 840:
        raise JobFailure("FAILED_RENDER", f"GODOT_RENDER_FAILED code={code} frames={frame_count}: {tail}", True)
    mix_command = [
        "python3", str(root / "scripts/mix_mf005_audio.py"), "--base", str(audio / "sfx.wav"), "--manifest", str(narration),
        "--music-manifest", str(validation / "music.json"), "--duck-db", "-3", "--slice", "MF-008", "--final-lufs", "-15.5",
        "--final-true-peak", "-2.0", "--output", str(audio / "final.wav"), "--report", str(validation / "mix.json")
    ]
    code, mix_ms, tail = run_command(mix_command, root, logs / "mix.log", timeout=180)
    if code != 0:
        raise JobFailure("FAILED_VALIDATION", f"AUDIO_MIX_FAILED: {tail}", True)
    media = job_dir / "final.mp4"
    encode_command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-start_number", "0", "-i", str(frames / "frame_%06d.png"),
        "-i", str(audio / "final.wav"), "-map", "0:v:0", "-map", "1:a:0", "-t", "28", "-vf", "scale=1080:1920:flags=neighbor,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-threads", "1", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z", str(media)
    ]
    code, encode_ms, tail = run_command(encode_command, root, logs / "encode.log", timeout=300)
    if code != 0:
        raise JobFailure("FAILED_RENDER", f"ENCODE_FAILED: {tail}", True)
    return media, render_ms, mix_ms + encode_ms


def finalize_and_validate(root, grammar, manifest, job, package, job_dir, media, render_ms, finalization_ms):
    validation_start = time.monotonic()
    validation = job_dir / "validation"
    command = [
        "python3", str(root / "scripts/validate_media.py"), str(media), "--slice", "MF-008", "--duration-min", "27.95", "--duration-max", "28.05",
        "--ffprobe-json", str(validation / "ffprobe.json"), "--result-json", str(validation / "media.json")
    ]
    code, _, tail = run_command(command, root, job_dir / "logs/media-validation.log", timeout=180)
    if code != 0:
        raise JobFailure("FAILED_VALIDATION", f"MEDIA_VALIDATION_FAILED: {tail}", True)
    media_result = json.loads((validation / "media.json").read_text())
    validate_job_outputs(job_dir, job, package, media_result)
    frame_times = ((3.2, "formation"), (8.7, "investigation"), (24.5, "cta"))
    representative = job_dir / "representative-frames"
    representative.mkdir(exist_ok=True)
    for stamp, label in frame_times:
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(stamp), "-i", str(media), "-frames:v", "1", str(representative / f"{label}.png")]
        code, _, tail = run_command(command, root, job_dir / f"logs/frame-{label}.log", timeout=60)
        if code != 0:
            raise JobFailure("FAILED_VALIDATION", f"EVIDENCE_FRAME_FAILED: {tail}", True)
    font = root / "godot/fonts/Lato-Heavy.ttf"
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(representative / "formation.png"), "-i", str(representative / "investigation.png"), "-i", str(representative / "cta.png"),
        "-filter_complex", f"[0:v]scale=270:480[v0];[1:v]scale=270:480[v1];[2:v]scale=270:480[v2];[v0][v1][v2]hstack=inputs=3,drawtext=fontfile='{font}':text='{job['id']}':x=12:y=12:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.7",
        "-frames:v", "1", str(job_dir / "contact-sheet.png")
    ]
    code, _, tail = run_command(command, root, job_dir / "logs/contact-sheet.log", timeout=90)
    if code != 0:
        raise JobFailure("FAILED_VALIDATION", f"CONTACT_SHEET_FAILED: {tail}", True)
    validation_ms = round((time.monotonic() - validation_start) * 1000)
    metrics_text = (validation / "render-metrics.txt").read_text() if (validation / "render-metrics.txt").is_file() else ""
    peak_kib = next((int(line.split("=", 1)[1]) for line in metrics_text.splitlines() if line.startswith("peak_kib=")), None)
    before_cleanup = directory_bytes(job_dir)
    shutil.rmtree(job_dir / "work", ignore_errors=True)
    result = {
        "job_id": job["id"], "state": "READY_FOR_REVIEW", "technical": "PASS", "editorial": "PENDING_HUMAN", "release": "PENDING_HUMAN",
        "artifact": {"path": str(media), "bytes": media.stat().st_size, "sha256": sha256(media), "render_timestamp": dt.datetime.fromtimestamp(media.stat().st_mtime, dt.timezone.utc).isoformat()},
        "production_grammar_id": grammar["id"], "git_source_ref": grammar["source_git_ref"], "content_package_sha256": sha256(job_dir / "content-package.json"),
        "metrics": {"codex_ms": job.get("codex_ms", 0), "render_ms": render_ms, "finalization_ms": finalization_ms, "validation_ms": validation_ms, "retry_ms": job.get("retry_ms", 0), "idle_ms": 0, "peak_render_memory_kib": peak_kib, "temporary_bytes_before_cleanup": before_cleanup, "retained_bytes": 0},
        "publish": False, "result": "PASS"
    }
    write_json(job_dir / "result.json", result)
    result["metrics"]["retained_bytes"] = directory_bytes(job_dir)
    write_json(job_dir / "result.json", result)
    (job_dir / "evidence-summary.md").write_text(
        f"# {job['id']} Evidence Summary\n\nTechnical: **PASS**. State: **READY_FOR_REVIEW**. Editorial/release: **PENDING HUMAN**.\n\n"
        f"Objective: {job['objective']}\n\nApproved phrases: " + "; ".join(job["approved_phrases"]) + ".\n\n"
        f"Artifact: `{media}`\n\nSHA-256: `{result['artifact']['sha256']}`\n\nNo publication or renderer modification occurred.\n"
    )
    return result


def reuse_validated_job(root, grammar, manifest, job, job_dir, reference_job_dir):
    for relative in ("final.mp4", "fixture.json", "content-package.json"):
        source = reference_job_dir / relative
        if not source.is_file():
            raise JobFailure("MISSING_ASSET", f"REUSE_SOURCE_MISSING: {source}", False)
        shutil.copy2(source, job_dir / relative)
    for directory in ("validation", "representative-frames"):
        shutil.copytree(reference_job_dir / directory, job_dir / directory)
    shutil.copy2(reference_job_dir / "contact-sheet.png", job_dir / "contact-sheet.png")
    package = json.loads((job_dir / "content-package.json").read_text())
    validate_content_package(package, job, manifest["approved_source"]["id"])
    media_result = json.loads((job_dir / "validation/media.json").read_text())
    validate_job_outputs(job_dir, job, package, media_result)
    media = job_dir / "final.mp4"
    result = {
        "job_id": job["id"], "state": "READY_FOR_REVIEW", "technical": "PASS", "editorial": "PENDING_HUMAN", "release": "PENDING_HUMAN",
        "artifact": {"path": str(media), "bytes": media.stat().st_size, "sha256": sha256(media), "render_timestamp": dt.datetime.fromtimestamp(media.stat().st_mtime, dt.timezone.utc).isoformat()},
        "production_grammar_id": grammar["id"], "git_source_ref": grammar["source_git_ref"], "content_package_sha256": sha256(job_dir / "content-package.json"),
        "metrics": {"codex_ms": 0, "render_ms": 0, "finalization_ms": 0, "validation_ms": 0, "retry_ms": 0, "idle_ms": 0, "peak_render_memory_kib": 0, "temporary_bytes_before_cleanup": 0, "retained_bytes": directory_bytes(job_dir)},
        "controlled_test_reuse": str(reference_job_dir), "publish": False, "result": "PASS"
    }
    write_json(job_dir / "result.json", result)
    (job_dir / "evidence-summary.md").write_text(f"# {job['id']} Controlled-Test Evidence\n\nA previously validated dry-run output was copied and independently revalidated to exercise orchestration continuation without another expensive render. State: **READY_FOR_REVIEW**.\n")
    return result


def batch_contact_sheet(root, run_dir, successful):
    if not successful:
        return None
    inputs = []
    for result in successful:
        inputs += ["-i", str(run_dir / result["job_id"] / "representative-frames/investigation.png")]
    labels = []
    for index, result in enumerate(successful):
        labels.append(f"[{index}:v]scale=270:480[v{index}]")
    stack = "".join(f"[v{index}]" for index in range(len(successful))) + f"hstack=inputs={len(successful)}"
    output = run_dir / "batch-contact-sheet.png"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(labels + [stack]), "-frames:v", "1", str(output)]
    code, _, _ = run_command(command, root, run_dir / "batch-contact-sheet.log", timeout=90)
    return output if code == 0 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--trigger-kind", choices=("supervised", "scheduled", "controlled-test"), required=True)
    parser.add_argument("--archive-root")
    parser.add_argument("--controlled-job-failure")
    parser.add_argument("--controlled-shared-failure", action="store_true")
    parser.add_argument("--controlled-needs-engineering")
    parser.add_argument("--reuse-run")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text())
    batch = manifest["batch"]
    archive = Path(args.archive_root or batch["output_archive"]).resolve()
    run_dir = archive / args.run_id
    if run_dir.exists():
        existing = run_dir / "batch-result.json"
        if existing.is_file() and json.loads(existing.read_text()).get("state") in {"COMPLETE", "PARTIAL", "FAILED"}:
            print(f"MF008_DUPLICATE_RUN_REFUSED run_id={args.run_id}", file=sys.stderr)
            return 4
        print(f"MF008_EXISTING_INCOMPLETE_RUN_REFUSED run_id={args.run_id}", file=sys.stderr)
        return 5
    run_dir.mkdir(parents=True)
    started_wall = now()
    started = time.monotonic()
    batch_state = {"batch_id": batch["id"], "run_id": args.run_id, "trigger_kind": args.trigger_kind, "state": "PENDING", "started_at": started_wall, "jobs": []}
    for job in manifest["jobs"]:
        batch_state["jobs"].append({"id": job["id"], "state": "PENDING", "attempts": 0, "transitions": [{"state": "PENDING", "at": started_wall}]})
    state_path = run_dir / "batch-state.json"
    write_json(state_path, batch_state)
    batch_state["state"] = "RUNNING"
    write_json(state_path, batch_state)
    preflight_output = run_dir / "shared-preflight.json"
    expected = "controlled-invalid-grammar" if args.controlled_shared_failure else batch["production_grammar"]
    command = ["python3", str(root / "scripts/validate_mf008_manifest.py"), "--project-root", str(root), "--manifest", str(manifest_path), "--output", str(preflight_output), "--expected-grammar-id", expected]
    code, preflight_ms, tail = run_command(command, root, run_dir / "shared-preflight.log", timeout=120)
    tools = {name: shutil.which(name) for name in ("godot", "ffmpeg", "ffprobe", "codex", "openclaw")}
    disk_free = shutil.disk_usage(archive.parent).free
    infrastructure_errors = []
    if code != 0:
        infrastructure_errors.append("PINNED_PRODUCTION_GRAMMAR_PREFLIGHT_FAILED")
    if not all(tools.values()):
        infrastructure_errors.append("REQUIRED_TOOL_MISSING")
    if disk_free < 20 * 1024 ** 3:
        infrastructure_errors.append("INSUFFICIENT_DISK_SPACE")
    health_code, _, _ = run_command(["openclaw", "health"], root, run_dir / "openclaw-health.log", timeout=60)
    if health_code != 0:
        infrastructure_errors.append("OPENCLAW_CONTEXT_INVALID")
    shared = {"result": "PASS" if not infrastructure_errors else "FAIL", "classification": None if not infrastructure_errors else "SHARED_INFRASTRUCTURE_FAILURE", "tools": tools, "disk_free_bytes": disk_free, "output_archive_writable": os.access(run_dir, os.W_OK), "codex_invocation_available": bool(tools["codex"]), "openclaw_context_valid": health_code == 0, "renderer_changes_allowed": False, "manifest_validation_ms": preflight_ms, "errors": infrastructure_errors}
    write_json(run_dir / "shared-infrastructure.json", shared)
    if infrastructure_errors:
        batch_state["state"] = "FAILED"
        batch_state["ended_at"] = now()
        batch_state["shared_failure"] = shared
        write_json(state_path, batch_state)
        result = {**batch_state, "jobs_started": 0, "ready_for_review": 0, "failed": 0, "needs_engineering": 0, "published": 0, "elapsed_ms": round((time.monotonic() - started) * 1000), "result": "FAIL"}
        write_json(run_dir / "batch-result.json", result)
        (run_dir / "batch-summary.md").write_text(f"# UNKNOWN PROCESS — BATCH 001\n\nBATCH RESULT: **FAILED**\n\nClassification: `SHARED_INFRASTRUCTURE_FAILURE`\n\nJobs started: 0\n\nReasons: {', '.join(infrastructure_errors)}\n")
        print(json.dumps(result, indent=2))
        return 2
    cue_map = json.loads((root / manifest["audio_cue_map"]).read_text())
    grammar_path = root / batch["production_grammar_file"]
    grammar = json.loads(grammar_path.read_text())
    schema_path = root / "schemas/mf008-content-package.schema.json"
    results = []
    reuse_root = archive / args.reuse_run if args.reuse_run else None
    for index, original_job in enumerate(manifest["jobs"]):
        state = batch_state["jobs"][index]
        job_dir = run_dir / original_job["id"]
        job_dir.mkdir()
        attempt_errors = []
        job_started = time.monotonic()
        final_result = None
        max_attempts = int(manifest["policy"]["max_technical_retries"]) + 1
        for attempt in range(1, max_attempts + 1):
            state["attempts"] = attempt
            attempt_started = time.monotonic()
            try:
                transition(batch_state, state_path, state, "PREFLIGHT", f"attempt {attempt}")
                job = per_job_preflight(root, manifest, cue_map, original_job, args.controlled_job_failure, args.controlled_needs_engineering)
                transition(batch_state, state_path, state, "READY")
                if reuse_root:
                    transition(batch_state, state_path, state, "GENERATING_CONTENT_PACKAGE", "reuse validated dry-run package")
                    transition(batch_state, state_path, state, "RENDERING", "reuse validated dry-run media")
                    transition(batch_state, state_path, state, "VALIDATING", "independent controlled-test revalidation")
                    final_result = reuse_validated_job(root, grammar, manifest, job, job_dir, reuse_root / job["id"])
                else:
                    transition(batch_state, state_path, state, "GENERATING_CONTENT_PACKAGE")
                    package, codex_ms = invoke_codex(root, schema_path, job, manifest["approved_source"]["id"], job_dir / "content-package.json", job_dir / "logs/codex.log")
                    job["codex_ms"] = codex_ms
                    transition(batch_state, state_path, state, "RENDERING")
                    media, render_ms, finalization_ms = render_job(root, root / "config/visual-grammar.json", job, job_dir)
                    transition(batch_state, state_path, state, "VALIDATING")
                    final_result = finalize_and_validate(root, grammar, manifest, job, package, job_dir, media, render_ms, finalization_ms)
                transition(batch_state, state_path, state, "READY_FOR_REVIEW")
                break
            except JobFailure as error:
                elapsed = round((time.monotonic() - attempt_started) * 1000)
                attempt_errors.append({"attempt": attempt, "state": error.state, "reason": error.reason, "retryable": error.retryable, "elapsed_ms": elapsed})
                if error.retryable and attempt < max_attempts:
                    state.setdefault("retries", []).append({"at": now(), "reason": error.reason, "attempt": attempt})
                    continue
                transition(batch_state, state_path, state, error.state, error.reason)
                final_result = {"job_id": original_job["id"], "state": error.state, "technical": "FAIL", "reason": error.reason, "attempts": attempt, "attempt_errors": attempt_errors, "editorial": "NOT_REACHED", "release": "NOT_REACHED", "publish": False, "result": "FAIL"}
                write_json(job_dir / "result.json", final_result)
                (job_dir / "evidence-summary.md").write_text(f"# {original_job['id']} Failure\n\nState: **{error.state}**\n\nReason: `{error.reason}`\n\nAttempts: {attempt}\n\nNo renderer modification or publication occurred.\n")
                break
        final_result["total_job_ms"] = round((time.monotonic() - job_started) * 1000)
        write_json(job_dir / "result.json", final_result)
        results.append(final_result)
    successful = [result for result in results if result["state"] == "READY_FOR_REVIEW"]
    failures = [result for result in results if result["state"] in FAILURE_STATES]
    batch_state["state"] = "COMPLETE" if len(successful) == 3 else ("PARTIAL" if successful else "FAILED")
    batch_state["ended_at"] = now()
    batch_state["jobs"] = [{**state, "result_path": str(run_dir / state["id"] / "result.json")} for state in batch_state["jobs"]]
    write_json(state_path, batch_state)
    sheet = batch_contact_sheet(root, run_dir, successful)
    result = {
        "batch_id": batch["id"], "run_id": args.run_id, "trigger_kind": args.trigger_kind, "state": batch_state["state"],
        "production_grammar_id": grammar["id"], "git_source_ref": grammar["source_git_ref"], "started_at": started_wall, "ended_at": batch_state["ended_at"],
        "elapsed_ms": round((time.monotonic() - started) * 1000), "shared_preflight": "PASS", "execution": "sequential", "jobs": results,
        "ready_for_review": len(successful), "failed": len(failures), "needs_engineering": sum(result["state"] == "NEEDS_ENGINEERING" for result in results),
        "published": 0, "renderer_changes": 0, "human_review": "PENDING_HUMAN", "batch_contact_sheet": str(sheet) if sheet else None,
        "archive_bytes": directory_bytes(run_dir), "result": "PASS" if batch_state["state"] == "COMPLETE" else "PASS_WITH_EXPECTED_FAILURE" if batch_state["state"] == "PARTIAL" and args.trigger_kind == "controlled-test" else "FAIL"
    }
    write_json(run_dir / "batch-result.json", result)
    lines = ["# UNKNOWN PROCESS — BATCH 001", "", f"Run: `{args.run_id}`", "", f"Trigger: `{args.trigger_kind}`", ""]
    for item in results:
        lines += [f"## {item['job_id']}", "", f"Technical: **{item['technical']}**", "", f"State: **{item['state']}**"]
        if item.get("artifact"):
            lines += ["", f"Output: `{item['artifact']['path']}`", "", f"Hash: `{item['artifact']['sha256']}`"]
        if item.get("reason"):
            lines += ["", f"Reason: `{item['reason']}`", "", f"Attempts: {item.get('attempts', 1)}"]
        lines.append("")
    lines += [f"BATCH RESULT: **{result['state']}**", "", f"Ready for review: {len(successful)}", "", f"Failed: {len(failures)}", "", f"Needs engineering: {result['needs_engineering']}", "", "Published: 0", "", "Human editorial/release review remains required."]
    (run_dir / "batch-summary.md").write_text("\n".join(lines) + "\n")
    write_json(run_dir / "retry-report.json", {"batch_id": batch["id"], "run_id": args.run_id, "jobs": [{"job_id": item["job_id"], "attempt_errors": item.get("attempt_errors", []), "attempts": item.get("attempts", 1)} for item in results], "result": "PASS"})
    print(json.dumps(result, indent=2))
    return 0 if result["state"] == "COMPLETE" or (args.trigger_kind == "controlled-test" and result["state"] == "PARTIAL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
