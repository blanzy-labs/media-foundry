#!/usr/bin/env python3
"""Apply a small declarative candidate overlay to a reusable production fixture."""

import argparse,json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--fixture",required=True); parser.add_argument("--candidate",required=True); parser.add_argument("--project-root",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
    try:
        fixture=json.loads(Path(args.fixture).read_text()); candidate=json.loads(Path(args.candidate).read_text()); beats={beat["id"]:beat for beat in fixture["beats"]}
        durations=candidate.get("beat_durations",{}); cues=candidate.get("audio_cues",{})
        if set(durations)!=set(beats) or set(cues)!=set(beats): raise ValueError("CANDIDATE_CONFIG_FAILED: duration/cue overlays must cover every beat")
        for beat_id,beat in beats.items():
            beat["duration"]=durations[beat_id]
            if beat_id in candidate.get("transitions",{}): beat["transition"]=candidate["transitions"][beat_id]
            if cues[beat_id] is None: beat.pop("audio_cue",None)
            else: beat["audio_cue"]=cues[beat_id]
        fixture["music"].update(candidate.get("music",{})); fixture["id"]=f"{fixture['id']}-{candidate['id']}"; fixture["candidate"]={key:candidate[key] for key in ("id","label","description")}
        media_source=Path(fixture["media"]["source"])
        if not media_source.is_absolute(): fixture["media"]["source"]=str((Path(args.project_root)/media_source).resolve())
        if abs(sum(float(beat["duration"]) for beat in beats.values())-float(fixture["format"]["duration_seconds"]))>1e-6: raise ValueError("CANDIDATE_CONFIG_FAILED: beat durations do not total production duration")
        result=fixture
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as error:
        print(str(error)); return 1
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(output); return 0


if __name__=="__main__": raise SystemExit(main())
