#!/usr/bin/env python3
"""Independently validate MF-008B-R2 A/B isolation and media integrity."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def decode(path):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True).returncode == 0


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True)
    parser.add_argument("--archive", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(args.project_root).resolve(); archive = Path(args.archive).resolve()
    result_path = archive / "result.json"; experiment = json.loads(result_path.read_text())
    grammar = json.loads((root / "config/production-grammars/unknown-process-recovered-record-v2.json").read_text())
    errors, pairs = [], []
    renderer = []
    for relative, expected in grammar["files"].items():
        if not relative.startswith("godot/"): continue
        actual = sha256(root / relative) if (root / relative).is_file() else None
        renderer.append({"path": relative, "expected_sha256": expected, "actual_sha256": actual,
                         "result": "PASS" if actual == expected else "FAIL"})
    if not renderer or any(item["result"] != "PASS" for item in renderer): errors.append({"code": "RENDERER_INTEGRITY_FAILED"})
    for pair in experiment.get("pairs", []):
        a, b, integrity = pair["candidate_a"], pair["candidate_b"], pair["integrity"]
        a_path, b_path = Path(a["path"]), Path(b["path"]); pair_root = a_path.parent
        checks = {
            "candidate_a_preserved": a_path.is_file() and sha256(a_path) == a["sha256"] == a["r1_sha256"],
            "candidate_b_hash": b_path.is_file() and sha256(b_path) == b["sha256"],
            "full_decode": decode(a_path) and decode(b_path),
            "video_stream_identity": a["video_stream_sha256"] == b["video_stream_sha256"] and integrity["video_stream_byte_identical"],
            "frame_and_runtime_identity": integrity["duration_equal"] and integrity["frame_count_equal"]
                and a["probe"]["frame_count"] == b["probe"]["frame_count"]
                and a["probe"]["duration"] == b["probe"]["duration"] == pair["runtime_seconds"],
            "decoded_frame_identity": integrity["representative_frame_equal"],
            "music_identity": integrity["music_identity_equal"] and integrity["music_offsets_equal"] and integrity["music_fades_equal"],
            "sfx_isolated": a["sfx_enabled"] and a["sfx_event_count"] > 0 and not b["sfx_enabled"] and b["sfx_event_count"] == 0,
            "music_only_source": len(b["audio_sources"]) == 1 and b["ambient_replacement"] is False and b["new_audio_events"] == 0
                and pair["narration"] == "NOT_PRESENT",
            "loudness_fairness": abs(a["loudness"]["integrated_lufs"] - b["loudness"]["integrated_lufs"]) <= 1.5
                and a["loudness"]["true_peak_dbfs"] <= -1.0 and b["loudness"]["true_peak_dbfs"] <= -1.0,
            "comparison_evidence": (pair_root / "waveform-comparison.png").is_file()
                and (pair_root / "timeline-a.svg").is_file() and (pair_root / "timeline-b.svg").is_file()
        }
        local = [key.upper() + "_FAILED" for key, passed in checks.items() if not passed]
        errors.extend({"video_id": pair["video_id"], "code": value} for value in local)
        pairs.append({"video_id": pair["video_id"], "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
                      "loudness_delta_lu": round(b["loudness"]["integrated_lufs"] - a["loudness"]["integrated_lufs"], 3),
                      "errors": local, "result": "PASS" if not local else "FAIL"})
    global_checks = {"three_pairs_six_outputs": len(pairs) == 3 and experiment.get("candidate_count") == 6,
                     "visual_changes_zero": experiment.get("visual_changes") == 0,
                     "renderer_changes_zero": experiment.get("renderer_changes") == 0,
                     "no_publication": experiment.get("published") == 0}
    errors.extend({"code": key.upper() + "_FAILED"} for key, passed in global_checks.items() if not passed)
    result = {"slice": "MF-008B-R2", "type": "independent_ab_validation", "archive": str(archive),
              "renderer_files": renderer, "pairs": pairs,
              "checks": {key: "PASS" if value else "FAIL" for key, value in global_checks.items()},
              "errors": errors, "result": "PASS" if not errors else "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2)); return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
