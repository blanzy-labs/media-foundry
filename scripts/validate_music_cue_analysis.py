#!/usr/bin/env python3
"""Independent, fail-closed validation for MF-010 cue-analysis artifacts."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import music_catalog


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_audio(path):
    process = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(path)
    ], capture_output=True, text=True)
    if process.returncode:
        return None
    try:
        data = json.loads(process.stdout)
        return float(data["format"]["duration"]) if data.get("streams") else None
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    catalog_path = root / "config/music/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    tracks = sorted((track for track in catalog.get("tracks", []) if track.get("project") == args.project),
                    key=lambda item: item["id"])
    errors, track_results = [], []

    validation_args = argparse.Namespace(root=root, catalog=catalog_path,
                                         provenance_defaults=root / "config/music/provenance-defaults.json")
    catalog_validation, catalog_code = music_catalog.validate_catalog(validation_args)
    if catalog_code:
        errors.append({"code": "CATALOG_VALIDATION_FAILED", "detail": catalog_validation.get("errors", [])})
    for track in tracks:
        source = root / track["source"]
        regions = track.get("cue_regions", [])
        local_errors = []
        if not source.is_file() or sha256(source) != track.get("integrity", {}).get("sha256"):
            local_errors.append("SOURCE_INTEGRITY_FAILED")
        if not 3 <= len(regions) <= 6:
            local_errors.append("REGION_COUNT_OUT_OF_RANGE")
        waveform = root / "artifacts/mf-010/waveforms" / f"{track['id']}__waveform.png"
        if not waveform.is_file() or waveform.stat().st_size == 0:
            local_errors.append("WAVEFORM_MISSING")
        analysis_path = root / "artifacts/mf-010/analysis" / f"{track['id']}.json"
        if not analysis_path.is_file():
            local_errors.append("ANALYSIS_MISSING")
            analysis = {}
        else:
            analysis = json.loads(analysis_path.read_text())
            if analysis.get("source_sha256") != track.get("integrity", {}).get("sha256"):
                local_errors.append("ANALYSIS_SOURCE_HASH_MISMATCH")
        artifact_regions = {item.get("id"): item for item in analysis.get("regions", [])}
        for region in regions:
            prefix = region.get("id", "unknown")
            approval = region.get("approval", {})
            if approval.get("status") != "PENDING_APPROVAL" or approval.get("approved_sha256") is not None:
                local_errors.append(prefix + ":AUTOMATIC_OR_PRIOR_APPROVAL_PRESENT")
            if approval.get("proposed_sha256") != track.get("integrity", {}).get("sha256"):
                local_errors.append(prefix + ":PROPOSAL_HASH_MISMATCH")
            if region.get("usable_end", 0) - region.get("usable_start", 0) < 10:
                local_errors.append(prefix + ":REGION_TOO_SHORT")
            if not region.get("mood_tags") or set(region["mood_tags"]) - music_catalog.MOOD_TAGS:
                local_errors.append(prefix + ":MOOD_TAG_INVALID")
            if not region.get("use_cases") or set(region["use_cases"]) - music_catalog.USE_CASES:
                local_errors.append(prefix + ":USE_CASE_INVALID")
            artifact_region = artifact_regions.get(prefix, {})
            preview = root / region.get("analysis", {}).get("preview", "__missing__")
            duration = probe_audio(preview) if preview.is_file() else None
            if duration is None or duration <= 0 or duration > 15.1:
                local_errors.append(prefix + ":PREVIEW_INVALID")
            if artifact_region.get("analysis", {}).get("preview_sha256") != (sha256(preview) if preview.is_file() else None):
                local_errors.append(prefix + ":PREVIEW_HASH_MISMATCH")
        track_results.append({"track_id": track["id"], "region_count": len(regions),
                              "errors": local_errors, "result": "PASS" if not local_errors else "FAIL"})
        errors.extend({"code": value, "track_id": track["id"]} for value in local_errors)

    result = {"slice": "MF-010", "type": "independent_cue_analysis_validation",
              "project": args.project, "track_count": len(tracks),
              "region_count": sum(item["region_count"] for item in track_results),
              "catalog_validation": catalog_validation.get("result"), "tracks": track_results,
              "automatic_approvals": sum(1 for track in tracks for region in track.get("cue_regions", [])
                                         if region.get("approval", {}).get("status") == "APPROVED"),
              "errors": errors, "result": "PASS" if len(tracks) == 4 and not errors else "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
