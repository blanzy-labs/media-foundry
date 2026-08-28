#!/usr/bin/env python3
"""Resolve and verify Blender without assuming an installation path."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--output", required=True); parser.add_argument("--blender"); parser.add_argument("--slice", default="MF-019")
    args = parser.parse_args(); root = Path(args.project_root).resolve(); started = time.monotonic()
    executable = args.blender or shutil.which("blender")
    checks = {"binary_exists": bool(executable and Path(executable).is_file()), "ffmpeg": shutil.which("ffmpeg") is not None, "ffprobe": shutil.which("ffprobe") is not None}
    details = {}; returncode = 127
    if checks["binary_exists"]:
        expression = "import bpy,sys,json; print('MF019_PREFLIGHT='+json.dumps({'version':bpy.app.version_string,'python':sys.version.split()[0],'engines':[e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]}))"
        process = subprocess.run([executable, "--background", "--factory-startup", "--python-expr", expression], capture_output=True, text=True)
        returncode = process.returncode; marker = next((line.split("=", 1)[1] for line in process.stdout.splitlines() if line.startswith("MF019_PREFLIGHT=")), None)
        if marker: details = json.loads(marker)
        checks["headless_background"] = process.returncode == 0
        checks["python_scripting"] = bool(details.get("python"))
        engines = details.get("engines", []); selected = next((engine for engine in engines if "EEVEE" in engine), None)
        details["selected_engine"] = selected; details["device"] = "CPU_HEADLESS_DEFAULT"
        checks["realtime_engine"] = selected is not None
    else:
        checks.update({"headless_background": False, "python_scripting": False, "realtime_engine": False})
    font = root / "godot/fonts/Lato-Regular.ttf"; checks["required_font"] = font.is_file()
    with tempfile.TemporaryDirectory(prefix="mf019-preflight-") as temp:
        test = Path(temp) / "write-test"; test.write_text("ok"); checks["output_writable"] = test.read_text() == "ok"
    result = "PASS" if all(checks.values()) else ("BLENDER_NOT_AVAILABLE" if not checks["binary_exists"] else "BLOCKED_RENDER_BACKEND")
    report = {"slice": args.slice, "result": result, "checks": checks, "blender": {"executable": str(Path(executable).resolve()) if executable else None, **details}, "font": "godot/fonts/Lato-Regular.ttf", "ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe"), "headless_returncode": returncode, "elapsed_ms": round((time.monotonic() - started) * 1000)}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n"); print(json.dumps(report, indent=2)); return 0 if result == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
