#!/usr/bin/env python3
"""Fail-closed validation for the bounded MF-008 scheduled batch contract."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


JOB_STATES = ["PENDING", "PREFLIGHT", "READY", "GENERATING_CONTENT_PACKAGE", "RENDERING", "VALIDATING", "READY_FOR_REVIEW", "BLOCKED_CONTENT", "MISSING_ASSET", "FAILED_RENDER", "FAILED_VALIDATION", "NEEDS_ENGINEERING", "CANCELLED"]
BATCH_STATES = ["PENDING", "RUNNING", "COMPLETE", "PARTIAL", "FAILED"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-grammar-id")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    errors = []
    checks = {}

    def record(name, passed, detail):
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
        if not passed:
            errors.append(name.upper() + "_FAILED")

    try:
        manifest = json.loads(Path(args.manifest).read_text())
        batch = manifest["batch"]
        policy = manifest["policy"]
        grammar_path = root / batch["production_grammar_file"]
        grammar = json.loads(grammar_path.read_text())
        cue_path = root / manifest["audio_cue_map"]
        cue_map = json.loads(cue_path.read_text())
        jobs = manifest["jobs"]
        expected_id = args.expected_grammar_id or batch["production_grammar"]
        record("grammar_id", grammar.get("id") == expected_id == batch.get("production_grammar") and grammar.get("status") == "FROZEN", grammar.get("id"))
        current_ref = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        record("git_ref", current_ref == batch.get("source_git_ref") == grammar.get("source_git_ref"), current_ref)
        pinned = []
        for relative, expected_hash in grammar.get("files", {}).items():
            path = root / relative
            actual = sha256(path) if path.is_file() else None
            pinned.append({"path": relative, "expected_sha256": expected_hash, "actual_sha256": actual, "status": "PASS" if actual == expected_hash else "FAIL"})
        record("pinned_files", bool(pinned) and all(item["status"] == "PASS" for item in pinned), f"{sum(item['status']=='PASS' for item in pinned)}/{len(pinned)}")
        record("renderer_frozen", policy.get("allow_renderer_changes") is False and policy.get("allow_runtime_architecture_changes") is False and grammar.get("policy", {}).get("allow_renderer_changes") is False, "renderer/runtime modifications prohibited")
        record("exact_job_count", len(jobs) == batch.get("job_limit") == 3 and len({job.get("id") for job in jobs}) == 3, ",".join(str(job.get("id")) for job in jobs))
        record("sequential_execution", batch.get("execution") == "sequential", str(batch.get("execution")))
        record("state_models", manifest.get("state_models", {}).get("job") == JOB_STATES and manifest.get("state_models", {}).get("batch") == BATCH_STATES, "explicit job and batch states")
        record("retry_policy", policy.get("max_technical_retries") == 1 and policy.get("continue_after_job_failure") is True, "one retry; continue after isolated failure")
        record("no_publication", batch.get("publish") is False and batch.get("require_human_release_approval") is True and policy.get("automatic_publication") is False and policy.get("automatic_editorial_approval") is False, "publish=false; human gate required")
        source = manifest.get("approved_source", {})
        allowlist = set(manifest.get("approved_phrase_allowlist", []))
        source_ok = source.get("id") == "unknown-process-approved-synopsis-v1" and source.get("canonical_url") == "https://rcblanzy.com/books/unknown-process" and bool(source.get("synopsis"))
        jobs_ok = True
        for job in jobs:
            jobs_ok &= job.get("source_id") == source.get("id")
            jobs_ok &= len(job.get("approved_phrases", [])) == 3 and set(job.get("approved_phrases", [])) <= allowlist
            jobs_ok &= job.get("cta") == "Continue the adventure"
            jobs_ok &= job.get("renderer_changes_required") is False
            jobs_ok &= job.get("audio", {}).get("mode") == "music"
            jobs_ok &= job.get("audio", {}).get("track_id") == cue_map.get("track_id")
            jobs_ok &= job.get("audio", {}).get("cue_id") in cue_map.get("sections", {})
        record("approved_content", source_ok and jobs_ok, "approved synopsis, phrase allowlist, CTA, and audio IDs")
        music_path = root / cue_map.get("source", "")
        music_hash = sha256(music_path) if music_path.is_file() else None
        sections_ok = all(float(section.get("start", -1)) >= 0 and float(section.get("duration", 0)) == 28.0 for section in cue_map.get("sections", {}).values())
        record("approved_audio", music_hash == cue_map.get("source_sha256") and sections_ok, music_hash or "MISSING")
        record("non_narrated", grammar.get("audio_grammar", {}).get("narration") == "PROHIBITED_UNTIL_EXPLICITLY_RELEASE_ELIGIBLE" and all("narration" not in job for job in jobs), "production narration prohibited")
        archive = Path(batch.get("output_archive", ""))
        record("external_archive", archive.is_absolute() and root not in archive.parents and archive != root, str(archive))
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
        record("dirty_worktree_policy", policy.get("dirty_worktree") == "ALLOW_ONLY_WITH_EXACT_PINNED_FILE_HASHES" and checks["pinned_files"]["status"] == "PASS", f"{len(dirty)} existing entries; pinned inputs exact")
        result = {"slice": "MF-008", "type": "batch_manifest_preflight", "batch_id": batch.get("id"), "checks": checks, "pinned_files": pinned, "dirty_worktree_entries": len(dirty), "errors": errors, "result": "PASS" if not errors else "FAIL"}
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        result = {"slice": "MF-008", "type": "batch_manifest_preflight", "checks": checks, "errors": errors + [str(error)], "result": "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
