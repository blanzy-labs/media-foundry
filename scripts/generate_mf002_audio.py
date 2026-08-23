#!/usr/bin/env python3
"""Generate the deterministic MF-002 tactile audio vocabulary as PCM WAV."""

import argparse
import json
import math
import struct
import wave
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grammar", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    grammar = json.loads(Path(args.grammar).read_text(encoding="utf-8"))
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    rate = int(grammar["audio"]["sample_rate"])
    duration = float(fixture.get("format", {}).get("duration_seconds", grammar["canvas"]["duration_seconds"]))
    events = grammar["audio"]["events"]
    if fixture.get("beats"):
        vocabulary = {event["name"].lower(): event for event in events}
        events, cursor = [], 0.0
        for beat in fixture["beats"]:
            cue = beat.get("audio_cue")
            if cue:
                event = dict(vocabulary[cue])
                event["time"] = cursor + min(0.12, float(beat["duration"]) * 0.1)
                events.append(event)
            cursor += float(beat["duration"])
    seed = int(fixture["seed"])
    samples = []
    noise = seed & 0x7FFFFFFF
    for index in range(int(rate * duration)):
        t = index / rate
        value = 0.007 * math.sin(2.0 * math.pi * 54.0 * t)
        for event in events:
            local = t - float(event["time"])
            event_duration = float(event["duration"])
            if 0.0 <= local < event_duration:
                envelope = (1.0 - local / event_duration) ** 2
                frequency = float(event["frequency"]) + (seed % 5 - 2)
                value += float(event["gain"]) * envelope * math.sin(2.0 * math.pi * frequency * local)
                if event["name"] == "INTRO_HIT":
                    noise = (1103515245 * noise + 12345) & 0x7FFFFFFF
                    value += (((noise / 0x7FFFFFFF) * 2.0) - 1.0) * 0.035 * envelope
        samples.append(max(-1.0, min(1.0, value)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"".join(struct.pack("<h", round(sample * 32767)) for sample in samples))
    print("MF_AUDIO_COMPLETE fixture=%s events=%s samples=%d" % (fixture["id"], ",".join(e["name"] for e in events), len(samples)))


if __name__ == "__main__":
    main()
