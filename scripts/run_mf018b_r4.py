#!/usr/bin/env python3
"""Render the narrow MF-018B-R4 control-panel linework polish."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from composition_contract import validate_manifest
from playable_scene_contract import sha256, validate_package
from run_mf018b import FONT, approved_audio, measure_audio, run_checked, write_json
from run_mf018b_r3 import contact_sheet


def labeled_crop(source: Path, box: tuple[int, int, int, int], label: str, scale: float, output: Path) -> None:
    crop = Image.open(source).convert("RGB").crop(box)
    crop = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (crop.width, crop.height + 54), (3, 9, 8)); canvas.paste(crop, (0, 54))
    ImageDraw.Draw(canvas).text((16, 14), label.upper(), font=ImageFont.truetype(FONT, 22), fill=(230, 185, 5))
    canvas.save(output, optimize=True)


def side_by_side(left: Path, right: Path, box: tuple[int, int, int, int], output: Path, full_scene: bool = False) -> None:
    if full_scene:
        a = Image.open(left).convert("RGB").resize((384, 576), Image.Resampling.LANCZOS)
        b = Image.open(right).convert("RGB").resize((384, 576), Image.Resampling.LANCZOS)
    else:
        a = Image.open(left).convert("RGB").crop(box).resize((468, 891), Image.Resampling.LANCZOS)
        b = Image.open(right).convert("RGB").crop(box).resize((468, 891), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (a.width + b.width, a.height + 60), (3, 9, 8)); canvas.paste(a, (0, 60)); canvas.paste(b, (a.width, 60))
    draw = ImageDraw.Draw(canvas); font = ImageFont.truetype(FONT, 27)
    draw.text((18, 17), "MF-018B-R3", font=font, fill=(224, 201, 139)); draw.text((a.width + 18, 17), "MF-018B-R4", font=font, fill=(230, 185, 5))
    canvas.save(output, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", default="."); parser.add_argument("--config", default="config/mf018b-r4-outline-polish.json"); parser.add_argument("--artifacts", default="artifacts/mf-018b-r4")
    args = parser.parse_args(); root = Path(args.project_root).resolve(); config_path = root / args.config; art = root / args.artifacts
    if art.exists(): raise SystemExit(f"refusing to overwrite: {art}")
    config = json.loads(config_path.read_text()); baseline = config["baseline"]
    for key in ("artifact", "scene", "script", "config", "manifest", "evidence", "handoff"):
        if sha256(root / baseline[key]) != baseline[f"{key}_sha256"]: raise SystemExit(f"MF-018B-R3 baseline {key} changed")
    composition = validate_manifest(json.loads((root / config["composition_manifest"]).read_text())); handoff_path = root / config["handoff_manifest"]; handoff = validate_package(root, json.loads(handoff_path.read_text()))
    if composition["result"] != "PASS" or handoff["result"] != "PASS": raise SystemExit("preserved composition or handoff invalid")
    music, track, cue = approved_audio(root, config["audio"])
    for folder in (art, art / "representative-frames", art / "closeups", art / "comparison", art / "validation", art / "logs"): folder.mkdir(parents=True, exist_ok=True)

    started = time.monotonic(); fps = config["video"]["fps"]; duration = config["video"]["duration_seconds"]; frame_count = round(fps * duration)
    probe = run_checked(["godot", "--headless", "--path", str(root / "godot"), "--script", "mf018b_r4_contract_probe.gd"], art / "logs/base-scene-probe.log", True)
    if "MF018B_R4_PROBE_OK" not in probe: raise RuntimeError("R4 probe marker missing")
    with tempfile.TemporaryDirectory(prefix="mf018b-r4-") as temp_name:
        temp = Path(temp_name); frames = temp / "frames"; silent_video = temp / "video.mp4"
        render = run_checked(["godot", "--headless", "--path", str(root / "godot"), "--script", "mf018b_r4_render.gd", "--", "--config", str(config_path), "--output", str(frames)], art / "logs/godot-render.log", True)
        if "MF018B_R4_NATIVE_OK" not in render or len(list(frames.glob("frame-*.png"))) != frame_count: raise RuntimeError("R4 render incomplete")
        run_checked(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps), "-i", str(frames / "frame-%04d.png"), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z", "-t", str(duration), str(silent_video)], art / "logs/video-encode.log")
        audio = config["audio"]; fade = duration - audio["fade_out_seconds"]; audio_filter = f"atrim=start={audio['start_seconds']}:end={audio['end_seconds']},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={audio['fade_in_seconds']},afade=t=out:st={fade}:d={audio['fade_out_seconds']},loudnorm=I={audio['target_lufs']}:TP={audio['true_peak_db']}:LRA=8,volume={audio['post_normalization_gain_db']}dB"
        final = art / "final-test.mp4"
        run_checked(["ffmpeg", "-y", "-v", "error", "-i", str(silent_video), "-i", str(music), "-filter_complex", f"[1:a]{audio_filter}[a]", "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z", str(final)], art / "logs/audio-mux.log")
        representatives, labels = [], []
        for seconds, label in config["representative_frames"]:
            target = art / "representative-frames" / f"{label}.png"; shutil.copy2(frames / f"frame-{round(seconds * fps):04d}.png", target); representatives.append(target); labels.append(f"{seconds:.1f}s {label}")
        sources = {label: frames / f"frame-{round(seconds * fps):04d}.png" for seconds, label in config["closeups"]}
        labeled_crop(sources["cleaned-control-panel"], (20, 530, 280, 1025), "cleaned-control-panel", 1.8, art / "closeups/cleaned-control-panel.png")
        labeled_crop(sources["previously-problematic-left-edge"], (20, 545, 105, 1010), "problematic-left-edge-cleaned", 4.0, art / "closeups/previously-problematic-left-edge.png")
        labeled_crop(sources["startup-controls-preserved"], (40, 740, 245, 980), "startup-controls-preserved", 2.5, art / "closeups/startup-controls-preserved.png")
    contact_sheet(representatives, labels, art / "representative-frames/contact-sheet.png")
    r3_frame = root / "artifacts/mf-018b-r3/representative-frames/full-panel-active.png"; r4_frame = art / "representative-frames/clean-outline-active.png"
    side_by_side(r3_frame, r4_frame, (20, 530, 280, 1025), art / "comparison/r3-vs-r4-panel-closeup.png")
    side_by_side(root / "artifacts/mf-018b-r3/representative-frames/final-active-machine-with-cta.png", art / "representative-frames/final-active-machine.png", (0, 0, 768, 1152), art / "comparison/r3-vs-r4.png", True)
    run_checked(["ffmpeg", "-y", "-v", "error", "-t", "8", "-i", str(root / baseline["artifact"]), "-t", "8", "-i", str(final), "-filter_complex", f"[0:v]setpts=PTS-STARTPTS,drawtext=fontfile={FONT}:text=MF-018B-R3:x=24:y=24:fontsize=32:fontcolor=0xE0C98B[v0];[1:v]setpts=PTS-STARTPTS,drawtext=fontfile={FONT}:text=MF-018B-R4:x=24:y=24:fontsize=32:fontcolor=0xE6B905[v1];[v0][v1]hstack=inputs=2[v]", "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", "8", str(art / "comparison/r3-vs-r4.mp4")], art / "logs/comparison-encode.log")
    selection = {"track": track["qualified_id"], "track_sha256": sha256(music), "track_approval": track["approval"]["status"], "cue": cue["id"], "cue_approval": cue["approval"]["status"], "actual_start": audio["start_seconds"], "actual_end": audio["end_seconds"], "loudness": measure_audio(final), "event_markers": audio["event_markers"], "changed_from_r3": False, "result": "PASS"}
    write_json(art / "validation/audio-selection.json", selection); write_json(art / "validation/inherited-handoff-validation.json", handoff); write_json(art / "validation/composition-validation.json", composition)
    files = [final, art / "representative-frames/contact-sheet.png", art / "comparison/r3-vs-r4-panel-closeup.png", art / "comparison/r3-vs-r4.png", art / "comparison/r3-vs-r4.mp4"] + representatives + sorted((art / "closeups").glob("*.png"))
    outputs = {str(path.relative_to(art)): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in files}
    manifest = {"slice": "MF-018B-R4", "config": str(config_path), "config_sha256": sha256(config_path), "seed": config["seed"], "baseline": baseline, "scene": {"path": config["scene"], "sha256": sha256(root / config["scene"]), "standalone_probe": "PASS", "r1_driver_reused": True}, "inherited_handoff": {"path": config["handoff_manifest"], "sha256": sha256(handoff_path), "validation": "PASS", "interface_changed": False}, "outline_contract": config["outline_contract"], "preservation_contract": config["preservation_contract"], "video": {**config["video"], "frame_count": frame_count}, "audio": selection, "outputs": outputs, "elapsed_ms": round((time.monotonic() - started) * 1000), "human_review": "PENDING_HUMAN", "release_ready": False, "gameplay_implemented": False, "published": False}
    write_json(art / "render-manifest.json", manifest); print(json.dumps(manifest, indent=2)); return 0


if __name__ == "__main__": sys.exit(main())
