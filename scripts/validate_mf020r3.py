#!/usr/bin/env python3
"""Independent invariant and brightness gate for MF-020R3."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(rendered.encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    art = root / "artifacts/mf-020r3"
    focus_path = root / "config/mf-020r3-dormant-lighting.json"
    base_path = root / "config/mf-bench-001.json"
    focus = json.loads(focus_path.read_text())
    base = json.loads(base_path.read_text())
    frozen = focus["frozen_invariants"]
    baseline_contract = json.loads((root / "artifacts/mf-020r2/proof/scene-contract.json").read_text())
    refined_contract = json.loads((art / "proof/scene-contract.json").read_text())
    before_gate = json.loads((root / "artifacts/mf-bench-001/blockout/validation.json").read_text())
    after_gate = json.loads((art / "validation/composition.json").read_text())
    checks: list[dict] = []

    def check(name: str, passed: bool, evidence: object) -> None:
        checks.append({"name": name, "passed": bool(passed), "evidence": evidence})

    allowed_focus_keys = {"slice", "base_manifest", "scope", "frozen_invariants", "dormant_lighting", "stages", "human_review", "publication"}
    check("lighting_only_manifest_scope", set(focus) <= allowed_focus_keys and focus["scope"] == "dormant_state_lighting_and_machine_readability_only", sorted(focus))
    base_integrity = sha256(base_path) == frozen["base_manifest_sha256"]
    canonical = {key: canonical_sha256(base[key]) for key in ("upper_ring_lamps", "shot", "text", "audio")}
    canonical_ok = canonical["upper_ring_lamps"] == frozen["upper_ring_lamps_canonical_sha256"] and canonical["shot"] == frozen["shot_canonical_sha256"] and canonical["text"] == frozen["text_canonical_sha256"] and canonical["audio"] == frozen["audio_canonical_sha256"]
    check("frozen_base_invariants", base_integrity and canonical_ok, {"base_sha256": sha256(base_path), "canonical_sha256": canonical})

    old_lamps = baseline_contract["upper_ring_lamps"]
    new_lamps = refined_contract["upper_ring_lamps"]
    lamp_keys = ("placement", "hierarchy", "master_geometry", "records", "spacing", "maximum_radial_deviation", "overlap_count", "protected_detail_intersection_count", "maximum_glow_anchor_delta", "position_samples", "maximum_position_drift", "placement_animation_channels", "screen_space_offsets", "per_lamp_manual_offsets")
    lamp_differences = [key for key in lamp_keys if old_lamps[key] != new_lamps[key]]
    check("r2_lamp_alignment_preserved_exactly", not lamp_differences, {"differences": lamp_differences, "baseline_contract": "artifacts/mf-020r2/proof/scene-contract.json", "refined_contract": "artifacts/mf-020r3/proof/scene-contract.json"})
    check("camera_and_scene_contract_preserved", baseline_contract["camera"] == refined_contract["camera"] and baseline_contract["objects"] == refined_contract["objects"] and baseline_contract["causality"] == refined_contract["causality"], {"camera": refined_contract["camera"], "objects": refined_contract["objects"], "causality": refined_contract["causality"]})
    check("text_preserved", baseline_contract["text"] == refined_contract["text"] == base["text"], refined_contract["text"])

    check("existing_composition_gate", after_gate["result"] == "STATIC_TECHNICAL_PASS" and after_gate["passed"] == after_gate["total"] == 11, {"result": after_gate["result"], "state": after_gate["state"], "passed": after_gate["passed"], "total": after_gate["total"]})
    before = before_gate["metrics"][0]
    metrics = after_gate["metrics"]
    dormant, startup, mid_active, peak = metrics
    check("dormant_readability_improved", dormant["frame_mean"] > before["frame_mean"] and dormant["hero_mean"] > before["hero_mean"] and dormant["hero_bright_pixels"] > 30, {"before": before, "after": dormant, "threshold": {"frame_mean_min": 3.0, "hero_mean_min": 2.0, "hero_bright_pixels_min_exclusive": 30, "bright_luma": 80}})
    monotonic = all(metrics[index]["frame_mean"] < metrics[index + 1]["frame_mean"] for index in range(3)) and all(metrics[index]["hero_mean"] < metrics[index + 1]["hero_mean"] for index in range(3))
    check("monotonic_lighting_progression", monotonic, [{"label": item["label"], "frame_mean": item["frame_mean"], "hero_mean": item["hero_mean"]} for item in metrics])
    dynamic_range = peak["frame_mean"] / dormant["frame_mean"] if dormant["frame_mean"] else 0
    hero_dynamic_range = peak["hero_mean"] / dormant["hero_mean"] if dormant["hero_mean"] else 0
    check("meaningful_dynamic_range", dynamic_range >= 2.0 and hero_dynamic_range >= 3.0 and dormant["hero_mean"] > dormant["console_mean"], {"peak_to_dormant_frame_ratio": round(dynamic_range, 6), "peak_to_dormant_hero_ratio": round(hero_dynamic_range, 6), "dormant_hero_mean": dormant["hero_mean"], "dormant_console_mean": dormant["console_mean"]})

    proof_paths = [art / "proof" / f"{label}.png" for label in ("dormant", "startup", "mid-active", "peak")]
    check("four_state_proof_complete", all(path.is_file() and path.stat().st_size > 1024 for path in proof_paths), [{"path": str(path.relative_to(root)), "sha256": sha256(path) if path.is_file() else None} for path in proof_paths])

    passed = all(item["passed"] for item in checks)
    result = {
        "slice": "MF-020R3",
        "result": "PASS" if passed else "FAIL",
        "technical_state": "LIGHTING_GATE_PASS" if passed else "LIGHTING_GATE_FAIL",
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_total": len(checks),
        "checks": checks,
        "metrics": {"before_dormant": before, "refined_states": metrics},
        "human_review": "PENDING_HUMAN",
        "publication": False
    }
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
