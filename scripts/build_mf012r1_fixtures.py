#!/usr/bin/env python3
"""Create two MF-012R1 fixtures by changing only renderer preference and micro controls."""

import argparse
import json
from pathlib import Path

from mf012r1_contract import build_micro_variation


SELECTIONS = [
    ("content/fixtures/mf011/02-leo-living-data-bridge.json", "video-01-restrained", "restrained", 121201),
    ("content/fixtures/mf011/06-the-kill-switch.json", "video-02-reactive", "reactive", 121202),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    output = root / "content/fixtures/mf012r1"
    output.mkdir(parents=True, exist_ok=True)
    for source_name, output_name, variant, seed in SELECTIONS:
        source = json.loads((root / source_name).read_text())
        source["visual_strategy"]["preference"] = "godot_indicator_pulse_refinement"
        source["micro_variation"] = build_micro_variation(variant, seed, float(source["format"]["duration_seconds"]))
        destination = output / f"{output_name}.json"
        destination.write_text(json.dumps(source, indent=2) + "\n")
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
