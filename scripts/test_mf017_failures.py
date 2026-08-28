#!/usr/bin/env python3
"""Isolated source-strategy failure, advisory, fallback, and compatibility tests."""

import argparse
import copy
import json
from pathlib import Path

from visual_source_contract import validate_visual_source


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve()
    base = json.loads((root / "config/mf017-pulp-visual-source.json").read_text()); cases = []

    def failure(name, mutate, expected):
        value = copy.deepcopy(base); mutate(value); result = validate_visual_source(root, value)
        codes = [error["code"] for error in result["errors"]]
        cases.append({"name": name, "expected": expected, "errors": codes,
                      "state": result["state"], "result": "PASS" if result["result"] == "FAIL" and expected in codes else "FAIL"})

    failure("missing_source_strategy", lambda value: value["visual_source"].pop("configured_strategy"), "MISSING_SOURCE_STRATEGY")
    failure("unknown_source_strategy", lambda value: value["visual_source"].update(configured_strategy="UNKNOWN"), "UNKNOWN_SOURCE_STRATEGY")
    failure("hybrid_missing_plate", lambda value: value["visual_source"]["plate"].update(source_path="media/visual/plates/missing.png"), "MISSING_APPROVED_PLATE")

    def changed_approved(value):
        value["visual_source"]["plate"]["approval"] = {"status": "APPROVED", "reviewer": "fixture", "approved_sha256": value["visual_source"]["plate"]["source_sha256"]}
        value["visual_source"]["plate"]["source_sha256"] = "0" * 64
    failure("changed_approved_plate_hash", changed_approved, "PLATE_HASH_CHANGED")

    def unreviewed_production(value):
        value["visual_source"]["mode"] = "production"
        value["visual_source"]["plate"]["approval"] = {"status": "UNREVIEWED", "reviewer": None, "approved_sha256": None}
    failure("unreviewed_plate_in_production", unreviewed_production, "UNREVIEWED_PLATE_FOR_PRODUCTION")
    failure("silent_fallback_attempt", lambda value: value["visual_source"].update(resolved_strategy="PROCEDURAL"), "SILENT_STRATEGY_FALLBACK_PROHIBITED")

    def missing_authentic(value):
        source = value["visual_source"]; source["configured_strategy"] = source["resolved_strategy"] = "AUTHENTIC_MEDIA"
        source["requirements"]["authenticity_requirement"] = "HIGH"
        source["authentic_media"] = {"source_path": "media/authentic/missing.png"}
    failure("authentic_media_missing", missing_authentic, "MISSING_AUTHENTIC_MEDIA")

    procedural_high = copy.deepcopy(base); procedural_high["visual_source"]["configured_strategy"] = "PROCEDURAL"
    procedural_high["visual_source"]["resolved_strategy"] = "PROCEDURAL"; procedural_high["visual_source"].pop("plate")
    high_result = validate_visual_source(root, procedural_high)
    high_warnings = [warning["code"] for warning in high_result["warnings"]]
    cases.append({"name": "high_illustration_procedural_advisory", "expected": "VISUAL_SOURCE_STRATEGY_WARNING",
                  "warnings": high_warnings, "result": "PASS" if high_result["result"] == "PASS" and "VISUAL_SOURCE_STRATEGY_WARNING" in high_warnings else "FAIL"})
    low = copy.deepcopy(procedural_high); low["complex_scene"] = False; low_source = low["visual_source"]
    for field in low_source["requirements"]: low_source["requirements"][field] = "LOW"
    low_source["requirements"]["geometric_precision"] = "HIGH"; low_source["requirements"]["motion_requirement"] = "MEDIUM"
    low_source["composition_gate"]["required"] = False
    low_result = validate_visual_source(root, low)
    cases.append({"name": "low_complexity_procedural", "expected": "PROCEDURAL PASS", "recommended": low_result["recommended_strategy"],
                  "result": "PASS" if low_result["result"] == "PASS" and low_result["recommended_strategy"] == "PROCEDURAL" and not low_result["warnings"] else "FAIL"})
    allowed = copy.deepcopy(base); allowed_source = allowed["visual_source"]
    allowed_source["resolved_strategy"] = "PROCEDURAL"; allowed_source["fallback"] = {"allowed": True, "strategies": ["PROCEDURAL"]}
    allowed_result = validate_visual_source(root, allowed)
    cases.append({"name": "explicit_fallback_allowed", "expected": "PASS", "errors": allowed_result["errors"],
                  "result": "PASS" if allowed_result["result"] == "PASS" else "FAIL"})
    base_result = validate_visual_source(root, base)
    cases.append({"name": "pulp_hybrid_development_integration", "expected": "PASS WITH PRODUCTION_PLATE_PENDING",
                  "warnings": base_result["warnings"], "result": "PASS" if base_result["result"] == "PASS"
                  and any(w["code"] == "PRODUCTION_PLATE_PENDING" for w in base_result["warnings"]) else "FAIL"})
    report = {"slice": "MF-017", "type": "visual_source_failure_tests", "tests": cases,
              "passed": sum(case["result"] == "PASS" for case in cases), "total": len(cases),
              "result": "PASS" if all(case["result"] == "PASS" for case in cases) else "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2)); return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
