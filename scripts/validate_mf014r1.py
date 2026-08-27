#!/usr/bin/env python3
"""Independent fail-closed validation for MF-014R1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image


BASELINE_VIDEO_SHA256 = "b6bb0ff0d6fee78ba3a7421706e790f8340862b8b2a785b3d149451fba3e318a"
BASELINE_SOURCE_SHA256 = "d2c59e27382c206ac8d195955d92daa8151e433a26a8fbc23d0635da7e1285f7"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(state: dict, name: str, passed: bool, detail: object) -> None:
    state[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf014r1-circuit-burn.json")
    parser.add_argument("--artifacts", default="artifacts/mf-014r1")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    config_path, artifacts, output = root / args.config, root / args.artifacts, root / args.output
    checks: dict = {}
    try:
        config = json.loads(config_path.read_text())
        visual, music_definition, paths = config["visual"], config["music"], config["paths"]
        manifest = json.loads((artifacts / "render-manifest.json").read_text())
        video = artifacts / "refined-final.mp4"
        baseline_video, source = root / "artifacts/mf-014/final-test.mp4", root / "artifacts/mf-014/source-reference.png"
        check(checks, "mf014_video_preserved", baseline_video.is_file() and sha256(baseline_video) == BASELINE_VIDEO_SHA256,
              sha256(baseline_video) if baseline_video.is_file() else "missing")
        check(checks, "source_plate_preserved", source.is_file() and sha256(source) == BASELINE_SOURCE_SHA256,
              sha256(source) if source.is_file() else "missing")
        check(checks, "config_identity", manifest.get("config_sha256") == sha256(config_path), manifest.get("config_sha256"))
        check(checks, "path_count", 4 <= len(paths) <= 7, len(paths))
        offscreen = []
        for path in paths:
            x, y = path["points"][0]
            offscreen.append(x < 0 or x > 1 or y < 0 or y > 1)
        check(checks, "all_origins_offscreen", all(offscreen), {path["id"]: state for path, state in zip(paths, offscreen)})
        destinations = {path["id"]: path["points"][-1] for path in paths}
        check(checks, "destinations_inside_title_region",
              all(0.15 <= point[0] <= 0.66 and 0.26 <= point[1] <= 0.56 for point in destinations.values()), destinations)
        starts = [path["start_seconds"] for path in paths]
        check(checks, "staggered_arrivals", len(set(starts)) >= 4 and starts == sorted(starts), starts)
        completions = [path["start_seconds"] + path["duration_seconds"] / visual["burn_speed"] for path in paths]
        check(checks, "burn_progression_completes", max(completions) <= visual["burn_end_seconds"] + 0.001, completions)
        peak_at = visual["title_heat_start"] + visual["title_heat_rise_duration"]
        peak_end = peak_at + visual["title_peak_hold_duration"]
        settle_end = peak_end + visual["title_settle_duration"]
        check(checks, "title_after_convergence", visual["title_heat_start"] <= max(completions) and peak_at > max(completions),
              {"heat_start": visual["title_heat_start"], "last_path_complete": max(completions), "peak_at": peak_at})
        check(checks, "title_peak_hold", 0.5 <= visual["title_peak_hold_duration"] <= 1.5, visual["title_peak_hold_duration"])
        ratio = visual["title_settle_level"] / visual["title_peak_level"]
        check(checks, "title_settle_level", 0.45 <= ratio <= 0.55, ratio)
        check(checks, "residual_hold_exists", settle_end < visual["duration_seconds"] - 0.5,
              {"settle_end": settle_end, "duration": visual["duration_seconds"], "hold_seconds": visual["duration_seconds"] - settle_end})
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
        check(checks, "video_contract", video_stream.get("codec_name") == "h264" and 11.99 <= duration <= 12.01 and 29.9 <= fps <= 30.1
              and int(video_stream.get("nb_frames", 0)) == 360,
              {"codec": video_stream.get("codec_name"), "duration": duration, "fps": fps, "frames": video_stream.get("nb_frames")})
        check(checks, "audio_stream", audio_stream.get("codec_name") == "aac", {"codec": audio_stream.get("codec_name"), "sample_rate": audio_stream.get("sample_rate")})
        decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
        check(checks, "audio_video_decode", decode.returncode == 0, "full decode succeeded" if decode.returncode == 0 else decode.stderr[-300:])
        catalog = json.loads((root / music_definition["catalog"]).read_text())
        track = next((item for item in catalog["tracks"] if item["project"] == music_definition["project"] and item["id"] == music_definition["track_id"]), {})
        region = next((item for item in track.get("cue_regions", []) if item["id"] == music_definition["cue_region_id"]), {})
        music_source = root / track.get("source", "missing")
        music_hash = sha256(music_source) if music_source.is_file() else None
        approved = (track.get("approval", {}).get("status") == "APPROVED" and track.get("approval", {}).get("approved_sha256") == music_hash
                    and region.get("approval", {}).get("status") == "APPROVED" and region.get("approval", {}).get("approved_sha256") == music_hash)
        check(checks, "approved_music_hash", approved, {"track": track.get("id"), "region": region.get("id"), "sha256": music_hash})
        check(checks, "approved_cue_bounds", bool(region) and region["usable_start"] <= music_definition["source_start"]
              < music_definition["source_end"] <= region["usable_end"],
              {"usable": [region.get("usable_start"), region.get("usable_end")], "actual": [music_definition["source_start"], music_definition["source_end"]]})
        loudness = manifest.get("music", {}).get("loudness", {})
        check(checks, "audio_loudness", -17.0 <= loudness.get("integrated_lufs", 99) <= -15.0 and loudness.get("true_peak_db", 99) <= -1.0, loudness)
        names = ("idle", "first-entry", "multiple-incoming", "title-early-heat", "title-peak", "title-settled", "final")
        frames = {name: artifacts / "representative-frames" / f"{name}.png" for name in names}
        check(checks, "evidence_frames", all(path.is_file() for path in frames.values()), [str(path) for path in frames.values()])
        if all(path.is_file() for path in frames.values()):
            arrays = {name: np.asarray(Image.open(path).convert("RGB"), dtype=np.int16) for name, path in frames.items()}
            idle = arrays["idle"]
            expected = Image.open(source).convert("RGB")
            expected_height = round(expected.height * idle.shape[1] / expected.width)
            if expected_height % 2:
                expected_height += 1
            expected_array = np.asarray(expected.resize((idle.shape[1], expected_height), Image.Resampling.LANCZOS), dtype=np.int16)
            check(checks, "idle_pixel_identity", np.array_equal(expected_array, idle), {"shape": list(idle.shape)})
            active_delta = np.abs(arrays["multiple-incoming"] - idle).max(axis=2)
            final_delta = np.abs(arrays["final"] - idle).max(axis=2)
            check(checks, "visible_multi_path_burn", float((active_delta > 8).mean()) > 0.012, round(float((active_delta > 8).mean()), 5))
            check(checks, "final_residual_visible", float((final_delta > 8).mean()) > 0.04, round(float((final_delta > 8).mean()), 5))
            height, width = idle.shape[:2]
            roi = (slice(round(height * 0.235), round(height * 0.535)), slice(round(width * 0.045), round(width * 0.605)))
            peak_red = float(arrays["title-peak"][roi][..., 0].mean())
            settled_red = float(arrays["title-settled"][roi][..., 0].mean())
            final_red = float(arrays["final"][roi][..., 0].mean())
            check(checks, "observed_peak_above_settle", peak_red > settled_red + 1.0,
                  {"peak_roi_red": round(peak_red, 3), "settled_roi_red": round(settled_red, 3)})
            check(checks, "residual_held_to_final", abs(final_red - settled_red) < 0.5,
                  {"settled_roi_red": round(settled_red, 3), "final_roi_red": round(final_red, 3)})
        check(checks, "not_published", manifest.get("published") is False, manifest.get("published"))
        passed = all(item["status"] == "PASS" for item in checks.values())
        result = {"slice": "MF-014R1", "checks": checks, "human_review": "PENDING_HUMAN", "published": False,
                  "result": "TECHNICAL_PASS" if passed else "FAIL"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result = {"slice": "MF-014R1", "checks": checks, "errors": [str(error)], "human_review": "PENDING_HUMAN",
                  "published": False, "result": "FAIL"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
