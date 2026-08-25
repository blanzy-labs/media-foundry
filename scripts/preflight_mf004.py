#!/usr/bin/env python3
"""Fail-closed MF-004 sequential beat preflight and timeline materializer."""

import argparse
import json
import time
from pathlib import Path


TYPES = {"intro", "statement", "media", "emphasis", "reveal", "outro"}
TRANSITIONS = {"cut", "scrappy_pop", "slide"}


def fail(message, code="TIMELINE_INVALID"):
    raise ValueError(f"{code}: {message}")


def media_assets(fixture):
    media = fixture.get("media")
    if media is None:
        return {}
    if not isinstance(media, dict):
        fail("media must be an object")
    if "type" in media:
        return {"default": media}
    if not media or not all(isinstance(value, dict) and "type" in value for value in media.values()):
        fail("named media must map identifiers to media objects")
    return media


def build(fixture, grammar, project_root):
    started = time.perf_counter()
    beats = fixture.get("beats")
    if beats is None:
        return {"slice": "MF-004", "fixture": fixture.get("id"), "mode": "legacy", "result": "PASS", "duration": fixture["format"]["duration_seconds"], "beats": [], "preflight_seconds": time.perf_counter() - started}
    if not isinstance(beats, list) or not beats:
        fail("beats must be a non-empty array", "MALFORMED_TIMELINE")
    duration = fixture.get("format", {}).get("duration_seconds")
    limits = grammar.get("beats", {}).get("duration_seconds", {"minimum": 10, "maximum": 20})
    extended = fixture.get("visual_strategy", {}).get("preference") in {"godot_extended_data_window_refinement", "godot_live_investigation_refinement", "godot_final_polish_refinement", "godot_lower_right_polish_refinement", "godot_integrated_lower_right_refinement", "godot_indicator_pulse_refinement"}
    maximum = 30 if extended else limits["maximum"]
    if not isinstance(duration, (int, float)) or not limits["minimum"] <= duration <= maximum:
        fail(f"configured duration must be between 10 and {maximum:g} seconds", "DURATION_INVALID")
    assets = media_assets(fixture)
    cues = set(grammar.get("beats", {}).get("audio_cues", []))
    timeline, cursor, seen, referenced_media = [], 0.0, set(), set()
    for index, source in enumerate(beats):
        if not isinstance(source, dict):
            fail(f"beat {index} must be an object", "MALFORMED_TIMELINE")
        if "start" in source or "end" in source:
            fail("explicit timing is unsupported; overlaps and gaps are impossible in sequential mode", "EXPLICIT_TIMING_UNSUPPORTED")
        kind = source.get("type")
        if kind not in TYPES:
            fail(f"unsupported beat type {kind!r}", "UNKNOWN_BEAT_TYPE")
        beat_duration = source.get("duration")
        if not isinstance(beat_duration, (int, float)) or isinstance(beat_duration, bool) or beat_duration <= 0:
            fail(f"beat {index} duration must be positive", "BEAT_DURATION_INVALID")
        transition = source.get("transition", "cut")
        if transition not in TRANSITIONS:
            fail(f"unsupported transition {transition!r}", "TRANSITION_INVALID")
        beat_id = source.get("id", f"{kind}-{index + 1:02d}")
        if not isinstance(beat_id, str) or not beat_id or beat_id in seen:
            fail(f"beat id {beat_id!r} is empty or duplicated", "BEAT_ID_INVALID")
        seen.add(beat_id)
        text = source.get("text", "")
        if kind in {"intro", "statement", "emphasis", "reveal", "outro"} and (not isinstance(text, str) or not text.strip()):
            fail(f"text beat {beat_id} requires text", "TEXT_REQUIRED")
        if kind == "statement" and beat_duration < 1.5:
            fail(f"statement {beat_id} requires at least 1.5 seconds", "TEXT_DENSITY_INVALID")
        if kind == "statement" and len(text) > int(beat_duration * 32):
            fail(f"statement {beat_id} has too much text for its duration", "TEXT_DENSITY_INVALID")
        if kind == "emphasis" and (beat_duration < 1.0 or len(text) > 45):
            fail(f"emphasis {beat_id} must be short and at least 1 second", "TEXT_DENSITY_INVALID")
        if kind in {"intro", "outro"} and beat_duration < 1.0:
            fail(f"{kind} {beat_id} requires at least 1 second", "TEXT_DENSITY_INVALID")
        if kind == "media":
            media_ref = source.get("media_ref", "default")
            if beat_duration < 1.5:
                fail(f"media {beat_id} requires at least 1.5 seconds", "MEDIA_DURATION_INVALID")
            if media_ref not in assets:
                fail(f"media {beat_id} references unknown asset {media_ref!r}", "MEDIA_REFERENCE_INVALID")
            referenced_media.add(media_ref)
            media_source = assets[media_ref].get("source", "")
            resolved = Path(media_source) if Path(media_source).is_absolute() else project_root / media_source
            if not media_source or not resolved.is_file():
                fail(f"media {beat_id} source does not exist", "MEDIA_REFERENCE_INVALID")
        cue = source.get("audio_cue")
        if cue is not None and cue not in cues:
            fail(f"beat {beat_id} references unknown audio cue {cue!r}", "AUDIO_CUE_INVALID")
        item = dict(source, id=beat_id, index=index, start=round(cursor, 6), end=round(cursor + beat_duration, 6), transition=transition)
        timeline.append(item)
        cursor += beat_duration
    if len(referenced_media) > 1:
        fail("one referenced media asset per timeline is supported in MF-004", "MULTIPLE_MEDIA_UNSUPPORTED")
    if abs(cursor - duration) > 1e-6:
        fail(f"beat duration total {cursor:g}s does not equal configured duration {duration:g}s", "TOTAL_DURATION_INVALID")
    if timeline[0]["type"] != "intro" or timeline[-1]["type"] != "outro":
        fail("timeline must begin with intro and end with outro", "BOUNDARY_BEAT_INVALID")
    return {"slice": "MF-004", "fixture": fixture.get("id"), "mode": "beats", "result": "PASS", "duration": duration, "number_of_beats": len(timeline), "sequential_no_gaps": True, "beats": timeline, "preflight_seconds": round(time.perf_counter() - started, 6)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--grammar", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        fixture = json.loads(Path(args.fixture).read_text())
        grammar = json.loads(Path(args.grammar).read_text())
        result = build(fixture, grammar, Path(args.project_root))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        result = {"slice": "MF-004", "result": "FAIL", "error": str(error)}
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 1
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
