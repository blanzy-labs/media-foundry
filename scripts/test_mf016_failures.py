#!/usr/bin/env python3
"""Isolated positive and negative tests for the MF-016 composition contract."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from composition_contract import authorize_animation, requires_composition_gate, validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    base = json.loads((root / "config/mf016-pulp-composition.json").read_text())
    cases = []

    def failure(name, mutate, expected):
        value = copy.deepcopy(base); mutate(value); result = validate_manifest(value)
        codes = [error["code"] for error in result["errors"]]
        passed = result["result"] == "FAIL" and expected in codes
        cases.append({"name": name, "expected": expected, "errors": codes, "result": "PASS" if passed else "FAIL"})

    failure("missing_semantic_role", lambda value: value["objects"][2].pop("semantic_role"), "MISSING_OR_INVALID_SEMANTIC_ROLE")
    failure("missing_visual_purpose", lambda value: value["objects"][2].update(purpose=[]), "INVALID_VISUAL_PURPOSE")
    failure("fill_empty_space_rejected", lambda value: value["objects"][2].update(purpose=["fill_empty_space"]), "INVALID_VISUAL_PURPOSE")

    def add_bad_crossing(value):
        value["objects"].append({
            "id": "bad_diagonal_pipe", "semantic_role": "foreground_frame", "purpose": ["establish_depth"],
            "visual_priority": "tertiary", "allowed_zone": "background_full",
            "geometry": {"kind": "line", "points": [[.02, .82], [.94, .22]]},
            "may_occlude": ["background_full"], "may_not_occlude": ["main_reactor"],
            "remove_if_no_visual_purpose": True, "major": True, "estimated_contrast": .9,
        })

    failure("unmotivated_hero_occlusion", add_bad_crossing, "UNMOTIVATED_HERO_OCCLUSION")
    failure("unmotivated_cross_scene_line", add_bad_crossing, "UNMOTIVATED_CROSS_SCENE_OCCLUSION")

    def overcrowd(value):
        for index, x in enumerate((.07, .18), start=1):
            obj = copy.deepcopy(value["objects"][2]); obj["id"] = f"extra_bank_{index}"
            obj["geometry"].update(x=x, y=.5, width=.08, height=.17); value["objects"].append(obj)

    failure("excessive_support_density", overcrowd, "EXCESSIVE_SUPPORT_DENSITY")

    valid = validate_manifest(base)
    cases.append({"name": "preserved_negative_space_is_valid", "expected": "PASS", "errors": valid["errors"],
                  "result": "PASS" if valid["result"] == "PASS" else "FAIL"})
    pending = authorize_animation(base)
    cases.append({"name": "pending_human_blocks_animation", "expected": "BLOCKED_COMPOSITION", "actual": pending["state"],
                  "result": "PASS" if not pending["animation_authorized"] and pending["state"] == "BLOCKED_COMPOSITION" else "FAIL"})
    approved = copy.deepcopy(base); approved["approval"] = {"human_status": "APPROVED", "reviewer": "test-reviewer"}
    ready = authorize_animation(approved)
    cases.append({"name": "valid_human_approval_authorizes_animation", "expected": "COMPOSITION_READY", "actual": ready["state"],
                  "result": "PASS" if ready["animation_authorized"] and ready["state"] == "COMPOSITION_READY" else "FAIL"})
    simple = {"format": "static_title_plate", "complex_scene": False}
    cases.append({"name": "legacy_simple_format_compatible", "expected": False, "actual": requires_composition_gate(simple),
                  "result": "PASS" if not requires_composition_gate(simple) else "FAIL"})
    cases.append({"name": "complex_scene_requires_gate", "expected": True, "actual": requires_composition_gate(base),
                  "result": "PASS" if requires_composition_gate(base) else "FAIL"})
    report = {"slice": "MF-016", "type": "composition_contract_tests", "tests": cases,
              "passed": sum(case["result"] == "PASS" for case in cases), "total": len(cases),
              "result": "PASS" if all(case["result"] == "PASS" for case in cases) else "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n"); print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
