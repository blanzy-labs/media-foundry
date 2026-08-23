#!/usr/bin/env python3
"""Independently validate instantiated MF-003 slot geometry and prepared input evidence."""

import argparse
import json
import sys
from pathlib import Path


EPSILON = 0.05


def rect(value):
    return tuple(float(value[key]) for key in ("x", "y", "width", "height"))


def contains(outer, inner):
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return ix >= ox - EPSILON and iy >= oy - EPSILON and ix + iw <= ox + ow + EPSILON and iy + ih <= oy + oh + EPSILON


def same(first, second):
    return all(abs(a - b) <= EPSILON for a, b in zip(first, second))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--grammar", required=True)
    parser.add_argument("--input-report", required=True)
    parser.add_argument("--renderer-report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    errors = []
    try:
        fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        grammar = json.loads(Path(args.grammar).read_text(encoding="utf-8"))
        prepared = json.loads(Path(args.input_report).read_text(encoding="utf-8"))
        rendered = json.loads(Path(args.renderer_report).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fixture, grammar, prepared, rendered = {}, {}, {}, {}
        errors.append(f"MEDIA_RENDER_FAILED: unreadable validation input: {error}")
    media = fixture.get("media", {})
    state = rendered.get("media", {})
    if prepared.get("result") != "PASS":
        errors.append("MEDIA_INPUT_FAILED: preparation report did not pass")
    if rendered.get("result") != "PASS" or state.get("status") != "PASS":
        errors.append("MEDIA_RENDER_FAILED: shared renderer did not instantiate media")
    for key in ("type", "fit", "anchor", "motion"):
        if state.get(key) != media.get(key, "none" if key == "motion" else None):
            errors.append(f"MEDIA_RENDER_FAILED: renderer {key} differs from fixture")
    try:
        safe = rect(grammar["media_slot"]["safe_rect"])
        reported_safe = rect(state["safe_rect"])
    except (KeyError, TypeError, ValueError):
        safe = reported_safe = ()
        errors.append("MEDIA_BOUNDS_FAILED: missing media safe rectangle")
    else:
        if not same(safe, reported_safe):
            errors.append("MEDIA_BOUNDS_FAILED: renderer safe rectangle differs from grammar")
    width = float(state.get("width", 0))
    height = float(state.get("height", 0))
    if width <= 0 or height <= 0:
        errors.append("MEDIA_RENDER_FAILED: invalid instantiated dimensions")
    samples = state.get("geometry_samples", [])
    if len(samples) != 3:
        errors.append("MEDIA_BOUNDS_FAILED: expected start/mid/end geometry samples")
    for sample in samples:
        try:
            destination = rect(sample["destination_rect"])
            source = rect(sample["source_rect"])
        except (KeyError, TypeError, ValueError):
            errors.append("MEDIA_BOUNDS_FAILED: malformed geometry sample")
            continue
        if not contains(safe, destination):
            errors.append(f"MEDIA_BOUNDS_FAILED: destination escapes safe area at progress={sample.get('progress')}")
        if not contains((0, 0, width, height), source):
            errors.append(f"MEDIA_BOUNDS_FAILED: crop escapes source at progress={sample.get('progress')}")
        if media.get("fit") == "cover" and not same(destination, safe):
            errors.append(f"MEDIA_BOUNDS_FAILED: cover does not fill slot at progress={sample.get('progress')}")
        if media.get("fit") == "contain" and not same(source, (0, 0, width, height)):
            errors.append(f"MEDIA_BOUNDS_FAILED: contain crops source at progress={sample.get('progress')}")
    timeline = state.get("timeline", {})
    if timeline.get("enter_seconds") != grammar.get("motion", {}).get("intro_end_seconds") or timeline.get("exit_seconds") != grammar.get("motion", {}).get("outro_start_seconds"):
        errors.append("MEDIA_TIMELINE_FAILED: media lifecycle differs from shared motion grammar")
    if media.get("type") == "video":
        expected = round(float(media.get("duration_seconds", 0)) * int(grammar.get("media_slot", {}).get("video_frame_rate", 0)))
        if state.get("normalized_frames") != expected or prepared.get("normalization", {}).get("frame_count") != expected:
            errors.append("MEDIA_TIMELINE_FAILED: normalized frame count does not satisfy clip duration")
    checks = {
        "input": "PASS" if not any("INPUT" in item for item in errors) else "FAIL",
        "slot_instantiated": "PASS" if not any("RENDER" in item for item in errors) else "FAIL",
        "bounds": "PASS" if not any("BOUNDS" in item for item in errors) else "FAIL",
        "aspect_mode": "PASS" if not any("BOUNDS" in item for item in errors) else "FAIL",
        "timeline": "PASS" if not any("TIMELINE" in item for item in errors) else "FAIL",
        "visible_during_expected_timeline": "PASS" if not errors else "FAIL",
    }
    result = {"slice": "MF-003", "fixture": fixture.get("id", "unknown"), "checks": checks, "errors": errors, "result": "PASS" if not errors else "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
