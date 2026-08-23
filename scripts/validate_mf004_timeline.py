#!/usr/bin/env python3
"""Independently compare MF-004 preflight intent with renderer execution evidence."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--execution", required=True)
    parser.add_argument("--layout", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    errors = []
    try:
        preflight = json.loads(Path(args.preflight).read_text())
        execution = json.loads(Path(args.execution).read_text())
        layout = json.loads(Path(args.layout).read_text())
    except (OSError, json.JSONDecodeError) as error:
        preflight, execution, layout = {}, {}, {}
        errors.append(f"unreadable evidence: {error}")
    if preflight.get("result") != "PASS" or execution.get("result") != "PASS" or layout.get("result") != "PASS":
        errors.append("preflight, renderer execution, or text layout did not pass")
    intended, observed = preflight.get("beats", []), execution.get("beats", [])
    if len(intended) != len(observed) or not intended:
        errors.append("renderer did not report exactly the intended beats")
    for expected, actual in zip(intended, observed):
        for key in ("id", "type", "start", "end"):
            if actual.get(key) != expected.get(key):
                errors.append(f"beat {expected.get('id')} execution differs for {key}")
        first_expected = round(float(expected["start"]) * 30)
        last_expected = round(float(expected["end"]) * 30) - 1
        if actual.get("first_frame") != first_expected or actual.get("last_frame") != last_expected or actual.get("status") != "PASS":
            errors.append(f"beat {expected.get('id')} frame interval did not execute exactly")
    checks = {
        "preflight": "PASS" if preflight.get("result") == "PASS" else "FAIL",
        "safe_text_layout": "PASS" if layout.get("result") == "PASS" else "FAIL",
        "beat_order_and_bounds": "PASS" if not errors else "FAIL",
        "one_active_beat": "PASS" if preflight.get("sequential_no_gaps") is True and not errors else "FAIL",
    }
    result = {"slice": "MF-004", "fixture": preflight.get("fixture"), "checks": checks, "errors": errors, "result": "PASS" if not errors else "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
