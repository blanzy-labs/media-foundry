#!/usr/bin/env python3
"""Deterministically propose advisory cue regions and review evidence."""

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import music_catalog


METHOD = "mf010_deterministic_energy_v1"
COLORS = {
    "ambient_a": (55, 137, 142, 58),
    "investigation_a": (89, 101, 190, 58),
    "pursuit_a": (222, 91, 55, 62),
    "revelation_a": (224, 146, 53, 62),
    "resolution_a": (67, 168, 105, 58),
}
PROFILES = {
    "ambient_a": {"length": 32, "mood_tags": ["ambient", "mystery", "reflective"], "use_cases": ["ambient_teaser", "excerpt"]},
    "investigation_a": {"length": 38, "mood_tags": ["investigation", "mystery", "paranoia"], "use_cases": ["classification", "direct_promo"]},
    "pursuit_a": {"length": 40, "mood_tags": ["pursuit", "tension", "escalation"], "use_cases": ["tracking", "direct_promo"]},
    "revelation_a": {"length": 44, "mood_tags": ["revelation", "discovery", "ominous"], "use_cases": ["biometric_reveal", "title_reveal"]},
    "resolution_a": {"length": 34, "mood_tags": ["resolution", "reflective"], "use_cases": ["cta", "excerpt"]},
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def decode(source, rate=8000):
    process = subprocess.run(["ffmpeg", "-v", "error", "-i", str(source), "-ac", "1", "-ar", str(rate),
                              "-f", "f32le", "pipe:1"], capture_output=True)
    if process.returncode:
        raise ValueError("AUDIO_ANALYSIS_DECODE_FAILED: " + process.stderr.decode(errors="replace"))
    values = np.frombuffer(process.stdout, dtype="<f4").astype(np.float64)
    if values.size < rate * 10:
        raise ValueError("AUDIO_ANALYSIS_TOO_SHORT")
    return values, rate


def profiles(samples, rate):
    seconds = samples.size // rate
    matrix = samples[:seconds * rate].reshape(seconds, rate)
    rms = np.sqrt(np.mean(matrix * matrix, axis=1) + 1e-12)
    rms_db = 20 * np.log10(np.maximum(rms, 1e-6))
    peak = np.max(np.abs(matrix), axis=1)
    transient = np.mean(np.abs(np.diff(matrix, axis=1)), axis=1)
    smooth = np.convolve(rms_db, np.ones(3) / 3, mode="same")
    return rms_db, peak, transient, smooth


def metrics(start, length, rms_db, transient):
    begin, end = int(start), min(len(rms_db), int(start + length))
    values = rms_db[begin:end]
    activity = transient[begin:end]
    quarter = max(1, len(values) // 4)
    delta = float(np.mean(values[-quarter:]) - np.mean(values[:quarter]))
    return float(np.mean(values)), float(np.std(values)), delta, float(np.mean(activity))


def choose_regions(duration, rms_db, transient, smooth):
    candidates = {}
    selected_ranges = []
    p33, p66 = np.percentile(rms_db, [33, 66])
    for region_id, profile in PROFILES.items():
        length = min(profile["length"], max(12, math.floor(duration - 10)))
        starts = list(range(5, max(6, math.floor(duration - length - 4)), 2)) or [0]
        scored = []
        for start in starts:
            mean, deviation, delta, activity = metrics(start, length, rms_db, transient)
            if region_id == "ambient_a": score = mean + activity * 120
            elif region_id == "investigation_a": score = deviation + abs(mean - float(np.median(rms_db))) * .25 + activity * 45
            elif region_id == "pursuit_a": score = -(mean + max(0, delta) * .65 + activity * 90)
            elif region_id == "revelation_a": score = -(delta * 1.25 + mean * .25)
            else: score = abs((start + length) - (duration - 3)) + deviation * .2
            for selected_start, selected_end in selected_ranges:
                overlap = max(0.0, min(start + length, selected_end) - max(start, selected_start))
                smaller = min(length, selected_end - selected_start)
                if smaller > 0 and overlap / smaller >= .78:
                    score += 1000.0
            scored.append((score, start, mean, deviation, delta, activity))
        _, start, mean, deviation, delta, activity = min(scored)
        end = min(duration, start + length)
        entry_range = range(int(start), min(int(end), int(start) + 8))
        exit_range = range(max(int(start), int(end) - 9), int(end))
        entry = min(entry_range, key=lambda index: abs(smooth[index] - smooth[max(0, index - 1)]) + transient[index] * 80)
        exit_point = min(exit_range, key=lambda index: abs(smooth[index] - smooth[max(0, index - 1)]) + transient[index] * 80)
        intensity = "rising" if delta > 2.0 else "falling" if delta < -2.0 else "high" if mean >= p66 else "low" if mean <= p33 else "medium"
        narration = "high" if mean <= p33 and activity <= np.percentile(transient, 50) else "low" if mean >= p66 or activity >= np.percentile(transient, 75) else "medium"
        confidence = "medium" if deviation < 5.5 else "low"
        note_kind = {
            "ambient_a": "Candidate lower-energy, comparatively sparse passage.",
            "investigation_a": "Candidate stable-energy passage with comparatively even density.",
            "pursuit_a": "Candidate higher-energy passage with sustained motion.",
            "revelation_a": "Candidate build/change passage selected from measured energy rise.",
            "resolution_a": "Candidate late-song passage with room for a fade or CTA transition.",
        }[region_id]
        candidates[region_id] = {
            "id": region_id, "usable_start": round(float(start), 3), "usable_end": round(float(end), 3),
            "preferred_entry": round(float(entry), 3), "preferred_exit": round(float(exit_point), 3),
            "mood_tags": profile["mood_tags"], "use_cases": profile["use_cases"],
            "narration_friendliness": narration, "intensity": intensity,
            "analysis": {"method": METHOD, "version": 1, "confidence": confidence,
                         "mean_rms_db": round(mean, 3), "energy_delta_db": round(delta, 3),
                         "transient_score": round(activity, 6), "notes": note_kind, "preview": ""},
            "human": {"notes": None, "edited": False},
            "approval": {"status": "PENDING_APPROVAL", "proposed_sha256": None, "approved_sha256": None,
                         "reviewed_at": None, "reviewer": None, "note": None},
            "notes": "Automatic analysis is advisory; human listening is authoritative."
        }
        selected_ranges.append((start, end))
    return candidates


def preview(root, source, track_id, region, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{track_id}__{region['id']}__preview.mp3"
    start = region["preferred_entry"] if region["preferred_entry"] is not None else region["usable_start"]
    duration = min(15.0, region["usable_end"] - start)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-i", str(source),
               "-t", str(duration), "-map", "0:a:0", "-map_metadata", "-1", "-c:a", "libmp3lame", "-q:a", "4",
               "-metadata", "creation_time=1970-01-01T00:00:00Z", str(path)]
    process = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if process.returncode:
        raise ValueError("PREVIEW_GENERATION_FAILED: " + process.stderr)
    return str(path.relative_to(root)), sha256(path), round(duration, 3)


def waveform(samples, rate, duration, regions, output):
    width, height = 1400, 320
    image = Image.new("RGB", (width, height), (7, 13, 17))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0)); overlay_draw = ImageDraw.Draw(overlay)
    for region in regions:
        x0 = round(region["usable_start"] / duration * width); x1 = round(region["usable_end"] / duration * width)
        overlay_draw.rectangle((x0, 0, x1, height), fill=COLORS[region["id"]])
        for value in [region["preferred_entry"], region["preferred_exit"]]:
            if value is not None:
                x = round(value / duration * width); overlay_draw.line((x, 0, x, height), fill=(235, 236, 220, 150), width=2)
        overlay_draw.text((x0 + 5, 8 + list(PROFILES).index(region["id"]) * 18), region["id"], fill=(238, 242, 232, 230))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    bucket = max(1, samples.size // width)
    trimmed = samples[:bucket * width].reshape(width, bucket)
    peaks = np.max(np.abs(trimmed), axis=1)
    center = height // 2
    for x, peak in enumerate(peaks):
        extent = max(1, round(float(peak) * (height * .43)))
        draw.line((x, center - extent, x, center + extent), fill=(83, 213, 194, 220))
    draw.line((0, center, width, center), fill=(196, 235, 223, 110), width=1)
    output.parent.mkdir(parents=True, exist_ok=True); image.convert("RGB").save(output)


def overlap_report(regions):
    pairs = []
    for index, first in enumerate(regions):
        for second in regions[index + 1:]:
            overlap = max(0.0, min(first["usable_end"], second["usable_end"]) - max(first["usable_start"], second["usable_start"]))
            if overlap > 0:
                smaller = min(first["usable_end"] - first["usable_start"], second["usable_end"] - second["usable_start"])
                pairs.append({"a": first["id"], "b": second["id"], "overlap_seconds": round(overlap, 3),
                              "smaller_region_overlap_ratio": round(overlap / smaller, 3),
                              "highly_overlapping": overlap / smaller >= .8})
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--catalog", default="config/music/catalog.json")
    parser.add_argument("--artifact-dir", default="artifacts/mf-010")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve(); catalog_path = root / args.catalog; artifact = root / args.artifact_dir
    catalog = json.loads(catalog_path.read_text())
    tracks = [track for track in catalog["tracks"] if track["project"] == args.project and track["discovery"]["status"] == "PRESENT"]
    if not tracks:
        raise SystemExit("NO_TRACKS_TO_ANALYZE")
    source_before = {track["qualified_id"]: sha256(root / track["source"]) for track in tracks}
    results = []
    for track in sorted(tracks, key=lambda item: item["id"]):
        source = root / track["source"]
        if source_before[track["qualified_id"]] != track["integrity"]["sha256"]:
            raise SystemExit("SOURCE_HASH_MISMATCH: " + track["qualified_id"])
        samples, rate = decode(source); rms_db, peak, transient, smooth = profiles(samples, rate)
        proposed = choose_regions(float(track["technical"]["duration_seconds"]), rms_db, transient, smooth)
        for region in proposed.values():
            region["approval"]["proposed_sha256"] = track["integrity"]["sha256"]
            relative, preview_hash, preview_duration = preview(root, source, track["id"], region, artifact / "previews")
            region["analysis"]["preview"] = relative
            region["analysis"]["preview_sha256"] = preview_hash
            region["analysis"]["preview_duration_seconds"] = preview_duration
        # Preview hashes/duration are evidence, not catalog fields covered by the bounded schema.
        catalog_proposals = []
        for region in proposed.values():
            clean = json.loads(json.dumps(region)); clean["analysis"].pop("preview_sha256"); clean["analysis"].pop("preview_duration_seconds")
            catalog_proposals.append(clean)
        existing = {region["id"]: region for region in track.get("cue_regions", [])}
        merged = []
        for region in catalog_proposals:
            old = existing.pop(region["id"], None)
            preserve = old is not None and (old.get("approval", {}).get("status") != "PENDING_APPROVAL" or old.get("human", {}).get("edited") is True)
            merged.append(old if preserve else region)
        merged.extend(existing.values()); merged.sort(key=lambda item: item["id"])
        track["cue_regions"] = merged
        waveform_path = artifact / "waveforms" / f"{track['id']}__waveform.png"
        waveform(samples, rate, float(track["technical"]["duration_seconds"]), list(proposed.values()), waveform_path)
        analysis = {
            "track_id": track["id"], "qualified_id": track["qualified_id"], "source_sha256": track["integrity"]["sha256"],
            "duration_seconds": track["technical"]["duration_seconds"], "analysis_method": METHOD, "sample_rate": rate,
            "one_second_windows": len(rms_db), "track_metrics": {"mean_rms_db": round(float(np.mean(rms_db)), 3),
            "minimum_rms_db": round(float(np.min(rms_db)), 3), "maximum_rms_db": round(float(np.max(rms_db)), 3),
            "peak_amplitude": round(float(np.max(peak)), 6), "mean_transient_score": round(float(np.mean(transient)), 6)},
            "regions": list(proposed.values()), "overlap_awareness": overlap_report(list(proposed.values())),
            "waveform": str(waveform_path.relative_to(root)), "advisory": True, "human_listening_authoritative": True,
        }
        path = artifact / "analysis" / f"{track['id']}.json"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(analysis, indent=2) + "\n")
        results.append({"track_id": track["id"], "regions": len(proposed), "analysis": str(path.relative_to(root)),
                        "waveform": str(waveform_path.relative_to(root)), "result": "PASS"})
    source_after = {track["qualified_id"]: sha256(root / track["source"]) for track in tracks}
    if source_before != source_after:
        raise SystemExit("SOURCE_MASTER_MODIFIED")
    previous = catalog_path.read_text()
    next_text = json.dumps(catalog, indent=2) + "\n"
    catalog_changed = previous != next_text
    if catalog_changed:
        catalog["updated_at"] = music_catalog.now(); next_text = json.dumps(catalog, indent=2) + "\n"; catalog_path.write_text(next_text)
    result = {"slice": "MF-010", "project": args.project, "analysis_method": METHOD, "tracks": results,
              "track_count": len(results), "region_count": sum(item["regions"] for item in results),
              "catalog_changed": catalog_changed, "all_regions_pending_approval": all(region["approval"]["status"] == "PENDING_APPROVAL"
              for track in tracks for region in track["cue_regions"] if region.get("analysis", {}).get("method") == METHOD),
              "source_immutability": "PASS", "automatic_approvals": 0, "result": "PASS"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
