#!/usr/bin/env python3
"""Independently validate a completed MF-011 campaign archive."""

import argparse
import hashlib
import itertools
import json
import subprocess
from pathlib import Path


PROFILE_NAMES = ["palette_profile", "camera_profile", "node_profile", "projection_profile", "cta_profile"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def object_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def probe(path: Path) -> dict:
    process = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)],
                             capture_output=True, text=True)
    data = json.loads(process.stdout) if process.returncode == 0 else {}
    streams = data.get("streams", [])
    video = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
    return {"video_streams": len(video), "audio_streams": len(audio),
            "decoded_frames": int(video[0].get("nb_read_frames", 0)) if video else 0,
            "width": int(video[0].get("width", 0)) if video else 0,
            "height": int(video[0].get("height", 0)) if video else 0,
            "duration": float(data.get("format", {}).get("duration", 0))}


def full_decode(path: Path) -> bool:
    process = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
                             capture_output=True, text=True)
    return process.returncode == 0 and not process.stderr.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    archive = Path(args.archive).resolve()
    result_path = archive / "campaign-result.json"
    state_path = archive / "campaign-state.json"
    manifest_path = archive / "campaign-manifest.json"
    batch = load(result_path)
    state = load(state_path)
    manifest = load(manifest_path)
    grammar_path = root / manifest["campaign"]["production_grammar_file"]
    grammar = load(grammar_path)
    catalog_path = root / manifest["music_catalog"]
    catalog = load(catalog_path)
    tracks = {track["id"]: track for track in catalog["tracks"] if track["project"] == "unknown-process"}
    errors, jobs = [], []
    manifest_jobs = {job["id"]: job for job in manifest["jobs"]}
    state_jobs = {job["id"]: job for job in state["jobs"]}
    for item in batch.get("jobs", []):
        job_id = item["job_id"]
        job = manifest_jobs[job_id]
        job_dir = archive / job_id
        media = job_dir / "final.mp4"
        output_validation = load(job_dir / "validation/output.json")
        sfx = load(job_dir / "validation/sfx.json")
        narration = load(job_dir / "validation/narration.json")
        music = load(job_dir / "validation/music.json")
        selection = load(job_dir / "validation/music-selection.json")
        mix = load(job_dir / "validation/mix.json")
        resolved = load(job_dir / "resolved-config.json")
        media_probe = probe(media) if media.is_file() else {"video_streams": 0, "audio_streams": 0, "decoded_frames": 0, "duration": 0}
        track = tracks.get(job["music"]["track_id"])
        region = None if track is None else next((entry for entry in track["cue_regions"] if entry["id"] == job["music"]["region_id"]), None)
        source = None if track is None else root / track["source"]
        source_hash = sha256(source) if source and source.is_file() else None
        runtime = float(job["music"]["video_duration"])
        checks = {
            "terminal_ready": item.get("state") == "READY_FOR_REVIEW" and item.get("result") == "PASS",
            "retry_limit": 1 <= item.get("attempts", 0) <= 2 and state_jobs[job_id].get("attempts") == item.get("attempts"),
            "artifact_hash": media.is_file() and sha256(media) == item.get("artifact", {}).get("sha256"),
            "media_streams": media_probe["video_streams"] == 1 and media_probe["audio_streams"] == 1,
            "media_shape": media_probe.get("width") == 1080 and media_probe.get("height") == 1920,
            "runtime_and_frames": abs(media_probe["duration"] - runtime) <= .05 and media_probe["decoded_frames"] == round(runtime * 30),
            "full_decode": full_decode(media) if media.is_file() else False,
            "job_validation": output_validation.get("result") == "PASS" and all(value == "PASS" for value in output_validation.get("checks", {}).values()),
            "resolved_fixture": resolved.get("creative") == job["creative"] and resolved.get("format", {}).get("duration_seconds") == runtime,
            "music_only": resolved.get("sfx") == [] and sfx.get("event_count") == 0 and sfx.get("generated_audio") is False
                and sfx.get("ambient_machine_audio") is False and mix.get("segments") == [],
            "narration_off": narration.get("policy") == "off" and narration.get("segments") == [],
            "approved_track": bool(track and track["approval"]["status"] == "APPROVED"
                and source_hash == track["integrity"]["sha256"] == track["approval"]["approved_sha256"]),
            "approved_region": bool(region and region["approval"]["status"] == "APPROVED"
                and region["approval"]["approved_sha256"] == source_hash),
            "cue_bounds": bool(region and region["usable_start"] <= job["music"]["actual_start"]
                < job["music"]["actual_end"] <= region["usable_end"]
                and abs(job["music"]["actual_end"] - job["music"]["actual_start"] - runtime) < 1e-6),
            "selection_identity": selection.get("track_id") == job["music"]["track_id"]
                and selection.get("region_id") == job["music"]["region_id"] and selection.get("track_sha256") == source_hash,
            "music_preparation": music.get("result") == "PASS" and music.get("source_sha256") == source_hash
                and abs(music.get("selected_offset", -1) - job["music"]["actual_start"]) < 1e-6,
            "evidence": all((job_dir / relative).is_file() for relative in [
                "job-brief.json", "resolved-creative-profile.json", "contact-sheet.png", "motion-evidence/sequence.png",
                "representative-frames/phase-1.png", "representative-frames/phase-2.png",
                "representative-frames/phase-3.png", "representative-frames/cta.png"
            ]),
            "not_published": item.get("publish") is False,
        }
        local = [name.upper() + "_FAILED" for name, passed in checks.items() if not passed]
        errors.extend({"job_id": job_id, "code": code} for code in local)
        jobs.append({
            "job_id": job_id, "runtime_seconds": runtime, "frame_count": media_probe["decoded_frames"],
            "mechanism": job["creative"]["mechanism"],
            "profiles": {name: job["creative"][name] for name in PROFILE_NAMES},
            "track_id": job["music"]["track_id"], "track_title": item["music"]["track_title"],
            "region_id": job["music"]["region_id"], "actual_start": job["music"]["actual_start"],
            "actual_end": job["music"]["actual_end"], "fade_in": job["music"]["fade_in"],
            "fade_out": job["music"]["fade_out"], "source_sha256": source_hash,
            "sfx_count": sfx.get("event_count"), "artifact_path": str(media),
            "artifact_sha256": sha256(media) if media.is_file() else None,
            "checks": {name: "PASS" if passed else "FAIL" for name, passed in checks.items()},
            "errors": local, "result": "PASS" if not local else "FAIL",
        })
    pairwise = []
    for left, right in itertools.combinations(manifest["jobs"], 2):
        differentiators = []
        if left["creative"]["mechanism"] != right["creative"]["mechanism"]: differentiators.append("mechanism")
        for name in PROFILE_NAMES:
            if left["creative"][name] != right["creative"][name]: differentiators.append(name)
        if left["creative"]["timing"] != right["creative"]["timing"]: differentiators.append("pacing")
        if left["phrases"] != right["phrases"]: differentiators.append("event_narrative")
        if (left["music"]["track_id"], left["music"]["region_id"], left["music"]["actual_start"]) != (
                right["music"]["track_id"], right["music"]["region_id"], right["music"]["actual_start"]):
            differentiators.append("music")
        pairwise.append({"left": left["id"], "right": right["id"], "differentiators": differentiators,
                         "result": "PASS" if len(differentiators) >= 3 else "FAIL"})
    renderer_actual = {relative: sha256(root / relative) for relative in grammar["files"] if relative.startswith("godot/")}
    campaign_checks = {
        "manifest_hash": sha256(manifest_path) == batch.get("manifest_sha256"),
        "one_manifest_ten_jobs": len(manifest["jobs"]) == 10 and len(jobs) == 10,
        "campaign_state_model": state.get("transitions", [])[0].get("state") == "PENDING"
            and [event["state"] for event in state.get("transitions", [])] == ["PENDING", "PREFLIGHT", "RUNNING", "COMPLETE"],
        "all_jobs_terminal": len(jobs) == 10 and all(job["result"] == "PASS" for job in jobs),
        "shared_preflight": load(archive / "shared-preflight.json").get("result") == "PASS",
        "final_preflight": load(archive / "final-shared-preflight.json").get("result") == "PASS",
        "renderer_integrity": batch.get("renderer_changes") == 0 and batch.get("renderer_state_before") == renderer_actual
            == batch.get("renderer_state_after") and object_hash(renderer_actual) == batch.get("renderer_source_hash_before")
            == batch.get("renderer_source_hash_after"),
        "grammar_integrity": batch.get("grammar_id") == grammar["id"] and batch.get("grammar_sha256") == sha256(grammar_path),
        "catalog_integrity": batch.get("catalog_changes") == 0 and batch.get("catalog_sha256_before") == sha256(catalog_path)
            == batch.get("catalog_sha256_after"),
        "music_only_all": all(job.get("sfx_count") == 0 for job in jobs),
        "campaign_diversity": len(pairwise) == 45 and all(pair["result"] == "PASS" for pair in pairwise),
        "mechanism_breadth": {job["mechanism"] for job in jobs} == {"tracking", "classification_link", "biometric_scan"},
        "music_distribution": len({job["track_id"] for job in jobs}) == 4 and len({(job["track_id"], job["region_id"]) for job in jobs}) >= 8,
        "runtime_distribution": len({job["runtime_seconds"] for job in jobs}) >= 5,
        "campaign_evidence": (archive / "campaign-contact-sheet.png").is_file(),
        "no_publication": batch.get("published") == 0 and manifest["campaign"]["publish"] is False,
        "human_review_not_fabricated": batch.get("human_review") == "PENDING_HUMAN" and batch.get("useful_candidate_percentage") is None,
    }
    errors.extend({"code": name.upper() + "_FAILED"} for name, passed in campaign_checks.items() if not passed)
    result = {
        "slice": "MF-011", "type": "independent_campaign_validation", "archive": str(archive),
        "jobs": jobs, "pairwise_diversity": pairwise,
        "checks": {name: "PASS" if passed else "FAIL" for name, passed in campaign_checks.items()},
        "errors": errors, "human_review": "PENDING_HUMAN", "result": "PASS" if not errors else "FAIL",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
