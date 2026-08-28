#!/usr/bin/env python3
"""Independent static composition gate for MF-BENCH-001."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from composition_contract import authorize_animation, validate_manifest
from visual_source_contract import validate_visual_source


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default="config/mf-bench-001.json")
    parser.add_argument("--composition", default="config/mf-bench-001-composition.json")
    parser.add_argument("--artifacts", default="artifacts/mf-bench-001")
    parser.add_argument("--frames-subdir", default="blockout")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    config_path = root / args.config
    composition_path = root / args.composition
    config_definition = json.loads(config_path.read_text())
    base_config_path = root / config_definition["base_manifest"] if config_definition.get("base_manifest") else None
    if base_config_path:
        config = json.loads(base_config_path.read_text())
        for config_key, config_value in config_definition.items():
            if config_key not in ("base_manifest", "frozen_invariants"):
                config[config_key] = config_value
    else:
        config = config_definition
    composition = json.loads(composition_path.read_text())
    art = root / args.artifacts
    checks = {}

    def check(name: str, passed: bool, detail) -> None:
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    source = validate_visual_source(root, config)
    check("source_strategy", source["result"] == "PASS" and source["configured_strategy"] == source["resolved_strategy"] == source["recommended_strategy"] == "PROCEDURAL", source)
    reference = Path(config["reference"]["path"])
    check("reference_art_direction_only", reference.is_file() and sha256(reference) == config["reference"]["sha256"] and config["reference"]["embedded_in_video"] is False, config["reference"])
    machine = validate_manifest(composition)
    check("semantic_composition_contract", machine["result"] == "PASS" and all(value == "PASS" for value in machine["checks"].values()), machine)
    gate = authorize_animation(composition)
    check("human_gate_preserved", gate["state"] == "BLOCKED_COMPOSITION" and gate["reason"] == "HUMAN_COMPOSITION_APPROVAL_REQUIRED" and gate["animation_authorized"] is False, gate)

    labels = config["stages"]["blockout"]["labels"]
    frames_dir = art / args.frames_subdir
    paths = [frames_dir / f"{label}.png" for label in labels]
    complete = all(path.is_file() and path.stat().st_size > 1024 for path in paths)
    images = [np.asarray(Image.open(path).convert("RGB")) for path in paths] if complete else []
    check("static_keyframes_exist", complete and all(image.shape == (1152, 768, 3) for image in images), [str(path.relative_to(root)) for path in paths])

    metrics = []
    for label, image in zip(labels, images):
        luma = .2126 * image[:, :, 0] + .7152 * image[:, :, 1] + .0722 * image[:, :, 2]
        hero = luma[160:900, 220:680]
        console = luma[430:1000, 0:245]
        title = image[35:145, 210:750]
        yellow = (title[:, :, 0] > 145) & (title[:, :, 1] > 75) & (title[:, :, 2] < 85)
        metrics.append({"label": label, "frame_mean": round(float(luma.mean()), 3), "hero_mean": round(float(hero.mean()), 3), "hero_bright_pixels": int((hero > 80).sum()), "console_mean": round(float(console.mean()), 3), "title_yellow_pixels": int(yellow.sum())})
    check("opening_hook_readable_not_dead_black", bool(metrics) and metrics[0]["frame_mean"] > 3.0 and metrics[0]["hero_mean"] > 2.0 and metrics[0]["hero_bright_pixels"] > 30, metrics[0] if metrics else None)
    check("hero_and_console_hierarchy", bool(metrics) and min(item["console_mean"] for item in metrics) > 2.0 and metrics[2]["hero_mean"] > metrics[2]["console_mean"] * 1.7 and metrics[2]["hero_bright_pixels"] > 15000, metrics)
    differences = [int(np.any(images[index] != images[index + 1], axis=2).sum()) for index in range(len(images) - 1)] if images else []
    check("static_progression_is_distinct", bool(differences) and min(differences) > 10000, differences)
    check("identity_reveal_earned_and_safe", bool(metrics) and max(item["title_yellow_pixels"] for item in metrics[:3]) < 25 and metrics[3]["title_yellow_pixels"] > 100, metrics)

    contract_path = frames_dir / "scene-contract.json"
    contract = json.loads(contract_path.read_text()) if contract_path.is_file() else {}
    fingerprint = contract.get("render_fingerprint", {})
    fingerprint_ok = fingerprint.get("config_sha256") == sha256(config_path) and fingerprint.get("base_config_sha256") == (sha256(base_config_path) if base_config_path else None) and fingerprint.get("builder_sha256") == sha256(root / config["render"]["blender"]["builder_script"]) and fingerprint.get("template_sha256") == sha256(root / config["render"]["blender"]["template"])
    check("render_fingerprint", fingerprint_ok, fingerprint)
    check("empty_lab_and_physical_causality", contract.get("objects", {}).get("operator_count") == 0 and contract.get("reference_embedded") is False and all(contract.get("causality", {}).values()), {"objects": contract.get("objects"), "causality": contract.get("causality"), "reference_embedded": contract.get("reference_embedded")})

    failures = [name for name, value in checks.items() if value["status"] != "PASS"]
    if failures:
        result, state = "FAIL", "BLOCKED_COMPOSITION"
    else:
        result, state = "STATIC_TECHNICAL_PASS", "READY_FOR_HUMAN_COMPOSITION_REVIEW"
    report = {"slice": config_definition.get("slice", "MF-BENCH-001"), "result": result, "state": state, "passed": len(checks) - len(failures), "total": len(checks), "checks": checks, "metrics": metrics, "full_video_rendered": False, "creative_status": "PENDING_HUMAN", "published": False}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if result == "STATIC_TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
