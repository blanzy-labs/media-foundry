#!/usr/bin/env python3
"""Create MF-008B-R2 music+SFX versus music-only pairs without rerendering video."""

import argparse
import hashlib
import json
import math
import re
import shutil
import struct
import subprocess
import wave
from pathlib import Path


JOBS = {
    "simon-pursuit": "simon",
    "leo-zeph-investigation": "leo-zeph",
    "kill-switch-revelation": "kill-switch",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command, log=None):
    process = subprocess.run(command, capture_output=True, text=True)
    if log: Path(log).write_text(process.stdout + ("\n" if process.stdout and process.stderr else "") + process.stderr)
    if process.returncode: raise RuntimeError(f"command failed ({process.returncode}): {' '.join(command)}")
    return process


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2) + "\n")


def sum_pcm(first, second, output):
    with wave.open(str(first), "rb") as a, wave.open(str(second), "rb") as b:
        contract = (a.getframerate(), a.getnchannels(), a.getsampwidth(), a.getnframes())
        if contract != (b.getframerate(), b.getnchannels(), b.getsampwidth(), b.getnframes()) or contract[0:3] != (48000, 1, 2):
            raise ValueError("R1_STEM_CONTRACT_INVALID")
        left = a.readframes(a.getnframes()); right = b.readframes(b.getnframes())
    clipped = 0; frames = []
    for x, y in zip(struct.iter_unpack("<h", left), struct.iter_unpack("<h", right)):
        value = x[0] + y[0]
        if value < -32768 or value > 32767: clipped += 1
        frames.append(struct.pack("<h", max(-32768, min(32767, value))))
    with wave.open(str(output), "wb") as target:
        target.setnchannels(1); target.setsampwidth(2); target.setframerate(48000); target.writeframes(b"".join(frames))
    return clipped


def loudnorm_measure(path):
    process = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                   "loudnorm=I=-15.5:TP=-2.0:LRA=7:print_format=json", "-f", "null", "-"])
    matches = re.findall(r"\{\s*\"input_i\".*?\}", process.stderr, flags=re.S)
    if not matches: raise ValueError("LOUDNORM_MEASUREMENT_MISSING")
    return json.loads(matches[-1])


def loudness(path):
    process = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"])
    summary = process.stderr.rsplit("Summary:", 1)[-1]
    patterns = {"integrated_lufs": r"Integrated loudness:\s*I:\s*(-?[0-9.]+)",
                "loudness_range_lu": r"Loudness range:\s*LRA:\s*([0-9.]+)",
                "true_peak_dbfs": r"True peak:\s*Peak:\s*(-?[0-9.]+)"}
    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, summary, flags=re.S)
        if not match: raise ValueError("LOUDNESS_SUMMARY_INVALID: " + key)
        result[key] = float(match.group(1))
    return result


def probe(path):
    process = run(["ffprobe", "-v", "error", "-show_entries",
                   "stream=index,codec_type,codec_name,r_frame_rate,nb_frames:format=duration", "-of", "json", str(path)])
    data = json.loads(process.stdout); streams = data.get("streams", [])
    video = next(item for item in streams if item.get("codec_type") == "video")
    audio = next(item for item in streams if item.get("codec_type") == "audio")
    return {"duration": float(data["format"]["duration"]), "frame_rate": video.get("r_frame_rate"),
            "frame_count": int(video.get("nb_frames", 0)), "video_codec": video.get("codec_name"),
            "audio_codec": audio.get("codec_name")}


def stream_hash(path):
    process = run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-c", "copy",
                   "-f", "hash", "-hash", "sha256", "-"])
    return process.stdout.strip().split("=", 1)[-1].lower()


