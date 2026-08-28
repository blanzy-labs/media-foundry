#!/usr/bin/env python3
"""Run the staged Blender-only MF-020 cinematic hero-shot production."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

from playable_scene_contract import sha256
from render_backend_contract import load_contract, select_backend, validate_portable_paths
from run_mf018b import FONT, approved_audio, measure_audio, run_checked, write_json
from run_mf019 import probe


def status(path: Path, state: str, detail: str = "") -> None:
    with path.open("a") as stream:
        stream.write(json.dumps({"state": state, "detail": detail, "monotonic_ms": round(time.monotonic() * 1000)}) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--manifest", default="config/mf020-cinematic-reactor.json")
    parser.add_argument("--artifacts", default="artifacts/mf-020")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    config_path = root / args.manifest
    art = root / args.artifacts
    if art.exists() and not args.resume:
        raise SystemExit(f"refusing to overwrite without --resume: {art}")
    config = json.loads(config_path.read_text())
    validate_portable_paths(config)
    backend_contract = load_contract(root / "config/render-backends.json")
    selected = select_backend(config, backend_contract)
    if selected != "BLENDER":
        raise SystemExit(f"MF-020 requires BLENDER, got {selected}")
    if config["render"]["fallback"]["allowed"]:
        raise SystemExit("SILENT_BACKEND_FALLBACK_FORBIDDEN")
    started = time.monotonic()
    for folder in ("blockout", "previews/detail", "previews/lighting", "previews/fx", "frames", "representative-stills", "validation", "logs", "work", "scene"):
        (art / folder).mkdir(parents=True, exist_ok=True)
    status_path = art / "logs/production-status.jsonl"
    status_path.write_text("")

    status(status_path, "BACKEND_PREFLIGHT")
    preflight_path = art / "validation/blender-preflight.json"
    run_checked([sys.executable, str(root / "scripts/blender/preflight.py"), "--project-root", str(root), "--slice", "MF-020", "--output", str(preflight_path)], art / "logs/blender-preflight.log")
    preflight = json.loads(preflight_path.read_text())
    if preflight["result"] != "PASS":
        raise SystemExit(preflight["result"])
    blender = preflight["blender"]["executable"]
    template = root / config["render"]["blender"]["template"]
    builder = root / config["render"]["blender"]["builder_script"]
    if not template.is_file() or not builder.is_file():
        raise SystemExit("BLENDER_SCENE_BUILD_FAILED")

    def render_stage(stage_name: str, output: Path, mode: str, performance: Path, scene_output: Path | None = None):
        command = [blender, "--background", str(template), "--python", str(builder), "--", "--manifest", args.manifest, "--output-dir", str(output), "--stage", stage_name, "--mode", mode, "--performance", str(performance)]
        if mode == "frames":
            command.append("--resume")
        if scene_output:
            command += ["--scene-output", str(scene_output)]
        text = run_checked(command, art / f"logs/{stage_name}-{mode}.log", True)
        if "MF020_BLENDER_RENDER_OK" not in text:
            raise SystemExit("BLENDER_RENDER_FAILED")

    status(status_path, "BLOCKOUT", "simple geometry and camera previs")
    render_stage("blockout", art / "blockout", "stills", art / "validation/blockout-performance.json")
    status(status_path, "BLOCKOUT_GATE")
    gate_path = art / "validation/blockout-gate.json"
    run_checked([sys.executable, str(root / "scripts/blender/validate_mf020_blockout.py"), "--project-root", str(root), "--manifest", args.manifest, "--frames", str((art / "blockout").relative_to(root)), "--output", str(gate_path)], art / "logs/blockout-gate.log")
    gate = json.loads(gate_path.read_text())
    if gate["result"] != "PASS" or not gate["detail_render_authorized"]:
        raise SystemExit("BLENDER_BLOCKOUT_GATE_FAILED")

    status(status_path, "DETAIL_PASS")
    render_stage("detail", art / "previews/detail", "stills", art / "validation/detail-performance.json")
    status(status_path, "LIGHTING_PASS")
    render_stage("lighting", art / "previews/lighting", "stills", art / "validation/lighting-performance.json")
    status(status_path, "ANIMATION_FX_PASS")
    render_stage("fx", art / "previews/fx", "stills", art / "validation/fx-performance.json")

    status(status_path, "FINAL_RENDER")
    scene_output = root / config["render"]["blender"]["scene_output"]
    full_perf = art / "validation/final-render-performance.json"
    time_report = art / "validation/final-render-resource-usage.txt"
    command = ["/usr/bin/time", "-v", "-o", str(time_report), blender, "--background", str(template), "--python", str(builder), "--", "--manifest", args.manifest, "--output-dir", str(art / "frames"), "--stage", "final", "--mode", "frames", "--performance", str(full_perf), "--resume", "--scene-output", str(scene_output)]
    process = subprocess.run(command, cwd=root, capture_output=True, text=True)
    (art / "logs/final-frames.log").write_text("COMMAND: " + " ".join(command) + "\n" + process.stdout + process.stderr)
    if process.returncode != 0 or "MF020_BLENDER_RENDER_OK" not in process.stdout:
        raise SystemExit("BLENDER_RENDER_FAILED")

    status(status_path, "VALIDATING_FRAMES")
    fps = config["shot"]["fps"]
    duration = config["shot"]["runtime_seconds"]
    expected = round(fps * duration)
    frames = [art / "frames" / f"frame-{index:04d}.png" for index in range(expected)]
    if len(list((art / "frames").glob("frame-*.png"))) != expected or not all(path.is_file() and path.stat().st_size > 1024 for path in frames):
        raise SystemExit("BLENDER_FRAME_SEQUENCE_INCOMPLETE")
    dimensions = {Image.open(path).size for path in frames}
    if dimensions != {tuple(config["shot"]["resolution"])}:
        raise SystemExit("BLENDER_FRAME_SEQUENCE_INCOMPLETE")
    frame_storage = sum(path.stat().st_size for path in frames)

    representative = [("dormant", .5), ("lever-locked", 2.3), ("pressure-release", 4.6), ("full-power", 7.3), ("final-hold", 9.4)]
    representative_paths = []
    for label, seconds in representative:
        source = art / "frames" / f"frame-{round(seconds * fps):04d}.png"
        target = art / "representative-stills" / f"{label}-{seconds:.1f}s.png"
        shutil.copy2(source, target)
        representative_paths.append(target)

    status(status_path, "FINALIZATION")
    finalization_started = time.monotonic()
    silent = art / "work/cinematic-silent.mp4"
    final = art / "final-test.mp4"
    finalization = config["finalization"]
    title = finalization["title"].replace("'", "\\'")
    video_filter = f"drawtext=fontfile={FONT}:text='{title}':x=(w-text_w)/2:y=h*0.875:fontsize=54:fontcolor=0xF3C75C:shadowcolor=black@0.8:shadowx=3:shadowy=3:enable='between(t,{finalization['title_start_seconds']},{finalization['title_end_seconds']})'"
    run_checked(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps), "-i", str(art / "frames/frame-%04d.png"), "-vf", video_filter, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z", "-t", str(duration), str(silent)], art / "logs/video-encode.log")
    music, track, cue = approved_audio(root, config["audio"])
    audio = config["audio"]
    fade_out_start = duration - audio["fade_out_seconds"]
    audio_filter = f"atrim=start={audio['start_seconds']}:end={audio['end_seconds']},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={audio['fade_in_seconds']},afade=t=out:st={fade_out_start}:d={audio['fade_out_seconds']},loudnorm=I={audio['target_lufs']}:TP={audio['true_peak_db']}:LRA=8,volume={audio['post_normalization_gain_db']}dB"
    run_checked(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(music), "-filter_complex", f"[1:a]{audio_filter}[a]", "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z", str(final)], art / "logs/audio-mux.log")
    finalization_ms = round((time.monotonic() - finalization_started) * 1000)
    media = probe(final)
    if media != {"video": "h264", "audio": "aac", "width": 768, "height": 1152, "fps": "30/1", "frames": 300, "duration": 10.0, "sample_rate": 48000}:
        raise SystemExit("FINALIZATION_VALIDATION_FAILED")
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"], capture_output=True)
    if decode.returncode != 0:
        raise SystemExit("FINAL_MEDIA_DECODE_FAILED")
    audio_evidence = {"track": track["qualified_id"], "track_sha256": sha256(music), "track_approval": track["approval"]["status"], "cue": cue["id"], "cue_approval": cue["approval"]["status"], "source_offsets_seconds": [audio["start_seconds"], audio["end_seconds"]], "fade_in_seconds": audio["fade_in_seconds"], "fade_out_seconds": audio["fade_out_seconds"], "post_normalization_gain_db": audio["post_normalization_gain_db"], "sfx_policy": audio["sfx_policy"], "loudness": measure_audio(final)}
    finalization_evidence = {"result": "PASS", "media": media, "full_decode": "PASS", "frame_count": expected, "frame_storage_bytes": frame_storage, "title": {"text": finalization["title"], "owner": finalization["title_owner"], "start_seconds": finalization["title_start_seconds"], "end_seconds": finalization["title_end_seconds"]}, "audio": audio_evidence, "elapsed_ms": finalization_ms}
    write_json(art / "validation/finalization.json", finalization_evidence)

    status(status_path, "READY_FOR_REVIEW")
    perf_files = {name: json.loads((art / f"validation/{name}-performance.json").read_text()) for name in ("blockout", "detail", "lighting", "fx")}
    final_perf = json.loads(full_perf.read_text())
    resource_text = time_report.read_text()
    peak_line = next((line for line in resource_text.splitlines() if "Maximum resident set size" in line), "")
    performance = {"preflight_ms": preflight["elapsed_ms"], "stages": perf_files, "final_render": final_perf, "finalization_ms": finalization_ms, "frame_storage_bytes": frame_storage, "artifact_bytes": final.stat().st_size, "peak_memory_kb": int(peak_line.split(":")[-1].strip()) if peak_line else None, "total_elapsed_ms": round((time.monotonic() - started) * 1000)}
    write_json(art / "validation/performance.json", performance)
    evidence_outputs = [*(art / "blockout").glob("*.png"), *(art / "previews/detail").glob("*.png"), *(art / "previews/lighting").glob("*.png"), *(art / "previews/fx").glob("*.png"), *representative_paths, final]
    outputs = {str(path.relative_to(art)): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in evidence_outputs}
    scene_contract = json.loads((art / "frames/scene-contract.json").read_text())
    manifest = {"slice": "MF-020", "result": "READY_FOR_TECHNICAL_VALIDATION", "backend": selected, "godot_dependency": False, "compare_mode": False, "config": args.manifest, "config_sha256": sha256(config_path), "template": {"path": config["render"]["blender"]["template"], "sha256": sha256(template)}, "builder": {"path": config["render"]["blender"]["builder_script"], "sha256": sha256(builder)}, "scene": {"path": config["render"]["blender"]["scene_output"], "sha256": sha256(scene_output), "bytes": scene_output.stat().st_size}, "blender": preflight["blender"], "shot": config["shot"], "stage_order": config["stages"]["order"], "blockout_gate": gate, "scene_contract": scene_contract, "render_settings": {**config["render"]["blender"], "resolved_engine": preflight["blender"]["selected_engine"], "device": preflight["blender"]["device"]}, "finalization": finalization_evidence, "performance": performance, "outputs": outputs, "human_review": "PENDING_HUMAN", "release_ready": False, "published": False, "gameplay_ready": False, "blender_to_godot_export": False}
    write_json(art / "render-manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
