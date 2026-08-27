#!/usr/bin/env python3
"""Independent fail-closed validation for the MF-014R4A position-only slice."""

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


R4_VIDEO_SHA256 = "5562e6d9217ce7bf467d05e4ef512f6273d2e93203a5b18a1b99ffe33136b233"
R4_CONFIG_SHA256 = "09e3b0b9a6610a6690fc2163f6911783912c242f73d0f62c4ba29269c1db3b44"
EXPECTED_AUDIO_SHA256 = "a14eeffb1caa7daf673c2561fcd95588a38b7919c92fd67a37df04fa81a85612"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(checks: dict, name: str, passed: bool, detail: object) -> None:
    checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}


def mask(size: tuple[int, int], definition: dict, spec: dict) -> np.ndarray:
    image = Image.new("L", size, 0)
    ImageDraw.Draw(image).multiline_text(
        (spec["position"][0] * size[0], spec["position"][1] * size[1]),
        "\n".join(spec["layout_lines"]), font=ImageFont.truetype(definition["font"], spec["font_size"]),
        fill=255, anchor="mm", align="center", spacing=spec.get("line_spacing", -2))
    return np.asarray(image)


def normalized_for_treatment(definition: dict) -> dict:
    copy = json.loads(json.dumps(definition))
    copy.pop("slice", None)
    copy.pop("prior_artifact", None)
    copy.pop("information_region", None)
    for spec in copy["elements"].values():
        spec.pop("position", None)
    return copy


