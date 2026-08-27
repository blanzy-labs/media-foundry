#!/usr/bin/env python3
"""Build five short declarative MF-012 activity demonstrations."""

import copy
import json
from pathlib import Path


DEMOS = [
    {
        "id": "01-moving-target-pursuit", "duration": 11.0, "dominant": "pursuit", "supporting": [],
        "opening": "target_already_moving", "camera": "lateral_track",
        "targets": ["primary_target", "tracker_field"],
        "spatial": ["target crosses center", "trackers enter from four scene quadrants", "reacquisition occurs off-center"],
        "text": ["type_on", "erase", "rewrite", "lock"],
        "phrases": ["TARGET ACTIVE", "TRACE LOST / SEARCHING", "TARGET LOCKED"],
        "sequence": [
            ["acquire", "target_acquire", "primary_target", 0.5, 1.0, 0.8],
            ["move", "target_move", "primary_target", 1.1, 3.0, 1.0],
            ["escape", "target_escape", "primary_target", 3.4, 1.0, 1.0],
            ["reacquire", "target_reacquire", "primary_target", 4.3, 1.3, 1.0],
            ["converge", "tracker_converge", "tracker_field", 4.8, 2.2, 0.9],
            ["lock", "target_lock", "primary_target", 6.8, 1.2, 1.0]
        ]
    },
    {
        "id": "02-record-reconstruction", "duration": 12.0, "dominant": "reconstruction", "supporting": [],
        "opening": "corrupt_record_resolve", "camera": "reveal_from_detail",
        "targets": ["fragment_field", "primary_record"],
        "spatial": ["fragments spawn across chamber", "pieces drift toward projection", "one coherent record consolidates"],
        "text": ["scramble", "resolve", "reveal_hidden"],
        "phrases": ["CORRUPT FRAGMENTS", "ALIGNING RECORD", "RECORD RECONSTRUCTED"],
        "sequence": [
            ["spawn", "fragment_spawn", "fragment_field", 0.5, 1.5, 0.9],
            ["drift", "fragment_drift", "fragment_field", 1.0, 3.2, 0.8],
            ["align", "fragment_align", "fragment_field", 3.6, 2.5, 1.0],
            ["reconstruct", "record_reconstruct", "primary_record", 5.8, 2.2, 1.0]
        ]
    },
    {
        "id": "03-signal-bridge", "duration": 12.0, "dominant": "connection", "supporting": [],
        "opening": "follow_energy_packet", "camera": "follow_packet",
        "targets": ["node_a", "node_b", "wall_cells"],
        "spatial": ["isolated side nodes", "packet crosses full width", "downstream wall cells respond"],
        "text": ["type_on", "rewrite", "highlight", "lock"],
        "phrases": ["CONNECTION ATTEMPT", "SIGNAL TRAVELLING", "BRIDGE STABLE"],
        "sequence": [
            ["attempt", "connection_attempt", "node_b", 0.7, 2.4, 0.8],
            ["travel", "signal_travel", "node_b", 1.5, 3.0, 1.0],
            ["form", "bridge_form", "node_b", 4.1, 2.0, 0.9],
            ["stabilize", "bridge_stabilize", "wall_cells", 5.6, 2.2, 1.0]
        ]
    },
    {
        "id": "04-override-reroute", "duration": 11.0, "dominant": "override", "supporting": [],
        "opening": "signal_intrusion", "camera": "wide_to_close",
        "targets": ["circuit_network", "central_hub", "west_bus"],
        "spatial": ["foreign signal enters from west", "multiple routes change priority", "control consolidates at hub"],
        "text": ["replace", "highlight", "lock"],
        "phrases": ["FOREIGN SIGNAL", "ROUTES CHANGING", "CONTROL TRANSFERRED"],
        "sequence": [
            ["override", "path_override", "circuit_network", 0.7, 3.2, 1.0],
            ["reroute", "network_reroute", "central_hub", 2.7, 4.0, 1.0]
        ]
    },
    {
        "id": "05-cascade-failure", "duration": 13.0, "dominant": "cascade_failure", "supporting": [],
        "opening": "warning_state_open", "camera": "pull_back",
        "targets": ["circuit_network", "survivor_path"],
        "spatial": ["anomaly begins upper-left", "failures cross chamber", "one lower-right path survives"],
        "text": ["highlight", "erase", "reveal_hidden"],
        "phrases": ["ANOMALY DETECTED", "CASCADE FAILURE", "ONE PATH SURVIVES"],
        "sequence": [
            ["anomaly", "anomaly_seed", "circuit_network", 0.8, 2.0, 0.9],
            ["cascade", "cascade_failure", "survivor_path", 2.2, 6.0, 1.0]
        ]
    }
]


def build(root: Path, spec: dict) -> dict:
    fixture = copy.deepcopy(json.loads((root / "content/fixtures/mf011/01-simon-target-acquired.json").read_text()))
    source_duration = float(fixture["format"]["duration_seconds"])
    duration = float(spec["duration"])
    scale = duration / source_duration
    fixture["id"] = "mf012-" + spec["id"]
    fixture["format"]["duration_seconds"] = duration
    fixture["visual_strategy"]["preference"] = "godot_activity_vocabulary_v1"
    fixture.pop("creative", None)
    fixture["page_phrases"] = spec["phrases"]
    fixture["sfx"] = []
    fixture["music"] = None
    fixture["activity"] = {
        "version": 1, "demo": True, "dominant_activity": spec["dominant"],
        "supporting_activities": spec["supporting"], "opening_choreography": spec["opening"],
        "camera_choreography": spec["camera"], "targets": spec["targets"],
        "spatial_behavior": spec["spatial"], "text_behavior": spec["text"],
        "sequence": [
            {"id": item[0], "type": item[1], "target": item[2], "start": item[3],
             "duration": item[4], "intensity": item[5], "overlap": True}
            for item in spec["sequence"]
        ]
    }
    for event in fixture["generated_scene"]["events"]:
        event["time"] = round(float(event["time"]) * scale, 3)
    fixture["beats"] = [
        {"id":"circuits", "type":"intro", "text":"VISUAL ACTIVITY", "duration":1.0, "transition":"cut", "narration":None},
        {"id":"formation", "type":"reveal", "text":spec["phrases"][0], "duration":.5, "transition":"cut", "narration":None},
        {"id":"opening", "type":"reveal", "text":spec["phrases"][0], "duration":.5, "transition":"cut", "narration":None},
        {"id":"page_1", "type":"statement", "text":spec["phrases"][0], "duration":1.5, "transition":"cut", "narration":None},
        {"id":"page_2", "type":"emphasis", "text":spec["phrases"][1], "duration":1.0, "transition":"cut", "narration":None},
        {"id":"page_3", "type":"statement", "text":spec["phrases"][2], "duration":1.5, "transition":"cut", "narration":None},
        {"id":"result_hold", "type":"reveal", "text":spec["phrases"][2], "duration":.5, "transition":"cut", "narration":None},
        {"id":"dissolve", "type":"statement", "text":"ACTIVITY COMPLETE", "duration":1.5, "transition":"cut", "narration":None},
        {"id":"cta", "type":"outro", "text":"VISUAL ACTIVITY", "duration":round(duration-8.0,3), "transition":"cut", "narration":None}
    ]
    return fixture


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / "content/fixtures/mf012"
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for spec in DEMOS:
        path = output / f"{spec['id']}.json"
        path.write_text(json.dumps(build(root, spec), indent=2) + "\n")
        paths.append(str(path.relative_to(root)))
    print(json.dumps({"fixtures": paths, "count": len(paths), "result": "PASS"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
