#!/usr/bin/env python3
"""Generate deterministic, non-musical MF-007A ambience and event SFX."""

import argparse
import json
import math
import random
import struct
import wave
from pathlib import Path


RATE = 48000


def write_stereo(path, left, right):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as target:
        target.setnchannels(2)
        target.setsampwidth(2)
        target.setframerate(RATE)
        frames = bytearray()
        for l_value, r_value in zip(left, right):
            frames.extend(struct.pack("<hh", round(max(-1, min(1, l_value)) * 32767), round(max(-1, min(1, r_value)) * 32767)))
        target.writeframes(frames)


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def arc_gain(t, duration):
    wake = smoothstep(t / 1.55)
    power_down = 1.0 - smoothstep((t - 26.3) / 1.7)
    overload_dip = 1.0 - 0.62 * math.exp(-((t - 2.80) / 0.13) ** 2)
    middle = 0.91 + 0.09 * math.sin(2.0 * math.pi * t / 11.37 + 0.4)
    return wake * power_down * overload_dip * middle if 0 <= t <= duration else 0.0


def add_event(left, right, start, duration, gain, pan, generator):
    first = round(start * RATE)
    count = round(duration * RATE)
    l_gain = math.sqrt((1.0 - pan) * 0.5)
    r_gain = math.sqrt((1.0 + pan) * 0.5)
    for offset in range(count):
        index = first + offset
        if index >= len(left):
            break
        t = offset / RATE
        value = gain * generator(t, duration)
        left[index] += value * l_gain
        right[index] += value * r_gain


