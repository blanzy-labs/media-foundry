#!/usr/bin/env python3
"""Independent fail-closed validation for the MF-017 source-strategy proof."""

import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from composition_contract import validate_manifest
from visual_source_contract import sha256, validate_visual_source


def probe(path: Path) -> dict:
    process = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    data = json.loads(process.stdout) if process.returncode == 0 else {}
    video = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
    return {"codec": video.get("codec_name"), "width": video.get("width"), "height": video.get("height"),
            "frames": int(video.get("nb_read_frames", 0)), "fps": video.get("avg_frame_rate"),
            "duration": float(data.get("format", {}).get("duration", 0)), "audio_streams": sum(s.get("codec_type") == "audio" for s in data.get("streams", []))}


def video_frame(path: Path, seconds: float) -> np.ndarray:
    process = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(seconds), "-i", str(path), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if process.returncode: raise RuntimeError(process.stderr.decode())
    return np.asarray(Image.open(io.BytesIO(process.stdout)).convert("RGB"))


def gradient_mean(values: np.ndarray) -> float:
    gray = .2126 * values[:, :, 0] + .7152 * values[:, :, 1] + .0722 * values[:, :, 2]
    return float((np.abs(np.diff(gray, axis=0)).mean() + np.abs(np.diff(gray, axis=1)).mean()) / 2)


