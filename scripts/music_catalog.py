#!/usr/bin/env python3
"""Deterministic music discovery, approval, validation, and production query."""

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path


SUPPORTED = [".flac", ".m4a", ".mp3", ".ogg", ".wav"]
APPROVAL_STATES = {"UNREVIEWED", "APPROVED", "REJECTED", "REVIEW_REQUIRED", "MISSING"}
REGION_STATES = {"UNREVIEWED", "PENDING_APPROVAL", "APPROVED", "REJECTED", "REVIEW_REQUIRED"}
MOOD_TAGS = {"mystery", "investigation", "pursuit", "tension", "paranoia", "discovery", "revelation", "ominous", "escalation", "ambient", "reflective", "resolution"}
USE_CASES = {"tracking", "classification", "biometric_reveal", "title_reveal", "cta", "excerpt", "ambient_teaser", "direct_promo"}
PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_id(filename):
    value = unicodedata.normalize("NFKD", Path(filename).stem).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value


def load_json(path, default):
    return json.loads(path.read_text()) if path.is_file() else default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n")
    temporary.replace(path)


def inspect(path):
    process = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=format_name,duration,bit_rate:stream=codec_type,codec_name,sample_rate,channels,bit_rate",
        "-of", "json", str(path)
    ], capture_output=True, text=True)
    if process.returncode:
        raise ValueError("FFPROBE_FAILED: " + (process.stderr.strip() or "unreadable audio"))
    try:
        probe = json.loads(process.stdout)
        stream = next(item for item in probe.get("streams", []) if item.get("codec_type") == "audio")
        duration = float(probe.get("format", {}).get("duration"))
        sample_rate = int(stream.get("sample_rate"))
        channels = int(stream.get("channels"))
        bitrate_value = stream.get("bit_rate") or probe.get("format", {}).get("bit_rate")
        bitrate = int(bitrate_value) if bitrate_value not in (None, "N/A", "") else None
    except (StopIteration, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"AUDIO_STREAM_INVALID: {error}") from error
    if duration <= 0 or sample_rate <= 0 or channels <= 0:
        raise ValueError("AUDIO_STREAM_INVALID: non-positive technical value")
    return {
        "has_audio_stream": True,
        "duration_seconds": round(duration, 6),
        "codec": str(stream.get("codec_name", "unknown")),
        "container": str(probe.get("format", {}).get("format_name", "unknown")),
        "sample_rate": sample_rate,
        "channels": channels,
        "bitrate": bitrate,
    }


def provenance_for(project, defaults):
    value = dict(defaults.get("default", {"source_type": "unknown", "generator": "unknown"}))
    value.update(defaults.get("projects", {}).get(project, {}))
    return {"source_type": value.get("source_type", "unknown"), "generator": value.get("generator", "unknown"), "notes": ""}


def new_human_fields(project, defaults):
    return {
        "provenance": provenance_for(project, defaults),
        "approval": {"status": "UNREVIEWED", "approved_sha256": None, "reviewed_at": None, "reviewer": None, "note": None},
        "editorial": {"mood_tags": [], "preferred_uses": [], "notes": "", "release_eligible": False},
        "cue_regions": [],
        "history": [],
    }