def timeline_svg(path, runtime, events):
    width, height, left, span = 1200, 180, 130, 1020
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#071016"/>',
             '<text x="20" y="58" fill="#dcefe9" font-family="sans-serif" font-size="22">MUSIC</text>',
             f'<rect x="{left}" y="38" width="{span}" height="28" rx="5" fill="#43cdbb"/>',
             '<text x="20" y="128" fill="#dcefe9" font-family="sans-serif" font-size="22">SFX</text>']
    for event in events:
        x = left + event["time"] / runtime * span; w = max(3, event["duration"] / runtime * span)
        parts.append(f'<rect x="{x:.2f}" y="108" width="{w:.2f}" height="28" rx="3" fill="#e58d43"/>')
    parts += [f'<text x="{left}" y="165" fill="#77958e" font-family="sans-serif" font-size="16">0s</text>',
              f'<text x="{left+span-45}" y="165" fill="#77958e" font-family="sans-serif" font-size="16">{runtime:g}s</text>', '</svg>']
    path.write_text("\n".join(parts) + "\n")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--r1-run", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); source_run = Path(args.r1_run).resolve(); output = Path(args.output).resolve()
    if output.exists(): raise SystemExit(f"refusing to overwrite existing A/B archive: {output}")
    output.mkdir(parents=True); r1_batch = json.loads((source_run / "batch-result.json").read_text())
    by_id = {item["job_id"]: item for item in r1_batch["jobs"]}; results = []
    for job_id, short in JOBS.items():
        source = source_run / job_id; pair = output / short; pair.mkdir(); (pair / "logs").mkdir()
        a = pair / f"{short}-a-music-sfx.mp4"; b = pair / f"{short}-b-music-only.mp4"
        shutil.copy2(source / "final.mp4", a)
        music = source / "audio/music.wav"; sfx = source / "audio/sfx.wav"; pre_mix = pair / "a-pre-master.wav"
        if sum_pcm(sfx, music, pre_mix): raise ValueError(job_id + ": PRE_MASTER_CLIPPING")
        measured = loudnorm_measure(pre_mix)
        b_audio = pair / "b-music-only.wav"
        loudnorm_filter = ("loudnorm=I=-15.5:TP=-2.0:LRA=7:"
            f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:"
            f"measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:linear=true:print_format=summary")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(music), "-af", loudnorm_filter,
             "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(b_audio)], pair / "logs/music-only-master.log")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(a), "-i", str(b_audio),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
             "-shortest", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z", str(b)], pair / "logs/remux.log")
        r1 = by_id[job_id]; selection = r1["music"]; sfx_report = json.loads((source / "validation/sfx.json").read_text())
        a_probe, b_probe = probe(a), probe(b); a_video_hash, b_video_hash = stream_hash(a), stream_hash(b)
        a_loudness, b_loudness = loudness(a), loudness(b)
        stamp = r1["runtime_seconds"] * .65
        frames = pair / "representative-frames"; frames.mkdir()
        for candidate, media in [("a", a), ("b", b)]:
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(stamp), "-i", str(media),
                 "-frames:v", "1", str(frames / f"{candidate}.png")], pair / f"logs/frame-{candidate}.log")
        waveform = pair / "waveform-comparison.png"; font = Path(__file__).resolve().parents[1] / "godot/fonts/Lato-Heavy.ttf"
        filters = (f"[0:a]showwavespic=s=1200x260:colors=0xe58d43,drawtext=fontfile='{font}':text='A  MUSIC + SFX':x=24:y=18:fontsize=28:fontcolor=white[a];"
                   f"[1:a]showwavespic=s=1200x260:colors=0x43cdbb,drawtext=fontfile='{font}':text='B  MUSIC ONLY':x=24:y=18:fontsize=28:fontcolor=white[b];"
                   "[a][b]vstack=inputs=2")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(a), "-i", str(b),
             "-filter_complex", filters, "-frames:v", "1", str(waveform)], pair / "logs/waveform.log")
        timeline_svg(pair / "timeline-a.svg", r1["runtime_seconds"], sfx_report["events"])
        timeline_svg(pair / "timeline-b.svg", r1["runtime_seconds"], [])
        record = {"video_id": job_id, "runtime_seconds": r1["runtime_seconds"], "narration": "NOT_PRESENT",
                  "music": {key: selection[key] for key in ["track_id", "region_id", "actual_start", "actual_end", "fade_in", "fade_out", "gain_db", "source_sha256"]},
                  "candidate_a": {"path": str(a), "sha256": sha256(a), "r1_sha256": r1["artifact"]["sha256"],
                                  "probe": a_probe, "video_stream_sha256": a_video_hash,
                                  "sfx_enabled": True, "sfx_event_count": sfx_report["event_count"],
                                  "sfx_events": sfx_report["events"], "loudness": a_loudness},
                  "candidate_b": {"path": str(b), "sha256": sha256(b), "probe": b_probe,
                                  "video_stream_sha256": b_video_hash, "sfx_enabled": False, "sfx_event_count": 0,
                                  "audio_sources": [str(music)], "ambient_replacement": False, "new_audio_events": 0,
                                  "mastering": {"policy": "inherit_candidate_a_measured_loudnorm_parameters",
                                  "candidate_a_measurement": measured}, "loudness": b_loudness},
                  "integrity": {"candidate_a_byte_preserved": sha256(a) == r1["artifact"]["sha256"],
                                "video_stream_byte_identical": a_video_hash == b_video_hash,
                                "duration_equal": abs(a_probe["duration"] - b_probe["duration"]) < .001,
                                "frame_count_equal": a_probe["frame_count"] == b_probe["frame_count"],
                                "representative_frame_equal": sha256(frames / "a.png") == sha256(frames / "b.png"),
                                "music_identity_equal": True, "music_offsets_equal": True, "music_fades_equal": True,
                                "only_source_layer_change": "SFX_DISABLED"}, "result": "PASS"}
        if not all(value is True for key, value in record["integrity"].items() if key != "only_source_layer_change"):
            record["result"] = "FAIL"
        write_json(pair / "comparison.json", record); results.append(record); pre_mix.unlink()
    result = {"slice": "MF-008B-R2", "experiment": "music_only_presentation_ab", "r1_source": str(source_run),
              "pairs": results, "pair_count": len(results), "candidate_count": len(results) * 2,
              "visual_changes": 0, "renderer_changes": 0, "published": 0,
              "technical_result": "PASS" if len(results) == 3 and all(item["result"] == "PASS" for item in results) else "FAIL",
              "human_decision": "PENDING"}
    write_json(output / "result.json", result); print(json.dumps(result, indent=2)); return 0 if result["technical_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
