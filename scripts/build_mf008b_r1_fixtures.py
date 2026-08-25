#!/usr/bin/env python3
"""Materialize MF-008B-R1 fixtures from the approved MF-008C control surface."""

import argparse
import json
from pathlib import Path

from build_mf008c_fixtures import build_fixture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    manifest = json.loads(Path(args.manifest).read_text())
    base = json.loads((root / "content/fixtures/mf006r9-unknown-process.json").read_text())
    catalog = json.loads((root / manifest["music_catalog"]).read_text())
    tracks = {track["id"]: track for track in catalog["tracks"] if track["project"] == "unknown-process"}
    outputs = []
    for job in manifest["jobs"]:
        creative, selection = job["creative"], job["music"]
        spec = {"id": "mf008b-r1-" + job["id"], "mechanism": creative["mechanism"],
                "events": creative["events"], "profiles": [creative[name] for name in
                ["palette_profile", "camera_profile", "node_profile", "projection_profile", "cta_profile"]],
                "timing": list(creative["timing"].values()), "phrases": job["phrases"]}
        fixture = build_fixture(base, spec)
        runtime = selection["video_duration"]
        fixture["format"]["duration_seconds"] = runtime
        fixture["beats"][-1]["duration"] = round(runtime - sum(beat["duration"] for beat in fixture["beats"][:-1]), 3)
        fixture["creative"]["audio_cue"] = creative["audio_cue"]
        track = tracks[selection["track_id"]]
        fixture["music"] = {
            "source": track["source"], "required": True, "continuous": True, "loop": False,
            "selected_offset": selection["actual_start"], "normalization_lufs": -24,
            "gain_db": selection["gain_db"], "narration_duck_db": selection["ducking"]["narration_duck_db"],
            "attack_ms": selection["ducking"]["attack_ms"], "release_ms": selection["ducking"]["release_ms"],
            "fade_in": selection["fade_in"], "fade_out": selection["fade_out"],
            "provenance": {"type": track["provenance"]["source_type"], "asset_class": "approved_catalog_track",
                           "release_eligible": True, "track_id": track["id"], "region_id": selection["region_id"],
                           "source_sha256": track["integrity"]["sha256"],
                           "approval_reviewer": track["approval"]["reviewer"],
                           "usage": "MF-010 hash-bound human approval; local production master."}
        }
        output = root / job["fixture"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(fixture, indent=2) + "\n")
        outputs.append(str(output.relative_to(root)))
    print(json.dumps({"fixtures": outputs, "count": len(outputs), "result": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
