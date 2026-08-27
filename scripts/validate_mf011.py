#!/usr/bin/env python3
"""Fail-closed shared and per-job validation for MF-011."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import music_catalog
from validate_mf008c_creative import EVENTS


PROFILE_NAMES = ["palette_profile", "camera_profile", "node_profile", "projection_profile", "cta_profile"]
MECHANISMS = {"tracking", "classification_link", "biometric_scan"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def object_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path) -> dict:
    return json.loads(Path(path).read_text())


def shared(args) -> dict:
    root = Path(args.project_root).resolve()
    manifest_path = Path(args.manifest).resolve()
    manifest = load(manifest_path)
    campaign = manifest["campaign"]
    grammar_path = root / campaign["production_grammar_file"]
    grammar = load(grammar_path)
    catalog_path = root / manifest["music_catalog"]
    common = argparse.Namespace(root=root, catalog=catalog_path, provenance_defaults=root / "config/music/provenance-defaults.json")
    refresh, refresh_code = music_catalog.refresh(common)
    catalog_validation, catalog_code = music_catalog.validate_catalog(common)
    catalog = load(catalog_path)
    tracks = {track["id"]: track for track in catalog["tracks"] if track["project"] == campaign["project"]}
    checks, errors, pinned, jobs = {}, [], [], []

    def check(name, passed, detail=None):
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
        if not passed:
            errors.append(name.upper() + "_FAILED")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    manifest_hash = sha256(manifest_path)
    grammar_hash = sha256(grammar_path)
    check("manifest_syntax", isinstance(manifest, dict) and isinstance(manifest.get("jobs"), list), manifest_hash)
    check("baseline_git_ref", head == campaign.get("baseline_git_ref"), {"head": head, "pinned": campaign.get("baseline_git_ref")})
    check("grammar_frozen", grammar.get("status") == "FROZEN" and grammar.get("id") == campaign.get("production_grammar"), grammar.get("id"))
    for relative, expected in grammar.get("files", {}).items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        pinned.append({"path": relative, "expected_sha256": expected, "actual_sha256": actual,
                       "status": "PASS" if actual == expected else "FAIL"})
    check("pinned_grammar_files", bool(pinned) and all(item["status"] == "PASS" for item in pinned),
          f"{sum(item['status'] == 'PASS' for item in pinned)}/{len(pinned)}")
    renderer_files = [item for item in pinned if item["path"].startswith("godot/")]
    renderer_hash = object_hash({item["path"]: item["actual_sha256"] for item in renderer_files})
    policy = manifest["policy"]
    check("renderer_changes_prohibited", all(policy.get(name) is False for name in
          ["allow_renderer_changes", "allow_runtime_architecture_changes", "allow_visual_grammar_changes"]), "config/fixture only")
    audio = manifest["audio_policy"]
    check("music_only_policy", audio == {"music": "enabled", "sfx": "disabled", "ambient_machine_audio": "disabled", "narration": "off", "presentation": "music_only"}, audio)
    check("catalog_refresh", refresh_code == 0 and not refresh.get("changed") and not refresh.get("missing"), refresh)
    check("catalog_validation", catalog_code == 0, catalog_validation)
    catalog_hash = sha256(catalog_path)
    check("catalog_frozen", catalog_hash == grammar.get("music_catalog_sha256_at_freeze"), catalog_hash)
    approved_tracks = [track for track in tracks.values() if track["approval"]["status"] == "APPROVED"
                       and track["approval"]["approved_sha256"] == track["integrity"]["sha256"]]
    approved_regions = [(track, region) for track in tracks.values() for region in track["cue_regions"]
                        if region["approval"]["status"] == "APPROVED"
                        and region["approval"]["approved_sha256"] == track["integrity"]["sha256"]]
    approval_snapshot = [{"track": track["id"], "track_status": track["approval"]["status"],
                          "track_hash": track["approval"]["approved_sha256"], "region": region["id"],
                          "region_status": region["approval"]["status"], "region_hash": region["approval"]["approved_sha256"]}
                         for track, region in approved_regions]
    check("approved_library", len(approved_tracks) == 4 and len(approved_regions) == 20,
          {"tracks": len(approved_tracks), "regions": len(approved_regions)})
    job_ids = [job.get("id") for job in manifest["jobs"]]
    fixture_paths = [job.get("fixture") for job in manifest["jobs"]]
    check("ten_manifest_jobs", len(job_ids) == campaign.get("job_limit") == 10 and len(set(job_ids)) == 10, job_ids)
    check("manifest_is_workload", len(set(fixture_paths)) == 10 and campaign.get("execution") == "sequential_unattended", fixture_paths)
    check("required_tools", all(shutil.which(name) for name in ["openclaw", "codex", "godot", "ffmpeg", "ffprobe"]), "required tools present")
    space_path = Path(campaign["output_archive"]).parent
    while not space_path.exists() and space_path != space_path.parent:
        space_path = space_path.parent
    free_bytes = shutil.disk_usage(space_path).free
    check("archive_space", free_bytes >= 20 * 1024**3, free_bytes)
    allowed_facts = set(manifest["approved_source"]["allowed_fact_ids"])
    for job in manifest["jobs"]:
        local = []
        fixture_path = root / job["fixture"]
        fixture = load(fixture_path) if fixture_path.is_file() else {}
        creative = job.get("creative", {})
        selection = job.get("music", {})
        mechanism = creative.get("mechanism")
        track = tracks.get(selection.get("track_id"))
        region = None if track is None else next((item for item in track["cue_regions"] if item["id"] == selection.get("region_id")), None)
        source = None if track is None else root / track["source"]
        source_hash = sha256(source) if source and source.is_file() else None
        runtime = float(selection.get("video_duration", 0))
        start = float(selection.get("actual_start", -1))
        end = float(selection.get("actual_end", -1))
        eligible = bool(track and region and source_hash == track["integrity"]["sha256"] == track["approval"]["approved_sha256"]
                        == region["approval"]["approved_sha256"] and track["approval"]["status"] == "APPROVED"
                        and region["approval"]["status"] == "APPROVED")
        bounds = bool(region and region["usable_start"] <= start < end <= region["usable_end"]
                      and abs((end - start) - runtime) < 1e-6 and 26 <= runtime <= 30)
        query = selection.get("query", {})
        query_match = bool(region and set(query.get("mood", [])) & set(region.get("mood_tags", []))
                           and set(query.get("use_case", [])) & set(region.get("use_cases", [])))
        fixture_match = fixture.get("creative") == creative and fixture.get("format", {}).get("duration_seconds") == runtime
        fixture_audio = fixture.get("campaign_audio_policy", {})
        phrases = job.get("phrases", [])
        facts_valid = bool(job.get("story_fact_ids")) and set(job["story_fact_ids"]) <= allowed_facts
        concise = len(phrases) == 3 and all(2 <= len(phrase.replace("/", " ").split()) <= 8 for phrase in phrases)
        if mechanism not in MECHANISMS: local.append("MECHANISM_UNAPPROVED")
        if creative.get("events") != EVENTS.get(mechanism): local.append("EVENT_SEQUENCE_UNAPPROVED")
        if not eligible: local.append("MUSIC_APPROVAL_OR_HASH_INVALID")
        if not bounds: local.append("MUSIC_SUBSECTION_OUTSIDE_APPROVED_REGION")
        if not query_match: local.append("MUSIC_QUERY_MISMATCH")
        if not fixture_match: local.append("RESOLVED_FIXTURE_DRIFT")
        if fixture.get("sfx") != [] or fixture_audio != audio: local.append("MUSIC_ONLY_FIXTURE_INVALID")
        if any(beat.get("narration") is not None for beat in fixture.get("beats", [])) or job.get("narration") is not None: local.append("NARRATION_POLICY_INVALID")
        if job.get("renderer_changes_required") is not False: local.append("WORKER_BOUNDARY_INVALID")
        if not facts_valid or not concise: local.append("STORY_OR_TEXT_CONTRACT_INVALID")
        jobs.append({"job_id": job["id"], "mechanism": mechanism, "track_id": selection.get("track_id"),
                     "region_id": selection.get("region_id"), "source_sha256": source_hash, "runtime_seconds": runtime,
                     "eligible": eligible, "bounds_valid": bounds, "query_match": query_match,
                     "fixture_match": fixture_match, "errors": local, "result": "PASS" if not local else "FAIL"})
    check("job_preflight", all(job["result"] == "PASS" for job in jobs), jobs)
    check("mechanism_breadth", {job["mechanism"] for job in jobs} == MECHANISMS, [job["mechanism"] for job in jobs])
    profile_sets = [tuple(job["creative"][name] for name in PROFILE_NAMES) for job in manifest["jobs"]]
    check("bounded_cosmetic_variety", len(set(profile_sets)) >= 8, len(set(profile_sets)))
    check("music_variety", len({job["track_id"] for job in jobs}) == 4 and len({(job["track_id"], job["region_id"]) for job in jobs}) >= 8, None)
    check("runtime_variety", len({job["runtime_seconds"] for job in jobs}) >= 5, sorted({job["runtime_seconds"] for job in jobs}))
    check("no_publication", campaign["publish"] is False and policy["automatic_publication"] is False, "publish=false")
    return {
        "slice": "MF-011", "type": "shared_preflight", "campaign_id": campaign["id"],
        "manifest_path": str(manifest_path), "manifest_sha256": manifest_hash, "grammar_id": grammar["id"],
        "grammar_source_git_ref": grammar["source_git_ref"], "grammar_sha256": grammar_hash,
        "baseline_git_ref": head, "renderer_source_hash": renderer_hash,
        "shared_style_sha256": sha256(root / "config/visual-grammar.json"), "catalog_sha256": catalog_hash,
        "approval_state_sha256": object_hash(approval_snapshot), "approved_tracks": len(approved_tracks),
        "approved_regions": len(approved_regions), "checks": checks, "pinned_files": pinned, "jobs": jobs,
        "errors": errors, "state": "READY" if not errors else "FAILED", "result": "PASS" if not errors else "FAIL"
    }


def job_output(args) -> dict:
    job = load(args.job)
    fixture = load(args.fixture)
    layout = load(args.layout)
    execution = load(args.execution)
    media = load(args.media)
    music = load(args.music)
    mix = load(args.mix)
    selection = load(args.selection)
    sfx = load(args.sfx)
    narration = load(args.narration)
    requested = fixture["creative"]
    observed = layout.get("generated_scene", {}).get("creative_control", {})
    runtime = float(job["music"]["video_duration"])
    mechanism = requested["mechanism"]
    exclusivity = observed.get("mechanism_exclusivity", {})
    checks = {
        "mechanism_loaded": observed.get("mechanism") == mechanism,
        "mechanism_exclusivity": set(exclusivity) == MECHANISMS and exclusivity.get(mechanism) == "PASS"
            and all(exclusivity.get(other) == "NOT_RUN" for other in MECHANISMS - {mechanism}),
        "unique_events": [item.get("id") for item in observed.get("event_evidence", [])] == requested["events"]
            and all(item.get("status") == "PASS" for item in observed.get("event_evidence", [])),
        "profiles_loaded": all(observed.get(key) == requested[key] for key in PROFILE_NAMES),
        "timing_loaded": observed.get("timing") == requested["timing"],
        "campaign_identity": observed.get("campaign_identity") == "unknown_process_recovered_record"
            and observed.get("single_window_preserved") is True,
        "timeline": execution.get("result") == "PASS" and execution.get("total_frames") == round(runtime * 30)
            and abs(float(execution.get("duration", 0)) - runtime) < 1e-6,
        "music_selection": selection.get("contract") == "mf010_music_selection_v1" and selection.get("result") == "PASS",
        "music_source": music.get("result") == "PASS" and music.get("source_sha256") == selection.get("track_sha256"),
        "music_offsets": abs(float(music.get("selected_offset", -1)) - job["music"]["actual_start"]) < 1e-6
            and abs(float(music.get("duration", -1)) - runtime) < .002,
        "music_mix": mix.get("result") == "PASS" and mix.get("segments") == [] and mix.get("music", {}).get("status") == "PASS",
        "sfx_disabled": fixture.get("sfx") == [] and sfx.get("event_count") == 0 and sfx.get("result") == "PASS",
        "ambient_disabled": sfx.get("ambient_machine_audio") is False,
        "narration_off": narration.get("segments") == [] and narration.get("policy") == "off" and narration.get("result") == "PASS",
        "encoded_media": media.get("result") == "PASS",
    }
    return {
        "slice": "MF-011", "type": "job_output_validation", "job_id": job["id"], "mechanism": mechanism,
        "mechanism_exclusivity": exclusivity, "profiles": {key: requested[key] for key in PROFILE_NAMES},
        "music_selection": selection, "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
        "errors": [key.upper() + "_FAILED" for key, value in checks.items() if not value],
        "result": "PASS" if all(checks.values()) else "FAIL"
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["shared", "job-output"], required=True)
    parser.add_argument("--project-root")
    parser.add_argument("--manifest")
    parser.add_argument("--job")
    parser.add_argument("--fixture")
    parser.add_argument("--layout")
    parser.add_argument("--execution")
    parser.add_argument("--media")
    parser.add_argument("--music")
    parser.add_argument("--mix")
    parser.add_argument("--selection")
    parser.add_argument("--sfx")
    parser.add_argument("--narration")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = shared(args) if args.mode == "shared" else job_output(args)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        result = {"slice": "MF-011", "type": args.mode, "errors": [{"code": "VALIDATOR_EXCEPTION", "detail": str(error)}], "result": "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
