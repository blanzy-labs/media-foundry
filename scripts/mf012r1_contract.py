#!/usr/bin/env python3
"""Shared deterministic micro-variation schedule construction for MF-012R1."""

import hashlib
import json


ALLOWED_COLORS = ["amber", "purple", "green", "blue"]
ALLOWED_CHANNELS = ["indicator_dots", "background_tiles", "floating_ring_dot"]
TILE_BEHAVIORS = ["tile_wake", "tile_color_shift", "tile_bright_pulse", "tile_dim", "tile_recover"]
RING_BEHAVIORS = ["slow_drift", "slow_hover", "gentle_arc", "pause_and_drift"]
PROTECTED_ZONES = [
    {"id": "main_projection_and_story_text", "x": -216, "y": -326, "width": 432, "height": 378},
    {"id": "cta_url_author", "x": -226, "y": -150, "width": 452, "height": 260},
    {"id": "emitter_and_indicators", "x": -125, "y": 190, "width": 250, "height": 75},
]


class Lcg:
    def __init__(self, seed: int):
        self.state = seed & 0x7FFFFFFF

    def next(self, bound: int) -> int:
        self.state = (1103515245 * self.state + 12345) & 0x7FFFFFFF
        return self.state % bound


def schedule_signature(config: dict) -> str:
    value = {key: config.get(key) for key in ["seed", "channels", "indicator_dots", "background_tiles", "floating_ring_dot"]}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_micro_variation(variant: str, seed: int, runtime: float) -> dict:
    rng = Lcg(seed)
    if variant == "restrained":
        active_tiles = [1, 42, 47]
        indicator = {"mode": "stable_indicators", "colors": ["amber"] * 4, "flashes": []}
        channels = ["indicator_dots", "background_tiles"]
        ring = None
        event_count = 6
        tile_intensity = 0.075
    elif variant == "reactive":
        active_tiles = [4, 11, 36, 41, 48]
        colors = ["amber", "purple", "green", "blue"]
        flashes, time_value, previous_dot = [], 1.4, -1
        while time_value < runtime - 1.2:
            time_value += 2.4 + rng.next(27) / 10
            if time_value >= runtime - 1.0:
                break
            dot = rng.next(4)
            if dot == previous_dot:
                dot = (dot + 1) % 4
            span = round(0.34 + rng.next(13) / 100, 2)
            flashes.append({"dot": dot, "start": round(time_value, 2), "duration": span, "intensity": 0.26})
            previous_dot = dot
        indicator = {"mode": "reactive_colored_indicators", "colors": colors, "flashes": flashes}
        channels = ["indicator_dots", "background_tiles", "floating_ring_dot"]
        ring = {
            "enabled": True,
            "behavior": "slow_hover",
            "color": "blue",
            "radius": 10.0,
            "active_start": 1.0,
            "active_end": round(runtime - 5.2, 2),
            "maximum_speed": 14.0,
            "safe_zone": {"x": 220, "y": -465, "width": 90, "height": 115},
            "protected_zones": PROTECTED_ZONES,
            "path": [{"x": 235, "y": -430}, {"x": 275, "y": -397}, {"x": 242, "y": -365}],
        }
        event_count = 9
        tile_intensity = 0.105
    else:
        raise ValueError(f"unknown variant: {variant}")

    events, time_value = [], 0.6
    for index in range(event_count):
        time_value += 2.6 + rng.next(22) / 10
        if time_value >= runtime - 1.0:
            break
        duration = round(1.45 + rng.next(9) / 10, 2)
        if time_value + duration >= runtime:
            break
        events.append({
            "tile_index": active_tiles[rng.next(len(active_tiles))],
            "start": round(time_value, 2),
            "duration": duration,
            "behavior": TILE_BEHAVIORS[rng.next(len(TILE_BEHAVIORS))],
            "color": ALLOWED_COLORS[rng.next(len(ALLOWED_COLORS))],
            "intensity": tile_intensity,
        })
    config = {
        "version": 1,
        "enabled": True,
        "generator": "mf012r1_lcg_v1",
        "seed": seed,
        "channels": channels,
        "motion_budget": {"major_motion_elements": 1 if ring else 0, "minor_simultaneous_accents": 3},
        "indicator_dots": indicator,
        "background_tiles": {
            "mode": "sparse_color_shifts",
            "visible_tile_count": 54,
            "active_indices": active_tiles,
            "active_density": round(len(active_tiles) / 54, 6),
            "peak_alpha": tile_intensity,
            "events": events,
        },
        "floating_ring_dot": ring,
        "audio_policy": {"music": True, "sfx": False, "ambient": False},
        "visual_priority": 5,
    }
    config["schedule_signature"] = schedule_signature(config)
    return config
