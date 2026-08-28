#!/usr/bin/env python3
"""Render the deterministic MF-018A Godot-native pulp machine-room proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from composition_contract import validate_manifest


FONT = "/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Bold.otf"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def run_checked(command: list[str], log: Path, reject_engine_errors: bool = False) -> str:
    process = subprocess.run(command, capture_output=True, text=True)
    rendered = process.stdout + process.stderr
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(rendered)
    engine_error = reject_engine_errors and ("SCRIPT ERROR:" in rendered or "ERROR:" in rendered)
    if process.returncode or engine_error:
        raise RuntimeError(f"command failed ({process.returncode}); see {log}")
    return rendered


def approved_audio(root: Path, definition: dict) -> tuple[Path, dict, dict]:
    catalog = json.loads((root / definition["catalog"]).read_text())
    track = next((item for item in catalog["tracks"] if item["qualified_id"] == definition["qualified_id"]), None)
    if not track:
        raise ValueError("configured audio track is absent from catalog")
    cue = next((item for item in track.get("cue_regions", []) if item["id"] == definition["cue_region"]), None)
    source = root / track["source"]
    actual_hash = sha256(source) if source.is_file() else None
    if actual_hash != definition["source_sha256"] or actual_hash != track["integrity"]["sha256"]:
        raise ValueError("configured audio source hash changed")
    if track["approval"]["status"] != "APPROVED" or track["approval"].get("approved_sha256") != actual_hash:
        raise ValueError("audio track is not approved for its current hash")
    if not cue or cue["approval"]["status"] != "APPROVED" or cue["approval"].get("approved_sha256") != actual_hash:
        raise ValueError("audio cue is not approved for its current hash")
    if not (cue["usable_start"] <= definition["start_seconds"] < definition["end_seconds"] <= cue["usable_end"]):
        raise ValueError("audio excerpt escapes approved cue bounds")
    return source, track, cue


def measure_audio(media: Path) -> dict:
    process = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(media), "-vn", "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=8:print_format=json", "-f", "null", "-",
    ], capture_output=True, text=True)
    blocks = re.findall(r'\{\s*"input_i".*?\}', process.stderr, re.DOTALL)
    if process.returncode or not blocks:
        raise RuntimeError("unable to measure final audio")
    values = json.loads(blocks[-1])
    return {"integrated_lufs": float(values["input_i"]), "true_peak_db": float(values["input_tp"]),
            "loudness_range_lu": float(values["input_lra"])}


def make_contact_sheet(frames: list[Path], labels: list[str], output: Path) -> None:
    font = ImageFont.truetype(FONT, 19)
    thumb_size = (240, 360)
    canvas = Image.new("RGB", (768, 838), (7, 12, 11))
    draw = ImageDraw.Draw(canvas)
    for index, (frame, label) in enumerate(zip(frames, labels)):
        image = Image.open(frame).convert("RGB").resize(thumb_size, Image.Resampling.LANCZOS)
        x = 12 + (index % 3) * 252
        y = 70 + (index // 3) * 398
        canvas.paste(image, (x, y))
        timestamp, name = label.split(" ", 1)
        draw.text((x, y - 51), timestamp.upper(), font=font, fill=(230, 185, 5))
        draw.text((x, y - 28), name.upper(), font=font, fill=(224, 201, 139))
    canvas.save(output, optimize=True)


def make_static_comparison(hybrid: Path, native: Path, output: Path) -> None:
    left = Image.open(hybrid).convert("RGB").resize((384, 576), Image.Resampling.LANCZOS)
    right = Image.open(native).convert("RGB").resize((384, 576), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (768, 636), (7, 12, 11))
    canvas.paste(left, (0, 60)); canvas.paste(right, (384, 60))
    draw = ImageDraw.Draw(canvas); font = ImageFont.truetype(FONT, 28)
    draw.text((18, 17), "MF-017 HYBRID", font=font, fill=(224, 201, 139))
    draw.text((402, 17), "MF-018A NATIVE", font=font, fill=(230, 185, 5))
    canvas.save(output, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf018a-native-pulp-scene.json")
    parser.add_argument("--artifacts", default="artifacts/mf-018a")
    args = parser.parse_args()
    root = Path(args.project_root).resolve(); config_path = root / args.config; artifacts = root / args.artifacts
    if artifacts.exists():
        raise SystemExit(f"refusing to overwrite: {artifacts}")
    definition = json.loads(config_path.read_text())
    composition_path = root / definition["composition_manifest"]
    composition = json.loads(composition_path.read_text()); composition_result = validate_manifest(composition)
    if composition_result["result"] != "PASS":
        raise SystemExit("MF-018A semantic composition validation failed")
    reference = Path(definition["art_direction_reference"]["path"])
    if not reference.is_file() or sha256(reference) != definition["art_direction_reference"]["sha256"]:
        raise SystemExit("art-direction reference is missing or changed")
    hybrid = root / definition["comparison"]["hybrid_artifact"]
    if not hybrid.is_file() or sha256(hybrid) != definition["comparison"]["hybrid_sha256"]:
        raise SystemExit("MF-017 hybrid proof is missing or changed")
    music, track, cue = approved_audio(root, definition["audio"])
    for directory in (artifacts, artifacts / "representative-frames", artifacts / "static-keyframes",
                      artifacts / "comparison", artifacts / "validation", artifacts / "logs"):
        directory.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="mf018a-") as temporary_name:
        temporary = Path(temporary_name); frames_dir = temporary / "frames"; video_only = temporary / "video-only.mp4"
        godot_output = run_checked([
            "godot", "--headless", "--path", str(root / "godot"), "--script", "mf018a_native_pulp_scene.gd", "--",
            "--config", str(config_path), "--output", str(frames_dir),
        ], artifacts / "logs/godot-native.log", reject_engine_errors=True)
        if "MF018A_NATIVE_SCENE_OK" not in godot_output:
            raise RuntimeError("Godot completion marker missing")
        expected_frames = round(definition["video"]["duration_seconds"] * definition["video"]["fps"])
        rendered_frames = sorted(frames_dir.glob("frame-*.png"))
        if len(rendered_frames) != expected_frames:
            raise RuntimeError(f"expected {expected_frames} frames, found {len(rendered_frames)}")
        run_checked([
            "ffmpeg", "-y", "-v", "error", "-framerate", str(definition["video"]["fps"]),
            "-i", str(frames_dir / "frame-%04d.png"), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z",
            "-t", str(definition["video"]["duration_seconds"]), str(video_only),
        ], artifacts / "logs/video-encode.log")
        audio = definition["audio"]; fade_out_start = definition["video"]["duration_seconds"] - audio["fade_out_seconds"]
        audio_filter = (
            f"atrim=start={audio['start_seconds']}:end={audio['end_seconds']},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d={audio['fade_in_seconds']},afade=t=out:st={fade_out_start}:d={audio['fade_out_seconds']},"
            f"loudnorm=I={audio['target_lufs']}:TP={audio['true_peak_db']}:LRA=8,"
            f"volume={audio['post_normalization_gain_db']}dB"
        )
        final = artifacts / "godot-native-pulp-scene.mp4"
        run_checked([
            "ffmpeg", "-y", "-v", "error", "-i", str(video_only), "-i", str(music), "-filter_complex",
            f"[1:a]{audio_filter}[music]", "-map", "0:v:0", "-map", "[music]", "-t", str(definition["video"]["duration_seconds"]),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
            "-metadata", "creation_time=1970-01-01T00:00:00Z", str(final),
        ], artifacts / "logs/audio-mux.log")
        representative, labels = [], []
        for seconds, name in definition["representative_frames"]:
            source = frames_dir / f"frame-{min(expected_frames - 1, round(seconds * definition['video']['fps'])):04d}.png"
            target = artifacts / "representative-frames" / f"{name}.png"; shutil.copy2(source, target)
            representative.append(target); labels.append(f"{seconds:.1f}s {name}")
        for seconds, name in ((0.4, "dormant"), (3.5, "activation"), (9.5, "peak")):
            source = frames_dir / f"frame-{round(seconds * definition['video']['fps']):04d}.png"
            shutil.copy2(source, artifacts / "static-keyframes" / f"{name}.png")
    make_contact_sheet(representative, labels, artifacts / "representative-frames/contact-sheet.png")
    make_static_comparison(root / "artifacts/mf-017/hybrid/static-proof.png",
                           artifacts / "representative-frames/reactor-mid-activation.png",
                           artifacts / "comparison/hybrid-vs-native.png")
    run_checked([
        "ffmpeg", "-y", "-v", "error", "-ss", "4", "-t", "4", "-i", str(final), "-i", str(hybrid),
        "-filter_complex",
        f"[0:v]setpts=PTS-STARTPTS,drawtext=fontfile={FONT}:text=MF-018A NATIVE:x=24:y=24:fontsize=34:fontcolor=0xE6B905[v0];"
        f"[1:v]setpts=PTS-STARTPTS,drawtext=fontfile={FONT}:text=MF-017 HYBRID:x=24:y=24:fontsize=34:fontcolor=0xE0C98B[v1];"
        "[v1][v0]hstack=inputs=2[v]", "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", "4", str(artifacts / "comparison/hybrid-vs-native.mp4"),
    ], artifacts / "logs/comparison-encode.log")
    selection = {
        "track_id": track["id"], "qualified_id": track["qualified_id"], "track_path": track["source"],
        "track_sha256": sha256(music), "track_approval": track["approval"]["status"], "cue_id": cue["id"],
        "cue_approval": cue["approval"]["status"], "usable_start": cue["usable_start"], "usable_end": cue["usable_end"],
        "actual_start": definition["audio"]["start_seconds"], "actual_end": definition["audio"]["end_seconds"],
        "fade_in": definition["audio"]["fade_in_seconds"], "fade_out": definition["audio"]["fade_out_seconds"],
        "post_normalization_gain_db": definition["audio"]["post_normalization_gain_db"],
        "direction": definition["audio"]["direction"], "loudness": measure_audio(final), "result": "PASS",
    }
    write_json(artifacts / "validation/audio-selection.json", selection)
    output_paths = [final, artifacts / "representative-frames/contact-sheet.png",
                    artifacts / "comparison/hybrid-vs-native.png", artifacts / "comparison/hybrid-vs-native.mp4"]
    output_paths += representative + sorted((artifacts / "static-keyframes").glob("*.png"))
    outputs = {str(path.relative_to(artifacts)): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in output_paths}
    manifest = {
        "slice": "MF-018A", "mode": definition["mode"], "native_scene": True,
        "config": str(config_path), "config_sha256": sha256(config_path), "composition": str(composition_path),
        "composition_sha256": sha256(composition_path), "composition_machine_validation": composition_result,
        "composition_gate": composition["gate"]["state"], "composition_human_status": composition["approval"]["human_status"],
        "godot_script": "godot/mf018a_native_pulp_scene.gd", "godot_script_sha256": sha256(root / "godot/mf018a_native_pulp_scene.gd"),
        "seed": definition["seed"], "video": {**definition["video"], "frame_count": expected_frames}, "audio": selection,
        "comparison_baseline": {"path": str(hybrid), "sha256": sha256(hybrid)}, "outputs": outputs,
        "raw_frames_retained": False, "elapsed_ms": round((time.monotonic() - started) * 1000),
        "human_review": "PENDING_HUMAN", "release_ready": False, "published": False,
    }
    write_json(artifacts / "render-manifest.json", manifest)
    print(json.dumps(manifest, indent=2)); return 0


if __name__ == "__main__":
    sys.exit(main())
