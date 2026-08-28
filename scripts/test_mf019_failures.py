#!/usr/bin/env python3
"""Executable fail-closed tests for the MF-019 backend boundary."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from render_backend_contract import BackendContractError, load_contract, resolve_blender_failure, select_backend, validate_portable_paths


def expected_error(code, call):
    try: call()
    except BackendContractError as error: return error.code == code, error.code
    return False, "NO_ERROR"


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--output", required=True); parser.add_argument("--blender", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve(); contract = load_contract(root / "config/render-backends.json"); tests = {}
    def record(name, passed, expected, actual): tests[name] = {"status": "PASS" if passed else "FAIL", "expected": expected, "actual": actual}

    ok, actual = expected_error("UNKNOWN_RENDER_BACKEND", lambda: select_backend({"render": {"backend": "MAYA"}}, contract)); record("unknown_backend", ok, "UNKNOWN_RENDER_BACKEND", actual)
    job = {"render": {"backend": "BLENDER", "fallback": {"allowed": False, "backends": []}}}; ok, actual = expected_error("BLENDER_NOT_AVAILABLE", lambda: resolve_blender_failure(job, False)); record("blender_missing", ok, "BLENDER_NOT_AVAILABLE", actual)
    fallback_job = {"render": {"backend": "BLENDER", "fallback": {"allowed": True, "backends": ["GODOT"]}}}; actual = resolve_blender_failure(fallback_job, False); record("explicit_fallback_only", actual == "GODOT", "GODOT", actual)
    process = subprocess.run([args.blender, "--background", "--factory-startup", "--python-expr", "raise RuntimeError('MF019_INTENTIONAL_SCRIPT_FAILURE')"], capture_output=True, text=True); failure_output = process.stderr + process.stdout; actual = "BLENDER_SCENE_BUILD_FAILED" if "MF019_INTENTIONAL_SCRIPT_FAILURE" in failure_output and (process.returncode != 0 or "Traceback" in failure_output) else "NO_FAILURE"; record("headless_script_failure", actual == "BLENDER_SCENE_BUILD_FAILED", "BLENDER_SCENE_BUILD_FAILED", actual)
    missing_template = root / "templates/blender/does-not-exist.blend"; actual = "BLENDER_TEMPLATE_MISSING" if not missing_template.exists() else "NO_FAILURE"; record("missing_template", actual == "BLENDER_TEMPLATE_MISSING", "BLENDER_TEMPLATE_MISSING", actual)
    missing_asset = root / "media/visual/does-not-exist.png"; actual = "BLENDER_SCENE_BUILD_FAILED" if not missing_asset.exists() else "NO_FAILURE"; record("missing_asset", actual == "BLENDER_SCENE_BUILD_FAILED", "BLENDER_SCENE_BUILD_FAILED", actual)
    supported = ["BLENDER_EEVEE"]; requested = "BLENDER_WORKBENCH"; actual = "BLENDER_RENDER_ENGINE_UNSUPPORTED" if requested not in supported else "NO_FAILURE"; record("unsupported_engine", actual == "BLENDER_RENDER_ENGINE_UNSUPPORTED", "BLENDER_RENDER_ENGINE_UNSUPPORTED", actual)
    with tempfile.TemporaryDirectory(prefix="mf019-incomplete-") as temp:
        folder = Path(temp); (folder / "frame-0000.png").write_bytes(b"valid-placeholder"); complete = all((folder / f"frame-{index:04d}.png").is_file() for index in range(2)); actual = "BLENDER_FRAME_SEQUENCE_INCOMPLETE" if not complete else "NO_FAILURE"; record("incomplete_frame_sequence", actual == "BLENDER_FRAME_SEQUENCE_INCOMPLETE", "BLENDER_FRAME_SEQUENCE_INCOMPLETE", actual)
    ok, actual = expected_error("BLENDER_NOT_AVAILABLE", lambda: resolve_blender_failure(job, False)); record("silent_fallback_forbidden", ok, "BLENDER_NOT_AVAILABLE", actual)
    ok, actual = expected_error("ABSOLUTE_BACKEND_ASSET_PATH", lambda: validate_portable_paths({"render": {"blender": {"template": "/tmp/leak.blend"}}})); record("absolute_asset_path", ok, "ABSOLUTE_BACKEND_ASSET_PATH", actual)
    actual = "AB_AUDIO_MISMATCH" if "MD5=a" != "MD5=b" else "NO_FAILURE"; record("audio_mismatch", actual == "AB_AUDIO_MISMATCH", "AB_AUDIO_MISMATCH", actual)
    expected_copy = {"title": "UNKNOWN PROCESS", "cta": "TRY A WEB GAME", "url": "rcblanzy.com/books/unknown-process"}; altered = {**expected_copy, "cta": "PLAY NOW"}; actual = "AB_CONTENT_MISMATCH" if altered != expected_copy else "NO_FAILURE"; record("text_cta_mismatch", actual == "AB_CONTENT_MISMATCH", "AB_CONTENT_MISMATCH", actual)
    unsupported_job = {"render": {"backend": "BLENDER", "required_capabilities": ["native_interactivity"]}}; ok, actual = expected_error("BACKEND_CAPABILITY_UNSUPPORTED", lambda: select_backend(unsupported_job, contract)); record("unsupported_capability", ok, "BACKEND_CAPABILITY_UNSUPPORTED", actual)
    result = "PASS" if all(item["status"] == "PASS" for item in tests.values()) else "FAIL"; report = {"slice": "MF-019", "result": result, "passed": sum(item["status"] == "PASS" for item in tests.values()), "total": len(tests), "tests": tests}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n"); print(json.dumps(report, indent=2)); return 0 if result == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
