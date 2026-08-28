#!/usr/bin/env python3
"""Fail-closed static composition gate for the MF-019 Blender candidate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from composition_contract import validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--manifest", required=True); parser.add_argument("--frames", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve(); config = json.loads((root / args.manifest).read_text()); folder = root / args.frames; checks = {}
    def check(name, passed, detail): checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
    labels = config["composition_gate"]["static_labels"]; paths = [folder / f"{label}.png" for label in labels]
    check("static_keyframes_exist", all(path.is_file() for path in paths), [str(path.relative_to(root)) for path in paths])
    images = [np.asarray(Image.open(path).convert("RGB")) for path in paths] if all(path.is_file() for path in paths) else []
    check("static_dimensions", bool(images) and all(image.shape == (1152, 768, 3) for image in images), [list(image.shape) for image in images])
    composition = validate_manifest(json.loads((root / config["composition_gate"]["manifest"]).read_text())); check("mf016_principles", composition["result"] == "PASS" and all(value == "PASS" for value in composition["checks"].values()), composition)
    metrics = []
    for label, image in zip(labels, images):
        luma = image.mean(axis=2); metrics.append({"label": label, "hero_luma": round(float(luma[200:1000, 285:750].mean()), 3), "console_luma": round(float(luma[520:1060, 0:300].mean()), 3), "display_luma": round(float(luma[190:490, 0:285].mean()), 3), "top_negative_space_luma": round(float(luma[0:180].mean()), 3), "bright_pixels": int((luma > 70).sum())})
    check("reactor_hero_visible", bool(metrics) and min(item["hero_luma"] for item in metrics) > 5 and min(item["bright_pixels"] for item in metrics) > 3000, metrics)
    check("console_readable", bool(metrics) and min(item["console_luma"] for item in metrics) > 12, metrics)
    check("negative_space_intentional", bool(metrics) and max(item["top_negative_space_luma"] for item in metrics) < 8, metrics)
    differences = [int(np.any(images[index] != images[index + 1], axis=2).sum()) for index in range(len(images) - 1)] if images else []
    check("semantic_states_visually_distinct", bool(differences) and min(differences) > 500, differences)
    final = images[-1] if images else None; display_contrast = int((final[200:470, 10:275].max(axis=2) > 100).sum()) if final is not None else 0
    check("final_information_panel_readable", display_contrast > 1500, {"high_contrast_pixels": display_contrast})
    scene_contract = json.loads((folder / "scene-contract.json").read_text()) if (folder / "scene-contract.json").is_file() else {}
    attached = scene_contract.get("attached_motion", {}); check("physical_attachment_contract", bool(attached) and all(attached.values()), attached)
    check("configured_ready_before_full_render", config["composition_gate"]["required_state"] == "CONFIGURED_READY" and config["composition_gate"]["human_review"] == "PENDING_HUMAN", config["composition_gate"])
    result = "PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"; report = {"slice": "MF-019", "gate": "BLENDER_STATIC_COMPOSITION", "result": result, "checks": checks, "metrics": metrics, "human_review": "PENDING_HUMAN"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n"); print(json.dumps(report, indent=2)); return 0 if result == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
