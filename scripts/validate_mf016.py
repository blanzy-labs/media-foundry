#!/usr/bin/env python3
"""Independent fail-closed validation of the MF-016 composition-gate package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from composition_contract import SEMANTIC_ROLES, VISUAL_PURPOSES, ZONE_KINDS, authorize_animation, requires_composition_gate, validate_manifest
from run_mf016 import STATE_INTENSITY, StaticCompositionRenderer


FROZEN = {
    "artifacts/mf-015/final-test.mp4": "f145f0b089f54e6db32a4ab907f53ae8eb4b6dbbe7ebcb7eed50bec8034b7d7c",
    "artifacts/mf-015r1/final-test.mp4": "4945abbb49965b1132fa99be45e2d9019e5214ef0ccf23905936da0077f113a6",
    "artifacts/mf-015r2/final-test.mp4": "3c3d570d9c8d33a0942373937beefef49809b46f2e7a256008c3b9c2de9dc080",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def region_mean(image: np.ndarray, zone: dict) -> float:
    h, w = image.shape[:2]
    x1, y1 = round(zone["x"] * w), round(zone["y"] * h)
    x2, y2 = round((zone["x"] + zone["width"]) * w), round((zone["y"] + zone["height"]) * h)
    crop = image[y1:y2, x1:x2]
    return float(np.mean(.2126 * crop[:, :, 0] + .7152 * crop[:, :, 1] + .0722 * crop[:, :, 2]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve()
    config_path = root / "config/mf016-pulp-composition.json"
    artifact_dir = root / "artifacts/mf-016"
    manifest = json.loads(config_path.read_text())
    package = json.loads((artifact_dir / "composition-approval-package.json").read_text())
    tests = json.loads((artifact_dir / "validation/failure-tests.json").read_text())
    layout = validate_manifest(manifest); gate = authorize_animation(manifest)
    checks = {}

    def check(name, passed, detail):
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    frozen = {path: sha256(root / path) if (root / path).is_file() else None for path in FROZEN}
    check("prior_candidates_frozen", frozen == FROZEN, frozen)
    check("contract_vocabulary", len(SEMANTIC_ROLES) == 12 and len(VISUAL_PURPOSES) == 10 and len(ZONE_KINDS) == 7,
          {"roles": sorted(SEMANTIC_ROLES), "purposes": sorted(VISUAL_PURPOSES), "zones": sorted(ZONE_KINDS)})
    check("semantic_manifest", layout["result"] == "PASS", layout)
    check("four_static_states", manifest["composition"]["static_states"] == list(STATE_INTENSITY), manifest["composition"]["static_states"])
    check("negative_space_first_class", any(zone.get("kind") == "negative_space_zone" and zone.get("preserve") is True for zone in manifest["zones"])
          and manifest["policies"]["empty_region_is_defect"] is False, "preserved and not occupancy-scored")
    check("known_problem_geometry_removed", not any(token in obj["id"] for obj in manifest["objects"]
          for token in ("crossing_pipe", "diagonal_rail", "cross_scene"))
          and sum(obj.get("major", False) and obj.get("allowed_zone") == "support_left" for obj in manifest["objects"]) == 1,
          [obj["id"] for obj in manifest["objects"]])
    check("one_intentional_support_bank", next(obj for obj in manifest["objects"] if obj["id"] == "left_control_bank")["purpose"]
          == ["communicate_machine_state", "establish_scale", "establish_depth"], "one major object in support_left")
    frame_details, deterministic, dimensions = {}, True, True
    renderer = StaticCompositionRenderer(manifest)
    hero = next(zone for zone in manifest["zones"] if zone["id"] == "hero_center_right")
    support = next(zone for zone in manifest["zones"] if zone["id"] == "support_left")
    negative = next(zone for zone in manifest["zones"] if zone["id"] == "negative_space_upper_left")
    hero_ratios = []
    for item in package["static_keyframes"]:
        path = Path(item["path"]); image = Image.open(path).convert("RGB"); values = np.asarray(image)
        dimensions = dimensions and image.size == (768, 1152) and sha256(path) == item["sha256"]
        rerendered = renderer.render(item["state"])
        deterministic = deterministic and hashlib.sha256(rerendered.tobytes()).hexdigest() == hashlib.sha256(image.tobytes()).hexdigest()
        hm, sm, nm = region_mean(values, hero), region_mean(values, support), region_mean(values, negative)
        ratio = hm / max(sm, 1); hero_ratios.append(ratio)
        frame_details[item["state"]] = {"hero_mean": round(hm, 3), "support_mean": round(sm, 3),
                                         "negative_space_mean": round(nm, 3), "hero_support_ratio": round(ratio, 3)}
    check("keyframe_integrity", dimensions, package["static_keyframes"])
    check("deterministic_keyframes", deterministic, "pixel-identical rerender")
    check("brightness_hierarchy", all(ratio > 1.18 for ratio in hero_ratios), frame_details)
    reactor_means = [frame_details[state]["hero_mean"] for state in STATE_INTENSITY]
    check("static_state_progression", all(b > a for a, b in zip(reactor_means, reactor_means[1:])), reactor_means)
    check("contact_sheet_and_comparison", Path(package["contact_sheet"]).is_file() and Path(package["before_after"]).is_file(),
          {"contact_sheet": package["contact_sheet"], "before_after": package["before_after"]})
    check("purpose_and_failure_tests", tests["result"] == "PASS" and tests["passed"] == tests["total"] >= 10,
          {"passed": tests["passed"], "total": tests["total"]})
    check("fail_closed_gate", gate["state"] == "BLOCKED_COMPOSITION" and not gate["animation_authorized"]
          and gate["reason"] == "HUMAN_COMPOSITION_APPROVAL_REQUIRED", gate)
    check("legacy_simple_compatibility", not requires_composition_gate({"format": "title_plate", "complex_scene": False})
          and requires_composition_gate(manifest), "simple bypasses; complex requires gate")
    videos = list(artifact_dir.rglob("*.mp4")) + list(artifact_dir.rglob("*.mov"))
    check("no_full_video_render", not videos and package["full_video_rendered"] is False, [str(path) for path in videos])
    check("human_authority_preserved", manifest["approval"] == {"human_status": "PENDING_HUMAN", "reviewer": None}, manifest["approval"])
    check("not_published", package["published"] is False, package["published"])
    result = "TECHNICAL_PASS" if all(value["status"] == "PASS" for value in checks.values()) else "FAIL"
    report = {"slice": "MF-016", "result": result, "composition_state": "COMPOSITION_PENDING",
              "human_review": "PENDING_HUMAN", "checks": checks, "frame_metrics": frame_details,
              "animation_authorized": False, "published": False}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n"); print(json.dumps(report, indent=2))
    return 0 if result == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
