#!/usr/bin/env python3
"""Isolated failure tests for the MF-012 activity contract."""

import argparse
import copy
import json
import tempfile
from pathlib import Path

from validate_mf012_activity import validate_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    base = json.loads((root / "content/fixtures/mf012/01-moving-target-pursuit.json").read_text())
    cases = []

    def run_case(name, mutate, expected):
        fixture = copy.deepcopy(base)
        mutate(fixture)
        result = validate_config(root, fixture)
        passed = result["result"] == "FAIL" and expected in result["errors"]
        cases.append({"name": name, "expected": expected, "actual_errors": result["errors"], "result": "PASS" if passed else "FAIL"})

    run_case("unknown_activity", lambda value: value["activity"]["sequence"][0].update(type="unknown_effect"), "UNKNOWN_ACTIVITY")
    run_case("missing_target_reference", lambda value: value["activity"]["sequence"][0].update(target="missing_target"), "MISSING_TARGET_REFERENCE")
    run_case("impossible_dependency", lambda value: value["activity"].update(sequence=[{
        "id":"lock", "type":"target_lock", "target":"primary_target", "start":1.0, "duration":1.0, "intensity":1.0, "overlap":True
    }]), "IMPOSSIBLE_ACTIVITY_DEPENDENCY")
    run_case("invalid_timing", lambda value: value["activity"]["sequence"][0].update(start=50.0), "INVALID_ACTIVITY_TIMING")
    run_case("excessive_complexity", lambda value: value["activity"].update(supporting_activities=["connection","override","reconstruction"]), "ACTIVITY_COMPLEXITY_EXCEEDED")
    run_case("unknown_opening", lambda value: value["activity"].update(opening_choreography="random_open"), "UNKNOWN_OPENING_CHOREOGRAPHY")
    result = {"slice": "MF-012", "type": "isolated_failure_tests", "tests": cases,
              "passed": sum(case["result"] == "PASS" for case in cases), "total": len(cases),
              "result": "PASS" if all(case["result"] == "PASS" for case in cases) else "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
