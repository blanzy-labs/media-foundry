#!/usr/bin/env python3
"""Independent fail-closed preflight for the bounded MF-008C creative API."""

import argparse
import json
from pathlib import Path


ENUMS = {
    "mechanism": {"tracking", "classification_link", "biometric_scan"},
    "palette_profile": {"baseline", "pursuit", "mystery", "revelation"},
    "camera_profile": {"baseline", "tight_pursuit", "wide_investigation", "calm_to_push"},
    "node_profile": {"baseline", "urgent", "analytical", "stable_then_overload"},
    "projection_profile": {"baseline", "warning_trace", "classification", "biometric"},
    "cta_profile": {"baseline", "warning", "cool_signal", "revelation"},
}
EVENTS = {
    "tracking": ["target_search", "target_reacquire", "target_lock"],
    "classification_link": ["leo_resolve", "zeph_resolve", "bridge_attempt", "bridge_stable"],
    "biometric_scan": ["biometric_scan", "deep_scan", "hidden_region", "kill_switch_reveal"],
}
TIMING_BOUNDS = {
    "intro_seconds": (5.0, 7.0), "investigation_seconds": (10.0, 14.0),
    "result_hold_seconds": (1.0, 3.0), "cta_seconds": (5.0, 8.0),
}


def validate(root: Path, fixture: dict, require_approved_audio: bool) -> dict:
    creative = fixture.get("creative")
    if creative is None:
        return {"slice": "MF-008C", "fixture": fixture.get("id"), "mode": "baseline_compatibility",
                "state": "READY", "result": "PASS", "checks": {"legacy_fixture_without_creative": "PASS"}}
    errors, checks = [], {}

    def check(name, passed, error):
        checks[name] = "PASS" if passed else "FAIL"
        if not passed:
            errors.append(error)

    required = set(ENUMS) | {"events", "timing", "audio_cue"}
    check("required_fields", required <= set(creative), "CREATIVE_CONTROL_INCOMPLETE")
    for name, allowed in ENUMS.items():
        check(name, creative.get(name) in allowed, "CREATIVE_PROFILE_INVALID")
    mechanism = creative.get("mechanism")
    check("mechanism_events", creative.get("events") == EVENTS.get(mechanism), "CREATIVE_EVENT_CONTRACT_INVALID")
    timing = creative.get("timing", {})
    timing_valid = set(timing) == set(TIMING_BOUNDS)
    if timing_valid:
        timing_valid = all(isinstance(timing[name], (int, float)) and low <= timing[name] <= high
                           for name, (low, high) in TIMING_BOUNDS.items())
    duration = fixture.get("format", {}).get("duration_seconds")
    timing_valid = timing_valid and 24 <= duration <= 32 and abs(sum(timing.values()) - duration) < 1e-6
    check("timing_bounds", timing_valid, "CREATIVE_TIMING_INVALID")
    configured = {item.get("id"): item.get("time") for item in fixture.get("generated_scene", {}).get("events", [])}
    event_times = [configured.get(name) for name in EVENTS.get(mechanism, [])]
    event_valid = all(isinstance(value, (int, float)) for value in event_times) and event_times == sorted(event_times)
    if event_valid:
        intro_end = timing["intro_seconds"]
        investigation_end = intro_end + timing["investigation_seconds"]
        event_valid = intro_end <= event_times[0] and event_times[-1] <= investigation_end
    check("event_timing", event_valid, "CREATIVE_EVENT_TIMING_INVALID")

    cue_map = json.loads((root / "config/audio-cues/unknown-process-track-a.json").read_text())
    cue_id = creative.get("audio_cue")
    cue = cue_map.get("sections", {}).get(cue_id)
    check("audio_cue_exists", cue is not None, "AUDIO_CUE_UNKNOWN")
    approval_blocked = bool(cue) and not cue.get("approved", True)
    approved_valid = bool(cue) and cue.get("approved", True) and isinstance(cue.get("start"), (int, float))
    if require_approved_audio:
        check("audio_cue_approved", approved_valid, "AUDIO_CUE_NOT_APPROVED")
    else:
        checks["audio_cue_approved"] = "PENDING_APPROVAL" if approval_blocked else "PASS" if approved_valid else "FAIL"

    engineering_errors = [error for error in errors if not error.startswith("AUDIO_CUE_")]
    if engineering_errors:
        state, result = "NEEDS_ENGINEERING", "FAIL"
    elif require_approved_audio and approval_blocked:
        state, result = "BLOCKED_APPROVAL", "FAIL"
    elif errors:
        state, result = "BLOCKED_APPROVAL", "FAIL"
    else:
        state, result = "READY", "PASS"
    return {"slice": "MF-008C", "fixture": fixture.get("id"), "mode": "directed", "state": state,
            "creative": creative, "checks": checks, "errors": errors, "result": result}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--require-approved-audio", action="store_true")
    args = parser.parse_args()
    result = validate(Path(args.project_root).resolve(), json.loads(Path(args.fixture).read_text()), args.require_approved_audio)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2 if result["state"] == "BLOCKED_APPROVAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
