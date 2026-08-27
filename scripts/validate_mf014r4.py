#!/usr/bin/env python3
"""Independent, fail-closed validation for MF-014R4."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


R1_VIDEO_SHA256 = "83e69ab2751959280ff9140caa910c90d1848b0990ff05aacf4c20e24d42069a"
R1_CONFIG_SHA256 = "214908b1baca6101243ab9a65e1aa64048cb790b0f8fd7cd142134bbec6b73c7"
SOURCE_SHA256 = "d2c59e27382c206ac8d195955d92daa8151e433a26a8fbc23d0635da7e1285f7"
TRACK_SHA256 = "44a3b01e4039a7dab21170814cb75a6d662701182b548fab211f89e9922b8ecf"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(checks: dict, name: str, passed: bool, detail: object) -> None:
    checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def text_mask(size: tuple[int, int], font_path: str, spec: dict) -> np.ndarray:
    image = Image.new("L", size, 0)
    font = ImageFont.truetype(font_path, spec["font_size"])
    ImageDraw.Draw(image).multiline_text(
        (spec["position"][0] * size[0], spec["position"][1] * size[1]),
        "\n".join(spec["layout_lines"]), font=font, fill=255, anchor="mm", align="center",
        spacing=spec.get("line_spacing", -2))
    return np.asarray(image)


def luma(rgb: np.ndarray) -> np.ndarray:
    return np.asarray(Image.fromarray(rgb.astype(np.uint8)).convert("L"), dtype=np.float32)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf014r4-incandescent-information.json")
    parser.add_argument("--artifacts", default="artifacts/mf-014r4")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, output = Path(args.project_root).resolve(), Path(args.output).resolve()
    config_path, artifacts = root / args.config, root / args.artifacts
    checks: dict = {}
    metrics: dict = {}
    try:
        definition = json.loads(config_path.read_text())
        baseline_path = root / definition["baseline_config"]
        baseline = json.loads(baseline_path.read_text())
        manifest = json.loads((artifacts / "render-manifest.json").read_text())
        video = artifacts / "refined-final.mp4"
        r1_video = root / "artifacts/mf-014r1/refined-final.mp4"
        source = root / "artifacts/mf-014/source-reference.png"
        check(checks, "r1_video_frozen", r1_video.is_file() and sha256(r1_video) == R1_VIDEO_SHA256,
              sha256(r1_video) if r1_video.is_file() else "missing")
        check(checks, "r1_config_frozen", baseline_path.is_file() and sha256(baseline_path) == R1_CONFIG_SHA256,
              sha256(baseline_path) if baseline_path.is_file() else "missing")
        check(checks, "source_frozen", source.is_file() and sha256(source) == SOURCE_SHA256,
              sha256(source) if source.is_file() else "missing")
        check(checks, "config_identity", manifest.get("config_sha256") == sha256(config_path), manifest.get("config_sha256"))

        elements = definition["elements"]
        tagline, website = elements["tagline"], elements["website"]
        check(checks, "exact_information", tagline["text"] == "SUBJUGATE THE PLANET"
              and website["text"] == "rcblanzy.com/books/unknown-process"
              and "".join(tagline["layout_lines"]).replace(" ", "") == tagline["text"].replace(" ", "")
              and "".join(website["layout_lines"]) == website["text"],
              {"tagline": tagline["text"], "website": website["text"], "website_lines": website["layout_lines"]})
        region = definition["information_region"]
        check(checks, "lower_right_rail_safe", region[0] >= 0.30 and region[1] >= 0.68 and region[2] <= 0.635
              and region[3] <= 0.92 and all(region[0] <= item["position"][0] <= region[2] for item in elements.values()),
              {"region": region, "rail_boundary": 0.635, "positions": [item["position"] for item in elements.values()]})
        check(checks, "hierarchy_and_settle", 0.60 <= tagline["final_level"] <= 0.70
              and 0.50 <= website["final_level"] <= 0.65
              and tagline["peak_level"] > website["peak_level"]
              and tagline["final_level"] > website["final_level"],
              {"tagline": [tagline["peak_level"], tagline["final_level"]],
               "website": [website["peak_level"], website["final_level"]]})
        check(checks, "controlled_combustion", 0.3 <= tagline["flame_intensity"] <= 0.8
              and 0 <= website["flame_intensity"] < tagline["flame_intensity"]
              and tagline["ember_count"] <= 6 and website["ember_count"] <= 3,
              {key: {"flame": value["flame_intensity"], "embers": value["ember_count"]} for key, value in elements.items()})
        route = definition["thermal_route"]
        baseline_points = [point for path in baseline["paths"] for point in path["points"]]
        check(checks, "route_connected", route["points"][0] in baseline_points and len(route["points"]) <= 4,
              {"start": route["points"][0], "point_count": len(route["points"])})
        tagline_end = tagline["heat_start"] + tagline["heat_travel_duration"] + tagline["peak_hold_duration"] + tagline["settle_duration"]
        website_end = website["heat_start"] + website["heat_travel_duration"] + website["peak_hold_duration"] + website["settle_duration"]
        hold = definition["duration_seconds"] - definition["final_hold_start"]
        check(checks, "thermal_timing", route["start"] < tagline["heat_start"] < website["heat_start"]
              and tagline["direction"] == website["direction"] == "right_to_left"
              and max(tagline_end, website_end) <= definition["final_hold_start"] + 0.001 and 2.0 <= hold <= 3.0,
              {"route_start": route["start"], "tagline_start": tagline["heat_start"], "website_start": website["heat_start"],
               "settle_ends": [tagline_end, website_end], "final_hold_seconds": hold})

        probe_run = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
                                   capture_output=True, text=True)
        probe = json.loads(probe_run.stdout) if probe_run.returncode == 0 else {}
        streams = probe.get("streams", [])
        video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
        audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})
        duration = float(probe.get("format", {}).get("duration", 0) or 0)
        try:
            fps = float(Fraction(video_stream.get("avg_frame_rate", "0/1")))
        except (ValueError, ZeroDivisionError):
            fps = 0
        check(checks, "video_contract", video_stream.get("codec_name") == "h264" and 16.99 <= duration <= 17.01
              and 29.9 <= fps <= 30.1 and int(video_stream.get("nb_frames", 0)) == 510
              and int(video_stream.get("width", 0)) == 768 and int(video_stream.get("height", 0)) == 1154,
              {"codec": video_stream.get("codec_name"), "duration": duration, "fps": fps,
               "frames": video_stream.get("nb_frames"), "size": [video_stream.get("width"), video_stream.get("height")]})
        check(checks, "audio_stream", audio_stream.get("codec_name") == "aac", {"codec": audio_stream.get("codec_name")})
        decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
        check(checks, "full_decode", decode.returncode == 0, "succeeded" if decode.returncode == 0 else decode.stderr[-300:])
        music = manifest.get("music", {})
        loudness = music.get("loudness", {})
        check(checks, "approved_music_preserved", music.get("track_id") == "cold_concrete_anatomy"
              and music.get("region_id") == "revelation_a" and music.get("track_sha256") == TRACK_SHA256
              and music.get("actual_start") == 5.0 and music.get("actual_end") == 22.0 <= music.get("usable_end", 0), music)
        check(checks, "audio_levels", -17 <= loudness.get("integrated_lufs", 99) <= -15
              and loudness.get("true_peak_db", 99) <= -1, loudness)

        names = ("idle", "main-circuit-burn", "title-peak", "title-residual", "information-cold",
                 "tagline-igniting", "tagline-peak", "url-heating", "final-information", "final-composition")
        frames = {name: artifacts / "representative-frames" / f"{name}.png" for name in names}
        mobile_files = [artifacts / "mobile-readability/final-mobile.png", artifacts / "mobile-readability/information-block-full.png",
                        artifacts / "mobile-readability/information-block-mobile-3x.png"]
        comparison = artifacts / "motion-evidence/mf014r1-vs-mf014r4.mp4"
        check(checks, "evidence_complete", all(path.is_file() for path in frames.values())
              and all(path.is_file() for path in mobile_files) and comparison.is_file(),
              {"representative_frames": len(frames), "mobile_files": len(mobile_files), "comparison": str(comparison)})
        if all(path.is_file() for path in frames.values()):
            arrays = {name: np.asarray(Image.open(path).convert("RGB"), dtype=np.int16) for name, path in frames.items()}
            height, width = arrays["final-composition"].shape[:2]
            r1_peak = np.asarray(Image.open(root / "artifacts/mf-014r1/representative-frames/title-peak.png").convert("RGB"))
            r1_settled = np.asarray(Image.open(root / "artifacts/mf-014r1/representative-frames/title-settled.png").convert("RGB"), dtype=np.int16)
            title_roi = (slice(round(height * .235), round(height * .535)), slice(round(width * .045), round(width * .605)))
            check(checks, "r1_title_peak_pixel_preserved", np.array_equal(arrays["title-peak"][title_roi], r1_peak[title_roi]),
                  {"roi": [0.045, 0.235, 0.605, 0.535]})
            gray = luma(arrays["final-composition"])
            cold = arrays["information-cold"]
            xgrid = np.indices((height, width))[1]
            for key, spec in elements.items():
                raw = text_mask((width, height), definition["font"], spec)
                mask = raw > 0
                dilated = np.asarray(Image.fromarray(raw).filter(ImageFilter.MaxFilter(15))) > 0
                ring = dilated & ~mask
                ys, xs = np.where(mask)
                delta = np.abs(arrays["final-composition"] - cold).max(axis=2)
                cold_delta = np.abs(cold - r1_settled).max(axis=2)
                item = {"bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                        "glyph_height": int(ys.max() - ys.min() + 1),
                        "changed_glyph_ratio": round(float((delta[mask] > 8).mean()), 5),
                        "cold_engraving_delta": round(float(cold_delta[mask].mean()), 3),
                        "cold_engraving_changed_ratio": round(float((cold_delta[mask] > 3).mean()), 5),
                        "local_luma_contrast": round(float(gray[mask].mean() - gray[ring].mean()), 3),
                        "glyph_luma_p95": round(float(np.percentile(gray[mask], 95)), 3)}
                sample = "tagline-igniting" if key == "tagline" else "url-heating"
                heat_delta = np.abs(arrays[sample] - cold).max(axis=2)
                midpoint = (xs.min() + xs.max()) // 2
                left = float(heat_delta[mask & (xgrid < midpoint)].mean())
                right = float(heat_delta[mask & (xgrid >= midpoint)].mean())
                item["thermal_left_delta"] = round(left, 3)
                item["thermal_right_delta"] = round(right, 3)
                item["right_to_left_ratio"] = round(right / max(left, .001), 3)
                metrics[key] = item
                check(checks, f"{key}_full_size_readable", item["changed_glyph_ratio"] > .9
                      and item["local_luma_contrast"] > 30 and item["glyph_height"] >= 45, item)
                check(checks, f"{key}_physically_engraved", 4 < item["cold_engraving_delta"] < 12
                      and item["cold_engraving_changed_ratio"] > .5, {
                          "cold_engraving_delta": item["cold_engraving_delta"],
                          "cold_engraving_changed_ratio": item["cold_engraving_changed_ratio"]})
                check(checks, f"{key}_right_to_left_reveal", right > left * 1.35 and right > 40, {"left": left, "right": right})
            title_gray = gray[title_roi]
            info_roi = gray[round(height * region[1]):round(height * region[3]), round(width * region[0]):round(width * region[2])]
            title_bright = int((title_gray > 110).sum())
            info_bright = int((info_roi > 110).sum())
            check(checks, "title_remains_hero", title_bright > info_bright * 3.0,
                  {"title_pixels_over_110": title_bright, "information_pixels_over_110": info_bright,
                   "dominance_ratio": round(title_bright / max(info_bright, 1), 3)})
            warm_halo = {}
            for key, spec in elements.items():
                raw = text_mask((width, height), definition["font"], spec)
                outer = np.asarray(Image.fromarray(raw).filter(ImageFilter.MaxFilter(31))) > 0
                inner = np.asarray(Image.fromarray(raw).filter(ImageFilter.MaxFilter(7))) > 0
                ring = outer & ~inner
                signed = arrays["final-composition"] - cold
                warm_halo[key] = {"red_gain": round(float(signed[:, :, 0][ring].mean()), 3),
                                  "red_over_blue_ratio": round(float((signed[:, :, 0][ring] > signed[:, :, 2][ring] + 2).mean()), 5)}
            check(checks, "local_warm_illumination", warm_halo["tagline"]["red_gain"] > 3
                  and warm_halo["tagline"]["red_over_blue_ratio"] > .55
                  and warm_halo["website"]["red_gain"] > 1, warm_halo)
            flame_mask = text_mask((width, height), definition["font"], tagline) > 0
            ys, xs = np.where(flame_mask)
            band = np.zeros(flame_mask.shape, dtype=bool)
            # Leave a four-pixel gap so the measurement samples airborne flame
            # and local light, not the incandescent glyph edge itself.
            band[max(0, ys.min() - 18):max(0, ys.min() - 4), xs.min():xs.max() + 1] = True
            flame_delta = np.abs(arrays["tagline-peak"] - cold).max(axis=2)
            flame_ratio = float((flame_delta[band] > 8).mean())
            check(checks, "controlled_flame_visible", .05 < flame_ratio < .4, {"changed_ratio_above_tagline": round(flame_ratio, 5)})
        if mobile_files[0].is_file():
            mobile = Image.open(mobile_files[0]).convert("L")
            mobile_gray = np.asarray(mobile, dtype=np.float32)
            for key, spec in elements.items():
                raw = Image.fromarray(text_mask((768, 1154), definition["font"], spec)).resize(mobile.size, Image.Resampling.LANCZOS)
                mask = np.asarray(raw) > 80
                ring = (np.asarray(raw.filter(ImageFilter.MaxFilter(9))) > 5) & ~mask
                ys, _ = np.where(mask)
                item = {"glyph_height": int(ys.max() - ys.min() + 1),
                        "local_luma_contrast": round(float(mobile_gray[mask].mean() - mobile_gray[ring].mean()), 3),
                        "glyph_luma_p95": round(float(np.percentile(mobile_gray[mask], 95)), 3)}
                metrics[f"{key}_mobile"] = item
                check(checks, f"{key}_mobile_readable", item["glyph_height"] >= 20
                      and item["local_luma_contrast"] > 30 and item["glyph_luma_p95"] > 100, item)
        check(checks, "not_published", manifest.get("published") is False, manifest.get("published"))
        passed = all(item["status"] == "PASS" for item in checks.values())
        result = {"slice": "MF-014R4", "checks": checks, "readability_and_material_metrics": metrics,
                  "human_review": "PENDING_HUMAN", "published": False,
                  "result": "TECHNICAL_PASS" if passed else "FAIL"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result = {"slice": "MF-014R4", "checks": checks, "readability_and_material_metrics": metrics,
                  "errors": [str(error)], "human_review": "PENDING_HUMAN", "published": False, "result": "FAIL"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
