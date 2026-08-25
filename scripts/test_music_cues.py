#!/usr/bin/env python3
"""Isolated approval, selection, invalidation, and failure tests for MF-010."""

import argparse
import json
import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path


def wav(path, frequency=220.0, duration=24.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 8000
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1); target.setsampwidth(2); target.setframerate(rate)
        frames = (struct.pack("<h", round(math.sin(2 * math.pi * frequency * index / rate) * 7000))
                  for index in range(round(rate * duration)))
        target.writeframes(b"".join(frames))


def run(command):
    process = subprocess.run(command, capture_output=True, text=True)
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError:
        result = {"result": "FAIL", "errors": [{"code": "NON_JSON_OUTPUT", "detail": process.stdout + process.stderr}]}
    return process.returncode, result


def catalog_command(tool, root, command, *extra):
    return run(["python3", str(tool), "--root", str(root), "--catalog", str(root / "config/music/catalog.json"),
                "--provenance-defaults", str(root / "config/music/provenance-defaults.json"), command, *extra, "--json"])


def cue_command(tool, root, command, *extra):
    return run(["python3", str(tool), "--root", str(root), "--catalog", str(root / "config/music/catalog.json"),
                command, *extra, "--json"])


def preflight(tool, root, request, output):
    return run(["python3", str(tool), "--project-root", str(root), "--project", "test-project",
                "--request", request, "--output", str(output)])


def environment(parent, name):
    root = parent / name
    defaults = root / "config/music/provenance-defaults.json"
    defaults.parent.mkdir(parents=True)
    defaults.write_text(json.dumps({"default": {"source_type": "test", "generator": "mf010-test"}, "projects": {}}))
    return root


def proposal(source_hash):
    return {
        "id": "pursuit_a", "usable_start": 2.0, "usable_end": 20.0,
        "preferred_entry": 3.0, "preferred_exit": 19.0,
        "mood_tags": ["pursuit", "tension"], "use_cases": ["tracking"],
        "narration_friendliness": "medium", "intensity": "rising",
        "analysis": {"method": "mf010_deterministic_energy_v1", "version": 1, "confidence": "medium",
                     "mean_rms_db": -24.0, "energy_delta_db": 2.5, "transient_score": .01,
                     "notes": "Controlled fixture.", "preview": "artifacts/test-preview.mp3"},
        "human": {"notes": None, "edited": False},
        "approval": {"status": "PENDING_APPROVAL", "proposed_sha256": source_hash, "approved_sha256": None,
                     "reviewed_at": None, "reviewer": None, "note": None},
        "notes": "Automatic analysis is advisory; human listening is authoritative."
    }


