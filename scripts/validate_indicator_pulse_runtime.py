#!/usr/bin/env python3
"""Validate runtime-component/headless-harness separation for indicator_pulse_stage.gd."""

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path


GUI_ERROR_MARKERS = ["doesn't inherit from SceneTree or MainLoop", "Can't load the script", "ALERT!"]
MF012R1_FIXTURES = ["video-01-restrained.json", "video-02-reactive.json"]


def run(command, root: Path) -> dict:
    process = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=60)
    output = process.stdout + ("\n" if process.stdout and process.stderr else "") + process.stderr
    return {"command": command, "exit_code": process.returncode, "output": output,
            "gui_error": any(marker in output for marker in GUI_ERROR_MARKERS)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    harness = run(["godot", "--headless", "--path", "godot", "--script", "indicator_pulse_stage_headless.gd"], root)
    layouts = []
    with tempfile.TemporaryDirectory(prefix="mf-indicator-runtime-") as temporary:
        temp = Path(temporary)
        for name in MF012R1_FIXTURES:
            destination = temp / name.removesuffix(".json")
            destination.mkdir()
            invocation = run([
                "godot", "--headless", "--path", "godot", "--fixed-fps", "30", "res://mf002.tscn", "--",
                "--fixture", str(root / "content/fixtures/mf012r1" / name),
                "--grammar", str(root / "config/visual-grammar.json"), "--output-dir", str(destination / "frames"),
                "--layout-report", str(destination / "layout.json"), "--timeline-report", str(destination / "timeline.json"),
                "--validate-layout-only",
            ], root)
            layout = json.loads((destination / "layout.json").read_text()) if (destination / "layout.json").is_file() else {}
            layouts.append({"fixture": name, "exit_code": invocation["exit_code"], "gui_error": invocation["gui_error"],
                            "layout_result": layout.get("result"),
                            "micro_variation_result": layout.get("generated_scene", {}).get("micro_variation", {}).get("result"),
                            "output": invocation["output"]})
    text_suffixes = {".gd", ".py", ".sh", ".json", ".md", ".tscn", ".cfg", ".toml", ".yaml", ".yml"}
    source_files = [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in text_suffixes
                    and ".git" not in path.parts and "artifacts" not in path.parts and "reports" not in path.parts]
    direct_runtime_entries = []
    for path in source_files:
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if re.search(r"--script(?:=|\s+)(?:res://)?indicator_pulse_stage\.gd(?:\s|$)", text):
            direct_runtime_entries.append(str(path.relative_to(root)))
    mf013_files = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()
                   and ("mf013" in path.name.lower() or "mf-013" in path.name.lower())]
    checks = {
        "runtime_inherits_node_chain": (root / "godot/indicator_pulse_stage.gd").read_text().startswith('extends "res://integrated_lower_right_stage.gd"'),
        "scene_runtime_preloads_component": 'preload("res://indicator_pulse_stage.gd")' in (root / "godot/mf002.gd").read_text()
            and "IndicatorPulseStageScript.new()" in (root / "godot/mf002.gd").read_text(),
        "activity_stage_subclasses_component": (root / "godot/activity_vocabulary_stage.gd").read_text().startswith('extends "res://indicator_pulse_stage.gd"'),
        "no_direct_runtime_script_entry": not direct_runtime_entries,
        "headless_harness": harness["exit_code"] == 0 and "INDICATOR_PULSE_STAGE_HEADLESS_OK" in harness["output"],
        "no_harness_gui_error": not harness["gui_error"],
        "mf012r1_layout_validation": len(layouts) == 2 and all(item["exit_code"] == 0 and item["layout_result"] == "PASS"
                                                              and item["micro_variation_result"] == "PASS" for item in layouts),
        "no_mf012r1_gui_error": all(not item["gui_error"] for item in layouts),
    }
    result = {
        "slice": "MF-012R1", "type": "indicator_runtime_headless_validation",
        "classification": "SCENE_ATTACHED_RUNTIME_NODE",
        "runtime_inheritance_preserved": True,
        "standalone_entry_point": "godot/indicator_pulse_stage_headless.gd",
        "references": {
            "preloaded_and_instantiated_by": "godot/mf002.gd",
            "subclassed_by": "godot/activity_vocabulary_stage.gd",
            "selected_by_fixtures": "visual_strategy.preference=godot_indicator_pulse_refinement",
            "direct_runtime_script_entries": direct_runtime_entries,
        },
        "harness": harness, "mf012r1_layouts": layouts,
        "mf013": {"status": "NOT_PRESENT", "repository_files": mf013_files} if not mf013_files else {"status": "PRESENT", "repository_files": mf013_files},
        "checks": {name: "PASS" if passed else "FAIL" for name, passed in checks.items()},
        "errors": [name.upper() + "_FAILED" for name, passed in checks.items() if not passed],
        "result": "PASS" if all(checks.values()) else "FAIL",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
