#!/usr/bin/env python3
"""Materialize the three deterministic MF-008C fixture-only proof inputs."""

import copy
import json
from pathlib import Path


SPECS = [
    {
        "id": "mf008c-tracking-pursuit", "mechanism": "tracking",
        "events": ["target_search", "target_reacquire", "target_lock"],
        "profiles": ["pursuit", "tight_pursuit", "urgent", "warning_trace", "warning"],
        "timing": [5.4, 13.2, 1.4, 8.0],
        "phrases": ["TARGET TRACE DETECTED", "SIMON IS BEING HUNTED", "TARGET LOCK CONFIRMED"],
    },
    {
        "id": "mf008c-classification-mystery", "mechanism": "classification_link",
        "events": ["leo_resolve", "zeph_resolve", "bridge_attempt", "bridge_stable"],
        "profiles": ["mystery", "wide_investigation", "analytical", "classification", "cool_signal"],
        "timing": [6.2, 12.0, 2.0, 7.8],
        "phrases": ["LEO: A LIVING DATA BRIDGE", "ZEPH: AN EVOLVING AI KERNEL", "TWO IMPOSSIBLE TARGETS"],
    },
    {
        "id": "mf008c-biometric-revelation", "mechanism": "biometric_scan",
        "events": ["biometric_scan", "deep_scan", "hidden_region", "kill_switch_reveal"],
        "profiles": ["revelation", "calm_to_push", "stable_then_overload", "biometric", "revelation"],
        "timing": [6.5, 13.0, 1.8, 6.7],
        "phrases": ["BIOMETRIC RECORD: NORMAL", "HIDDEN REGION DETECTED", "KILL-SWITCH IN HIS BIOMETRICS"],
    },
]


def rounded(value):
    return round(value, 3)


def build_events(timing, mechanism_events):
    intro, investigation, hold, cta = timing
    phase = investigation / 3
    events = []

    def add(identifier, kind, when):
        events.append({"id": identifier, "type": kind, "time": rounded(when)})

    add("path_draw_start", "path_draw_start", 0)
    add("paths_drawn", "paths_drawn", intro * .13)
    add("energy_flow", "energy_flow", intro * .14)
    add("central_node_charge", "central_node_charge", intro * .27)
    add("overload", "overload", intro * .35)
    add("overload_pulse_1", "overload_pulse", intro * .39)
    add("overload_pulse_2", "overload_pulse", intro * .45)
    add("overload_peak", "overload_peak", intro * .47)
    add("spark_burst", "spark_burst", intro * .50)
    add("title_form", "title_form", intro * .515)
    add("projection_emission", "projection_emission", intro * .535)
    add("screen_initialize", "screen_initialize", intro * .535)
    add("camera_push", "camera_push", intro * .57)
    add("title_stabilized", "title_stabilized", intro * .64)
    phases = []
    for index in range(3):
        start = intro + index * phase
        phases.append({
            "query": start, "typing": start + phase * .13, "activity": start + phase * .28,
            "confirm": start + phase * .66, "lock": start + phase * .76,
            "hold": start + phase * .85, "reset": start + phase * .93,
            "refresh": start + phase * .96,
        })
        number = index + 1
        add(f"record_query_{number}", "record_query", phases[-1]["query"])
        add(f"record_typing_{number}", "record_typing", phases[-1]["typing"])
        add(f"record_activity_{number}", "record_activity", phases[-1]["activity"])
        add(f"record_confirm_{number}", "record_confirm", phases[-1]["confirm"])
        add(f"record_lock_{number}", "record_lock", phases[-1]["lock"])
        add(f"record_hold_{number}", "record_hold", phases[-1]["hold"])
        if index < 2:
            add(f"record_reset_{number}", "record_reset", phases[-1]["reset"])
            add(f"screen_refresh_{number}", "screen_refresh", phases[-1]["refresh"])
    if len(mechanism_events) == 3:
        custom_times = [phases[0]["activity"], phases[1]["activity"], phases[2]["lock"]]
    else:
        custom_times = [phases[0]["activity"], phases[1]["activity"], phases[2]["activity"], phases[2]["lock"]]
    for identifier, when in zip(mechanism_events, custom_times):
        add(identifier, identifier, when)
    investigation_end = intro + investigation
    collapse = investigation_end + hold
    add("final_record_settle", "settle", investigation_end)
    add("screen_collapse", "screen_collapse", collapse)
    add("data_dissolve", "data_dissolve", collapse)
    add("energy_reclaimed", "energy_reclaimed", collapse + min(.8, cta * .12))
    add("return_energy", "return_energy", collapse + cta * .16)
    add("camera_pull_back", "camera_pull_back", collapse + cta * .22)
    add("cta_energy", "cta_energy", collapse + cta * .34)
    add("cta_typing", "cta_typing", collapse + cta * .43)
    add("cta_lock", "cta_lock", collapse + cta * .55)
    add("website_reveal", "website_reveal", collapse + cta * .62)
    add("cta_reveal", "cta_reveal", collapse + cta * .62)
    add("cta_settle", "settle", collapse + cta * .70)
    return sorted(events, key=lambda item: (item["time"], item["id"]))


