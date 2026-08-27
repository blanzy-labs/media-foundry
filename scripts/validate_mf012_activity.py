#!/usr/bin/env python3
"""Independent fail-closed validation for MF-012 activity configs and outputs."""

import argparse
import json
from pathlib import Path


SUBJECT_TERMS = ["simon", "leo", "zeph", "syndicate", "kill-switch", "kill_switch"]
ALLOWED_EVENT_KEYS = {"id", "type", "target", "start", "duration", "intensity", "repeat", "origin", "destination", "overlap"}


def load(path) -> dict:
    return json.loads(Path(path).read_text())


def validate_config(root: Path, fixture: dict) -> dict:
    vocabulary = load(root / "config/activity-vocabulary/visual-activity-v1.json")
    definitions = {entry["name"]: entry for entry in vocabulary["primitives"]}
    openings = {entry["name"] for entry in vocabulary["openings"]}
    cameras = {entry["name"] for entry in vocabulary["cameras"]}
    known_targets = set(vocabulary["targets"])
    activity = fixture.get("activity", {})
    errors, checks = [], {}

    def check(name, passed, code):
        checks[name] = "PASS" if passed else "FAIL"
        if not passed:
            errors.append(code)

    serialized = json.dumps(vocabulary).lower()
    primitive_names = list(definitions)
    check("vocabulary_size", 12 <= len(primitive_names) <= 18 and len(primitive_names) == len(set(primitive_names)), "VOCABULARY_SIZE_INVALID")
    check("subject_agnostic", not any(term in serialized for term in SUBJECT_TERMS), "SUBJECT_SPECIFIC_ACTIVITY_INVALID")
    check("activity_present", bool(activity) and activity.get("version") == 1, "ACTIVITY_SEQUENCE_MISSING")
    required = {"version", "demo", "dominant_activity", "supporting_activities", "opening_choreography",
                "camera_choreography", "targets", "spatial_behavior", "text_behavior", "sequence"}
    check("contract_fields", required <= set(activity), "ACTIVITY_CONTRACT_INCOMPLETE")
    runtime = float(fixture.get("format", {}).get("duration_seconds", 0))
    check("demo_runtime", activity.get("demo") is True and 8 <= runtime <= 15, "ACTIVITY_DEMO_DURATION_INVALID")
    supporting = activity.get("supporting_activities", [])
    dominant = activity.get("dominant_activity")
    check("complexity_budget", isinstance(supporting, list) and len(supporting) <= vocabulary["complexity"]["maximum_supporting_activities"], "ACTIVITY_COMPLEXITY_EXCEEDED")
    check("opening", activity.get("opening_choreography") in openings, "UNKNOWN_OPENING_CHOREOGRAPHY")
    check("camera", activity.get("camera_choreography") in cameras, "UNKNOWN_CAMERA_CHOREOGRAPHY")
    targets = activity.get("targets", [])
    check("target_declarations", bool(targets) and len(targets) == len(set(targets)) and set(targets) <= known_targets, "INVALID_TARGET_DECLARATION")
    sequence = activity.get("sequence", [])
    check("sequence_size", 1 <= len(sequence) <= vocabulary["complexity"]["maximum_sequence_entries"], "ACTIVITY_SEQUENCE_SIZE_INVALID")
    event_errors, seen, ids, prior_start = [], [], set(), -1.0
    intervals = []
    for entry in sequence:
        identifier = str(entry.get("id", ""))
        activity_type = str(entry.get("type", ""))
        target = str(entry.get("target", ""))
        if set(entry) - ALLOWED_EVENT_KEYS:
            event_errors.append("ACTIVITY_FIELD_UNKNOWN")
        if not identifier or identifier in ids:
            event_errors.append("ACTIVITY_ID_INVALID")
        ids.add(identifier)
        if activity_type not in definitions:
            event_errors.append("UNKNOWN_ACTIVITY")
            continue
        if target not in targets or target not in known_targets:
            event_errors.append("MISSING_TARGET_REFERENCE")
        start = entry.get("start")
        duration = entry.get("duration")
        intensity = entry.get("intensity")
        repeat = entry.get("repeat", 1)
        timing_valid = all(isinstance(value, (int, float)) for value in [start, duration, intensity])
        timing_valid = timing_valid and start >= 0 and duration > 0 and start + duration <= runtime and .1 <= intensity <= 1 and isinstance(repeat, int) and 1 <= repeat <= 4
        if not timing_valid:
            event_errors.append("INVALID_ACTIVITY_TIMING")
        elif start < prior_start:
            event_errors.append("ACTIVITY_SEQUENCE_ORDER_INVALID")
        else:
            prior_start = float(start)
            intervals.append((float(start), float(start + duration)))
        for dependency in definitions[activity_type].get("dependencies", []):
            if dependency not in seen:
                event_errors.append("IMPOSSIBLE_ACTIVITY_DEPENDENCY")
        seen.append(activity_type)
        family = definitions[activity_type]["family"]
        if family != dominant and family not in supporting:
            event_errors.append("ACTIVITY_FAMILY_OUTSIDE_BUDGET")
    check("sequence_entries", not event_errors, event_errors[0] if event_errors else "ACTIVITY_SEQUENCE_INVALID")
    has_overlap = any(left[0] < right[1] and right[0] < left[1] for index, left in enumerate(intervals) for right in intervals[index + 1:])
    check("intentional_overlap", has_overlap, "ACTIVITY_OVERLAP_MISSING")
    check("fixture_strategy", fixture.get("visual_strategy", {}).get("preference") == "godot_activity_vocabulary_v1", "ACTIVITY_RENDERER_STRATEGY_INVALID")
    check("silent_visual_demo", fixture.get("music") is None and fixture.get("sfx") == [] and all(beat.get("narration") is None for beat in fixture.get("beats", [])), "ACTIVITY_DEMO_AUDIO_POLICY_INVALID")
    return {"slice": "MF-012", "type": "activity_config_validation", "fixture": fixture.get("id"),
            "dominant_activity": dominant, "supporting_activities": supporting,
            "opening_choreography": activity.get("opening_choreography"), "camera_choreography": activity.get("camera_choreography"),
            "primitive_count": len(primitive_names), "sequence": sequence, "checks": checks,
            "errors": errors, "result": "PASS" if not errors else "FAIL"}