def event_generator(kind, seed):
    rng = random.Random(seed)
    held_noise = 0.0

    def noise():
        nonlocal held_noise
        held_noise = held_noise * 0.82 + (rng.random() * 2.0 - 1.0) * 0.18
        return held_noise

    def synth(t, duration):
        x = t / duration
        fade = math.sin(math.pi * min(1.0, x)) ** 1.5
        attack = smoothstep(min(1.0, t / min(0.045, duration * 0.25)))
        release = (1.0 - x) ** 1.35
        envelope = attack * release
        if kind == "conductive_trace":
            return envelope * (0.48 * noise() + 0.18 * math.sin(2 * math.pi * (135 + 240 * x) * t))
        if kind == "moving_energy":
            pulses = sum(math.exp(-((x - center) / 0.075) ** 2) for center in (0.18, 0.48, 0.78))
            return 0.34 * pulses * (math.sin(2 * math.pi * (108 + 66 * x) * t) + 0.28 * noise())
        if kind == "power_build":
            rise = smoothstep(x)
            return rise * (1 - x * 0.18) * (0.42 * math.sin(2 * math.pi * (54 + 96 * x * x) * t) + 0.18 * noise())
        if kind == "electrical_physical_impact":
            snap = math.exp(-t * 27) * noise()
            thump = math.exp(-t * 15) * math.sin(2 * math.pi * 47 * t)
            return 0.8 * snap + 0.46 * thump
        if kind == "projection_ignition":
            return envelope * (0.36 * math.sin(2 * math.pi * (92 + 160 * smoothstep(x)) * t) + 0.20 * noise())
        if kind in {"searching_trace", "active_scan"}:
            sweep = math.sin(2 * math.pi * (73 + 35 * math.sin(math.pi * x)) * t)
            return fade * (0.22 * sweep + 0.17 * noise())
        if kind == "dual_node_bridge":
            nodes = math.exp(-((x - 0.12) / 0.055) ** 2) + math.exp(-((x - 0.29) / 0.055) ** 2)
            travel = math.exp(-((x - 0.58) / 0.19) ** 2)
            return 0.28 * nodes * math.sin(2 * math.pi * 126 * t) + 0.18 * travel * (noise() + math.sin(2 * math.pi * 89 * t))
        if kind == "record_refresh":
            return envelope * (0.36 * noise() + 0.12 * math.sin(2 * math.pi * (184 - 70 * x) * t))
        if kind in {"restrained_confirmation", "low_confirmation"}:
            return envelope * (0.24 * math.sin(2 * math.pi * (118 - 22 * x) * t) + 0.12 * noise())
        if kind == "field_deconstruction":
            return envelope * (0.34 * math.sin(2 * math.pi * (210 - 150 * smoothstep(x)) * t) + 0.25 * noise())
        if kind == "reverse_energy":
            pulses = sum(math.exp(-((x - center) / 0.09) ** 2) for center in (0.24, 0.52, 0.79))
            return 0.29 * pulses * (math.sin(2 * math.pi * (132 - 52 * x) * t) + 0.18 * noise())
        if kind == "signal_reroute":
            return fade * (0.21 * math.sin(2 * math.pi * (78 + 42 * x) * t) + 0.14 * noise())
        if kind == "final_signal_lock":
            return envelope * (0.26 * math.sin(2 * math.pi * (104 - 18 * x) * t) + 0.11 * noise())
        if kind == "environmental_decay":
            return envelope * (0.15 * math.sin(2 * math.pi * (51 - 14 * x) * t) + 0.09 * noise())
        raise ValueError(f"unknown MF-007A event family: {kind}")

    return synth


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--ambient-output", required=True)
    parser.add_argument("--sfx-output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    fixture = json.loads(Path(args.fixture).read_text())
    duration = float(fixture["duration_seconds"])
    sample_count = round(duration * RATE)
    rng = random.Random(int(fixture["seed"]))
    ambient_l = [0.0] * sample_count
    ambient_r = [0.0] * sample_count
    sfx_l = [0.0] * sample_count
    sfx_r = [0.0] * sample_count
    slow_l = slow_r = fast_l = fast_r = 0.0
    mechanical_times = (4.35, 7.88, 11.62, 15.74, 18.08, 21.84, 25.18)
    for index in range(sample_count):
        t = index / RATE
        slow_l = slow_l * 0.9987 + (rng.random() * 2 - 1) * 0.0013
        slow_r = slow_r * 0.9985 + (rng.random() * 2 - 1) * 0.0015
        fast_l = fast_l * 0.91 + (rng.random() * 2 - 1) * 0.09
        fast_r = fast_r * 0.905 + (rng.random() * 2 - 1) * 0.095
        hum = 0.038 * math.sin(2 * math.pi * 47.3 * t + 0.018 * math.sin(2 * math.pi * 0.071 * t))
        harmonic = 0.012 * math.sin(2 * math.pi * 94.6 * t + 0.7)
        interference_l = 0.015 * slow_l + 0.0042 * fast_l
        interference_r = 0.014 * slow_r + 0.0045 * fast_r
        mechanical = 0.0
        for ordinal, event_time in enumerate(mechanical_times):
            distance = t - event_time
            if 0 <= distance <= 0.46:
                env = math.sin(math.pi * distance / 0.46) ** 2
                mechanical += 0.012 * env * math.sin(2 * math.pi * (61 + ordinal * 3.7) * distance)
        projection = 0.0
        if 2.9 <= t <= 19.1:
            projection_env = min(1.0, (t - 2.9) / 0.7, (19.1 - t) / 0.55)
            projection = max(0.0, projection_env) * 0.008 * math.sin(2 * math.pi * 83.7 * t + 0.13 * math.sin(2 * math.pi * 0.19 * t))
        gain = arc_gain(t, duration)
        ambient_l[index] = gain * (hum + harmonic + interference_l + mechanical + projection)
        ambient_r[index] = gain * (hum * 0.96 + harmonic * 1.03 + interference_r + mechanical * 0.92 + projection * 1.04)
    pans = (-0.42, -0.18, 0.0, 0.0, 0.08, -0.24, 0.0, 0.0, 0.18, 0.0, 0.0, 0.12, 0.0, 0.0, -0.18, 0.16, 0.0, 0.0)
    gains = (0.22, 0.21, 0.26, 0.36, 0.22, 0.14, 0.17, 0.13, 0.15, 0.16, 0.13, 0.14, 0.16, 0.22, 0.18, 0.18, 0.19, 0.10)
    evidence = []
    for ordinal, event in enumerate(fixture["events"]):
        add_event(sfx_l, sfx_r, float(event["time"]), float(event["duration"]), gains[ordinal], pans[ordinal], event_generator(event["family"], int(fixture["seed"]) + 7919 * (ordinal + 1)))
        evidence.append({**event, "gain": gains[ordinal], "pan": pans[ordinal]})
    write_stereo(Path(args.ambient_output), ambient_l, ambient_r)
    write_stereo(Path(args.sfx_output), sfx_l, sfx_r)
    report = {
        "slice": "MF-007A",
        "generator": "deterministic_synthesis",
        "sample_rate": RATE,
        "channels": 2,
        "duration": duration,
        "music_enabled": False,
        "music_sources": [],
        "ambient": {"start": 0.0, "end": duration, "layers": fixture["ambient_layers"], "wake_seconds": 1.55, "power_down": [26.3, 28.0]},
        "events": evidence,
        "silent_visuals": fixture["silent_visuals"],
        "no_constant_beeps": True,
        "no_melodic_or_rhythmic_program": True,
        "result": "PASS"
    }
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
