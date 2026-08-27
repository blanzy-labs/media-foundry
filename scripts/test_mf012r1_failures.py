#!/usr/bin/env python3
"""Isolated fail-closed tests for the MF-012R1 micro-variation contract."""

import argparse
import copy
import json
from pathlib import Path

from validate_mf012r1 import validate_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    base = json.loads((root / "content/fixtures/mf012r1/video-02-reactive.json").read_text())
    source = json.loads((root / "content/fixtures/mf011/06-the-kill-switch.json").read_text())
    cases = []

    def run_case(name, mutate, expected):
        fixture = copy.deepcopy(base)
        mutate(fixture)
        result = validate_config(root, fixture, source)
        passed = result["result"] == "FAIL" and expected in result["errors"]
        cases.append({"name": name, "expected": expected, "actual_errors": result["errors"], "result": "PASS" if passed else "FAIL"})

    run_case("ring_enters_text_zone", lambda value: value["micro_variation"]["floating_ring_dot"]["path"].__setitem__(0, {"x": 0, "y": -100}), "MICRO_VARIATION_SAFE_ZONE_VIOLATION")
    run_case("unsupported_indicator_color", lambda value: value["micro_variation"]["indicator_dots"]["colors"].__setitem__(0, "red"), "UNSUPPORTED_INDICATOR_COLOR")
    run_case("excessive_active_tiles", lambda value: value["micro_variation"]["background_tiles"].update(active_indices=list(range(9))), "MICRO_VARIATION_TILE_DENSITY_EXCEEDED")
    run_case("unseeded_random_configuration", lambda value: value["micro_variation"].pop("seed"), "MICRO_VARIATION_SEED_REQUIRED")
    run_case("too_many_channels", lambda value: value["micro_variation"].update(channels=["indicator_dots", "background_tiles", "floating_ring_dot", "mild_circuit_accent"]), "MICRO_VARIATION_BUDGET_EXCEEDED")
    run_case("unknown_micro_variation", lambda value: value["micro_variation"].update(channels=["indicator_dots", "unknown_overlay"]), "UNKNOWN_MICRO_VARIATION_TYPE")
    result = {"slice": "MF-012R1", "type": "isolated_failure_tests", "tests": cases,
              "passed": sum(case["result"] == "PASS" for case in cases), "total": len(cases),
              "result": "PASS" if all(case["result"] == "PASS" for case in cases) else "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
