#!/usr/bin/env python3
"""Independent fail-closed acceptance validation for MF-014R2."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


R1_VIDEO_SHA256 = "83e69ab2751959280ff9140caa910c90d1848b0990ff05aacf4c20e24d42069a"
R1_CONFIG_SHA256 = "214908b1baca6101243ab9a65e1aa64048cb790b0f8fd7cd142134bbec6b73c7"
SOURCE_SHA256 = "d2c59e27382c206ac8d195955d92daa8151e433a26a8fbc23d0635da7e1285f7"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(state: dict, name: str, passed: bool, detail: object) -> None:
    state[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def text_mask(size: tuple[int, int], spec: dict, font_path: str) -> np.ndarray:
    mask = Image.new("L", size, 0)
    font = ImageFont.truetype(font_path, spec["font_size"])
    ImageDraw.Draw(mask).text((spec["position"][0] * size[0], spec["position"][1] * size[1]),
                              spec["text"], font=font, fill=255, anchor="mm")
    return np.asarray(mask) > 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf014r2-etched-supporting-text.json")
    parser.add_argument("--artifacts", default="artifacts/mf-014r2")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, output = Path(args.project_root).resolve(), Path(args.output).resolve()
    config_path, artifacts = root / args.config, root / args.artifacts
    checks: dict = {}
    readability: dict = {}
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
        support = definition["supporting_text"]
        check(checks, "tagline_exact", support["tagline"]["text"] == "SUBJUGATE THE PLANET", support["tagline"]["text"])
        check(checks, "website_exact", support["website"]["text"] == "rcblanzy.com/books/unknown-process", support["website"]["text"])
        check(checks, "font_assets", all(Path(path).is_file() for path in definition["font_assets"].values()), definition["font_assets"])
        title_settle_end = (baseline["visual"]["title_heat_start"] + baseline["visual"]["title_heat_rise_duration"]
                            + baseline["visual"]["title_peak_hold_duration"] + baseline["visual"]["title_settle_duration"])
        tag_end = support["tagline"]["reveal_start"] + support["tagline"]["reveal_duration"]
        site_end = support["website"]["reveal_start"] + support["website"]["reveal_duration"]
        check(checks, "supporting_reveal_order", support["tagline"]["reveal_start"] >= title_settle_end
              and support["website"]["reveal_start"] > tag_end and site_end <= definition["final_hold_start"] + 0.001,
              {"title_settle_end": title_settle_end, "tagline": [support["tagline"]["reveal_start"], tag_end],
               "website": [support["website"]["reveal_start"], site_end]})
        hold = definition["duration_seconds"] - definition["final_hold_start"]
        check(checks, "final_reading_hold", hold >= 2.0, hold)
        check(checks, "supporting_hierarchy_config", support["tagline"]["font_size"] > support["website"]["font_size"]
              and support["tagline"]["supporting_brightness"] > support["website"]["supporting_brightness"],
              {"tagline_size": support["tagline"]["font_size"], "website_size": support["website"]["font_size"],
               "tagline_brightness": support["tagline"]["supporting_brightness"], "website_brightness": support["website"]["supporting_brightness"]})
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
        check(checks, "video_contract", video_stream.get("codec_name") == "h264" and 14.99 <= duration <= 15.01
              and 29.9 <= fps <= 30.1 and int(video_stream.get("nb_frames", 0)) == 450,
              {"codec": video_stream.get("codec_name"), "duration": duration, "fps": fps, "frames": video_stream.get("nb_frames")})
        check(checks, "audio_stream", audio_stream.get("codec_name") == "aac", {"codec": audio_stream.get("codec_name"), "sample_rate": audio_stream.get("sample_rate")})
        decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
        check(checks, "audio_video_decode", decode.returncode == 0, "full decode succeeded" if decode.returncode == 0 else decode.stderr[-300:])
        music = manifest.get("music", {})
        check(checks, "music_direction_preserved", music.get("track_id") == baseline["music"]["track_id"]
              and music.get("region_id") == baseline["music"]["cue_region_id"] and music.get("actual_start") == baseline["music"]["source_start"],
              {"track": music.get("track_id"), "region": music.get("region_id"), "start": music.get("actual_start")})
        check(checks, "music_extension_bounded", music.get("actual_end") == 20.0 and music.get("usable_start") <= music.get("actual_start")
              < music.get("actual_end") <= music.get("usable_end"),
              {"actual": [music.get("actual_start"), music.get("actual_end")], "usable": [music.get("usable_start"), music.get("usable_end")]})
        loudness = music.get("loudness", {})
        check(checks, "audio_loudness", -17.0 <= loudness.get("integrated_lufs", 99) <= -15.0 and loudness.get("true_peak_db", 99) <= -1.0, loudness)
        names = ("idle", "active-incoming", "title-peak", "title-settled", "tagline-revealed", "website-revealed", "final")
        frames = {name: artifacts / "representative-frames" / f"{name}.png" for name in names}
        check(checks, "evidence_frames", all(path.is_file() for path in frames.values()), [str(path) for path in frames.values()])
        if all(path.is_file() for path in frames.values()):
            arrays = {name: np.asarray(Image.open(path).convert("RGB"), dtype=np.int16) for name, path in frames.items()}
            r1_peak = np.asarray(Image.open(root / "artifacts/mf-014r1/representative-frames/title-peak.png").convert("RGB"), dtype=np.int16)
            check(checks, "title_peak_pixel_preserved", np.array_equal(arrays["title-peak"], r1_peak), {"shape": list(r1_peak.shape)})
            final, settled = arrays["final"], arrays["title-settled"]
            height, width = final.shape[:2]
            gray = np.asarray(Image.fromarray(final.astype(np.uint8)).convert("L"), dtype=np.float32)
            delta = np.abs(final - settled).max(axis=2)
            for key in ("tagline", "website"):
                mask = text_mask((width, height), support[key], definition["font_assets"][key])
                ys, xs = np.where(mask)
                ring = np.zeros(mask.shape, dtype=bool)
                ring[max(0, ys.min() - 5):min(height, ys.max() + 6), max(0, xs.min() - 5):min(width, xs.max() + 6)] = True
                ring &= ~mask
                readability[key] = {
                    "glyph_pixels": int(mask.sum()), "mean_absolute_delta": round(float(delta[mask].mean()), 3),
                    "changed_glyph_ratio": round(float((delta[mask] > 8).mean()), 5),
                    "local_luma_contrast": round(abs(float(gray[mask].mean() - gray[ring].mean())), 3),
                    "glyph_luma_p95": round(float(np.percentile(gray[mask], 95)), 3),
                }
            check(checks, "tagline_readability", readability["tagline"]["changed_glyph_ratio"] > 0.80
                  and readability["tagline"]["local_luma_contrast"] > 10.0, readability["tagline"])
            check(checks, "website_readability", readability["website"]["changed_glyph_ratio"] > 0.75
                  and readability["website"]["local_luma_contrast"] > 12.0, readability["website"])
            title_roi = gray[round(height * 0.235):round(height * 0.535), round(width * 0.045):round(width * 0.605)]
            title_p95 = float(np.percentile(title_roi, 95))
            support_p95 = max(readability["tagline"]["glyph_luma_p95"], readability["website"]["glyph_luma_p95"])
            check(checks, "title_visual_dominance", title_p95 > support_p95 + 15.0,
                  {"title_roi_luma_p95": round(title_p95, 3), "support_glyph_luma_p95": support_p95})
            changed_ratio = float((delta > 8).mean())
            check(checks, "bounded_added_coverage", changed_ratio < 0.03, round(changed_ratio, 5))
            site_revealed = arrays["website-revealed"]
            final_drift = float(np.abs(final - site_revealed).mean())
            check(checks, "final_state_stable", final_drift < 0.2, round(final_drift, 5))
        check(checks, "not_published", manifest.get("published") is False, manifest.get("published"))
        passed = all(item["status"] == "PASS" for item in checks.values())
        result = {"slice": "MF-014R2", "checks": checks, "readability": readability, "human_review": "PENDING_HUMAN",
                  "published": False, "result": "TECHNICAL_PASS" if passed else "FAIL"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result = {"slice": "MF-014R2", "checks": checks, "readability": readability, "errors": [str(error)],
                  "human_review": "PENDING_HUMAN", "published": False, "result": "FAIL"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
