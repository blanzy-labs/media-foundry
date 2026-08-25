#!/usr/bin/env python3
"""Isolated lifecycle and failure tests for MF-009."""

import argparse
import json
import math
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path


def wav(path, frequency=220.0, duration=.25):
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 8000
    samples = [round(math.sin(2 * math.pi * frequency * index / rate) * 8000) for index in range(round(rate * duration))]
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1); target.setsampwidth(2); target.setframerate(rate)
        target.writeframes(b"".join(struct.pack("<h", value) for value in samples))


def invoke(tool, root, command, *extra):
    catalog = root / "config/music/catalog.json"
    defaults = root / "config/music/provenance-defaults.json"
    process = subprocess.run(["python3", str(tool), "--root", str(root), "--catalog", str(catalog),
                              "--provenance-defaults", str(defaults), command, *extra, "--json"],
                             capture_output=True, text=True)
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError:
        value = {"result": "FAIL", "errors": [{"code": "NON_JSON_OUTPUT", "detail": process.stdout + process.stderr}]}
    return process.returncode, value


def environment(parent, name):
    root = parent / name
    (root / "media/audio/music/test-project").mkdir(parents=True)
    defaults = root / "config/music/provenance-defaults.json"
    defaults.parent.mkdir(parents=True)
    defaults.write_text(json.dumps({"default": {"source_type": "unknown", "generator": "unknown"}, "projects": {}}))
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--work-root", default="/home/blanzy/media-foundry-output/mf009-tests")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    project = Path(args.project_root).resolve()
    tool = project / "scripts/music_catalog.py"
    work_parent = Path(args.work_root).resolve()
    work_parent.mkdir(parents=True, exist_ok=True)
    results = {}
    with tempfile.TemporaryDirectory(prefix="run-", dir=work_parent) as temporary:
        parent = Path(temporary)

        root = environment(parent, "lifecycle")
        source = root / "media/audio/music/test-project/New_Song.wav"
        wav(source)
        (source.parent / "notes.txt").write_text("not audio")
        code1, first = invoke(tool, root, "refresh")
        before = (root / "config/music/catalog.json").read_bytes()
        code2, second = invoke(tool, root, "refresh")
        after = (root / "config/music/catalog.json").read_bytes()
        results["add_one_track"] = {
            "first_new": first.get("new"), "second_unchanged": second.get("unchanged"),
            "unsupported_ignored": any(item.get("path", "").endswith("notes.txt") for item in first.get("ignored", [])),
            "byte_stable_second_refresh": before == after,
            "result": "PASS" if code1 == code2 == 0 and len(first.get("new", [])) == 1 and not second.get("catalog_changed") and before == after else "FAIL"
        }
        approve_code, approved = invoke(tool, root, "approve", "test-project", "new_song", "--reviewer", "mf009-test", "--note", "controlled approval")
        catalog_path = root / "config/music/catalog.json"
        catalog = json.loads(catalog_path.read_text())
        catalog["tracks"][0]["editorial"]["mood_tags"] = ["controlled"]
        catalog["tracks"][0]["editorial"]["notes"] = "preserve me"
        catalog_path.write_text(json.dumps(catalog, indent=2) + "\n")
        _, preserved_refresh = invoke(tool, root, "refresh")
        preserved = json.loads(catalog_path.read_text())["tracks"][0]["editorial"]
        wav(source, frequency=330.0)
        change_code, changed = invoke(tool, root, "refresh")
        changed_track = json.loads(catalog_path.read_text())["tracks"][0]
        results["source_change"] = {
            "approved_first": approve_code == 0 and approved.get("status") == "APPROVED",
            "changed": changed.get("changed"), "approval": changed_track["approval"]["status"],
            "prior_review_in_history": any(item.get("event") == "SOURCE_CHANGED" for item in changed_track["history"]),
            "human_metadata_preserved": preserved.get("mood_tags") == ["controlled"] and preserved.get("notes") == "preserve me",
            "result": "PASS" if change_code == 0 and changed_track["approval"]["status"] == "REVIEW_REQUIRED"
                and preserved_refresh.get("result") == "PASS" and preserved.get("notes") == "preserve me" else "FAIL"
        }

        missing_source = source.parent / "Missing.wav"
        wav(missing_source, frequency=440.0)
        invoke(tool, root, "refresh")
        invoke(tool, root, "approve", "test-project", "missing")
        missing_source.unlink()
        _, missing_refresh = invoke(tool, root, "refresh")
        validation_code, missing_validation = invoke(tool, root, "validate")
        missing_track = next(item for item in json.loads(catalog_path.read_text())["tracks"] if item["id"] == "missing")
        results["missing_approved_file"] = {
            "catalog_status": missing_track["approval"]["status"],
            "refresh_missing": missing_refresh.get("missing"),
            "validation_errors": missing_validation.get("errors"),
            "result": "PASS" if validation_code == 1 and missing_track["approval"]["status"] == "MISSING"
                and any(item.get("code") == "MISSING_LOCAL_ASSET" for item in missing_validation.get("errors", [])) else "FAIL"
        }

        collision_root = environment(parent, "collision")
        wav(collision_root / "media/audio/music/test-project/Same_Name.wav")
        wav(collision_root / "media/audio/music/test-project/Same-Name.wav")
        collision_code, collision = invoke(tool, collision_root, "refresh")
        results["duplicate_normalized_id"] = {
            "exit_code": collision_code, "errors": collision.get("errors"),
            "result": "PASS" if collision_code == 1 and any(item.get("code") == "TRACK_ID_COLLISION" for item in collision.get("errors", [])) else "FAIL"
        }

        corrupt_root = environment(parent, "corrupt")
        (corrupt_root / "media/audio/music/test-project/Corrupt.mp3").write_bytes(b"not an audio stream")
        corrupt_code, corrupt = invoke(tool, corrupt_root, "refresh")
        results["corrupt_audio"] = {
            "exit_code": corrupt_code, "errors": corrupt.get("errors"),
            "result": "PASS" if corrupt_code == 1 and any(item.get("code") == "AUDIO_INSPECTION_FAILED" for item in corrupt.get("errors", [])) else "FAIL"
        }

        region_root = environment(parent, "regions")
        region_source = region_root / "media/audio/music/test-project/Regions.wav"
        wav(region_source, duration=20.0)
        invoke(tool, region_root, "refresh")
        invoke(tool, region_root, "approve", "test-project", "regions")
        region_catalog_path = region_root / "config/music/catalog.json"
        region_catalog = json.loads(region_catalog_path.read_text())
        track = region_catalog["tracks"][0]; current_hash = track["integrity"]["sha256"]
        analysis = {"method": "mf010_deterministic_energy_v1", "version": 1, "confidence": "medium",
                    "mean_rms_db": -24.0, "energy_delta_db": 1.0, "transient_score": .01,
                    "notes": "Synthetic regression fixture.", "preview": "artifacts/test-preview.mp3"}
        approval = lambda: {"status": "APPROVED", "proposed_sha256": current_hash,
                            "approved_sha256": current_hash, "reviewed_at": "2026-01-01T00:00:00Z",
                            "reviewer": "mf009-test", "note": "Regression fixture."}
        track["cue_regions"] = [
            {"id": "region_a", "usable_start": .2, "usable_end": 11.2, "preferred_entry": .3, "preferred_exit": 11.0,
             "mood_tags": ["ambient"], "use_cases": ["excerpt"], "narration_friendliness": "high",
             "intensity": "low", "analysis": analysis.copy(), "human": {"notes": None, "edited": False},
             "approval": approval(), "notes": ""},
            {"id": "region_b", "usable_start": 8.0, "usable_end": 19.0, "preferred_entry": 8.5, "preferred_exit": 18.0,
             "mood_tags": ["tension"], "use_cases": ["tracking"], "narration_friendliness": "medium",
             "intensity": "rising", "analysis": analysis.copy(), "human": {"notes": None, "edited": False},
             "approval": approval(), "notes": ""}
        ]
        region_catalog_path.write_text(json.dumps(region_catalog, indent=2) + "\n")
        overlap_code, overlap = invoke(tool, region_root, "validate")
        query_code, region_query = invoke(tool, region_root, "query", "test-project", "--require-approved-regions")
        track["cue_regions"][0]["usable_start"] = 12.0
        track["cue_regions"][0]["usable_end"] = 10.0
        region_catalog_path.write_text(json.dumps(region_catalog, indent=2) + "\n")
        invalid_code, invalid = invoke(tool, region_root, "validate")
        results["cue_regions"] = {
            "overlap_validation": overlap.get("result"), "approved_query_count": len(region_query.get("approved_tracks", [])),
            "invalid_exit_code": invalid_code, "invalid_errors": invalid.get("errors"),
            "result": "PASS" if overlap_code == query_code == 0 and len(region_query.get("approved_tracks", [])) == 1
                and invalid_code == 1 and any(item.get("code") == "CUE_REGION_BOUNDS_INVALID" for item in invalid.get("errors", [])) else "FAIL"
        }

        reject_root = environment(parent, "reject")
        wav(reject_root / "media/audio/music/test-project/Rejected.wav")
        invoke(tool, reject_root, "refresh")
        reject_code, rejected = invoke(tool, reject_root, "reject", "test-project", "rejected", "--reviewer", "mf009-test")
        query_code, rejected_query = invoke(tool, reject_root, "query", "test-project")
        results["rejection"] = {"status": rejected.get("status"), "approved_tracks": rejected_query.get("approved_tracks"),
                                "result": "PASS" if reject_code == query_code == 0 and rejected.get("status") == "REJECTED" and rejected_query.get("approved_tracks") == [] else "FAIL"}

    overall = all(item.get("result") == "PASS" for item in results.values())
    output = {"slice": "MF-009", "tests": results, "passed": sum(item.get("result") == "PASS" for item in results.values()),
              "total": len(results), "result": "PASS" if overall else "FAIL"}
    path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