def validate_output(args) -> dict:
    fixture = load(args.fixture)
    config = validate_config(Path(args.project_root).resolve(), fixture)
    layout = load(args.layout)
    media = load(args.media)
    observed = layout.get("generated_scene", {}).get("activity_vocabulary", {})
    expected = fixture["activity"]
    checks = {
        "config": config["result"] == "PASS",
        "renderer_strategy": layout.get("generated_scene", {}).get("strategy") == "godot_activity_vocabulary_v1",
        "dominant_activity": observed.get("dominant_activity") == expected["dominant_activity"],
        "supporting_activities": observed.get("supporting_activities") == expected["supporting_activities"],
        "opening": observed.get("opening_choreography") == expected["opening_choreography"],
        "camera": observed.get("camera_choreography") == expected["camera_choreography"],
        "all_events_observed": observed.get("all_observed") is True and observed.get("result") == "PASS"
            and len(observed.get("event_evidence", [])) == len(expected["sequence"]),
        "deterministic_seed": observed.get("deterministic") is True and observed.get("seed") == fixture.get("seed"),
        "encoded_media": media.get("result") == "PASS",
    }
    errors = [name.upper() + "_FAILED" for name, passed in checks.items() if not passed]
    return {"slice": "MF-012", "type": "activity_output_validation", "fixture": fixture.get("id"),
            "activity": observed, "checks": {name: "PASS" if passed else "FAIL" for name, passed in checks.items()},
            "errors": errors, "result": "PASS" if not errors else "FAIL"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["config", "output"], required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--layout")
    parser.add_argument("--media")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = validate_config(Path(args.project_root).resolve(), load(args.fixture)) if args.mode == "config" else validate_output(args)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        result = {"slice": "MF-012", "type": args.mode, "errors": [{"code": "VALIDATOR_EXCEPTION", "detail": str(error)}], "result": "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
