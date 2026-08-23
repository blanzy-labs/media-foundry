#!/usr/bin/env python3
"""Record reproducible source-audio metadata and level evidence."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--input", required=True); parser.add_argument("--output", required=True); args = parser.parse_args()
    source = Path(args.input); output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(source)], capture_output=True, text=True)
        data = json.loads(probe.stdout) if probe.returncode == 0 else {}
        stream = next((item for item in data.get("streams", []) if item.get("codec_type") == "audio"), None)
        if stream is None:
            raise ValueError("AUDIO_INSPECTION_FAILED: no readable audio stream")
        levels = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(source), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
        integrated = re.findall(r"I:\s+(-?[0-9.]+) LUFS", levels.stderr); peaks = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", levels.stderr)
        if levels.returncode != 0 or not integrated or not peaks:
            raise ValueError("AUDIO_INSPECTION_FAILED: level measurement failed")
        format_data = data.get("format", {})
        result = {"source": str(source), "readable": True, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "bytes": source.stat().st_size, "codec": stream.get("codec_name"), "container": format_data.get("format_name"), "duration_seconds": float(stream.get("duration") or format_data.get("duration")), "sample_rate": int(stream.get("sample_rate")), "channels": int(stream.get("channels")), "channel_layout": stream.get("channel_layout"), "bit_rate": int(stream.get("bit_rate") or format_data.get("bit_rate") or 0), "integrated_lufs": float(integrated[-1]), "true_peak_dbfs": float(peaks[-1]), "result": "PASS"}
    except (OSError, json.JSONDecodeError, StopIteration, TypeError, ValueError) as error:
        result = {"source": str(source), "readable": False, "error": str(error), "result": "FAIL"}
    output.write_text(json.dumps(result, indent=2) + "\n"); print(json.dumps(result, indent=2)); return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
