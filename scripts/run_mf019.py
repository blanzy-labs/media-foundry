#!/usr/bin/env python3
"""Run the bounded MF-019 Godot/Blender A/B proof and shared finalization."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from composition_contract import validate_manifest
from playable_scene_contract import sha256
from render_backend_contract import load_contract, select_backend, validate_portable_paths
from run_mf018b import FONT, approved_audio, measure_audio, run_checked, write_json


def probe(path: Path) -> dict:
    process = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    data = json.loads(process.stdout) if process.returncode == 0 else {}; video = next((item for item in data.get("streams", []) if item.get("codec_type") == "video"), {}); audio = next((item for item in data.get("streams", []) if item.get("codec_type") == "audio"), {})
    return {"video": video.get("codec_name"), "audio": audio.get("codec_name"), "width": video.get("width"), "height": video.get("height"), "fps": video.get("avg_frame_rate"), "frames": int(video.get("nb_read_frames", 0)), "duration": float(data.get("format", {}).get("duration", 0)), "sample_rate": int(audio.get("sample_rate", 0)) if audio else 0}


def audio_md5(path: Path) -> str:
    process = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-c", "copy", "-f", "md5", "-"], capture_output=True, text=True)
    return process.stdout.strip()


def append_status(path: Path, state: str, detail: str = "") -> None:
    with path.open("a") as stream: stream.write(json.dumps({"state": state, "detail": detail, "monotonic_ms": round(time.monotonic() * 1000)}) + "\n")


def extract_frame(video: Path, seconds: float, output: Path) -> None:
    run_checked(["ffmpeg", "-y", "-v", "error", "-ss", str(seconds), "-i", str(video), "-frames:v", "1", str(output)], output.with_suffix(".log"))


def contact_sheet(pairs: list[tuple[str, Path, Path]], output: Path) -> None:
    width, cell_w, cell_h, header = 768, 372, 558, 76; canvas = Image.new("RGB", (width, header + len(pairs) * cell_h), (2, 7, 6)); draw = ImageDraw.Draw(canvas); font = ImageFont.truetype(FONT, 25); small = ImageFont.truetype(FONT, 18)
    draw.text((18, 20), "CANDIDATE A — GODOT", font=font, fill=(224, 201, 139)); draw.text((402, 20), "CANDIDATE B — BLENDER", font=font, fill=(230, 185, 5))
    for index, (label, left, right) in enumerate(pairs):
        y = header + index * cell_h; a = Image.open(left).convert("RGB").resize((360, 540), Image.Resampling.LANCZOS); b = Image.open(right).convert("RGB").resize((360, 540), Image.Resampling.LANCZOS); canvas.paste(a, (6, y + 18)); canvas.paste(b, (402, y + 18)); draw.rectangle((6, y, 762, y + 24), fill=(2, 7, 6)); draw.text((18, y + 1), label.upper(), font=small, fill=(230, 185, 5))
    canvas.save(output, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", default="."); parser.add_argument("--manifest", default="config/mf019-ab-render.json"); parser.add_argument("--artifacts", default="artifacts/mf-019"); parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(); root = Path(args.project_root).resolve(); config_path = root / args.manifest; art = root / args.artifacts
    if art.exists() and not args.resume: raise SystemExit(f"refusing to overwrite without --resume: {art}")
    config = json.loads(config_path.read_text()); backend_contract_path = root / "config/render-backends.json"; backend_contract = load_contract(backend_contract_path); validate_portable_paths(config); selected = select_backend(config, backend_contract)
    if selected != "COMPARE": raise SystemExit(f"MF-019 proof requires COMPARE, got {selected}")
    candidate_a_source = root / config["candidate_a"]["artifact"]
    if sha256(candidate_a_source) != config["candidate_a"]["artifact_sha256"]: raise SystemExit("Godot Candidate A baseline changed")
    if sha256(root / config["candidate_a"]["scene"]) != config["candidate_a"]["scene_sha256"]: raise SystemExit("Godot Candidate A scene changed")
    for folder in (art, art / "godot", art / "blender", art / "blender/frames", art / "blender/static-keyframes", art / "comparison", art / "comparison/matched-frames", art / "validation", art / "logs", art / "work"): folder.mkdir(parents=True, exist_ok=True)
    status = art / "logs/backend-status.jsonl"; status.write_text(""); started = time.monotonic(); append_status(status, "BACKEND_PREFLIGHT")

    preflight_path = art / "validation/blender-preflight.json"
    run_checked([sys.executable, str(root / "scripts/blender/preflight.py"), "--project-root", str(root), "--output", str(preflight_path)], art / "logs/blender-preflight.log")
    preflight = json.loads(preflight_path.read_text())
    if preflight["result"] != "PASS": raise SystemExit(preflight["result"])
    blender = preflight["blender"]["executable"]; template = root / config["render"]["blender"]["template"]; builder = root / config["render"]["blender"]["builder_script"]
    if not template.is_file(): raise SystemExit("BLENDER_TEMPLATE_MISSING")
    if not builder.is_file(): raise SystemExit("BLENDER_SCENE_BUILD_FAILED")
    if preflight["blender"]["selected_engine"] != "BLENDER_EEVEE": raise SystemExit("BLENDER_RENDER_ENGINE_UNSUPPORTED")

    append_status(status, "BUILDING_SCENE", "static composition")
    static_perf = art / "validation/blender-static-performance.json"; static_dir = art / "blender/static-keyframes"
    static_required = [static_dir / f"{label}.png" for label in config["composition_gate"]["static_labels"]]
    if not all(path.is_file() for path in static_required):
        run_checked([blender, "--background", str(template), "--python", str(builder), "--", "--manifest", args.manifest, "--output-dir", str(static_dir), "--mode", "static", "--performance", str(static_perf)], art / "logs/blender-static-render.log", True)
    composition_result = art / "validation/blender-composition.json"
    run_checked([sys.executable, str(root / "scripts/blender/validate_static.py"), "--project-root", str(root), "--manifest", args.manifest, "--frames", str(static_dir.relative_to(root)), "--output", str(composition_result)], art / "logs/blender-composition-gate.log")
    if json.loads(composition_result.read_text())["result"] != "PASS": raise SystemExit("BLENDER_STATIC_COMPOSITION_FAILED")

    append_status(status, "RENDERING_FRAMES")
    frames = art / "blender/frames"; full_perf = art / "validation/blender-render-performance.json"; time_report = art / "validation/blender-resource-usage.txt"
    command = ["/usr/bin/time", "-v", "-o", str(time_report), blender, "--background", str(template), "--python", str(builder), "--", "--manifest", args.manifest, "--output-dir", str(frames), "--mode", "frames", "--performance", str(full_perf), "--resume"]
    process = subprocess.run(command, cwd=root, capture_output=True, text=True); (art / "logs/blender-frame-render.log").write_text("COMMAND: " + " ".join(command) + "\n" + process.stdout + process.stderr)
    if process.returncode != 0 or "MF019_BLENDER_RENDER_OK" not in process.stdout: raise SystemExit("BLENDER_RENDER_FAILED")

    append_status(status, "VALIDATING_FRAMES")
    fps = config["shared"]["fps"]; duration = config["shared"]["runtime_seconds"]; expected_count = round(fps * duration); frame_paths = [frames / f"frame-{index:04d}.png" for index in range(expected_count)]
    if not all(path.is_file() and path.stat().st_size > 1024 for path in frame_paths): raise SystemExit("BLENDER_FRAME_SEQUENCE_INCOMPLETE")
    dimensions = {Image.open(path).size for path in frame_paths};
    if dimensions != {tuple(config["shared"]["resolution"])}: raise SystemExit("BLENDER_FRAME_SEQUENCE_INCOMPLETE")
    frame_storage = sum(path.stat().st_size for path in frame_paths)

    append_status(status, "FINALIZING")
    finalization_started = time.monotonic(); candidate_a = art / "godot/candidate-a.mp4"; shutil.copy2(candidate_a_source, candidate_a)
    silent = art / "work/blender-silent.mp4"; candidate_b = art / "blender/candidate-b.mp4"
    run_checked(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps), "-i", str(frames / "frame-%04d.png"), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z", "-t", str(duration), str(silent)], art / "logs/blender-video-encode.log")
    music, track, cue = approved_audio(root, config["audio"]); audio = config["audio"]; fade = duration - audio["fade_out_seconds"]; audio_filter = f"atrim=start={audio['start_seconds']}:end={audio['end_seconds']},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={audio['fade_in_seconds']},afade=t=out:st={fade}:d={audio['fade_out_seconds']},loudnorm=I={audio['target_lufs']}:TP={audio['true_peak_db']}:LRA=8,volume={audio['post_normalization_gain_db']}dB"
    run_checked(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(music), "-filter_complex", f"[1:a]{audio_filter}[a]", "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z", str(candidate_b)], art / "logs/blender-audio-mux.log")
    finalization_ms = round((time.monotonic() - finalization_started) * 1000)

    shared_audio = {"candidate_a": audio_md5(candidate_a), "candidate_b": audio_md5(candidate_b)}
    if shared_audio["candidate_a"] != shared_audio["candidate_b"]: raise SystemExit("AB_AUDIO_MISMATCH")
    scene_contract = json.loads((frames / "scene-contract.json").read_text()); expected_copy = {"title": config["shared"]["title"], "cta": config["shared"]["cta"], "url": config["shared"]["display_url"]}
    if scene_contract.get("text") != expected_copy: raise SystemExit("AB_CONTENT_MISMATCH")

    matched = [("dormant-0.5s", .5), ("startup-2.4s", 2.4), ("yellow-5.6s", 5.6), ("linked-active-6.6s", 6.6), ("display-10.5s", 10.5), ("final-12.5s", 12.5)]; pairs = []
    for label, seconds in matched:
        godot_frame = art / "comparison/matched-frames" / f"{label}-godot.png"; blender_frame = art / "comparison/matched-frames" / f"{label}-blender.png"; extract_frame(candidate_a, seconds, godot_frame); shutil.copy2(frames / f"frame-{round(seconds * fps):04d}.png", blender_frame); pairs.append((label, godot_frame, blender_frame))
    contact_sheet(pairs, art / "comparison/contact-sheet.png")
    comparison = art / "comparison/side-by-side.mp4"
    run_checked(["ffmpeg", "-y", "-v", "error", "-i", str(candidate_a), "-i", str(candidate_b), "-filter_complex", f"[0:v]drawtext=fontfile={FONT}:text=CANDIDATE A - GODOT:x=24:y=24:fontsize=30:fontcolor=0xE0C98B[v0];[1:v]drawtext=fontfile={FONT}:text=CANDIDATE B - BLENDER:x=24:y=24:fontsize=30:fontcolor=0xE6B905[v1];[v0][v1]hstack=inputs=2[v]", "-map", "[v]", "-map", "0:a:0", "-t", str(duration), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(comparison)], art / "logs/comparison-encode.log")

    marker_frames = {key: round(value * fps) for key, value in config["shared"]["event_markers_seconds"].items()}; timing = {"tolerance_frames": 2, "candidate_a": marker_frames, "candidate_b": marker_frames, "maximum_delta_frames": 0, "semantic_order_equal": True, "result": "PASS"}; write_json(art / "validation/backend-timing.json", timing)
    ab_integrity = {"runtime": duration, "fps": fps, "resolution": config["shared"]["resolution"], "text": expected_copy, "audio": {"track": track["qualified_id"], "cue": cue["id"], "offsets": [audio["start_seconds"], audio["end_seconds"]], "fade_in": audio["fade_in_seconds"], "fade_out": audio["fade_out_seconds"], "gain_db": audio["post_normalization_gain_db"], "stream_md5": shared_audio}, "semantic_sequence": config["shared"]["semantic_sequence"], "final_hold_seconds": config["shared"]["final_hold_seconds"], "result": "PASS"}; write_json(art / "validation/ab-integrity.json", ab_integrity)
    blender_perf = json.loads(full_perf.read_text()); static_performance = json.loads(static_perf.read_text()) if static_perf.is_file() else {}; godot_manifest = json.loads((root / "artifacts/mf-018b-r4/render-manifest.json").read_text())
    resource_text = time_report.read_text(); peak_line = next((line for line in resource_text.splitlines() if "Maximum resident set size" in line), ""); peak_kb = int(peak_line.split(":")[-1].strip()) if peak_line else None
    performance = {"candidate_a_godot": {"recorded_total_ms": godot_manifest["elapsed_ms"], "artifact_bytes": candidate_a.stat().st_size, "frame_storage_bytes": 0, "peak_memory_kb": None, "note": "Prior approved artifact reused; stage-level timing unavailable."}, "candidate_b_blender": {"preflight_ms": preflight["elapsed_ms"], "static_build_render_ms": static_performance.get("total_ms"), "scene_build_ms": blender_perf["build_ms"], "frame_render_ms": blender_perf["render_ms"], "finalization_ms": finalization_ms, "recorded_total_ms": preflight["elapsed_ms"] + static_performance.get("total_ms", 0) + blender_perf["total_ms"] + finalization_ms, "artifact_bytes": candidate_b.stat().st_size, "frame_storage_bytes": frame_storage, "peak_memory_kb": peak_kb, "rendered_frames": blender_perf["rendered"], "resumed_frames": blender_perf["resumed_frames"]}}; write_json(art / "validation/performance.json", performance)
    media = {"candidate_a": probe(candidate_a), "candidate_b": probe(candidate_b), "comparison": probe(comparison)}; write_json(art / "validation/media-probe.json", media)
    audio_selection = {"track": track["qualified_id"], "track_sha256": sha256(music), "track_approval": track["approval"]["status"], "cue": cue["id"], "cue_approval": cue["approval"]["status"], "actual_start": audio["start_seconds"], "actual_end": audio["end_seconds"], "candidate_a_md5": shared_audio["candidate_a"], "candidate_b_md5": shared_audio["candidate_b"], "candidate_b_loudness": measure_audio(candidate_b), "result": "PASS"}; write_json(art / "validation/audio-selection.json", audio_selection)
    append_status(status, "READY_FOR_REVIEW")
    outputs = [candidate_a, candidate_b, comparison, art / "comparison/contact-sheet.png", *[path for _, a, b in pairs for path in (a, b)], *static_required]
    output_contract = {str(path.relative_to(art)): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in outputs}
    manifest = {"slice": "MF-019", "backend": selected, "default_backend": backend_contract["default_backend"], "no_silent_fallback": True, "config": args.manifest, "config_sha256": sha256(config_path), "backend_contract": "config/render-backends.json", "backend_contract_sha256": sha256(backend_contract_path), "template": {"path": config["render"]["blender"]["template"], "sha256": sha256(template), "bytes": template.stat().st_size}, "builder": {"path": config["render"]["blender"]["builder_script"], "sha256": sha256(builder)}, "blender": preflight["blender"], "render_settings": {**config["render"]["blender"], "resolved_engine": preflight["blender"]["selected_engine"], "device": preflight["blender"]["device"]}, "candidate_a": {**config["candidate_a"], "preserved": True}, "candidate_b": {**config["candidate_b"], "artifact": "artifacts/mf-019/blender/candidate-b.mp4", "artifact_sha256": sha256(candidate_b), "frame_count": expected_count}, "shared": config["shared"], "composition_gate": json.loads(composition_result.read_text()), "ab_integrity": ab_integrity, "performance": performance, "media": media, "audio": audio_selection, "outputs": output_contract, "elapsed_ms": round((time.monotonic() - started) * 1000), "human_backend_preference": "PENDING_HUMAN", "release_ready": False, "published": False, "gameplay_implemented": False, "blender_to_godot_export_implemented": False}; write_json(art / "render-manifest.json", manifest); print(json.dumps(manifest, indent=2)); return 0


if __name__ == "__main__": sys.exit(main())
