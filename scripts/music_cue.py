#!/usr/bin/env python3
"""Human cue-region review, listing, editing, and selection evidence."""

import argparse
import json
from pathlib import Path

import music_catalog


def locate(catalog, project, track_id, region_id=None):
    track = next((item for item in catalog.get("tracks", []) if item.get("project") == project and item.get("id") == track_id), None)
    region = None if track is None or region_id is None else next((item for item in track.get("cue_regions", []) if item.get("id") == region_id), None)
    return track, region


def current_hash(root, track):
    source = root / track["source"]
    if not source.is_file():
        raise ValueError("MISSING_LOCAL_ASSET")
    actual = music_catalog.sha256(source)
    if actual != track.get("integrity", {}).get("sha256"):
        raise ValueError("SOURCE_HASH_MISMATCH")
    return actual


def valid_region(track, region):
    start, end = region.get("usable_start"), region.get("usable_end")
    duration = float(track.get("technical", {}).get("duration_seconds", 0))
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start < 0 or end <= start or end > duration or end - start < 10:
        raise ValueError("CUE_REGION_BOUNDS_INVALID")
    for name in ["preferred_entry", "preferred_exit"]:
        value = region.get(name)
        if value is not None and (not isinstance(value, (int, float)) or value < start or value > end):
            raise ValueError("CUE_REGION_PREFERRED_POINT_INVALID")
    if set(region.get("mood_tags", [])) - music_catalog.MOOD_TAGS:
        raise ValueError("CUE_REGION_MOOD_INVALID")
    if set(region.get("use_cases", [])) - music_catalog.USE_CASES:
        raise ValueError("CUE_REGION_USE_CASE_INVALID")


def review(args, status):
    catalog = json.loads(args.catalog.read_text()); track, region = locate(catalog, args.project, args.track_id, args.region_id)
    if track is None: raise ValueError("TRACK_NOT_FOUND")
    if region is None: raise ValueError("CUE_REGION_NOT_FOUND")
    actual = current_hash(args.root, track); valid_region(track, region)
    if region.get("approval", {}).get("proposed_sha256") != actual:
        raise ValueError("CUE_REGION_REVIEW_REQUIRED")
    if status == "APPROVED" and (track.get("approval", {}).get("status") != "APPROVED" or track.get("approval", {}).get("approved_sha256") != actual):
        raise ValueError("TRACK_NOT_APPROVED")
    previous = region["approval"].copy()
    region["approval"] = {"status": status, "proposed_sha256": actual,
                          "approved_sha256": actual if status == "APPROVED" else None,
                          "reviewed_at": music_catalog.now(), "reviewer": args.reviewer, "note": args.note}
    track["history"].append({"event": "CUE_" + status, "at": music_catalog.now(), "region_id": region["id"],
                             "sha256": actual, "previous_approval": previous})
    catalog["updated_at"] = music_catalog.now(); music_catalog.write_json(args.catalog, catalog)
    return {"operation": "cue_" + status.lower(), "qualified_id": track["qualified_id"], "region_id": region["id"],
            "source_sha256": actual, "status": status, "result": "PASS"}


def edit(args):
    catalog = json.loads(args.catalog.read_text()); track, region = locate(catalog, args.project, args.track_id, args.region_id)
    if track is None: raise ValueError("TRACK_NOT_FOUND")
    if region is None: raise ValueError("CUE_REGION_NOT_FOUND")
    actual = current_hash(args.root, track)
    for name in ["usable_start", "usable_end", "preferred_entry", "preferred_exit"]:
        value = getattr(args, name)
        if value is not None: region[name] = value
    if args.clear_preferred_entry: region["preferred_entry"] = None
    if args.clear_preferred_exit: region["preferred_exit"] = None
    if args.mood_tags is not None: region["mood_tags"] = [value for value in args.mood_tags.split(",") if value]
    if args.use_cases is not None: region["use_cases"] = [value for value in args.use_cases.split(",") if value]
    if args.narration_friendliness is not None: region["narration_friendliness"] = args.narration_friendliness
    if args.intensity is not None: region["intensity"] = args.intensity
    if args.notes is not None: region["human"]["notes"] = args.notes
    region["human"]["edited"] = True; valid_region(track, region)
    previous = region["approval"].copy()
    region["approval"] = {"status": "PENDING_APPROVAL", "proposed_sha256": actual, "approved_sha256": None,
                          "reviewed_at": None, "reviewer": None, "note": "Edited region requires review."}
    track["history"].append({"event": "CUE_EDITED", "at": music_catalog.now(), "region_id": region["id"],
                             "sha256": actual, "previous_approval": previous})
    catalog["updated_at"] = music_catalog.now(); music_catalog.write_json(args.catalog, catalog)
    return {"operation": "cue_edit", "qualified_id": track["qualified_id"], "region": region, "status": "PENDING_APPROVAL", "result": "PASS"}


