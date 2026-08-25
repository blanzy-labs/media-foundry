#!/usr/bin/env python3
"""Independently aggregate and validate a completed MF-008B-R1 batch archive."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path):
    process = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    data = json.loads(process.stdout) if process.returncode == 0 else {}
    streams = data.get("streams", [])
    return {"video": any(item.get("codec_type") == "video" for item in streams),
            "audio": any(item.get("codec_type") == "audio" for item in streams),
            "duration": float(data.get("format", {}).get("duration", 0))}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--run-dir", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); run_dir = Path(args.run_dir).resolve(); batch = json.loads((run_dir / "batch-result.json").read_text())
    errors, jobs = [], []
    for item in batch.get("jobs", []):
        job_dir = run_dir / item["job_id"]; media = job_dir / "final.mp4"
        output = json.loads((job_dir / "validation/output.json").read_text())
        media_probe = probe(media) if media.is_file() else {"video": False, "audio": False, "duration": 0}
        local = []
        if item.get("state") != "READY_FOR_REVIEW" or item.get("result") != "PASS": local.append("JOB_NOT_READY")
        if output.get("result") != "PASS": local.append("JOB_VALIDATION_FAILED")
        if not media_probe["video"] or not media_probe["audio"] or abs(media_probe["duration"] - item["runtime_seconds"]) > .05: local.append("MEDIA_DECODE_FAILED")
        if not media.is_file() or sha256(media) != item.get("artifact", {}).get("sha256"): local.append("ARTIFACT_HASH_FAILED")
        jobs.append({"job_id": item["job_id"], "mechanism": item["mechanism"], "profiles": item["profiles"],
                     "track_id": item["music"]["track_id"], "region_id": item["music"]["region_id"],
                     "runtime_seconds": item["runtime_seconds"], "media_probe": media_probe,
                     "errors": local, "result": "PASS" if not local else "FAIL"})
        errors.extend({"job_id": item["job_id"], "code": value} for value in local)
    profiles = [tuple(job["profiles"].values()) for job in jobs]
    batch_checks = {
        "exact_three_ready": len(jobs) == 3 and all(job["result"] == "PASS" for job in jobs),
        "mechanisms_distinct": len({job["mechanism"] for job in jobs}) == 3,
        "profiles_distinct": len(set(profiles)) == 3,
        "music_distinct": len({(job["track_id"], job["region_id"]) for job in jobs}) == 3,
        "runtimes_flexible": len({job["runtime_seconds"] for job in jobs}) == 3,
        "renderer_integrity": batch.get("renderer_changes") == 0 and batch.get("renderer_state_before") == batch.get("renderer_state_after"),
        "contact_sheet": (run_dir / "batch-contact-sheet.png").is_file(),
        "no_publication": batch.get("published") == 0
    }
    errors.extend({"code": key.upper() + "_FAILED"} for key, value in batch_checks.items() if not value)
    result = {"slice": "MF-008B-R1", "type": "independent_batch_validation", "run_dir": str(run_dir),
              "jobs": jobs, "checks": {key: "PASS" if value else "FAIL" for key, value in batch_checks.items()},
              "errors": errors, "result": "PASS" if not errors else "FAIL"}
    output_path = Path(args.output); output_path.parent.mkdir(parents=True, exist_ok=True); output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2)); return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
