#!/usr/bin/env python3
"""Independent validation of the MF-014R3 recessed-material thermal reveal."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


R1_VIDEO_SHA256 = "83e69ab2751959280ff9140caa910c90d1848b0990ff05aacf4c20e24d42069a"
R1_CONFIG_SHA256 = "214908b1baca6101243ab9a65e1aa64048cb790b0f8fd7cd142134bbec6b73c7"
SOURCE_SHA256 = "d2c59e27382c206ac8d195955d92daa8151e433a26a8fbc23d0635da7e1285f7"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(state: dict, name: str, passed: bool, detail: object) -> None:
    state[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def masks(size: tuple[int, int], spec: dict) -> tuple[np.ndarray, np.ndarray]:
    mask = Image.new("L", size, 0)
    font = ImageFont.truetype(spec["font"], spec["font_size"])
    display = "\n".join(spec.get("layout_lines", [spec["text"]]))
    ImageDraw.Draw(mask).multiline_text((spec["position"][0] * size[0], spec["position"][1] * size[1]),
                                        display, font=font, fill=255, anchor="mm", align="center", spacing=-2)
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(5)), mask.filter(ImageFilter.MinFilter(3)))
    return np.asarray(mask) > 0, np.asarray(edge) > 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf014r3-thermal-recessed-tagline.json")
    parser.add_argument("--artifacts", default="artifacts/mf-014r3")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, output = Path(args.project_root).resolve(), Path(args.output).resolve()
    config_path, artifacts = root / args.config, root / args.artifacts
    checks: dict = {}
    material: dict = {}
    try:
        definition = json.loads(config_path.read_text())
        baseline_path = root / definition["baseline_config"]
        baseline = json.loads(baseline_path.read_text())
        manifest = json.loads((artifacts / "render-manifest.json").read_text())
        r1_video, source = root / "artifacts/mf-014r1/refined-final.mp4", root / "artifacts/mf-014/source-reference.png"
        video = artifacts / "refined-final.mp4"
        check(checks, "r1_video_preserved", r1_video.is_file() and sha256(r1_video) == R1_VIDEO_SHA256,
              sha256(r1_video) if r1_video.is_file() else "missing")
        check(checks, "r1_config_preserved", baseline_path.is_file() and sha256(baseline_path) == R1_CONFIG_SHA256,
              sha256(baseline_path) if baseline_path.is_file() else "missing")
        check(checks, "source_plate_preserved", source.is_file() and sha256(source) == SOURCE_SHA256,
              sha256(source) if source.is_file() else "missing")
        check(checks, "config_identity", manifest.get("config_sha256") == sha256(config_path), manifest.get("config_sha256"))
        serialized = json.dumps({"config": definition, "manifest_tagline": manifest.get("tagline"), "url_included": manifest.get("url_included")}).lower()
        check(checks, "url_excluded", "rcblanzy.com" not in serialized and manifest.get("url_included") is False, manifest.get("url_included"))
        spec = definition["tagline"]
        check(checks, "tagline_exact", spec["text"] == "SUBJUGATE THE PLANET", spec["text"])
        x, y = spec["position"]
        bounds = spec["bounding_region"]
        check(checks, "lower_right_placement", x >= 0.62 and y >= 0.70 and bounds[0] >= 0.45 and bounds[2] <= 0.92 and bounds[3] < 0.9,
              {"position": spec["position"], "bounds": bounds})
        check(checks, "recessed_controls", spec["recessed_intensity"] > 0 and 0 < spec["cold_visibility"] < spec["final_settle_brightness"]
              < spec["active_heat_level"] < 1, {key: spec[key] for key in ("recessed_intensity", "cold_visibility", "active_heat_level", "final_settle_brightness")})
        title_settle_end = (baseline["visual"]["title_heat_start"] + baseline["visual"]["title_heat_rise_duration"]
                            + baseline["visual"]["title_peak_hold_duration"] + baseline["visual"]["title_settle_duration"])
        route = definition["thermal_route"]
        heat_end = spec["heat_reveal_start"] + spec["heat_propagation_duration"] + spec["heat_settle_duration"]
        check(checks, "post_title_thermal_causality", route["start"] >= title_settle_end and spec["heat_reveal_start"] < route["start"] + route["duration"]
              and spec["direction"] == "right_to_left", {"title_settle_end": title_settle_end, "route": [route["start"], route["start"] + route["duration"]],
                                                          "heat_start": spec["heat_reveal_start"], "direction": spec["direction"]})
        baseline_points = [point for path in baseline["paths"] for point in path["points"]]
        check(checks, "route_branches_from_existing_path", route["points"][0] in baseline_points and len(route["points"]) <= 4,
              {"route_start": route["points"][0], "point_count": len(route["points"])})
        hold = definition["duration_seconds"] - definition["final_hold_start"]
        check(checks, "settle_and_final_hold", heat_end <= definition["final_hold_start"] + 0.001 and hold >= 1.5,
              {"heat_settle_end": heat_end, "hold_start": definition["final_hold_start"], "hold_seconds": hold})
        probe_process = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], capture_output=True, text=True)
        probe = json.loads(probe_process.stdout) if probe_process.returncode == 0 else {}
        streams = probe.get("streams", [])
        video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
        audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})
        duration = float(probe.get("format", {}).get("duration", 0.0) or 0.0)
        try:
            fps = float(Fraction(video_stream.get("avg_frame_rate", "0/1")))
        except (ValueError, ZeroDivisionError):
            fps = 0.0
        check(checks, "video_contract", video_stream.get("codec_name") == "h264" and 15.49 <= duration <= 15.51 and 29.9 <= fps <= 30.1
              and int(video_stream.get("nb_frames", 0)) == 465,
              {"codec": video_stream.get("codec_name"), "duration": duration, "fps": fps, "frames": video_stream.get("nb_frames")})
        check(checks, "audio_stream", audio_stream.get("codec_name") == "aac", {"codec": audio_stream.get("codec_name"), "sample_rate": audio_stream.get("sample_rate")})
        decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
        check(checks, "audio_video_decode", decode.returncode == 0, "full decode succeeded" if decode.returncode == 0 else decode.stderr[-300:])
        music = manifest.get("music", {})
        check(checks, "music_direction_preserved", music.get("track_id") == baseline["music"]["track_id"]
              and music.get("region_id") == baseline["music"]["cue_region_id"] and music.get("actual_start") == baseline["music"]["source_start"],
              {"track": music.get("track_id"), "region": music.get("region_id"), "start": music.get("actual_start")})
        check(checks, "music_extension_bounded", music.get("actual_end") == 20.5 and music.get("actual_end") <= music.get("usable_end"),
              {"actual": [music.get("actual_start"), music.get("actual_end")], "usable": [music.get("usable_start"), music.get("usable_end")]})
        loudness = music.get("loudness", {})
        check(checks, "audio_loudness", -17.0 <= loudness.get("integrated_lufs", 99) <= -15.0 and loudness.get("true_peak_db", 99) <= -1.0, loudness)
        names = ("cold-plate", "active-incoming", "title-peak", "title-settled", "tagline-cold-detail", "tagline-thermal-reveal", "final")
        frames = {name: artifacts / "representative-frames" / f"{name}.png" for name in names}
        check(checks, "evidence_frames", all(path.is_file() for path in frames.values()), [str(path) for path in frames.values()])
        if all(path.is_file() for path in frames.values()):
            arrays = {name: np.asarray(Image.open(path).convert("RGB"), dtype=np.int16) for name, path in frames.items()}
            r1_idle = np.asarray(Image.open(root / "artifacts/mf-014r1/representative-frames/idle.png").convert("RGB"), dtype=np.int16)
            r1_peak = np.asarray(Image.open(root / "artifacts/mf-014r1/representative-frames/title-peak.png").convert("RGB"), dtype=np.int16)
            height, width = arrays["final"].shape[:2]
            mask, edge = masks((width, height), spec)
            cold_delta = np.abs(arrays["cold-plate"] - r1_idle).max(axis=2)
            material["cold"] = {"mean_glyph_delta": round(float(cold_delta[mask].mean()), 3),
                                "changed_glyph_ratio": round(float((cold_delta[mask] > 8).mean()), 5),
                                "full_frame_changed_ratio": round(float((cold_delta > 8).mean()), 5)}
            cold_gray = np.asarray(Image.fromarray(arrays["cold-plate"].astype(np.uint8)).convert("L"), dtype=np.int16)
            r1_gray = np.asarray(Image.fromarray(r1_idle.astype(np.uint8)).convert("L"), dtype=np.int16)
            signed_edge = cold_gray[edge] - r1_gray[edge]
            material["cold"]["edge_highlight_ratio"] = round(float((signed_edge > 0).mean()), 5)
            material["cold"]["edge_shadow_ratio"] = round(float((signed_edge < 0).mean()), 5)
            check(checks, "cold_recess_physically_present", 2.0 < material["cold"]["mean_glyph_delta"] < 10.0
                  and material["cold"]["full_frame_changed_ratio"] < 0.005
                  and material["cold"]["edge_highlight_ratio"] > 0.2 and material["cold"]["edge_shadow_ratio"] > 0.3, material["cold"])
            title_roi = (slice(round(height * 0.235), round(height * 0.535)), slice(round(width * 0.045), round(width * 0.605)))
            check(checks, "r1_title_peak_preserved", np.array_equal(arrays["title-peak"][title_roi], r1_peak[title_roi]), {"roi": "title"})
            heat_delta = np.abs(arrays["tagline-thermal-reveal"] - arrays["tagline-cold-detail"]).max(axis=2)
            xgrid = np.indices(mask.shape)[1]
            midpoint = (np.where(mask)[1].min() + np.where(mask)[1].max()) // 2
            left_heat = float(heat_delta[mask & (xgrid < midpoint)].mean())
            right_heat = float(heat_delta[mask & (xgrid >= midpoint)].mean())
            material["thermal"] = {"left_half_delta": round(left_heat, 3), "right_half_delta": round(right_heat, 3),
                                   "right_to_left_ratio": round(right_heat / max(left_heat, 0.001), 3)}
            check(checks, "heat_driven_spatial_reveal", right_heat > left_heat * 2.0 and right_heat > 20.0, material["thermal"])
            final = arrays["final"]
            final_gray = np.asarray(Image.fromarray(final.astype(np.uint8)).convert("L"), dtype=np.float32)
            ys, xs = np.where(mask)
            ring = np.zeros(mask.shape, dtype=bool)
            ring[max(0, ys.min() - 6):min(height, ys.max() + 7), max(0, xs.min() - 6):min(width, xs.max() + 7)] = True
            ring &= ~mask
            final_delta = np.abs(final - arrays["tagline-cold-detail"]).max(axis=2)
            material["final"] = {"changed_glyph_ratio": round(float((final_delta[mask] > 8).mean()), 5),
                                 "local_luma_contrast": round(abs(float(final_gray[mask].mean() - final_gray[ring].mean())), 3),
                                 "glyph_luma_p95": round(float(np.percentile(final_gray[mask], 95)), 3)}
            check(checks, "settled_stamp_readable", material["final"]["changed_glyph_ratio"] > 0.65
                  and material["final"]["local_luma_contrast"] > 5.0, material["final"])
            title_p95 = float(np.percentile(final_gray[title_roi], 95))
            check(checks, "title_remains_dominant", title_p95 > material["final"]["glyph_luma_p95"] + 40.0,
                  {"title_luma_p95": round(title_p95, 3), "tagline_luma_p95": material["final"]["glyph_luma_p95"]})
            added_delta = np.abs(final - arrays["title-settled"]).max(axis=2)
            check(checks, "bounded_added_coverage", float((added_delta > 8).mean()) < 0.01, round(float((added_delta > 8).mean()), 5))
        check(checks, "not_published", manifest.get("published") is False, manifest.get("published"))
        passed = all(item["status"] == "PASS" for item in checks.values())
        result = {"slice": "MF-014R3", "checks": checks, "material_metrics": material, "human_review": "PENDING_HUMAN",
                  "published": False, "result": "TECHNICAL_PASS" if passed else "FAIL"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result = {"slice": "MF-014R3", "checks": checks, "material_metrics": material, "errors": [str(error)],
                  "human_review": "PENDING_HUMAN", "published": False, "result": "FAIL"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