def scan_files(root):
    music_root = root / "media/audio/music"
    found, ignored, errors = [], [], []
    if not music_root.is_dir():
        return found, ignored, [{"code": "MUSIC_ROOT_MISSING", "path": str(music_root)}]
    for item in sorted(music_root.iterdir(), key=lambda path: path.name.lower()):
        if item.is_file():
            ignored.append({"path": str(item.relative_to(root)), "reason": "LEGACY_ROOT_FILE_OUTSIDE_PROJECT_NAMESPACE"})
            continue
        if not item.is_dir():
            continue
        project = item.name
        if not PROJECT_RE.fullmatch(project):
            errors.append({"code": "PROJECT_ID_INVALID", "project": project})
            continue
        candidates = []
        for source in sorted(item.iterdir(), key=lambda path: path.name.lower()):
            relative = str(source.relative_to(root))
            if not source.is_file() or source.suffix.lower() not in SUPPORTED:
                ignored.append({"path": relative, "reason": "UNSUPPORTED_OR_NON_FILE"})
                continue
            track_id = stable_id(source.name)
            if not track_id:
                errors.append({"code": "TRACK_ID_INVALID", "path": relative})
                continue
            candidates.append((track_id, source))
        by_id = {}
        for track_id, source in candidates:
            by_id.setdefault(track_id, []).append(source)
        for track_id, sources in by_id.items():
            if len(sources) > 1:
                errors.append({"code": "TRACK_ID_COLLISION", "project": project, "track_id": track_id,
                               "paths": [str(path.relative_to(root)) for path in sources]})
            else:
                found.append((project, track_id, sources[0]))
    return found, ignored, errors


def refresh(args):
    root, catalog_path = args.root, args.catalog
    catalog = load_json(catalog_path, {"version": 1, "music_root": "media/audio/music", "supported_extensions": SUPPORTED, "tracks": []})
    defaults = load_json(args.provenance_defaults, {"default": {"source_type": "unknown", "generator": "unknown"}, "projects": {}})
    existing = {track.get("qualified_id"): track for track in catalog.get("tracks", [])}
    found, ignored, errors = scan_files(root)
    if any(error["code"] == "TRACK_ID_COLLISION" for error in errors):
        return {"operation": "refresh", "catalog": str(catalog_path), "discovered": len(found), "new": [], "changed": [],
                "unchanged": [], "missing": [], "ignored": ignored, "errors": errors, "result": "FAIL"}, 1
    output_tracks, seen = [], set()
    summary = {"new": [], "changed": [], "unchanged": [], "missing": [], "restored": []}
    for project, track_id, source in found:
        qualified = f"{project}:{track_id}"
        relative = str(source.relative_to(root))
        seen.add(qualified)
        try:
            technical = inspect(source)
            current_hash = sha256(source)
        except (OSError, ValueError) as error:
            errors.append({"code": "AUDIO_INSPECTION_FAILED", "path": relative, "detail": str(error)})
            continue
        old = existing.get(qualified)
        human = new_human_fields(project, defaults) if old is None else {
            key: old.get(key, new_human_fields(project, defaults)[key])
            for key in ["provenance", "approval", "editorial", "cue_regions", "history"]
        }
        first_discovered = old.get("discovery", {}).get("first_discovered_at") if old else now()
        previous_hash = old.get("integrity", {}).get("sha256") if old else None
        if old is None:
            change = "NEW"; summary["new"].append(qualified)
        elif previous_hash != current_hash:
            change = "SOURCE_CHANGED"; summary["changed"].append(qualified)
            human["history"].append({"event": "SOURCE_CHANGED", "at": now(), "previous_sha256": previous_hash,
                                     "previous_approval": human["approval"].copy()})
            human["approval"] = {**human["approval"], "status": "REVIEW_REQUIRED", "approved_sha256": None,
                                 "reviewed_at": None, "reviewer": None,
                                 "note": "Source bytes changed; prior review retained in history."}
            for region in human["cue_regions"]:
                region["approval"] = {**region.get("approval", {}), "status": "REVIEW_REQUIRED", "approved_sha256": None}
        elif old.get("discovery", {}).get("status") == "MISSING":
            change = "RESTORED"; summary["restored"].append(qualified)
            previous = human["approval"].get("previous_status", "REVIEW_REQUIRED")
            if previous == "APPROVED" and human["approval"].get("approved_sha256") == current_hash:
                human["approval"]["status"] = "APPROVED"
            else:
                human["approval"]["status"] = previous if previous in APPROVAL_STATES - {"MISSING"} else "REVIEW_REQUIRED"
            human["approval"].pop("previous_status", None)
        else:
            change = "UNCHANGED"; summary["unchanged"].append(qualified)
        recorded_change = old.get("discovery", {}).get("last_change", "NEW") if change == "UNCHANGED" else change
        output_tracks.append({
            "id": track_id, "qualified_id": qualified, "project": project, "source": relative,
            "discovery": {"status": "PRESENT", "first_discovered_at": first_discovered, "last_change": recorded_change},
            "technical": technical, "integrity": {"sha256": current_hash, "bytes": source.stat().st_size}, **human
        })
    for qualified, old in existing.items():
        if qualified in seen:
            continue
        missing = json.loads(json.dumps(old))
        missing["discovery"]["status"] = "MISSING"
        missing["discovery"]["last_change"] = "MISSING"
        if missing["approval"].get("status") != "MISSING":
            missing["history"].append({"event": "MISSING", "at": now(), "previous_approval": missing["approval"].copy()})
            missing["approval"]["previous_status"] = missing["approval"].get("status", "UNREVIEWED")
            missing["approval"]["status"] = "MISSING"
        output_tracks.append(missing)
        summary["missing"].append(qualified)
    output_tracks.sort(key=lambda track: (track["project"], track["id"]))
    next_catalog = {"version": 1, "music_root": "media/audio/music", "supported_extensions": SUPPORTED,
                    "updated_at": catalog.get("updated_at", now()), "tracks": output_tracks}
    comparable_old = {key: catalog.get(key) for key in ["version", "music_root", "supported_extensions", "tracks"]}
    comparable_new = {key: next_catalog.get(key) for key in ["version", "music_root", "supported_extensions", "tracks"]}
    catalog_changed = comparable_old != comparable_new
    if catalog_changed and not errors:
        next_catalog["updated_at"] = now()
        write_json(catalog_path, next_catalog)
    result = {"operation": "refresh", "catalog": str(catalog_path), "catalog_changed": catalog_changed,
              "discovered": len(found), **summary, "ignored": ignored, "errors": errors,
              "unreviewed": sum(track["approval"]["status"] == "UNREVIEWED" for track in output_tracks),
              "approved": sum(track["approval"]["status"] == "APPROVED" for track in output_tracks),
              "review_required": sum(track["approval"]["status"] == "REVIEW_REQUIRED" for track in output_tracks),
              "result": "PASS" if not errors else "FAIL"}
    return result, 0 if not errors else 1