def list_regions(args):
    catalog = json.loads(args.catalog.read_text()); rows = []
    for track in catalog.get("tracks", []):
        if track.get("project") != args.project: continue
        for region in track.get("cue_regions", []):
            status = region.get("approval", {}).get("status")
            if args.approved and status != "APPROVED": continue
            if args.mood and args.mood not in region.get("mood_tags", []): continue
            if args.use_case and args.use_case not in region.get("use_cases", []): continue
            rows.append({"track_id": track["id"], "qualified_id": track["qualified_id"], "region_id": region["id"],
                         "status": status, "usable_start": region["usable_start"], "usable_end": region["usable_end"],
                         "preferred_entry": region["preferred_entry"], "preferred_exit": region["preferred_exit"],
                         "mood_tags": region["mood_tags"], "use_cases": region["use_cases"]})
    return {"operation": "cue_list", "project": args.project, "approved_only": args.approved, "regions": rows, "count": len(rows), "result": "PASS"}


def select(args):
    catalog = json.loads(args.catalog.read_text()); track, region = locate(catalog, args.project, args.track_id, args.region_id)
    if track is None: raise ValueError("TRACK_NOT_FOUND")
    if region is None: raise ValueError("CUE_REGION_NOT_FOUND")
    actual = current_hash(args.root, track); valid_region(track, region)
    if track["approval"].get("status") != "APPROVED" or track["approval"].get("approved_sha256") != actual:
        raise ValueError("TRACK_NOT_APPROVED")
    if region["approval"].get("status") != "APPROVED" or region["approval"].get("approved_sha256") != actual:
        raise ValueError("CUE_REGION_NOT_APPROVED")
    if args.actual_start < region["usable_start"] or args.actual_end > region["usable_end"] or args.actual_end <= args.actual_start:
        raise ValueError("CUE_SUBSECTION_OUTSIDE_APPROVED_REGION")
    selected_duration = args.actual_end - args.actual_start
    if abs(selected_duration - args.video_duration) > .05:
        raise ValueError("CUE_SUBSECTION_DURATION_MISMATCH")
    if args.fade_in < 0 or args.fade_out < 0 or args.fade_in + args.fade_out >= selected_duration:
        raise ValueError("CUE_FADE_INVALID")
    result = {"contract": "mf010_music_selection_v1", "project": args.project, "track_id": track["id"],
              "qualified_id": track["qualified_id"], "track_sha256": actual, "region_id": region["id"],
              "usable_start": region["usable_start"], "usable_end": region["usable_end"],
              "actual_start": args.actual_start, "actual_end": args.actual_end, "video_duration": args.video_duration,
              "fade_in": args.fade_in, "fade_out": args.fade_out, "result": "PASS"}
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1]); parser.add_argument("--catalog", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ["approve", "reject"]:
        child = sub.add_parser(command); child.add_argument("project"); child.add_argument("track_id"); child.add_argument("region_id")
        child.add_argument("--reviewer"); child.add_argument("--note"); child.add_argument("--json", action="store_true")
    child = sub.add_parser("edit"); child.add_argument("project"); child.add_argument("track_id"); child.add_argument("region_id")
    child.add_argument("--usable-start", type=float); child.add_argument("--usable-end", type=float); child.add_argument("--preferred-entry", type=float); child.add_argument("--preferred-exit", type=float)
    child.add_argument("--clear-preferred-entry", action="store_true"); child.add_argument("--clear-preferred-exit", action="store_true")
    child.add_argument("--mood-tags"); child.add_argument("--use-cases"); child.add_argument("--narration-friendliness", choices=["high", "medium", "low"]); child.add_argument("--intensity", choices=["low", "medium", "high", "rising", "falling"]); child.add_argument("--notes"); child.add_argument("--json", action="store_true")
    child = sub.add_parser("list"); child.add_argument("--project", required=True); child.add_argument("--approved", action="store_true"); child.add_argument("--mood", choices=sorted(music_catalog.MOOD_TAGS)); child.add_argument("--use-case", choices=sorted(music_catalog.USE_CASES)); child.add_argument("--json", action="store_true")
    child = sub.add_parser("select"); child.add_argument("project"); child.add_argument("track_id"); child.add_argument("region_id"); child.add_argument("--actual-start", type=float, required=True); child.add_argument("--actual-end", type=float, required=True); child.add_argument("--video-duration", type=float, required=True); child.add_argument("--fade-in", type=float, default=0); child.add_argument("--fade-out", type=float, default=0); child.add_argument("--output"); child.add_argument("--json", action="store_true")
    args = parser.parse_args(); args.root = args.root.resolve(); args.catalog = (args.catalog or args.root / "config/music/catalog.json").resolve()
    try:
        if args.command == "approve": result = review(args, "APPROVED")
        elif args.command == "reject": result = review(args, "REJECTED")
        elif args.command == "edit": result = edit(args)
        elif args.command == "list": result = list_regions(args)
        else: result = select(args)
        code = 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        result = {"operation": "cue_" + args.command, "errors": [{"code": str(error)}], "result": "FAIL"}; code = 1
    print(json.dumps(result, indent=2)); return code


if __name__ == "__main__":
    raise SystemExit(main())
