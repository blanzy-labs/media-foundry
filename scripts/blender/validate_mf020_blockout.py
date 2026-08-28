#!/usr/bin/env python3
"""Fail-closed MF-020 blockout composition and camera-path gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--frames", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    config = json.loads((root / args.manifest).read_text())
    folder = root / args.frames
    stage = config["stages"]["blockout"]
    checks = {}

    def check(name, passed, detail):
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    paths = [folder / f"{label}.png" for label in stage["labels"]]
    exists = all(path.is_file() and path.stat().st_size > 1024 for path in paths)
    check("blockout_keyframes_exist", exists, [str(path.relative_to(root)) for path in paths])
    images = [np.asarray(Image.open(path).convert("RGB")) for path in paths] if exists else []
    check("portrait_output_contract", bool(images) and all(image.shape == (1152, 768, 3) for image in images), [list(image.shape) for image in images])
    metrics = []
    for label, image in zip(stage["labels"], images):
        luma = image.mean(axis=2)
        center = luma[170:1050, 205:690]
        console = luma[520:1090, 0:340]
        edges = np.concatenate((luma[:, :80].ravel(), luma[:, -80:].ravel()))
        metrics.append({"label": label, "hero_luma": round(float(center.mean()), 3), "console_luma": round(float(console.mean()), 3), "edge_bright_pixels": int((edges > 110).sum()), "hero_bright_pixels": int((center > 70).sum())})
    check("reactor_is_readable_hero", bool(metrics) and min(item["hero_luma"] for item in metrics) > 20 and min(item["hero_bright_pixels"] for item in metrics) > 800, metrics)
    check("console_visible_secondary", bool(metrics) and min(item["console_luma"] for item in metrics) > 4, metrics)
    check("no_distracting_edge_clutter", bool(metrics) and max(item["edge_bright_pixels"] for item in metrics) < 25000, metrics)
    differences = [int(np.any(images[index] != images[index + 1], axis=2).sum()) for index in range(len(images) - 1)] if images else []
    check("camera_path_and_escalation_readable", bool(differences) and min(differences) > 12000, differences)
    contract_path = folder / "scene-contract.json"
    contract = json.loads(contract_path.read_text()) if contract_path.is_file() else {}
    camera = contract.get("camera", {})
    check("single_perspective_camera_contract", camera.get("single_shot") is True and camera.get("lens_mm") == 46.0 and camera.get("move") == "slow_push_with_subtle_rightward_orbit", camera)
    objects = contract.get("objects", {})
    check("purposeful_blockout_elements", objects.get("reactor") and objects.get("console") and objects.get("gauges") == 3 and objects.get("lever"), objects)
    check("configured_ready_before_detail", stage["required_state"] == "CONFIGURED_READY", stage)
    result = "PASS" if all(value["status"] == "PASS" for value in checks.values()) else "FAIL"
    report = {"slice": "MF-020", "gate": "BLENDER_BLOCKOUT", "result": result, "checks": checks, "metrics": metrics, "stage_state": stage["required_state"], "detail_render_authorized": result == "PASS"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
