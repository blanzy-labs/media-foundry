#!/usr/bin/env python3
"""Validate MF-003 media contracts and normalize selected MP4 clips to PNG frames."""

import argparse
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from PIL import Image, UnidentifiedImageError


IMAGE_EXTENSIONS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
PROVENANCE_TYPES = {"supplied", "generated", "project_asset", "captured", "public_domain", "licensed"}


def add(checks, name, passed, detail):
    checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def contained(outer, inner):
    return (
        inner[0] >= outer[0] and inner[1] >= outer[1]
        and inner[0] + inner[2] <= outer[0] + outer[2]
        and inner[1] + inner[3] <= outer[1] + outer[3]
    )


def intersects(first, second):
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def rect(value):
    return tuple(float(value[key]) for key in ("x", "y", "width", "height"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--grammar", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--normalized-dir")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    checks = {}
    metadata = {}
    normalized = {"status": "NOT_REQUIRED"}
    try:
        fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        grammar = json.loads(Path(args.grammar).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fixture, grammar = {}, {}
        add(checks, "contract_readable", False, str(error))
    else:
        add(checks, "contract_readable", True, fixture.get("id", ""))

    media = fixture.get("media")
    add(checks, "media_object", isinstance(media, dict), "explicit object required for MF-003 capability fixtures")
    if not isinstance(media, dict):
        return finish(args.output, fixture, checks, metadata, normalized)

    media_type = media.get("type")
    add(checks, "media_type", media_type in {"image", "screenshot", "video"}, str(media_type))
    slot = grammar.get("media_slot", {})
    add(checks, "fit_mode", media.get("fit") in slot.get("fit_modes", []), str(media.get("fit")))
    add(checks, "anchor", media.get("anchor") in slot.get("anchors", []), str(media.get("anchor")))
    motion = media.get("motion", "none")
    motion_ok = motion == "none" if media_type == "video" else motion in slot.get("image_motion", [])
    add(checks, "motion", motion_ok, str(motion))
    add(checks, "required_policy", isinstance(media.get("required"), bool), repr(media.get("required")))
    provenance = media.get("provenance", {})
    provenance_ok = isinstance(provenance, dict) and provenance.get("type") in PROVENANCE_TYPES and bool(str(provenance.get("description", "")).strip())
    add(checks, "provenance", provenance_ok, json.dumps(provenance, sort_keys=True))
    caption = media.get("caption", "")
    add(checks, "caption", isinstance(caption, str) and 0 < len(caption.strip()) <= 80, str(caption))
    try:
        panel = rect(slot["panel_rect"])
        safe = rect(slot["safe_rect"])
        slot_ok = safe[2] > 0 and safe[3] > 0 and contained(panel, safe)
    except (KeyError, TypeError, ValueError):
        slot_ok = False
        safe = ()
    add(checks, "media_safe_area", slot_ok, str(safe))
    if slot_ok:
        origin = slot.get("stage_origin", [])
        stage_ok = isinstance(origin, list) and len(origin) == 2
        if stage_ok:
            media_stage = (safe[0] + float(origin[0]), safe[1] + float(origin[1]), safe[2], safe[3])
            canvas_safe = grammar.get("canvas", {}).get("safe_area", {})
            mobile = (float(canvas_safe.get("left", 0)), float(canvas_safe.get("top", 0)), float(canvas_safe.get("right", 0)) - float(canvas_safe.get("left", 0)), float(canvas_safe.get("bottom", 0)) - float(canvas_safe.get("top", 0)))
            stage_ok = contained(mobile, media_stage)
            text_areas = grammar.get("typography", {}).get("safe_areas", {})
            for area_name in slot.get("collision_checks", []):
                area = text_areas.get(area_name, {})
                area_origin = area.get("stage_origin", [])
                if len(area_origin) != 2:
                    stage_ok = False
                    break
                area_rect = rect(area)
                text_stage = (area_rect[0] + float(area_origin[0]), area_rect[1] + float(area_origin[1]), area_rect[2], area_rect[3])
                if intersects(media_stage, text_stage):
                    stage_ok = False
                    break
        add(checks, "media_stage_collisions", stage_ok, "inside mobile safe area; no configured text-region overlap")

    project_root = Path(args.project_root).resolve()
    source_value = media.get("source")
    source = (project_root / source_value).resolve() if isinstance(source_value, str) and source_value else None
    source_in_project = bool(source and (source == project_root or project_root in source.parents))
    add(checks, "source_path", source_in_project, str(source_value))
    supported = bool(source and ((media_type in {"image", "screenshot"} and source.suffix.lower() in IMAGE_EXTENSIONS) or (media_type == "video" and source.suffix.lower() == ".mp4")))
    add(checks, "supported_format", supported, source.suffix.lower() if source else "missing")
    exists = bool(source and source.is_file() and source.stat().st_size > 0)
    if not exists and media.get("required") is False:
        add(checks, "source_exists", True, "optional source unavailable; deterministic fixture_visual fallback")
        normalized = {"status": "OPTIONAL_FALLBACK", "fallback": "fixture_visual"}
        return finish(args.output, fixture, checks, metadata, normalized)
    add(checks, "source_exists", exists, str(source) if source else "missing")
    if not exists or not supported:
        return finish(args.output, fixture, checks, metadata, normalized)

    if media_type in {"image", "screenshot"}:
        try:
            with Image.open(source) as image:
                image.verify()
            with Image.open(source) as image:
                width, height = image.size
                actual_format = image.format
        except (OSError, UnidentifiedImageError) as error:
            add(checks, "asset_readable", False, str(error))
        else:
            format_ok = actual_format == IMAGE_EXTENSIONS[source.suffix.lower()]
            dimensions_ok = 0 < width <= int(slot.get("maximum_source_width", 0)) and 0 < height <= int(slot.get("maximum_source_height", 0))
            add(checks, "asset_readable", format_ok, actual_format)
            add(checks, "dimensions", dimensions_ok, f"{width}x{height}")
            metadata = {"type": media_type, "format": actual_format, "width": width, "height": height, "source": str(source)}
    elif media_type == "video":
        proc = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)], capture_output=True, text=True)
        try:
            probe = json.loads(proc.stdout) if proc.returncode == 0 else {}
        except json.JSONDecodeError:
            probe = {}
        video = next((stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"), None)
        add(checks, "video_stream", video is not None, video.get("codec_name", "missing") if video else (proc.stderr.strip() or "missing"))
        duration = float(probe.get("format", {}).get("duration", 0) or 0)
        width = int(video.get("width", 0)) if video else 0
        height = int(video.get("height", 0)) if video else 0
        try:
            fps = float(Fraction(video.get("avg_frame_rate", "0/1"))) if video else 0
        except (ValueError, ZeroDivisionError):
            fps = 0
        add(checks, "video_dimensions", width > 0 and height > 0, f"{width}x{height}")
        add(checks, "video_frame_rate", fps > 0, f"{fps:.3f}")
        start = media.get("start_seconds")
        clip_duration = media.get("duration_seconds")
        timing_types = isinstance(start, (int, float)) and not isinstance(start, bool) and isinstance(clip_duration, (int, float)) and not isinstance(clip_duration, bool)
        start_ok = timing_types and 0 <= float(start) < duration
        duration_ok = timing_types and float(clip_duration) > 0 and float(start) + float(clip_duration) <= duration + 0.001
        add(checks, "start_offset", start_ok, f"start={start!r} source_duration={duration:.3f}")
        add(checks, "clip_duration", duration_ok, f"requested={clip_duration!r} available={max(0, duration-float(start or 0)):.3f}")
        add(checks, "muted", media.get("muted") is True, repr(media.get("muted")))
        metadata = {"type": "video", "format": "MP4", "codec": video.get("codec_name") if video else None, "width": width, "height": height, "frame_rate": fps, "source_duration": duration, "start_seconds": start, "duration_seconds": clip_duration, "source": str(source)}
        if all(item["status"] == "PASS" for item in checks.values()) and args.normalized_dir:
            output_dir = Path(args.normalized_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            expected = round(float(clip_duration) * int(slot["video_frame_rate"]))
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-i", str(source), "-an", "-vf", f"fps={int(slot['video_frame_rate'])}", "-frames:v", str(expected), "-start_number", "0", str(output_dir / "frame_%06d.png")]
            encoded = subprocess.run(command, capture_output=True, text=True)
            frames = sorted(output_dir.glob("frame_*.png"))
            normalized_ok = encoded.returncode == 0 and len(frames) == expected and all(path.stat().st_size > 0 for path in frames)
            add(checks, "normalization", normalized_ok, f"{len(frames)}/{expected} frames" if normalized_ok else encoded.stderr[-500:])
            normalized = {"status": "PASS" if normalized_ok else "FAIL", "frame_rate": int(slot["video_frame_rate"]), "frame_count": len(frames), "expected_frame_count": expected, "directory": str(output_dir)}
    return finish(args.output, fixture, checks, metadata, normalized)


def finish(output_path, fixture, checks, metadata, normalized):
    passed = bool(checks) and all(item["status"] == "PASS" for item in checks.values())
    failures = [{"code": "MEDIA_ASSET_FAILED", "stage": name, "reason": item["detail"]} for name, item in checks.items() if item["status"] == "FAIL"]
    result = {"slice": "MF-003", "fixture": fixture.get("id", "unknown"), "checks": checks, "asset": metadata, "normalization": normalized, "failures": failures, "result": "PASS" if passed else "FAIL"}
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
