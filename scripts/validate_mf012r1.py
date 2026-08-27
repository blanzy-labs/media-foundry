#!/usr/bin/env python3
"""Independent fail-closed validation for MF-012R1 configs and A/B outputs."""

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

from mf012r1_contract import ALLOWED_CHANNELS, ALLOWED_COLORS, PROTECTED_ZONES, RING_BEHAVIORS, TILE_BEHAVIORS, schedule_signature


SUBJECT_TERMS = ["simon", "leo", "zeph", "syndicate", "kill-switch", "kill_switch"]


def load(path) -> dict:
    return json.loads(Path(path).read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def without_micro(value: dict) -> dict:
    clone = json.loads(json.dumps(value))
    clone.pop("micro_variation", None)
    return clone


def overlaps(left: dict, right: dict) -> bool:
    return left["x"] < right["x"] + right["width"] and left["x"] + left["width"] > right["x"] \
        and left["y"] < right["y"] + right["height"] and left["y"] + left["height"] > right["y"]


def point_bounds(point: dict, radius: float) -> dict:
    return {"x": point["x"] - radius, "y": point["y"] - radius, "width": radius * 2, "height": radius * 2}


def event_active(event: dict, time_value: float) -> bool:
    return event["start"] <= time_value < event["start"] + event["duration"]


def validate_config(root: Path, fixture: dict, source: dict) -> dict:
    micro = fixture.get("micro_variation", {})
    errors, checks = [], {}

    def check(name, passed, code):
        checks[name] = "PASS" if passed else "FAIL"
        if not passed:
            errors.append(code)

    required = {"version", "enabled", "generator", "seed", "channels", "motion_budget", "indicator_dots",
                "background_tiles", "floating_ring_dot", "audio_policy", "visual_priority", "schedule_signature"}
    check("schema", isinstance(micro, dict) and set(micro) == required and micro.get("version") == 1
          and micro.get("enabled") is True and micro.get("visual_priority") == 5, "MICRO_VARIATION_SCHEMA_INVALID")
    check("source_preservation", without_micro(fixture) == source, "SOURCE_CONFIG_CHANGED")
    channels = micro.get("channels", [])
    check("channel_budget", isinstance(channels, list) and 1 <= len(channels) <= 3 and len(channels) == len(set(channels)), "MICRO_VARIATION_BUDGET_EXCEEDED")
    check("known_channels", bool(channels) and set(channels) <= set(ALLOWED_CHANNELS), "UNKNOWN_MICRO_VARIATION_TYPE")
    seed = micro.get("seed")
    check("seed", isinstance(seed, int) and seed > 0 and micro.get("generator") == "mf012r1_lcg_v1", "MICRO_VARIATION_SEED_REQUIRED")
    check("schedule_signature", bool(micro) and micro.get("schedule_signature") == schedule_signature(micro), "MICRO_VARIATION_SCHEDULE_NOT_REPRODUCIBLE")
    check("audio_policy", micro.get("audio_policy") == {"music": True, "sfx": False, "ambient": False}, "MICRO_VARIATION_AUDIO_POLICY_INVALID")

    indicator = micro.get("indicator_dots", {})
    indicator_mode = indicator.get("mode")
    check("indicator_mode", indicator_mode in ["stable_indicators", "reactive_colored_indicators"], "UNKNOWN_MICRO_VARIATION_TYPE")
    colors = indicator.get("colors", [])
    check("indicator_colors", len(colors) == 4 and set(colors) <= set(ALLOWED_COLORS), "UNSUPPORTED_INDICATOR_COLOR")
    flashes = indicator.get("flashes", [])
    valid_flashes = all(isinstance(event.get("dot"), int) and 0 <= event["dot"] < 4 and event.get("duration", 0) >= .1
                        and 0 < event.get("intensity", 0) <= .3 for event in flashes)
    check("indicator_flashes", valid_flashes and (not flashes if indicator_mode == "stable_indicators" else True), "MICRO_VARIATION_INDICATOR_CONFIG_INVALID")

    tiles = micro.get("background_tiles", {})
    indices = tiles.get("active_indices", [])
    density = len(indices) / 54 if indices else 0
    check("tile_density", len(indices) == len(set(indices)) and 3 <= len(indices) <= 8 and .05 <= density <= .15, "MICRO_VARIATION_TILE_DENSITY_EXCEEDED")
    safe_tiles = True
    for index in indices:
        row, column = divmod(index, 6)
        tile = {"x": -315 + column * 108 + (10 if row % 2 else 0), "y": -515 + row * 118, "width": 92, "height": 102}
        if index < 0 or index > 53 or any(overlaps(tile, zone) for zone in PROTECTED_ZONES):
            safe_tiles = False
    check("tile_text_exclusion", safe_tiles, "MICRO_VARIATION_TILE_TEXT_CONTRAST_VIOLATION")
    tile_events = tiles.get("events", [])
    valid_tile_events = all(event.get("tile_index") in indices and event.get("behavior") in TILE_BEHAVIORS
                            and event.get("color") in ALLOWED_COLORS and .1 <= event.get("duration", 0)
                            and 0 < event.get("intensity", 0) <= .12 for event in tile_events)
    check("tile_events", bool(tile_events) and valid_tile_events and tiles.get("peak_alpha", 1) <= .12, "MICRO_VARIATION_TILE_CONFIG_INVALID")

    runtime = float(fixture.get("format", {}).get("duration_seconds", 0))
    ring = micro.get("floating_ring_dot")
    ring_required = "floating_ring_dot" in channels
    check("ring_channel", (ring_required and isinstance(ring, dict)) or (not ring_required and ring is None), "MICRO_VARIATION_RING_CONFIG_INVALID")
    ring_safe, ring_speed = True, 0.0
    if isinstance(ring, dict):
        path, radius, zone = ring.get("path", []), float(ring.get("radius", 0)), ring.get("safe_zone", {})
        ring_safe = ring.get("behavior") in RING_BEHAVIORS and 4 <= radius <= 14 and len(path) >= 2
        for point in path:
            bounds = point_bounds(point, radius)
            inside = bounds["x"] >= zone.get("x", 0) and bounds["y"] >= zone.get("y", 0) \
                and bounds["x"] + bounds["width"] <= zone.get("x", 0) + zone.get("width", 0) \
                and bounds["y"] + bounds["height"] <= zone.get("y", 0) + zone.get("height", 0)
            ring_safe = ring_safe and inside and not any(overlaps(bounds, protected) for protected in ring.get("protected_zones", []))
        length = sum(math.dist((left["x"], left["y"]), (right["x"], right["y"])) for left, right in zip(path, path[1:]))
        span = ring.get("active_end", 0) - ring.get("active_start", 0)
        ring_speed = length / span if span > 0 else float("inf")
        ring_safe = ring_safe and ring.get("active_start", -1) >= 0 and ring.get("active_end", runtime + 1) <= runtime \
            and ring_speed <= ring.get("maximum_speed", 0) <= 18
    check("ring_safe_zone", ring_safe, "MICRO_VARIATION_SAFE_ZONE_VIOLATION")

    maximum_minor = 0
    for frame in range(round(runtime * 30)):
        time_value = frame / 30
        indicator_count = 2 if indicator_mode == "stable_indicators" else sum(event_active(event, time_value) for event in flashes)
        tile_count = sum(event_active(event, time_value) for event in tile_events)
        maximum_minor = max(maximum_minor, indicator_count + tile_count)
    major = 1 if ring_required else 0
    check("motion_budget", major <= 1 and maximum_minor <= 3, "MICRO_VARIATION_BUDGET_EXCEEDED")
    check("event_timing", all(0 <= event.get("start", -1) and event.get("start", 0) + event.get("duration", 0) <= runtime
                              for event in flashes + tile_events), "MICRO_VARIATION_TIMING_INVALID")
    return {
        "slice": "MF-012R1", "type": "micro_variation_config", "fixture": fixture.get("id"),
        "seed": seed, "channels": channels, "channel_count": len(channels),
        "active_tile_count": len(indices), "active_tile_density": round(density, 6),
        "maximum_minor_simultaneous": maximum_minor, "major_motion_elements": major,
        "ring_speed": round(ring_speed, 3), "checks": checks, "errors": errors,
        "result": "PASS" if not errors else "FAIL",
    }


def probe(path: Path) -> dict:
    process = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    data = json.loads(process.stdout) if process.returncode == 0 else {}
    video = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
    audio = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"), {})
    return {"width": video.get("width"), "height": video.get("height"), "frames": int(video.get("nb_read_frames", 0)),
            "duration": float(data.get("format", {}).get("duration", 0)), "video_codec": video.get("codec_name"),
            "audio_codec": audio.get("codec_name"), "sample_rate": int(audio.get("sample_rate", 0)), "channels": audio.get("channels")}


def stream_hash(path: Path, decoded: bool) -> str:
    command = ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0"]
    command += ["-f", "hash", "-hash", "sha256", "-"] if decoded else ["-c", "copy", "-f", "data", "-"]
    process = subprocess.run(command, capture_output=True)
    if process.returncode:
        return ""
    if decoded:
        return process.stdout.decode().strip().split("=")[-1].lower()
    return hashlib.sha256(process.stdout).hexdigest()


def validate_output(args) -> dict:
    root = Path(args.project_root).resolve()
    fixture, source_fixture = load(args.fixture), load(args.source_fixture)
    config = validate_config(root, fixture, source_fixture)
    layout, media = load(args.layout), load(args.media)
    source_video, refined_video = Path(args.source_video), Path(args.refined_video)
    source_probe, refined_probe = probe(source_video), probe(refined_video)
    source_job = Path(args.source_job_dir)
    source_selection = load(source_job / "validation/music-selection.json")
    source_mix = load(source_job / "validation/mix.json")
    source_sfx = load(source_job / "validation/sfx.json")
    source_narration = load(source_job / "validation/narration.json")
    report = layout.get("generated_scene", {}).get("micro_variation", {})
    text_fields = ["page_phrases", "beats", "cta", "subject"]
    checks = {
        "config": config["result"] == "PASS",
        "runtime": source_probe["duration"] == refined_probe["duration"] == float(fixture["format"]["duration_seconds"]),
        "frame_count": source_probe["frames"] == refined_probe["frames"] == round(source_probe["duration"] * 30),
        "media_shape": refined_probe["width"] == 1080 and refined_probe["height"] == 1920,
        "audio_stream_format": source_probe["audio_codec"] == refined_probe["audio_codec"] == "aac"
            and source_probe["sample_rate"] == refined_probe["sample_rate"] == 48000 and source_probe["channels"] == refined_probe["channels"] == 1,
        "audio_packet_identity": stream_hash(source_video, False) == stream_hash(refined_video, False),
        "audio_decode_identity": stream_hash(source_video, True) == stream_hash(refined_video, True),
        "text_equivalence": all(fixture.get(key) == source_fixture.get(key) for key in text_fields),
        "music_config_equivalence": fixture.get("music") == source_fixture.get("music"),
        "cue_identity": source_selection.get("track_id") == fixture["music"]["provenance"]["track_id"]
            and source_selection.get("region_id") == fixture["music"]["provenance"]["region_id"]
            and source_selection.get("actual_start") == fixture["music"]["selected_offset"]
            and source_selection.get("actual_end") - source_selection.get("actual_start") == source_probe["duration"]
            and source_selection.get("fade_in") == fixture["music"]["fade_in"] and source_selection.get("fade_out") == fixture["music"]["fade_out"],
        "gain_identity": source_mix.get("music", {}).get("gain_db") == fixture["music"]["gain_db"],
        "music_only": source_sfx.get("event_count") == 0 and source_sfx.get("ambient_machine_audio") is False
            and source_narration.get("segments") == [] and source_mix.get("segments") == [],
        "safe_zone": report.get("safe_zone_result") == "PASS" and config["checks"].get("ring_safe_zone") == "PASS",
        "motion_budget": report.get("motion_budget", {}).get("major_motion_elements", 2) <= 1
            and report.get("motion_budget", {}).get("maximum_minor_simultaneous", 4) <= 3,
        "deterministic_seed": report.get("deterministic") is True and report.get("seed") == fixture["micro_variation"]["seed"],
        "no_noisy_geometry": report.get("large_crossing_lines") == 0 and report.get("new_central_web_geometry") == 0,
        "subject_agnostic": report.get("subject_specific_branches") == 0,
        "media_validation": media.get("result") == "PASS",
    }
    errors = [name.upper() + "_FAILED" for name, passed in checks.items() if not passed]
    return {
        "slice": "MF-012R1", "type": "ab_output_validation", "source_video": str(source_video), "refined_video": str(refined_video),
        "source_sha256": sha256(source_video), "refined_sha256": sha256(refined_video),
        "source_probe": source_probe, "refined_probe": refined_probe,
        "audio": {"source_packet_sha256": stream_hash(source_video, False), "refined_packet_sha256": stream_hash(refined_video, False),
                  "source_decoded_sha256": stream_hash(source_video, True), "refined_decoded_sha256": stream_hash(refined_video, True)},
        "music_selection": source_selection, "checks": {name: "PASS" if passed else "FAIL" for name, passed in checks.items()},
        "errors": errors, "result": "PASS" if not errors else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["config", "output"])
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--source-fixture", required=True)
    parser.add_argument("--source-video")
    parser.add_argument("--refined-video")
    parser.add_argument("--source-job-dir")
    parser.add_argument("--layout")
    parser.add_argument("--media")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = validate_config(Path(args.project_root).resolve(), load(args.fixture), load(args.source_fixture)) if args.mode == "config" else validate_output(args)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        result = {"slice": "MF-012R1", "type": args.mode, "errors": [{"code": "VALIDATOR_EXCEPTION", "detail": str(error)}], "result": "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
