#!/usr/bin/env python3
"""Batch-start refresh/validation/eligibility integration point for OpenClaw."""

import argparse
import json
from pathlib import Path

import music_catalog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--request", action="append", default=[], help="track_id or track_id@cue_region_id")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    common = argparse.Namespace(
        root=root,
        catalog=root / "config/music/catalog.json",
        provenance_defaults=root / "config/music/provenance-defaults.json",
    )
    refresh, refresh_code = music_catalog.refresh(common)
    validation, validation_code = music_catalog.validate_catalog(common)
    catalog = json.loads(common.catalog.read_text()) if common.catalog.is_file() else {"tracks": []}
    by_id = {track["id"]: track for track in catalog.get("tracks", []) if track.get("project") == args.project}
    errors, eligible = [], []
    for request in args.request:
        track_id, separator, region_id = request.partition("@")
        track = by_id.get(track_id)
        if track is None:
            errors.append({"code": "MUSIC_TRACK_UNKNOWN", "request": request})
            continue
        status = track.get("approval", {}).get("status")
        if track.get("discovery", {}).get("status") == "MISSING" or status == "MISSING":
            errors.append({"code": "MUSIC_TRACK_MISSING", "request": request})
            continue
        if status == "REVIEW_REQUIRED":
            errors.append({"code": "MUSIC_TRACK_REVIEW_REQUIRED", "request": request})
            continue
        if status != "APPROVED":
            errors.append({"code": "MUSIC_TRACK_NOT_APPROVED", "request": request, "status": status})
            continue
        if track.get("approval", {}).get("approved_sha256") != track.get("integrity", {}).get("sha256"):
            errors.append({"code": "MUSIC_TRACK_REVIEW_REQUIRED", "request": request})
            continue
        selected = {"id": track_id, "qualified_id": track["qualified_id"], "source": track["source"],
                    "sha256": track["integrity"]["sha256"]}
        if separator:
            region = next((item for item in track.get("cue_regions", []) if item.get("id") == region_id), None)
            if region is None:
                errors.append({"code": "MUSIC_CUE_REGION_UNKNOWN", "request": request})
                continue
            approval = region.get("approval", {})
            if approval.get("status") == "REJECTED":
                errors.append({"code": "MUSIC_CUE_REJECTED", "request": request})
                continue
            if approval.get("status") == "REVIEW_REQUIRED":
                errors.append({"code": "MUSIC_CUE_REVIEW_REQUIRED", "request": request})
                continue
            if approval.get("status") != "APPROVED" or approval.get("approved_sha256") != track["integrity"]["sha256"]:
                errors.append({"code": "MUSIC_CUE_REGION_NOT_APPROVED", "request": request})
                continue
            selected["cue_region"] = region
        eligible.append(selected)
    approval_errors = {"MUSIC_TRACK_NOT_APPROVED", "MUSIC_TRACK_REVIEW_REQUIRED", "MUSIC_CUE_REGION_NOT_APPROVED", "MUSIC_CUE_REJECTED", "MUSIC_CUE_REVIEW_REQUIRED"}
    if errors and all(item["code"] in approval_errors for item in errors):
        state = "BLOCKED_APPROVAL"
    elif errors or refresh_code or validation_code:
        state = "FAILED_VALIDATION"
    else:
        state = "READY"
    result = {
        "slice": "MF-009", "type": "music_catalog_batch_preflight", "project": args.project,
        "refresh": {key: refresh.get(key) for key in ["result", "new", "changed", "missing", "unreviewed", "approved"]},
        "catalog_validation": validation.get("result"), "requests": args.request, "eligible": eligible,
        "errors": errors or ([] if refresh_code == validation_code == 0 else refresh.get("errors", []) + validation.get("errors", [])),
        "state": state, "result": "PASS" if state == "READY" else "FAIL"
    }
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if state == "READY" else 2 if state == "BLOCKED_APPROVAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
