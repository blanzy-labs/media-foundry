#!/usr/bin/env python3
"""Render MF-014R2 with etched tagline and website over frozen MF-014R1."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from metal_circuit_burn_stage import BurnPath
from metal_circuit_burn_stage_r1 import RefinedBurnConfig
from metal_circuit_burn_stage_r2 import EtchedSupportingTextStage
from run_mf014 import encode, make_contact_sheet, sha256, write_json
from run_mf014r1 import approved_music, measure_audio, mux_music


R1_VIDEO_SHA256 = "83e69ab2751959280ff9140caa910c90d1848b0990ff05aacf4c20e24d42069a"
R1_CONFIG_SHA256 = "214908b1baca6101243ab9a65e1aa64048cb790b0f8fd7cd142134bbec6b73c7"
SOURCE_SHA256 = "d2c59e27382c206ac8d195955d92daa8151e433a26a8fbc23d0635da7e1285f7"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf014r2-etched-supporting-text.json")
    parser.add_argument("--artifacts", default="artifacts/mf-014r2")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    config_path, artifacts = root / args.config, root / args.artifacts
    r1_video = root / "artifacts/mf-014r1/refined-final.mp4"
    source = root / "artifacts/mf-014/source-reference.png"
    if not r1_video.is_file() or sha256(r1_video) != R1_VIDEO_SHA256:
        raise SystemExit("frozen MF-014R1 video is missing or changed")
    if not source.is_file() or sha256(source) != SOURCE_SHA256:
        raise SystemExit("source plate is missing or changed")
    if artifacts.exists():
        raise SystemExit(f"refusing to overwrite: {artifacts}")
    definition = json.loads(config_path.read_text())
    baseline_path = root / definition["baseline_config"]
    if sha256(baseline_path) != R1_CONFIG_SHA256:
        raise SystemExit("frozen MF-014R1 configuration changed")
    baseline = json.loads(baseline_path.read_text())
    visual = dict(baseline["visual"])
    visual["duration_seconds"] = definition["duration_seconds"]
    music_definition = dict(baseline["music"])
    music_definition.update(definition["music_override"])
    music, track, region = approved_music(root, music_definition)
    burn_span, speed = visual["burn_end_seconds"] - visual["idle_seconds"], visual["burn_speed"]
    paths = []
    for item in baseline["paths"]:
        end = item["start_seconds"] + item["duration_seconds"] / speed
        paths.append(BurnPath(tuple(tuple(point) for point in item["points"]),
                              (item["start_seconds"] - visual["idle_seconds"]) / burn_span,
                              (end - visual["idle_seconds"]) / burn_span))
    stage_config = RefinedBurnConfig(
        width=visual["width"], duration_seconds=visual["duration_seconds"], fps=visual["fps"],
        idle_seconds=visual["idle_seconds"], burn_end_seconds=visual["burn_end_seconds"],
        scorch_intensity=visual["burn_intensity"], glow_intensity=visual["glow_intensity"],
        title_heat_start=visual["title_heat_start"], title_heat_rise_duration=visual["title_heat_rise_duration"],
        title_peak_level=visual["title_peak_level"], title_peak_hold_duration=visual["title_peak_hold_duration"],
        title_settle_level=visual["title_settle_level"], title_settle_duration=visual["title_settle_duration"],
    )
    for font in definition["font_assets"].values():
        if not Path(font).is_file():
            raise SystemExit(f"configured font missing: {font}")
    stage = EtchedSupportingTextStage(source, stage_config, paths, definition["supporting_text"], definition["font_assets"])
    for directory in (artifacts, artifacts / "representative-frames", artifacts / "motion-evidence", artifacts / "validation", artifacts / "logs"):
        directory.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    output = artifacts / "refined-final.mp4"
    with tempfile.TemporaryDirectory(prefix="mf014r2-") as temporary:
        video_only = Path(temporary) / "video-only.mp4"
        frame_hash = encode(stage, video_only, artifacts / "logs/video-encode.log")
        mux_music(video_only, music, music_definition, output, artifacts / "logs/music-mux.log")
    stamps = ((0.5, "idle"), (4.3, "active-incoming"), (8.65, "title-peak"), (10.42, "title-settled"),
              (11.55, "tagline-revealed"), (12.85, "website-revealed"), (14.97, "final"))
    frames = []
    for timestamp, name in stamps:
        destination = artifacts / "representative-frames" / f"{name}.png"
        stage.render_frame(min(stage.frame_count - 1, round(timestamp * stage.config.fps))).save(destination, optimize=True)
        frames.append(destination)
    make_contact_sheet(frames, [name for _, name in stamps], artifacts / "motion-evidence/refined-sequence.png")
    audio = measure_audio(output)
    selection = {
        "contract": "mf010_music_selection_v1", "project": track["project"], "track_id": track["id"], "qualified_id": track["qualified_id"],
        "track_path": track["source"], "track_sha256": track["integrity"]["sha256"], "track_approval": track["approval"]["status"],
        "region_id": region["id"], "region_approval": region["approval"]["status"], "usable_start": region["usable_start"],
        "usable_end": region["usable_end"], "actual_start": music_definition["source_start"], "actual_end": music_definition["source_end"],
        "video_duration": visual["duration_seconds"], "fade_in": music_definition["fade_in"], "fade_out": music_definition["fade_out"],
        "post_normalization_gain_db": music_definition["post_normalization_gain_db"], "loudness": audio, "result": "PASS",
    }
    write_json(artifacts / "validation/music-selection.json", selection)
    manifest = {
        "slice": "MF-014R2", "config": str(config_path), "config_sha256": sha256(config_path),
        "baseline": {"video": str(r1_video), "video_sha256": sha256(r1_video), "config_sha256": sha256(baseline_path),
                     "source_sha256": sha256(source), "music": baseline["music"]},
        "output": {"path": str(output), "sha256": sha256(output), "bytes": output.stat().st_size},
        "video": {"duration_seconds": visual["duration_seconds"], "fps": visual["fps"], "frame_count": stage.frame_count,
                  "width": stage.size[0], "height": stage.size[1], "raw_frame_sequence_sha256": frame_hash},
        "supporting_text": definition["supporting_text"], "font_assets": definition["font_assets"],
        "title_timing": {key: visual[key] for key in ("title_heat_start", "title_heat_rise_duration", "title_peak_level",
                                                        "title_peak_hold_duration", "title_settle_level", "title_settle_duration")},
        "final_hold_start": definition["final_hold_start"], "final_hold_seconds": visual["duration_seconds"] - definition["final_hold_start"],
        "music": selection, "representative_frames": [str(path) for path in frames],
        "motion_evidence": str(artifacts / "motion-evidence/refined-sequence.png"), "elapsed_ms": round((time.monotonic() - started) * 1000),
        "human_review": "PENDING_HUMAN", "published": False,
    }
    write_json(artifacts / "render-manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