def build_fixture(base, spec):
    fixture = copy.deepcopy(base)
    fixture["id"] = spec["id"]
    fixture["page_phrases"] = spec["phrases"]
    palette, camera, node, projection, cta = spec["profiles"]
    intro, investigation, hold, cta_seconds = spec["timing"]
    fixture["creative"] = {
        "mechanism": spec["mechanism"], "events": spec["events"],
        "timing": {"intro_seconds": intro, "investigation_seconds": investigation,
                   "result_hold_seconds": hold, "cta_seconds": cta_seconds},
        "palette_profile": palette, "camera_profile": camera, "node_profile": node,
        "projection_profile": projection, "cta_profile": cta, "audio_cue": "baseline_full",
    }
    fixture["generated_scene"]["events"] = build_events(spec["timing"], spec["events"])
    phase = investigation / 3
    fixture["beats"] = [
        {"id": "circuits", "type": "intro", "text": "UNKNOWN PROCESS", "duration": 2.3, "transition": "cut", "narration": None},
        {"id": "formation", "type": "reveal", "text": "UNKNOWN PROCESS", "duration": 2.1, "transition": "cut", "narration": None},
        {"id": "opening", "type": "reveal", "text": "UNKNOWN PROCESS", "duration": rounded(intro - 4.4), "transition": "cut", "narration": None},
        *[{"id": f"page_{index+1}", "type": "statement" if index != 1 else "emphasis", "text": phrase,
           "duration": rounded(phase), "transition": "cut", "narration": None} for index, phrase in enumerate(spec["phrases"])],
        {"id": "result_hold", "type": "reveal", "text": spec["phrases"][-1], "duration": hold, "transition": "cut", "narration": None},
        {"id": "dissolve", "type": "statement", "text": "CONTINUE THE ADVENTURE", "duration": 2.0, "transition": "cut", "narration": None},
        {"id": "cta", "type": "outro", "text": "CONTINUE THE ADVENTURE", "duration": rounded(cta_seconds - 2.0), "transition": "cut", "narration": None},
    ]
    # Eliminate accumulated decimal drift while retaining bounded group timing.
    fixture["beats"][-1]["duration"] = rounded(28.0 - sum(beat["duration"] for beat in fixture["beats"][:-1]))
    return fixture


def main():
    root = Path(__file__).resolve().parents[1]
    base = json.loads((root / "content/fixtures/mf006r9-unknown-process.json").read_text())
    output = root / "content/fixtures/mf008c"
    output.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        path = output / f"{spec['id']}.json"
        path.write_text(json.dumps(build_fixture(base, spec), indent=2) + "\n")
        print(path)


if __name__ == "__main__":
    main()
