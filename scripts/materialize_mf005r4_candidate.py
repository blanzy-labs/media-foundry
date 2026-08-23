#!/usr/bin/env python3
"""Apply bounded R4 music/motion candidate settings to a generated-scene fixture."""

import argparse,json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--fixture",required=True); parser.add_argument("--candidate",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
    try:
        fixture=json.loads(Path(args.fixture).read_text()); candidate=json.loads(Path(args.candidate).read_text()); fixture["id"]+=f"-{candidate['id']}"; fixture["candidate"]={key:candidate[key] for key in ("id","label","description")}; fixture["music"].update(candidate["music"]); fixture["generated_scene"]["motion_intensity"]=candidate["motion_intensity"]
        overrides=candidate.get("event_times",{}); known={event["id"] for event in fixture["generated_scene"]["events"]}
        if not set(overrides)<=known: raise ValueError("R4_CANDIDATE_CONFIG_FAILED: unknown scene event override")
        for event in fixture["generated_scene"]["events"]:
            if event["id"] in overrides: event["time"]=overrides[event["id"]]
        output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(fixture,indent=2)+"\n"); return 0
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as error: print(str(error)); return 1


if __name__=="__main__": raise SystemExit(main())
