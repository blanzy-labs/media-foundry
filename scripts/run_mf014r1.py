#!/usr/bin/env python3
"""Render MF-014R1 and integrate an approved Unknown Process music cue."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from metal_circuit_burn_stage import BurnPath
from metal_circuit_burn_stage_r1 import RefinedBurnConfig, RefinedMetalCircuitBurnStage
from run_mf014 import encode, make_contact_sheet, sha256, write_json


BASELINE_VIDEO_SHA256 = "b6bb0ff0d6fee78ba3a7421706e790f8340862b8b2a785b3d149451fba3e318a"
BASELINE_SOURCE_SHA256 = "d2c59e27382c206ac8d195955d92daa8151e433a26a8fbc23d0635da7e1285f7"


def approved_music(root: Path, definition: dict) -> tuple[Path, dict, dict]:
    catalog_path = root / definition["catalog"]
    catalog = json.loads(catalog_path.read_text())
    track = next((item for item in catalog["tracks"] if item["project"] == definition["project"] and item["id"] == definition["track_id"]), None)
    if not track:
        raise ValueError("configured music track is absent from catalog")
    region = next((item for item in track.get("cue_regions", []) if item["id"] == definition["cue_region_id"]), None)
    source = root / track["source"]
    actual_hash = sha256(source) if source.is_file() else None
    if track["approval"]["status"] != "APPROVED" or track["approval"].get("approved_sha256") != actual_hash:
        raise ValueError("music track is not approved for its current source hash")
    if not region or region["approval"]["status"] != "APPROVED" or region["approval"].get("approved_sha256") != actual_hash:
        raise ValueError("music cue region is not approved for its current source hash")
    if not (region["usable_start"] <= definition["source_start"] < definition["source_end"] <= region["usable_end"]):
        raise ValueError("configured music selection escapes approved cue bounds")
    return source, track, region


def measure_audio(media: Path) -> dict:
    process = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(media), "-vn", "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-",
    ], capture_output=True, text=True)
    blocks = re.findall(r'\{\s*"input_i".*?\}', process.stderr, re.DOTALL)
    if process.returncode or not blocks:
        raise RuntimeError("unable to measure final audio")
    data = json.loads(blocks[-1])
    return {"integrated_lufs": float(data["input_i"]), "true_peak_db": float(data["input_tp"]), "loudness_range_lu": float(data["input_lra"])}


def mux_music(video: Path, music: Path, definition: dict, output: Path, log: Path) -> None:
    duration = definition["source_end"] - definition["source_start"]
    fade_out_start = duration - definition["fade_out"]
    audio_filter = (
        f"atrim=start={definition['source_start']}:end={definition['source_end']},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d={definition['fade_in']},afade=t=out:st={fade_out_start}:d={definition['fade_out']},"
        f"loudnorm=I={definition['target_integrated_lufs']}:TP={definition['target_true_peak_db']}:LRA=7,"
        f"volume={definition['post_normalization_gain_db']}dB"
    )
    process = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(music),
        "-filter_complex", f"[1:a]{audio_filter}[music]", "-map", "0:v:0", "-map", "[music]", "-t", str(duration),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        "-metadata", "creation_time=1970-01-01T00:00:00Z", str(output),
    ], capture_output=True, text=True)
    log.write_text(process.stdout + process.stderr)
    if process.returncode:
        raise RuntimeError(f"music mux failed ({process.returncode}); see {log}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf014r1-circuit-burn.json")
    parser.add_argument("--source", default="artifacts/mf-014/source-reference.png")
    parser.add_argument("--artifacts", default="artifacts/mf-014r1")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    config_path = (root / args.config).resolve()
    source = (root / args.source).resolve()
    artifacts = (root / args.artifacts).resolve()
    baseline_video = root / "artifacts/mf-014/final-test.mp4"
    if not baseline_video.is_file() or sha256(baseline_video) != BASELINE_VIDEO_SHA256:
        raise SystemExit("MF-014 baseline video is missing or changed")
    if not source.is_file() or sha256(source) != BASELINE_SOURCE_SHA256:
        raise SystemExit("MF-014 source plate is missing or changed")
    if artifacts.exists():
        raise SystemExit(f"refusing to overwrite: {artifacts}")
    definition = json.loads(config_path.read_text())
    visual, music_definition = definition["visual"], definition["music"]
    music, track, region = approved_music(root, music_definition)
    burn_span = visual["burn_end_seconds"] - visual["idle_seconds"]
    burn_speed = visual["burn_speed"]
    paths = []
    for item in definition["paths"]:
        effective_end = item["start_seconds"] + item["duration_seconds"] / burn_speed
        paths.append(BurnPath(tuple(tuple(point) for point in item["points"]),
                              (item["start_seconds"] - visual["idle_seconds"]) / burn_span,
                              (effective_end - visual["idle_seconds"]) / burn_span))
    stage_config = RefinedBurnConfig(
        width=visual["width"], duration_seconds=visual["duration_seconds"], fps=visual["fps"],
        idle_seconds=visual["idle_seconds"], burn_end_seconds=visual["burn_end_seconds"],
        scorch_intensity=visual["burn_intensity"], glow_intensity=visual["glow_intensity"],
        title_heat_start=visual["title_heat_start"], title_heat_rise_duration=visual["title_heat_rise_duration"],
        title_peak_level=visual["title_peak_level"], title_peak_hold_duration=visual["title_peak_hold_duration"],
        title_settle_level=visual["title_settle_level"], title_settle_duration=visual["title_settle_duration"],
    )
    stage = RefinedMetalCircuitBurnStage(source, stage_config, paths)
    for directory in (artifacts, artifacts / "representative-frames", artifacts / "motion-evidence", artifacts / "validation", artifacts / "logs"):
        directory.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    output = artifacts / "refined-final.mp4"
    with tempfile.TemporaryDirectory(prefix="mf014r1-") as temporary:
        video_only = Path(temporary) / "video-only.mp4"
        frame_hash = encode(stage, video_only, artifacts / "logs/video-encode.log")
        mux_music(video_only, music, music_definition, output, artifacts / "logs/music-mux.log")
    stamps = ((0.5, "idle"), (1.65, "first-entry"), (4.3, "multiple-incoming"), (6.35, "title-early-heat"),
              (8.65, "title-peak"), (10.65, "title-settled"), (11.97, "final"))
    frames = []
    for timestamp, name in stamps:
        path = artifacts / "representative-frames" / f"{name}.png"
        stage.render_frame(min(stage.frame_count - 1, round(timestamp * stage_config.fps))).save(path, optimize=True)
        frames.append(path)
    make_contact_sheet(frames, [name for _, name in stamps], artifacts / "motion-evidence/refined-sequence.png")
    audio = measure_audio(output)
    selection = {
        "contract": "mf010_music_selection_v1", "project": track["project"], "track_id": track["id"], "qualified_id": track["qualified_id"],
        "track_path": track["source"], "track_sha256": track["integrity"]["sha256"], "track_approval": track["approval"]["status"],
        "region_id": region["id"], "region_approval": region["approval"]["status"], "usable_start": region["usable_start"],
        "usable_end": region["usable_end"], "actual_start": music_definition["source_start"], "actual_end": music_definition["source_end"],
        "video_duration": visual["duration_seconds"], "fade_in": music_definition["fade_in"], "fade_out": music_definition["fade_out"],
        "post_normalization_gain_db": music_definition["post_normalization_gain_db"],
        "visual_peak_source_time": music_definition["source_start"] + visual["title_heat_start"] + visual["title_heat_rise_duration"],
        "loudness": audio, "result": "PASS",
    }
    write_json(artifacts / "validation/music-selection.json", selection)
    manifest = {
        "slice": "MF-014R1", "config": str(config_path), "config_sha256": sha256(config_path), "seed": definition["seed"],
        "baseline": {"video": str(baseline_video), "video_sha256": sha256(baseline_video), "source_sha256": sha256(source)},
        "output": {"path": str(output), "sha256": sha256(output), "bytes": output.stat().st_size},
        "video": {"duration_seconds": visual["duration_seconds"], "fps": visual["fps"], "frame_count": stage.frame_count,
                  "width": stage.size[0], "height": stage.size[1], "raw_frame_sequence_sha256": frame_hash},
        "paths": [{"id": item["id"], "origin": item["origin"], "start": item["points"][0], "destination": item["points"][-1],
                   "start_seconds": item["start_seconds"], "duration_seconds": item["duration_seconds"]} for item in definition["paths"]],
        "title": {"heat_start": visual["title_heat_start"], "rise_duration": visual["title_heat_rise_duration"],
                  "peak_level": visual["title_peak_level"], "peak_hold": visual["title_peak_hold_duration"],
                  "settle_level": visual["title_settle_level"], "settle_duration": visual["title_settle_duration"],
                  "residual_hold_start": visual["title_heat_start"] + visual["title_heat_rise_duration"] + visual["title_peak_hold_duration"] + visual["title_settle_duration"]},
        "music": selection, "representative_frames": [str(path) for path in frames],
        "motion_evidence": str(artifacts / "motion-evidence/refined-sequence.png"), "elapsed_ms": round((time.monotonic() - started) * 1000),
        "human_review": "PENDING_HUMAN", "published": False,
    }
    write_json(artifacts / "render-manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
