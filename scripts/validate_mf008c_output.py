#!/usr/bin/env python3
"""Independently validate an encoded MF-008C proof and Godot evidence."""

import argparse
import json
from pathlib import Path


MECHANISMS = {"tracking", "classification_link", "biometric_scan"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--creative-preflight", required=True)
    parser.add_argument("--layout", required=True)
    parser.add_argument("--execution", required=True)
    parser.add_argument("--media", required=True)
    parser.add_argument("--music", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    fixture = json.loads(Path(args.fixture).read_text())
    preflight = json.loads(Path(args.creative_preflight).read_text())
    layout = json.loads(Path(args.layout).read_text())
    execution = json.loads(Path(args.execution).read_text())
    media = json.loads(Path(args.media).read_text())
    music = json.loads(Path(args.music).read_text())
    requested = fixture["creative"]
    observed = layout.get("generated_scene", {}).get("creative_control", {})
    mechanism = requested["mechanism"]
    exclusivity = observed.get("mechanism_exclusivity", {})
    checks = {
        "creative_preflight": preflight.get("result") == "PASS",
        "layout": layout.get("result") == "PASS",
        "creative_report": observed.get("result") == "PASS" and observed.get("mode") == "directed",
        "mechanism_loaded": observed.get("mechanism") == mechanism,
        "mechanism_exclusivity": set(exclusivity) == MECHANISMS and exclusivity.get(mechanism) == "PASS"
            and all(exclusivity.get(other) == "NOT_RUN" for other in MECHANISMS - {mechanism}),
        "unique_events": [item.get("id") for item in observed.get("event_evidence", [])] == requested["events"]
            and all(item.get("status") == "PASS" for item in observed.get("event_evidence", [])),
        "profiles_loaded": all(observed.get(name) == requested[name] for name in
            ["palette_profile", "camera_profile", "node_profile", "projection_profile", "cta_profile"]),
        "timing_loaded": observed.get("timing") == requested["timing"],
        "single_window": observed.get("single_window_preserved") is True,
        "campaign_identity": observed.get("campaign_identity") == "unknown_process_recovered_record",
        "timeline": execution.get("result") == "PASS" and execution.get("total_frames") == 840
            and abs(float(execution.get("duration", 0)) - 28.0) < 1e-6,
        "baseline_audio": music.get("result") == "PASS" and float(music.get("selected_offset", -1)) == 0.0,
        "encoded_media": media.get("result") == "PASS",
    }
    result = {"slice": "MF-008C", "fixture": fixture["id"], "mechanism": mechanism,
              "requested_profiles": {name: requested[name] for name in
                  ["palette_profile", "camera_profile", "node_profile", "projection_profile", "cta_profile"]},
              "mechanism_exclusivity": exclusivity, "event_evidence": observed.get("event_evidence", []),
              "checks": {name: "PASS" if passed else "FAIL" for name, passed in checks.items()},
              "result": "PASS" if all(checks.values()) else "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
