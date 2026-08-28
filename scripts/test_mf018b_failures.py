#!/usr/bin/env python3
"""Required negative tests for the MF-018B playable scene package."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from playable_scene_contract import validate_package


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve()
    baseline = json.loads((root / "handoff/playable-scene/mf018b/manifest.json").read_text())
    cases = []

    def case(name: str, mutate, expected: str) -> None:
        candidate = copy.deepcopy(baseline); mutate(candidate); result = validate_package(root, candidate)
        codes = [item["code"] for item in result["errors"]]
        cases.append({"name": name, "expected_code": expected, "observed_codes": codes,
                      "status": "PASS" if result["result"] == "FAIL" and expected in codes else "FAIL"})

    case("duplicate_interaction_id", lambda m: m["interaction_points"].__setitem__(1, {**m["interaction_points"][1], "id": m["interaction_points"][0]["id"]}), "DUPLICATE_INTERACTION_ID")
    case("missing_interaction_node", lambda m: m["interaction_points"][0].__setitem__("node", "Machines/MissingControl"), "MISSING_INTERACTION_NODE")
    case("invalid_state_variable", lambda m: m["state_variables"][0].__setitem__("setter", "set_score"), "INVALID_STATE_VARIABLE")
    case("missing_audio_hook", lambda m: m.__setitem__("audio_events", [item for item in m["audio_events"] if item["id"] != "lever_clunk"]), "MISSING_AUDIO_HOOK")
    case("absolute_local_path", lambda m: m["package"].__setitem__("scene_path", "/home/user/private/scene.tscn"), "ABSOLUTE_OR_UNSAFE_PATH")
    case("promo_dependency_in_base", lambda m: m["package"].__setitem__("promo_driver_optional", False), "PROMO_DEPENDENCY_IN_BASE_SCENE")
    case("unresolved_asset", lambda m: m["assets"][0].__setitem__("path", "godot/missing-scene.tscn"), "UNRESOLVED_OR_CHANGED_ASSET")
    passed = sum(item["status"] == "PASS" for item in cases)
    report = {"slice": "MF-018B", "result": "PASS" if passed == len(cases) else "FAIL", "passed": passed, "total": len(cases), "cases": cases}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2)); return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