def validate_catalog(args):
    errors, warnings = [], []
    try:
        catalog = json.loads(args.catalog.read_text())
    except (OSError, json.JSONDecodeError) as error:
        return {"operation": "validate", "errors": [{"code": "CATALOG_SYNTAX_INVALID", "detail": str(error)}], "result": "FAIL"}, 1
    tracks = catalog.get("tracks")
    if catalog.get("version") != 1 or catalog.get("music_root") != "media/audio/music" or not isinstance(tracks, list):
        errors.append({"code": "CATALOG_CONTRACT_INVALID"})
        tracks = tracks if isinstance(tracks, list) else []
    seen = set()
    eligible = []
    for track in tracks:
        qualified = track.get("qualified_id")
        if qualified in seen:
            errors.append({"code": "DUPLICATE_QUALIFIED_ID", "qualified_id": qualified})
        seen.add(qualified)
        project, track_id = track.get("project"), track.get("id")
        if not PROJECT_RE.fullmatch(str(project)) or not ID_RE.fullmatch(str(track_id)) or qualified != f"{project}:{track_id}":
            errors.append({"code": "TRACK_ID_INVALID", "qualified_id": qualified})
        source = args.root / str(track.get("source", ""))
        status = track.get("approval", {}).get("status")
        if status not in APPROVAL_STATES:
            errors.append({"code": "APPROVAL_STATUS_INVALID", "qualified_id": qualified})
        if not source.is_file():
            errors.append({"code": "MISSING_LOCAL_ASSET", "qualified_id": qualified, "source": track.get("source")})
            continue
        current_hash = sha256(source)
        catalog_hash = track.get("integrity", {}).get("sha256")
        if current_hash != catalog_hash:
            errors.append({"code": "SOURCE_HASH_MISMATCH", "qualified_id": qualified})
        approval_hash = track.get("approval", {}).get("approved_sha256")
        if status == "APPROVED" and (approval_hash != current_hash or track.get("discovery", {}).get("status") != "PRESENT"):
            errors.append({"code": "APPROVED_HASH_STALE", "qualified_id": qualified})
        region_ids = set()
        duration = float(track.get("technical", {}).get("duration_seconds", 0))
        for region in track.get("cue_regions", []):
            region_id = region.get("id")
            if region_id in region_ids or not ID_RE.fullmatch(str(region_id)):
                errors.append({"code": "CUE_REGION_ID_INVALID", "qualified_id": qualified, "region": region_id})
            region_ids.add(region_id)
            start, end = region.get("usable_start"), region.get("usable_end")
            bounds = isinstance(start, (int, float)) and isinstance(end, (int, float)) and 0 <= start < end <= duration and end - start >= 10.0
            entry, exit_value = region.get("preferred_entry"), region.get("preferred_exit")
            preferred = (entry is None or bounds and start <= entry <= end) and (exit_value is None or bounds and start <= exit_value <= end)
            region_approval = region.get("approval", {})
            if not bounds or not preferred:
                errors.append({"code": "CUE_REGION_BOUNDS_INVALID", "qualified_id": qualified, "region": region_id})
            if region_approval.get("status") not in REGION_STATES:
                errors.append({"code": "CUE_REGION_APPROVAL_INVALID", "qualified_id": qualified, "region": region_id})
            if set(region.get("mood_tags", [])) - MOOD_TAGS:
                errors.append({"code": "CUE_REGION_MOOD_INVALID", "qualified_id": qualified, "region": region_id})
            if set(region.get("use_cases", [])) - USE_CASES:
                errors.append({"code": "CUE_REGION_USE_CASE_INVALID", "qualified_id": qualified, "region": region_id})
            if region.get("narration_friendliness") not in {"high", "medium", "low"}:
                errors.append({"code": "CUE_REGION_NARRATION_INVALID", "qualified_id": qualified, "region": region_id})
            if region.get("intensity") not in {"low", "medium", "high", "rising", "falling"}:
                errors.append({"code": "CUE_REGION_INTENSITY_INVALID", "qualified_id": qualified, "region": region_id})
            if region_approval.get("status") == "PENDING_APPROVAL" and region_approval.get("proposed_sha256") != current_hash:
                errors.append({"code": "CUE_REGION_PROPOSAL_HASH_STALE", "qualified_id": qualified, "region": region_id})
            if region_approval.get("status") == "APPROVED" and (status != "APPROVED" or region_approval.get("approved_sha256") != current_hash):
                errors.append({"code": "CUE_REGION_APPROVED_HASH_STALE", "qualified_id": qualified, "region": region_id})
        if status == "APPROVED" and approval_hash == current_hash:
            eligible.append(qualified)
        elif status in {"UNREVIEWED", "REJECTED", "REVIEW_REQUIRED"}:
            warnings.append({"code": "TRACK_NOT_PRODUCTION_ELIGIBLE", "qualified_id": qualified, "status": status})
    result = {"operation": "validate", "catalog": str(args.catalog), "tracks": len(tracks),
              "production_eligible": eligible, "errors": errors, "warnings": warnings,
              "result": "PASS" if not errors else "FAIL"}
    return result, 0 if not errors else 1


