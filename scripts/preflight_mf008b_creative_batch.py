#!/usr/bin/env python3
"""Fail closed when MF-008B direction exceeds the frozen grammar's controls."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    manifest = json.loads(Path(args.manifest).read_text())
    batch = manifest["batch"]
    policy = manifest["policy"]
    grammar = json.loads((root / batch["production_grammar_file"]).read_text())
    cue_map = json.loads((root / manifest["audio_cue_map"]).read_text())
    stage_path = root / "godot/projected_data_window_stage.gd"
    pulse_path = root / "godot/indicator_pulse_stage.gd"
    stage = stage_path.read_text()
    pulse = pulse_path.read_text()

    pinned = []
    for relative, expected in grammar["files"].items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        pinned.append({"path": relative, "expected_sha256": expected, "actual_sha256": actual,
                       "status": "PASS" if actual == expected else "FAIL"})

    creative_checks = {
        "exactly_three_briefs": len(manifest["jobs"]) == batch["job_limit"] == 3,
        "unique_mechanisms_declared": len({job["primary_investigation_mechanism"] for job in manifest["jobs"]}) == 3,
        "unique_arcs_declared": len({tuple(job["emotional_arc"]) for job in manifest["jobs"]}) == 3,
        "three_or_more_cosmetic_differences_declared": all(len(job["cosmetic_profile"]) >= 3 for job in manifest["jobs"]),
        "concise_three_phrase_packages": all(len(job["visible_phrases"]) == 3 for job in manifest["jobs"]),
        "non_narrated": all(job["narration"] is None for job in manifest["jobs"]),
        "bounded_runtime": all(job["target_runtime_seconds"] == {"minimum": 24, "maximum": 32} for job in manifest["jobs"]),
        "shared_campaign_identity": bool(manifest.get("shared_identity")),
    }

    # These checks deliberately inspect only the pinned, frozen implementation.
    capabilities = {
        "select_one_investigation_mechanism": {
            "supported": False,
            "evidence": "_record_index advances through indices 0, 1, and 2; _draw_record_content hardcodes all three branches"
                if all(token in stage for token in ["if index==0:", "elif index==1:", "if current_time>=_time(\"record_typing_2\")", "if current_time>=_time(\"record_typing_3\")"])
                else "required frozen implementation signatures not found"
        },
        "job_specific_investigation_events": {
            "supported": False,
            "evidence": "frozen stage exposes record_typing/refresh events, not target_search, bridge_attempt, deep_scan, or their required peers"
        },
        "configurable_cosmetic_profile": {
            "supported": False,
            "evidence": "ACCENT_COLORS, screen/CTA colors, camera push magnitude, and projection behavior are literals in the frozen stage"
                if "const ACCENT_COLORS" in stage and "push*.055-pull*.045" in stage and "Color(\"e68d43\")" in stage
                else "required frozen implementation signatures not found"
        },
        "configurable_node_pulse_character": {
            "supported": False,
            "evidence": "indicator periods, offsets, and durations are constants"
                if all(token in pulse for token in ["const INDICATOR_PERIODS", "const INDICATOR_OFFSETS", "const INDICATOR_DURATIONS"])
                else "required frozen implementation signatures not found"
        },
        "approved_distinct_music_cues": {
            "supported": False,
            "evidence": f"cue map contains only {sorted(cue_map.get('sections', {}))}; no pursuit, investigation, or revelation cue IDs are approved"
        },
        "natural_runtime_variation": {
            "supported": False,
            "evidence": f"frozen grammar runtime is {grammar.get('runtime_seconds')} seconds and its timeline fixture is pinned"
        }
    }

    renderer_frozen = (
        grammar.get("status") == "FROZEN"
        and policy.get("allow_renderer_changes") is False
        and policy.get("allow_runtime_architecture_changes") is False
        and policy.get("allow_visual_grammar_changes") is False
        and all(item["status"] == "PASS" for item in pinned)
    )
    blockers = [name for name, item in capabilities.items() if not item["supported"]]
    jobs = []
    for brief in manifest["jobs"]:
        jobs.append({
            "job_id": brief["id"],
            "state": "NEEDS_ENGINEERING",
            "creative_brief": "PASS" if all(creative_checks.values()) else "FAIL",
            "render_attempted": False,
            "technical_validation": "NOT_RUN_UNSUPPORTED_BRIEF",
            "editorial": "NOT_READY",
            "release": "NOT_READY",
            "artifact": None,
            "blockers": blockers,
        })

    execution_ref = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()
    result = {
        "slice": "MF-008B",
        "type": "directed_batch_capability_preflight",
        "batch_id": batch["id"],
        "state": "FAILED",
        "production_grammar_id": grammar["id"],
        "grammar_origin_git_ref": grammar["source_git_ref"],
        "execution_git_ref": execution_ref,
        "renderer_frozen_and_exact": renderer_frozen,
        "renderer_changes": 0,
        "creative_brief_checks": {name: "PASS" if passed else "FAIL" for name, passed in creative_checks.items()},
        "capabilities": capabilities,
        "approved_audio_sections": cue_map.get("sections", {}),
        "jobs": jobs,
        "ready_for_review": 0,
        "needs_engineering": len(jobs),
        "rendered": 0,
        "published": 0,
        "human_review": "BLOCKED_NO_CANDIDATES",
        "artifacts": [],
        "pinned_files": pinned,
        "blockers": blockers,
        "result": "NEEDS_ENGINEERING"
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
