#!/usr/bin/env python3
"""Independent fail-closed validation for the MF-008B-R1 production proof."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import music_catalog


MECHANISMS = {"tracking", "classification_link", "biometric_scan"}
PROFILE_KEYS = ["palette_profile", "camera_profile", "node_profile", "projection_profile", "cta_profile"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def shared(args):
    root = Path(args.project_root).resolve(); manifest = load(args.manifest)
    batch = manifest["batch"]; grammar = load(root / batch["production_grammar_file"])
    catalog_path = root / manifest["music_catalog"]
    common = argparse.Namespace(root=root, catalog=catalog_path,
                                provenance_defaults=root / "config/music/provenance-defaults.json")
    refresh, refresh_code = music_catalog.refresh(common)
    catalog_validation, catalog_code = music_catalog.validate_catalog(common)
    catalog = load(catalog_path)
    tracks = {track["id"]: track for track in catalog["tracks"] if track["project"] == "unknown-process"}
    checks, errors, pinned, jobs = {}, [], [], []

    def check(name, passed, detail=None):
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
        if not passed: errors.append(name.upper() + "_FAILED")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    check("grammar_frozen", grammar.get("status") == "FROZEN" and grammar.get("id") == batch["production_grammar"], grammar.get("id"))
    check("grammar_git_ref", head == grammar.get("source_git_ref") == batch.get("source_git_ref"), head)
    for relative, expected in grammar.get("files", {}).items():
        path = root / relative; actual = sha256(path) if path.is_file() else None
        item = {"path": relative, "expected_sha256": expected, "actual_sha256": actual,
                "status": "PASS" if actual == expected else "FAIL"}
        pinned.append(item)
    check("pinned_grammar_files", bool(pinned) and all(item["status"] == "PASS" for item in pinned), f"{sum(item['status']=='PASS' for item in pinned)}/{len(pinned)}")
    check("renderer_changes_prohibited", all(manifest["policy"].get(key) is False for key in
          ["allow_renderer_changes", "allow_runtime_architecture_changes", "allow_visual_grammar_changes"]), "fixture/config only")
    check("catalog_refresh", refresh_code == 0 and not refresh.get("changed") and not refresh.get("missing"), refresh)
    check("catalog_validation", catalog_code == 0, catalog_validation)
    check("catalog_freeze_hash", sha256(catalog_path) == grammar.get("music_catalog_sha256_at_freeze"), sha256(catalog_path))
    approved_tracks = [track for track in tracks.values() if track["approval"]["status"] == "APPROVED"
                       and track["approval"]["approved_sha256"] == track["integrity"]["sha256"]]
    approved_regions = [(track, region) for track in tracks.values() for region in track["cue_regions"]
                        if region["approval"]["status"] == "APPROVED"
                        and region["approval"]["approved_sha256"] == track["integrity"]["sha256"]]
    check("approved_library", len(approved_tracks) == 4 and len(approved_regions) == 20,
          {"tracks": len(approved_tracks), "regions": len(approved_regions)})
    check("exact_three_sequential_jobs", len(manifest["jobs"]) == batch["job_limit"] == 3 and batch["execution"] == "sequential", len(manifest["jobs"]))
    check("openclaw_tools", all(shutil.which(name) for name in ["openclaw", "codex", "godot", "ffmpeg", "ffprobe"]), "required tools present")
    mechanisms, profiles = [], []
    for job in manifest["jobs"]:
        fixture = load(root / job["fixture"]); creative = job["creative"]; selection = job["music"]
        track = tracks.get(selection["track_id"])
        region = None if track is None else next((item for item in track["cue_regions"] if item["id"] == selection["region_id"]), None)
        source = None if track is None else root / track["source"]
        actual_hash = sha256(source) if source and source.is_file() else None
        runtime = float(selection["video_duration"]); start = float(selection["actual_start"]); end = float(selection["actual_end"])
        eligible = bool(track and region and actual_hash == track["integrity"]["sha256"] == track["approval"]["approved_sha256"]
                        == region["approval"]["approved_sha256"] and track["approval"]["status"] == "APPROVED"
                        and region["approval"]["status"] == "APPROVED")
        bounds = bool(region and region["usable_start"] <= start < end <= region["usable_end"]
                      and abs((end - start) - runtime) < 1e-6 and 24 <= runtime <= 32)
        fades = selection["fade_in"] >= 0 and selection["fade_out"] >= 0 and selection["fade_in"] + selection["fade_out"] < runtime
        fixture_match = fixture.get("creative") == creative and fixture.get("format", {}).get("duration_seconds") == runtime
        job_errors = []
        if not eligible: job_errors.append("MUSIC_APPROVAL_OR_HASH_INVALID")
        if not bounds: job_errors.append("MUSIC_SUBSECTION_OUTSIDE_APPROVED_REGION")
        if not fades: job_errors.append("MUSIC_FADE_INVALID")
        if not fixture_match: job_errors.append("RESOLVED_FIXTURE_DRIFT")
        if job.get("renderer_changes_required") is not False or job.get("narration") is not None: job_errors.append("WORKER_BOUNDARY_INVALID")
        jobs.append({"job_id": job["id"], "track_id": selection["track_id"], "region_id": selection["region_id"],
                     "source_sha256": actual_hash, "eligible": eligible, "bounds_valid": bounds,
                     "fixture_match": fixture_match, "errors": job_errors, "result": "PASS" if not job_errors else "FAIL"})
        mechanisms.append(creative["mechanism"]); profiles.append(tuple(creative[key] for key in PROFILE_KEYS))
    check("job_music_and_fixture_preflight", all(job["result"] == "PASS" for job in jobs), jobs)
    check("mechanism_distinctness", set(mechanisms) == MECHANISMS, mechanisms)
    check("cosmetic_distinctness", len(set(profiles)) == 3, profiles)
    check("no_publication", batch["publish"] is False and manifest["policy"]["automatic_publication"] is False, "publish=false")
    return {"slice": "MF-008B-R1", "type": "shared_preflight", "batch_id": batch["id"],
            "grammar_id": grammar["id"], "git_ref": head, "catalog_sha256": sha256(catalog_path),
            "approved_tracks": len(approved_tracks), "approved_regions": len(approved_regions),
            "checks": checks, "pinned_files": pinned, "jobs": jobs, "errors": errors,
            "state": "READY" if not errors else "FAILED", "result": "PASS" if not errors else "FAIL"}


def job_output(args):
    job = load(args.job); fixture = load(args.fixture); layout = load(args.layout); execution = load(args.execution)
    media = load(args.media); music = load(args.music); mix = load(args.mix); selection = load(args.selection)
    requested = fixture["creative"]; observed = layout.get("generated_scene", {}).get("creative_control", {})
    runtime = float(job["music"]["video_duration"]); mechanism = requested["mechanism"]
    exclusivity = observed.get("mechanism_exclusivity", {})
    checks = {
        "mechanism_loaded": observed.get("mechanism") == mechanism,
        "mechanism_exclusivity": set(exclusivity) == MECHANISMS and exclusivity.get(mechanism) == "PASS"
            and all(exclusivity.get(other) == "NOT_RUN" for other in MECHANISMS - {mechanism}),
        "unique_events": [item.get("id") for item in observed.get("event_evidence", [])] == requested["events"]
            and all(item.get("status") == "PASS" for item in observed.get("event_evidence", [])),
        "profiles_loaded": all(observed.get(key) == requested[key] for key in PROFILE_KEYS),
        "timing_loaded": observed.get("timing") == requested["timing"],
        "campaign_identity": observed.get("campaign_identity") == "unknown_process_recovered_record"
            and observed.get("single_window_preserved") is True,
        "timeline": execution.get("result") == "PASS" and execution.get("total_frames") == round(runtime * 30)
            and abs(float(execution.get("duration", 0)) - runtime) < 1e-6,
        "music_selection_contract": selection.get("contract") == "mf010_music_selection_v1" and selection.get("result") == "PASS",
        "music_source": music.get("result") == "PASS" and music.get("source_sha256") == selection.get("track_sha256"),
        "music_offsets": abs(float(music.get("selected_offset", -1)) - job["music"]["actual_start"]) < 1e-6
            and abs(float(music.get("duration", -1)) - runtime) < .002,
        "music_mix": mix.get("result") == "PASS",
        "encoded_media": media.get("result") == "PASS"
    }
    return {"slice": "MF-008B-R1", "type": "job_output_validation", "job_id": job["id"],
            "mechanism": mechanism, "mechanism_exclusivity": exclusivity,
            "profiles": {key: requested[key] for key in PROFILE_KEYS}, "music_selection": selection,
            "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
            "errors": [key.upper() + "_FAILED" for key, value in checks.items() if not value],
            "result": "PASS" if all(checks.values()) else "FAIL"}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=["shared", "job-output"], required=True)
    parser.add_argument("--project-root"); parser.add_argument("--manifest"); parser.add_argument("--job")
    parser.add_argument("--fixture"); parser.add_argument("--layout"); parser.add_argument("--execution")
    parser.add_argument("--media"); parser.add_argument("--music"); parser.add_argument("--mix"); parser.add_argument("--selection")
    parser.add_argument("--output", required=True); args = parser.parse_args()
    try: result = shared(args) if args.mode == "shared" else job_output(args)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        result = {"slice": "MF-008B-R1", "type": args.mode, "errors": [{"code": "VALIDATOR_EXCEPTION", "detail": str(error)}], "result": "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2)); return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