def material_metrics(values: np.ndarray) -> dict:
    gray = .2126 * values[:, :, 0] + .7152 * values[:, :, 1] + .0722 * values[:, :, 2]
    laplacian = np.abs(gray[1:-1, 1:-1] * 4 - gray[:-2, 1:-1] - gray[2:, 1:-1]
                       - gray[1:-1, :-2] - gray[1:-1, 2:])
    quantized_colors = len(np.unique((values // 8).astype(np.uint8).reshape(-1, 3), axis=0))
    return {"gradient_mean": gradient_mean(values), "laplacian_p90": float(np.percentile(laplacian, 90)),
            "quantized_color_count": quantized_colors}


def region_mean(values: np.ndarray, zone: dict) -> float:
    h, w = values.shape[:2]; x1, y1 = round(zone["x"] * w), round(zone["y"] * h)
    x2, y2 = round((zone["x"] + zone["width"]) * w), round((zone["y"] + zone["height"]) * h)
    crop = values[y1:y2, x1:x2]; return float(np.mean(.2126 * crop[:, :, 0] + .7152 * crop[:, :, 1] + .0722 * crop[:, :, 2]))


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve(); artifacts = root / "artifacts/mf-017"
    config = json.loads((root / "config/mf017-pulp-visual-source.json").read_text())
    manifest = json.loads((artifacts / "proof-manifest.json").read_text())
    failures = json.loads((root / "reports/mf-017/failure-tests.json").read_text())
    composition = json.loads((root / "config/mf016-pulp-composition.json").read_text())
    source = validate_visual_source(root, config); composition_result = validate_manifest(composition); checks = {}

    def check(name, passed, detail): checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    check("mf016_frozen_and_valid", sha256(root / "config/mf016-pulp-composition.json") == "53971df4c454268eb09c5d9715fae7fab6defd8979484888d318d643355b26ef"
          and composition_result["result"] == "PASS", composition_result)
    check("source_strategy_contract", source["result"] == "PASS" and source["configured_strategy"] == source["resolved_strategy"] == "HYBRID", source)
    check("independent_hybrid_recommendation", source["recommended_strategy"] == "HYBRID", source["recommendation_reasons"])
    plate = root / config["visual_source"]["plate"]["source_path"]
    plate_image = Image.open(plate)
    check("plate_integrity_and_dimensions", sha256(plate) == config["visual_source"]["plate"]["source_sha256"]
          and plate_image.size == (1024, 1536), {"sha256": sha256(plate), "size": plate_image.size})
    check("plate_provenance_and_review_state", config["visual_source"]["plate"]["provenance"] == "generated"
          and config["visual_source"]["plate"]["approval"]["status"] == "REVIEW_REQUIRED"
          and source["release_ready"] is False, config["visual_source"]["plate"]["approval"])
    check("no_silent_fallback", source["checks"]["no_silent_fallback"] == "PASS" and not config["visual_source"]["fallback"]["allowed"], config["visual_source"]["fallback"])
    check("layer_and_animation_regions", len(config["visual_source"]["plate"]["layer_plan"]) >= 5
          and len(config["visual_source"]["plate"]["animated_regions"]) >= 4, {"layers": config["visual_source"]["plate"]["layer_plan"], "regions": config["visual_source"]["plate"]["animated_regions"]})
    check("failure_and_compatibility_tests", failures["result"] == "PASS" and failures["passed"] == failures["total"] >= 10,
          {"passed": failures["passed"], "total": failures["total"]})
    outputs_ok, output_hashes = True, {}
    for relative, detail in manifest["outputs"].items():
        path = Path(detail["path"]); actual = sha256(path) if path.is_file() else None
        outputs_ok = outputs_ok and actual == detail["sha256"] and path.stat().st_size == detail["bytes"]
        output_hashes[relative] = actual
    check("proof_artifact_integrity", outputs_ok, output_hashes)
    probes = {name: probe(artifacts / name) for name in ("procedural/motion-proof.mp4", "hybrid/motion-proof.mp4", "comparison/side-by-side.mp4")}
    media_ok = all(value["codec"] == "h264" and value["duration"] == 4.0 and value["frames"] == 120 and value["fps"] == "30/1" and value["audio_streams"] == 0 for value in probes.values())
    media_ok = media_ok and probes["procedural/motion-proof.mp4"]["width"] == probes["hybrid/motion-proof.mp4"]["width"] == 768 \
        and probes["comparison/side-by-side.mp4"]["width"] == 1536
    check("matched_motion_proof_contract", media_ok, probes)
    decode_ok = True
    for relative in probes:
        process = subprocess.run(["ffmpeg", "-v", "error", "-i", str(artifacts / relative), "-f", "null", "-"], capture_output=True)
        decode_ok = decode_ok and process.returncode == 0
    check("full_decode", decode_ok, "all three proof videos decoded")
    logs = {mode: (artifacts / f"logs/godot-{mode}.log").read_text() for mode in ("procedural", "hybrid")}
    godot_ok = all("MF017_VISUAL_SOURCE_PROOF_OK" in value and "ERROR:" not in value and "SCRIPT ERROR:" not in value for value in logs.values())
    check("godot_hybrid_integration", godot_ok and all(manifest["godot_overlay"].values()), manifest["godot_overlay"])
    proc_static = np.asarray(Image.open(artifacts / "procedural/static-proof.png").convert("RGB"))
    hybrid_static = np.asarray(Image.open(artifacts / "hybrid/static-proof.png").convert("RGB"))
    proc_material, hybrid_material = material_metrics(proc_static), material_metrics(hybrid_static)
    material_ratios = {key: hybrid_material[key] / proc_material[key] for key in proc_material}
    material_pass = material_ratios["gradient_mean"] > 1.20 and material_ratios["laplacian_p90"] > 1.35 \
        and material_ratios["quantized_color_count"] > 1.80
    check("plate_material_richness", material_pass,
          {"procedural": proc_material, "hybrid": hybrid_material,
           "ratios": {key: round(value, 3) for key, value in material_ratios.items()}})
    hybrid_base = np.asarray(plate_image.convert("RGB").resize((768, 1152), Image.Resampling.LANCZOS)).astype(int)
    overlay_delta = np.abs(hybrid_static.astype(int) - hybrid_base)
    reactor_delta = float(overlay_delta[330:750, 440:650].mean()); changed_ratio = float(np.mean(np.any(overlay_delta > 8, axis=2)))
    check("local_light_and_hero_overlay_visible", reactor_delta > 6 and changed_ratio > .025,
          {"reactor_region_mean_delta": round(reactor_delta, 3), "changed_ratio": round(changed_ratio, 4)})
    motion = {}
    for mode in ("procedural", "hybrid"):
        first = video_frame(artifacts / f"{mode}/motion-proof.mp4", 0.1).astype(int)
        later = video_frame(artifacts / f"{mode}/motion-proof.mp4", 2.1).astype(int)
        delta = np.abs(first - later); motion[mode] = {"mean_delta": round(float(delta.mean()), 3), "changed_ratio": round(float(np.mean(np.any(delta > 7, axis=2))), 4)}
    check("meaningful_local_motion", all(value["mean_delta"] > 1.0 and value["changed_ratio"] > .01 for value in motion.values()), motion)
    zones = {zone["id"]: zone for zone in composition["zones"]}
    hierarchy = {}
    for mode, values in (("procedural", proc_static), ("hybrid", hybrid_static)):
        hero = region_mean(values, zones["hero_center_right"]); support = region_mean(values, zones["support_left"])
        hierarchy[mode] = {"hero_mean": round(hero, 3), "support_mean": round(support, 3), "ratio": round(hero / max(support, 1), 3)}
    check("mf016_hero_hierarchy_preserved", all(value["ratio"] > 1.1 for value in hierarchy.values()), hierarchy)
    check("source_status_fail_closed", manifest["source_status"] == "PRODUCTION_PLATE_PENDING" and manifest["human_review"] == "PENDING_HUMAN", {"source": manifest["source_status"], "human": manifest["human_review"]})
    check("no_full_trailer", manifest["full_trailer_rendered"] is False and all(value["duration"] <= 6 for value in probes.values()), manifest["full_trailer_rendered"])
    check("not_published", manifest["published"] is False, manifest["published"])
    result = "TECHNICAL_PASS" if all(value["status"] == "PASS" for value in checks.values()) else "FAIL"
    report = {"slice": "MF-017", "result": result, "source_status": "PRODUCTION_PLATE_PENDING", "release_ready": False,
              "human_review": "PENDING_HUMAN", "checks": checks, "metrics": {"materiality": {"procedural": proc_material, "hybrid": hybrid_material, "ratios": material_ratios}, "motion": motion, "hierarchy": hierarchy}, "published": False}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2)); return 0 if result == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