def review(args, status):
    catalog = json.loads(args.catalog.read_text())
    qualified = f"{args.project}:{args.track_id}"
    track = next((item for item in catalog.get("tracks", []) if item.get("qualified_id") == qualified), None)
    if track is None:
        return {"operation": status.lower(), "errors": [{"code": "TRACK_NOT_FOUND", "qualified_id": qualified}], "result": "FAIL"}, 1
    source = args.root / track["source"]
    if not source.is_file():
        return {"operation": status.lower(), "errors": [{"code": "MISSING_LOCAL_ASSET", "qualified_id": qualified}], "result": "FAIL"}, 1
    current = sha256(source)
    if current != track.get("integrity", {}).get("sha256"):
        return {"operation": status.lower(), "errors": [{"code": "SOURCE_HASH_MISMATCH", "qualified_id": qualified}], "result": "FAIL"}, 1
    previous = track["approval"].copy()
    track["history"].append({"event": status, "at": now(), "sha256": current, "previous_approval": previous})
    track["approval"] = {"status": status, "approved_sha256": current if status == "APPROVED" else None,
                         "reviewed_at": now(), "reviewer": args.reviewer, "note": args.note}
    track["editorial"]["release_eligible"] = status == "APPROVED"
    catalog["updated_at"] = now()
    write_json(args.catalog, catalog)
    return {"operation": status.lower(), "qualified_id": qualified, "sha256": current, "status": status, "result": "PASS"}, 0