def decoded_audio_hash(video: Path) -> tuple[str, str]:
    run = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a:0", "-f", "s16le",
                          "-acodec", "pcm_s16le", "-"], capture_output=True)
    return hashlib.sha256(run.stdout).hexdigest(), run.stderr.decode(errors="replace")[-300:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf014r4a-rightward-reposition.json")
    parser.add_argument("--artifacts", default="artifacts/mf-014r4a")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, output = Path(args.project_root).resolve(), Path(args.output).resolve()
    config_path, artifacts = root / args.config, root / args.artifacts
    checks, metrics = {}, {}
    try:
        current = json.loads(config_path.read_text())
        prior_config_path = root / current["prior_artifact"]["config_path"]
        prior = json.loads(prior_config_path.read_text())
        prior_video = root / current["prior_artifact"]["path"]
        video = artifacts / "refined-final.mp4"
        manifest = json.loads((artifacts / "render-manifest.json").read_text())
        check(checks, "prior_r4_frozen", prior_video.is_file() and sha256(prior_video) == R4_VIDEO_SHA256,
              sha256(prior_video) if prior_video.is_file() else "missing")
        check(checks, "prior_r4_config_frozen", prior_config_path.is_file() and sha256(prior_config_path) == R4_CONFIG_SHA256,
              sha256(prior_config_path) if prior_config_path.is_file() else "missing")
        check(checks, "config_identity", manifest.get("config_sha256") == sha256(config_path), manifest.get("config_sha256"))
        check(checks, "treatment_timing_music_unchanged", normalized_for_treatment(current) == normalized_for_treatment(prior),
              "all non-placement configuration fields are identical")
        exact = (current["elements"]["tagline"]["text"] == "SUBJUGATE THE PLANET"
                 and current["elements"]["website"]["text"] == "rcblanzy.com/books/unknown-process")
        check(checks, "exact_text_preserved", exact,
              {key: value["text"] for key, value in current["elements"].items()})
        deltas = {}
        position_ok = True
        for key in current["elements"]:
            before = prior["elements"][key]["position"]
            after = current["elements"][key]["position"]
            delta = [after[0] - before[0], after[1] - before[1]]
            deltas[key] = {"before": before, "after": after, "normalized_delta": delta,
                           "pixel_delta": [round(delta[0] * 768, 3), round(delta[1] * 1154, 3)]}
            position_ok &= abs(delta[0] - .06) < 1e-9 and abs(delta[1]) < 1e-9
        check(checks, "measurable_rightward_translation", position_ok, deltas)
        check(checks, "lower_right_identity", current["information_region"][0] >= .35
              and current["information_region"][1] >= .68 and current["information_region"][3] <= .92,
              current["information_region"])

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
              and [video_stream.get("width"), video_stream.get("height")] == [768, 1154],
              {"codec": video_stream.get("codec_name"), "duration": duration, "fps": fps,
               "frames": video_stream.get("nb_frames"), "size": [video_stream.get("width"), video_stream.get("height")]})
        check(checks, "audio_stream", audio_stream.get("codec_name") == "aac", audio_stream.get("codec_name"))
        decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
        check(checks, "full_decode", decode.returncode == 0, "succeeded" if decode.returncode == 0 else decode.stderr[-300:])
        prior_audio_hash, prior_audio_error = decoded_audio_hash(prior_video)
        current_audio_hash, current_audio_error = decoded_audio_hash(video)
        check(checks, "audio_bit_exact", prior_audio_hash == current_audio_hash == EXPECTED_AUDIO_SHA256,
              {"prior_pcm_sha256": prior_audio_hash, "current_pcm_sha256": current_audio_hash,
               "errors": [prior_audio_error, current_audio_error]})
        check(checks, "final_hold_preserved", manifest.get("final_hold_seconds") == 2.5,
              manifest.get("final_hold_seconds"))

        names = ("idle", "main-circuit-burn", "title-peak", "title-residual", "information-cold",
                 "tagline-igniting", "tagline-peak", "url-heating", "final-information", "final-composition")
        frames = {name: artifacts / "representative-frames" / f"{name}.png" for name in names}
        evidence = [artifacts / "before-after-comparison/final-placement.png",
                    artifacts / "before-after-comparison/r4-vs-r4a.mp4",
                    artifacts / "mobile-readability/final-mobile.png"]
        check(checks, "evidence_complete", all(path.is_file() for path in frames.values()) and all(path.is_file() for path in evidence),
              {"representative_frames": len(frames), "comparison_files": [str(path) for path in evidence[:2]]})
        if all(path.is_file() for path in frames.values()):
            final = np.asarray(Image.open(frames["final-composition"]).convert("RGB"), dtype=np.int16)
            prior_final = np.asarray(Image.open(root / "artifacts/mf-014r4/representative-frames/final-composition.png").convert("RGB"), dtype=np.int16)
            gray = np.asarray(Image.fromarray(final.astype(np.uint8)).convert("L"), dtype=np.float32)
            prior_title = np.asarray(Image.open(root / "artifacts/mf-014r4/representative-frames/title-peak.png").convert("RGB"))
            current_title = np.asarray(Image.open(frames["title-peak"]).convert("RGB"))
            title_roi = (slice(round(1154 * .235), round(1154 * .535)), slice(round(768 * .045), round(768 * .605)))
            check(checks, "title_sequence_preserved", np.array_equal(prior_title[title_roi], current_title[title_roi]),
                  {"pixel_identical_roi": [0.045, 0.235, 0.605, 0.535]})
            union = np.zeros((1154, 768), dtype=bool)
            for definition in (prior, current):
                for spec in definition["elements"].values():
                    raw = mask((768, 1154), definition, spec)
                    union |= np.asarray(Image.fromarray(raw).filter(ImageFilter.MaxFilter(61))) > 0
            check(checks, "unrelated_final_pixels_unchanged", np.array_equal(prior_final[~union], final[~union]),
                  {"excluded": "61-pixel expanded union of old and new information masks"})
            mobile = Image.open(evidence[2]).convert("L")
            mobile_gray = np.asarray(mobile, dtype=np.float32)
            for key, spec in current["elements"].items():
                raw = mask((768, 1154), current, spec)
                glyph = raw > 0
                ys, xs = np.where(glyph)
                ring = (np.asarray(Image.fromarray(raw).filter(ImageFilter.MaxFilter(15))) > 0) & ~glyph
                item = {"bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                        "right_margin_px": int(767 - xs.max()), "clipped": bool(xs.min() <= 0 or xs.max() >= 767),
                        "full_contrast": round(float(gray[glyph].mean() - gray[ring].mean()), 3),
                        "dark_glyph_ratio": round(float((gray[glyph] < 60).mean()), 5)}
                resized = Image.fromarray(raw).resize(mobile.size, Image.Resampling.LANCZOS)
                mobile_glyph = np.asarray(resized) > 80
                mobile_ring = (np.asarray(resized.filter(ImageFilter.MaxFilter(9))) > 5) & ~mobile_glyph
                my, _ = np.where(mobile_glyph)
                item.update({"mobile_height": int(my.max() - my.min() + 1),
                             "mobile_contrast": round(float(mobile_gray[mobile_glyph].mean() - mobile_gray[mobile_ring].mean()), 3),
                             "mobile_p95": round(float(np.percentile(mobile_gray[mobile_glyph], 95)), 3)})
                metrics[key] = item
                check(checks, f"{key}_visible_unobstructed", not item["clipped"] and item["right_margin_px"] >= 20
                      and item["dark_glyph_ratio"] == 0 and item["full_contrast"] > 30, item)
                check(checks, f"{key}_mobile_readable", item["mobile_height"] >= 20
                      and item["mobile_contrast"] > 30 and item["mobile_p95"] > 100, item)
        check(checks, "not_published", manifest.get("published") is False, manifest.get("published"))
        passed = all(value["status"] == "PASS" for value in checks.values())
        result = {"slice": "MF-014R4A", "checks": checks, "placement_and_readability_metrics": metrics,
                  "human_review": "PENDING_HUMAN", "published": False,
                  "result": "TECHNICAL_PASS" if passed else "FAIL"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result = {"slice": "MF-014R4A", "checks": checks, "placement_and_readability_metrics": metrics,
                  "errors": [str(error)], "human_review": "PENDING_HUMAN", "published": False, "result": "FAIL"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
