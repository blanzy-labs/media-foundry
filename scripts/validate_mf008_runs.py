#!/usr/bin/env python3
"""Validate MF-008 dry, scheduled, and controlled orchestration evidence."""

import argparse
import datetime as dt
import json
from pathlib import Path


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    parser = argparse.ArgumentParser()
    for name in ("project_root", "archive_root", "dry_run", "scheduled_run", "partial_run", "shared_failure_run", "engineering_run", "manifest_validation", "schedule", "cron_job", "cron_runs", "cron_status", "idempotency", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    args = parser.parse_args()
    root = Path(args.project_root)
    archive = Path(args.archive_root)
    errors = []
    checks = {}

    def record(name, passed, detail):
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
        if not passed:
            errors.append(name.upper() + "_FAILED")

    try:
        load = lambda path: json.loads(Path(path).read_text())
        manifest_validation = load(args.manifest_validation)
        dry = load(archive / args.dry_run / "batch-result.json")
        dry_state = load(archive / args.dry_run / "batch-state.json")
        scheduled = load(archive / args.scheduled_run / "batch-result.json")
        scheduled_state = load(archive / args.scheduled_run / "batch-state.json")
        partial = load(archive / args.partial_run / "batch-result.json")
        shared = load(archive / args.shared_failure_run / "batch-result.json")
        engineering = load(archive / args.engineering_run / "batch-result.json")
        schedule = load(args.schedule)
        cron_job = load(args.cron_job)
        cron_runs = load(args.cron_runs)
        cron_status = load(args.cron_status)
        idempotency = load(args.idempotency)
        record("manifest_and_pins", manifest_validation.get("result") == "PASS" and manifest_validation.get("checks", {}).get("pinned_files", {}).get("status") == "PASS", "14 pinned production inputs")
        record("supervised_dry_run", dry.get("state") == "COMPLETE" and dry.get("ready_for_review") == 3 and dry.get("result") == "PASS", f"{dry.get('ready_for_review')}/3 READY_FOR_REVIEW")
        record("scheduled_run", scheduled.get("trigger_kind") == "scheduled" and scheduled.get("state") == "COMPLETE" and scheduled.get("ready_for_review") == 3 and scheduled.get("result") == "PASS", f"{scheduled.get('ready_for_review')}/3 READY_FOR_REVIEW")
        scheduled_hashes = [item.get("artifact", {}).get("sha256") for item in scheduled.get("jobs", [])]
        dry_hashes = [item.get("artifact", {}).get("sha256") for item in dry.get("jobs", [])]
        record("deterministic_outputs", scheduled_hashes == dry_hashes and all(scheduled_hashes), ",".join(scheduled_hashes))
        sequential = True
        states = scheduled_state.get("jobs", [])
        for previous, current in zip(states, states[1:]):
            previous_ready = next((parse_time(item["at"]) for item in previous.get("transitions", []) if item["state"] == "READY_FOR_REVIEW"), None)
            current_preflight = next((parse_time(item["at"]) for item in current.get("transitions", []) if item["state"] == "PREFLIGHT"), None)
            sequential &= previous_ready is not None and current_preflight is not None and current_preflight >= previous_ready
        record("sequential_state_order", sequential, "each job preflight begins after prior READY_FOR_REVIEW")
        codex_ok = all(item.get("metrics", {}).get("codex_ms", 0) > 0 and item.get("content_package_sha256") for item in scheduled.get("jobs", []))
        record("codex_worker_boundary", codex_ok, "three schema-constrained read-only content packages")
        media_ok = True
        packages_ok = True
        for item in scheduled.get("jobs", []):
            job_dir = Path(item["artifact"]["path"]).parent
            required = [job_dir / "fixture.json", job_dir / "result.json", job_dir / "evidence-summary.md", job_dir / "contact-sheet.png", job_dir / "validation/media.json", job_dir / "logs/codex.log"]
            packages_ok &= all(path.is_file() for path in required)
            media = load(job_dir / "validation/media.json")
            media_ok &= media.get("result") == "PASS" and Path(item["artifact"]["path"]).is_file()
        record("per_job_evidence", packages_ok, "fixture, result, summary, contact sheet, validation, and logs")
        record("full_media_validation", media_ok, "three external MP4s fully decoded")
        partial_states = {item["job_id"]: item for item in partial.get("jobs", [])}
        partial_ok = partial.get("state") == "PARTIAL" and partial.get("ready_for_review") == 2 and partial_states.get("up-video-002", {}).get("state") == "FAILED_VALIDATION" and partial_states["up-video-002"].get("attempts") == 2 and partial_states.get("up-video-003", {}).get("state") == "READY_FOR_REVIEW"
        record("controlled_partial_failure", partial_ok, "Job 2 rejected invalid cue after one retry; Job 3 continued")
        record("controlled_shared_failure", shared.get("state") == "FAILED" and shared.get("jobs_started") == 0 and shared.get("shared_failure", {}).get("classification") == "SHARED_INFRASTRUCTURE_FAILURE", "invalid grammar; zero jobs started")
        engineering_states = {item["job_id"]: item for item in engineering.get("jobs", [])}
        engineering_ok = engineering.get("state") == "PARTIAL" and engineering_states.get("up-video-002", {}).get("state") == "NEEDS_ENGINEERING" and engineering_states["up-video-002"].get("attempts") == 1 and engineering.get("renderer_changes") == 0
        record("needs_engineering_gate", engineering_ok, "renderer request stopped without retry or source changes")
        run_entries = cron_runs.get("entries", [])
        cron_entry = run_entries[0] if run_entries else {}
        declared = parse_time(schedule["scheduled_at_utc"])
        actual = dt.datetime.fromtimestamp(float(cron_entry.get("runAtMs", 0)) / 1000, dt.timezone.utc)
        schedule_delta = abs((actual - declared).total_seconds())
        schedule_ok = cron_job.get("id") == schedule.get("schedule_id") and cron_job.get("state", {}).get("lastRunStatus") == "ok" and cron_job.get("delivery", {}).get("mode") == "none" and cron_job.get("enabled") is False and schedule_delta <= 1.0
        record("openclaw_one_time_schedule", schedule_ok, f"start delta {schedule_delta:.3f}s; retained disabled after success")
        record("schedule_persistence_and_inspection", cron_status.get("storage") == "sqlite" and cron_status.get("jobs") == 1 and cron_job.get("deleteAfterRun") is False, cron_status.get("sqlitePath", ""))
        record("noninteractive_execution", cron_entry.get("status") == "ok" and cron_entry.get("deliveryStatus") == "not-requested", f"OpenClaw command duration {cron_entry.get('durationMs')} ms")
        record("idempotency", idempotency.get("exit_code") == 4 and idempotency.get("result") == "PASS", "duplicate completed run refused")
        no_publish = all(batch.get("published") == 0 and all(job.get("publish") is False for job in batch.get("jobs", [])) for batch in (dry, scheduled, partial, engineering))
        record("no_publication", no_publish and cron_job.get("delivery", {}).get("mode") == "none", "published=0; OpenClaw delivery=none")
        repo_mp4 = list((root / "artifacts/mf-008").rglob("*.mp4")) if (root / "artifacts/mf-008").exists() else []
        external = all(Path(item["artifact"]["path"]).is_relative_to(archive) for item in scheduled.get("jobs", []))
        record("external_output_archive", external and not repo_mp4, f"{archive}; repository MP4 count={len(repo_mp4)}")
        metrics_ok = all(all(key in item.get("metrics", {}) for key in ("codex_ms", "render_ms", "finalization_ms", "validation_ms", "peak_render_memory_kib", "temporary_bytes_before_cleanup", "retained_bytes")) for item in scheduled.get("jobs", []))
        record("production_resource_metrics", metrics_ok and scheduled.get("elapsed_ms", 0) > 0 and scheduled.get("archive_bytes", 0) > 0, f"batch {scheduled.get('elapsed_ms')} ms; {scheduled.get('archive_bytes')} bytes")
        record("human_gate", scheduled.get("human_review") == "PENDING_HUMAN" and all(item.get("editorial") == "PENDING_HUMAN" and item.get("release") == "PENDING_HUMAN" for item in scheduled.get("jobs", [])), "editorial/release pending human")
        result = {"slice": "MF-008", "checks": checks, "scheduled_artifact_hashes": scheduled_hashes, "schedule_start_delta_seconds": round(schedule_delta, 3), "errors": errors, "technical_result": "PASS" if not errors else "FAIL", "human_review": "PENDING_HUMAN", "release_eligible": False, "result": "PASS_WITH_HUMAN_GATE" if not errors else "FAIL"}
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        result = {"slice": "MF-008", "checks": checks, "errors": errors + [str(error)], "technical_result": "FAIL", "human_review": "PENDING_HUMAN", "release_eligible": False, "result": "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["technical_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