def query(args):
    validation, code = validate_catalog(args)
    catalog = json.loads(args.catalog.read_text()) if args.catalog.is_file() else {"tracks": []}
    approved = []
    if code == 0:
        for track in catalog["tracks"]:
            if track["project"] != args.project or track["qualified_id"] not in validation["production_eligible"]:
                continue
            regions = [region for region in track["cue_regions"] if region.get("approval", {}).get("status") == "APPROVED"
                       and region.get("approval", {}).get("approved_sha256") == track["integrity"]["sha256"]
                       and (args.mood is None or args.mood in region.get("mood_tags", []))
                       and (args.use_case is None or args.use_case in region.get("use_cases", []))]
            if args.require_approved_regions and not regions:
                continue
            approved.append({"id": track["id"], "qualified_id": track["qualified_id"], "source": track["source"],
                             "sha256": track["integrity"]["sha256"], "approved_regions": regions})
    matches = [{"track_id": track["id"], "qualified_id": track["qualified_id"], "region_id": region["id"],
                "usable_start": region["usable_start"], "usable_end": region["usable_end"],
                "preferred_entry": region["preferred_entry"], "preferred_exit": region["preferred_exit"]}
               for track in approved for region in track["approved_regions"]]
    result = {"operation": "query", "project": args.project, "mood": args.mood, "use_case": args.use_case,
              "require_approved_regions": args.require_approved_regions,
              "approved_tracks": approved, "matches": matches, "catalog_validation": validation["result"],
              "errors": validation["errors"], "result": "PASS" if code == 0 else "FAIL"}
    return result, code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--provenance-defaults", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["refresh", "validate"]:
        child = sub.add_parser(name); child.add_argument("--json", action="store_true")
    for name in ["approve", "reject"]:
        child = sub.add_parser(name); child.add_argument("project"); child.add_argument("track_id")
        child.add_argument("--reviewer"); child.add_argument("--note"); child.add_argument("--json", action="store_true")
    child = sub.add_parser("query"); child.add_argument("project"); child.add_argument("--require-approved-regions", action="store_true"); child.add_argument("--mood", choices=sorted(MOOD_TAGS)); child.add_argument("--use-case", choices=sorted(USE_CASES)); child.add_argument("--json", action="store_true")
    args = parser.parse_args()
    args.root = args.root.resolve()
    args.catalog = (args.catalog or args.root / "config/music/catalog.json").resolve()
    args.provenance_defaults = (args.provenance_defaults or args.root / "config/music/provenance-defaults.json").resolve()
    if args.command == "refresh": result, code = refresh(args)
    elif args.command == "validate": result, code = validate_catalog(args)
    elif args.command == "approve": result, code = review(args, "APPROVED")
    elif args.command == "reject": result, code = review(args, "REJECTED")
    else: result, code = query(args)
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