def error_codes(result):
    return [item.get("code") for item in result.get("errors", [])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--work-root", default="/home/blanzy/media-foundry-output/mf010-tests")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    project = Path(args.project_root).resolve()
    catalog_tool = project / "scripts/music_catalog.py"
    cue_tool = project / "scripts/music_cue.py"
    preflight_tool = project / "scripts/music_catalog_batch_preflight.py"
    parent_root = Path(args.work_root).resolve(); parent_root.mkdir(parents=True, exist_ok=True)
    tests = {}

    with tempfile.TemporaryDirectory(prefix="run-", dir=parent_root) as temporary:
        parent = Path(temporary)
        root = environment(parent, "workflow")
        source = root / "media/audio/music/test-project/Test_Track.wav"
        wav(source)
        catalog_command(catalog_tool, root, "refresh")
        catalog_command(catalog_tool, root, "approve", "test-project", "test_track", "--reviewer", "mf010-test")
        catalog_path = root / "config/music/catalog.json"
        catalog = json.loads(catalog_path.read_text()); track = catalog["tracks"][0]
        track["cue_regions"] = [proposal(track["integrity"]["sha256"])]
        catalog_path.write_text(json.dumps(catalog, indent=2) + "\n")

        pending_code, pending = preflight(preflight_tool, root, "test_track@pursuit_a", root / "pending.json")
        tests["unapproved_cue_requested"] = {
            "state": pending.get("state"), "errors": pending.get("errors"),
            "result": "PASS" if pending_code == 2 and pending.get("state") == "BLOCKED_APPROVAL"
            and "MUSIC_CUE_REGION_NOT_APPROVED" in error_codes(pending) else "FAIL"}

        reject_code, rejected = cue_command(cue_tool, root, "reject", "test-project", "test_track", "pursuit_a",
                                             "--reviewer", "mf010-test", "--note", "Controlled rejection")
        rejected_preflight_code, rejected_preflight = preflight(preflight_tool, root, "test_track@pursuit_a", root / "rejected.json")
        tests["rejected_cue_requested"] = {
            "review_status": rejected.get("status"), "errors": rejected_preflight.get("errors"),
            "result": "PASS" if reject_code == 0 and rejected_preflight_code == 2
            and "MUSIC_CUE_REJECTED" in error_codes(rejected_preflight) else "FAIL"}

        edit_code, edited = cue_command(cue_tool, root, "edit", "test-project", "test_track", "pursuit_a",
                                         "--usable-start", "1.5", "--preferred-entry", "2.5",
                                         "--notes", "Human adjusted the lead-in")
        approve_code, approved = cue_command(cue_tool, root, "approve", "test-project", "test_track", "pursuit_a",
                                               "--reviewer", "mf010-test", "--note", "Controlled approval")
        tests["human_edit_and_approval"] = {
            "edit_status": edited.get("status"), "approval_status": approved.get("status"),
            "result": "PASS" if edit_code == approve_code == 0 and edited.get("status") == "PENDING_APPROVAL"
            and approved.get("status") == "APPROVED" else "FAIL"}

        select_code, selected = cue_command(cue_tool, root, "select", "test-project", "test_track", "pursuit_a",
                                             "--actual-start", "3", "--actual-end", "15", "--video-duration", "12",
                                             "--fade-in", ".5", "--fade-out", "1")
        outside_code, outside = cue_command(cue_tool, root, "select", "test-project", "test_track", "pursuit_a",
                                             "--actual-start", "0", "--actual-end", "12", "--video-duration", "12")
        tests["selection_boundary_and_evidence"] = {
            "selection_contract": selected.get("contract"), "outside_errors": outside.get("errors"),
            "result": "PASS" if select_code == 0 and selected.get("contract") == "mf010_music_selection_v1"
            and outside_code == 1 and "CUE_SUBSECTION_OUTSIDE_APPROVED_REGION" in error_codes(outside) else "FAIL"}

        query_code, query = catalog_command(catalog_tool, root, "query", "test-project", "--require-approved-regions",
                                             "--mood", "pursuit", "--use-case", "tracking")
        tests["approved_region_query"] = {"matches": query.get("matches"),
            "result": "PASS" if query_code == 0 and len(query.get("matches", [])) == 1 else "FAIL"}

        original = json.loads(catalog_path.read_text())
        invalid = json.loads(json.dumps(original)); invalid["tracks"][0]["cue_regions"][0]["usable_end"] = 1.0
        catalog_path.write_text(json.dumps(invalid, indent=2) + "\n")
        invalid_code, invalid_result = catalog_command(catalog_tool, root, "validate")
        preferred = json.loads(json.dumps(original)); preferred["tracks"][0]["cue_regions"][0]["preferred_entry"] = 21.0
        catalog_path.write_text(json.dumps(preferred, indent=2) + "\n")
        preferred_code, preferred_result = catalog_command(catalog_tool, root, "validate")
        catalog_path.write_text(json.dumps(original, indent=2) + "\n")
        tests["invalid_bounds"] = {"errors": invalid_result.get("errors"),
            "result": "PASS" if invalid_code == 1 and "CUE_REGION_BOUNDS_INVALID" in error_codes(invalid_result) else "FAIL"}
        tests["preferred_entry_outside"] = {"errors": preferred_result.get("errors"),
            "result": "PASS" if preferred_code == 1 and "CUE_REGION_BOUNDS_INVALID" in error_codes(preferred_result) else "FAIL"}

        missing_track_code, missing_track = cue_command(cue_tool, root, "approve", "test-project", "missing", "pursuit_a")
        tests["region_references_missing_track"] = {"errors": missing_track.get("errors"),
            "result": "PASS" if missing_track_code == 1 and "TRACK_NOT_FOUND" in error_codes(missing_track) else "FAIL"}

        source.unlink()
        missing_code, missing = catalog_command(catalog_tool, root, "validate")
        tests["approved_region_missing_asset"] = {"errors": missing.get("errors"),
            "result": "PASS" if missing_code == 1 and "MISSING_LOCAL_ASSET" in error_codes(missing) else "FAIL"}

        change_root = environment(parent, "source-change")
        change_source = change_root / "media/audio/music/test-project/Changed.wav"
        wav(change_source)
        catalog_command(catalog_tool, change_root, "refresh")
        catalog_command(catalog_tool, change_root, "approve", "test-project", "changed", "--reviewer", "mf010-test")
        change_catalog_path = change_root / "config/music/catalog.json"
        change_catalog = json.loads(change_catalog_path.read_text()); change_track = change_catalog["tracks"][0]
        change_track["cue_regions"] = [proposal(change_track["integrity"]["sha256"])]
        change_catalog_path.write_text(json.dumps(change_catalog, indent=2) + "\n")
        cue_command(cue_tool, change_root, "approve", "test-project", "changed", "pursuit_a", "--reviewer", "mf010-test")
        wav(change_source, frequency=330.0)
        refresh_code, refreshed = catalog_command(catalog_tool, change_root, "refresh")
        changed = json.loads(change_catalog_path.read_text())["tracks"][0]
        tests["source_change_revalidation"] = {
            "refresh_changed": refreshed.get("changed"), "track_status": changed["approval"]["status"],
            "region_status": changed["cue_regions"][0]["approval"]["status"],
            "result": "PASS" if refresh_code == 0 and changed["approval"]["status"] == "REVIEW_REQUIRED"
            and changed["cue_regions"][0]["approval"]["status"] == "REVIEW_REQUIRED" else "FAIL"}

    passed = sum(item["result"] == "PASS" for item in tests.values())
    result = {"slice": "MF-010", "type": "isolated_failure_and_workflow_tests", "tests": tests,
              "passed": passed, "total": len(tests), "result": "PASS" if passed == len(tests) else "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
