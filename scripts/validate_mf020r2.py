#!/usr/bin/env python3
"""Independent fail-closed validation for the MF-020R2 lamp alignment correction."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--proof-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    contract_path = (root / args.contract).resolve()
    proof_dir = (root / args.proof_dir).resolve()
    output = (root / args.output).resolve()
    focused_path = root / "config/mf-020r2-ring-lamp-alignment.json"
    base_path = root / "config/mf-bench-001.json"
    builder_path = root / "scripts/blender/build_mf_bench_001.py"
    contract = json.loads(contract_path.read_text())
    focused = json.loads(focused_path.read_text())
    base = json.loads(base_path.read_text())
    lamps = contract["upper_ring_lamps"]
    placement = lamps["placement"]
    records = lamps["records"]
    tolerances = focused["tolerances_scene_units"]
    checks: list[dict] = []

    def check(name: str, passed: bool, evidence: object) -> None:
        checks.append({"name": name, "passed": bool(passed), "evidence": evidence})

    check("slice_contract", focused["slice"] == "MF-020R2" and contract["backend"] == "BLENDER", {"focused_slice": focused["slice"], "backend": contract["backend"]})
    check("single_parameter_block", placement == base["upper_ring_lamps"] and placement["placement_space"] == "UPPER_RING_LOCAL" and placement["radius"] == placement["host_outer_radius"], placement)
    check("lamp_count", len(records) == placement["count"] == contract["objects"]["ring_lamps"], {"records": len(records), "configured": placement["count"]})
    check("hierarchy", lamps["hierarchy"][:3] == focused["required_hierarchy"] and all(item["parent"] == "LampArcRoot" and item["bulb_parent"] == f"UpperRingLamp_{item['index']:02d}" for item in records), lamps["hierarchy"])
    bulb_meshes = {item["shared_bulb_mesh"] for item in records}
    socket_meshes = {item["shared_socket_mesh"] for item in records}
    check("shared_master_geometry", bulb_meshes == {lamps["master_geometry"]["bulb_mesh"]} and socket_meshes == {lamps["master_geometry"]["socket_mesh"]}, {"bulb_meshes": sorted(bulb_meshes), "socket_meshes": sorted(socket_meshes)})

    expected_angles = [placement["start_angle_degrees"] + (placement["end_angle_degrees"] - placement["start_angle_degrees"]) * index / (placement["count"] - 1) for index in range(placement["count"])]
    angle_error = max(abs(item["angle_degrees"] - expected_angles[item["index"]]) for item in records)
    check("even_arc_interpolation", angle_error <= 1e-6, {"maximum_angle_error_degrees": angle_error, "angles": [item["angle_degrees"] for item in records]})
    check("constant_scale", all(item["scale"] == [1.0, 1.0, 1.0] for item in records), [item["scale"] for item in records])
    check("radial_deviation", lamps["maximum_radial_deviation"] <= tolerances["radial_deviation_max"], lamps["maximum_radial_deviation"])
    check("spacing_tolerance", lamps["spacing"]["maximum_variation"] <= tolerances["spacing_variation_max"] and lamps["spacing"]["minimum_observed"] > lamps["spacing"]["minimum_allowed"], lamps["spacing"])
    check("no_lamp_overlap", lamps["overlap_count"] == focused["required_overlap_count"], lamps["overlap_count"])
    check("no_protected_detail_intersection", lamps["protected_detail_intersection_count"] == focused["required_protected_detail_intersection_count"], lamps["protected_detail_intersection_count"])
    check("centered_glow", lamps["maximum_glow_anchor_delta"] <= tolerances["glow_anchor_delta_max"] and all(item["bulb_local_position"] == [0.0, 0.0, 0.0] for item in records), lamps["maximum_glow_anchor_delta"])
    check("no_placement_hacks", lamps["placement_animation_channels"] == 0 and lamps["screen_space_offsets"] == focused["required_screen_space_offset_count"] and lamps["per_lamp_manual_offsets"] == focused["required_manual_offset_count"], {key: lamps[key] for key in ("placement_animation_channels", "screen_space_offsets", "per_lamp_manual_offsets")})
    check("activation_position_invariance", lamps["maximum_position_drift"] <= tolerances["position_drift_max"] and len(lamps["position_samples"]) == 4, {"maximum_position_drift": lamps["maximum_position_drift"], "states": sorted(lamps["position_samples"])})
    activation = lamps["activation_samples"]
    activation_ok = activation["off"]["active_count"] == 0 and 3 <= activation["half"]["active_count"] <= 6 and activation["all"]["active_count"] == placement["count"]
    check("activation_changes_emission_only", activation_ok, {state: data["active_count"] for state, data in activation.items()})
    proof_camera = contract["proof_camera"]
    check("fixed_proof_camera", not proof_camera["animated"], proof_camera)

    proof_files = [proof_dir / name for name in ("lamps-off.png", "lamps-half.png", "lamps-all.png")]
    proof_evidence = []
    images_ok = True
    for path in proof_files:
        if not path.is_file():
            images_ok = False
            proof_evidence.append({"path": str(path.relative_to(root)), "missing": True})
            continue
        with Image.open(path) as image:
            size = list(image.size)
        images_ok &= size == base["shot"]["resolution"]
        proof_evidence.append({"path": str(path.relative_to(root)), "sha256": sha256(path), "resolution": size})
    check("fixed_camera_proof_images", images_ok and len({item.get("sha256") for item in proof_evidence}) == 3, proof_evidence)

    source = builder_path.read_text()
    centralized = all(token in source for token in ("start_angle + (end_angle - start_angle) * t", "root.parent = lamp_arc_root", "bulb.parent = root", "socket.parent = root"))
    prohibited_index_condition = re.search(r"if\s+(?:index|lamp_index)\s*==", source) is not None
    check("geometry_level_source_implementation", centralized and not prohibited_index_condition, {"centralized_formula": centralized, "per_index_condition_found": prohibited_index_condition})

    passed = all(item["passed"] for item in checks)
    result = {
        "slice": "MF-020R2",
        "result": "PASS" if passed else "FAIL",
        "technical_state": "ALIGNMENT_GATE_PASS" if passed else "ALIGNMENT_GATE_FAIL",
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_total": len(checks),
        "checks": checks,
        "inputs": {
            "contract": str(contract_path.relative_to(root)),
            "contract_sha256": sha256(contract_path),
            "focused_config_sha256": sha256(focused_path),
            "base_config_sha256": sha256(base_path),
            "builder_sha256": sha256(builder_path)
        },
        "human_review": "PENDING_HUMAN",
        "publication": False
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
