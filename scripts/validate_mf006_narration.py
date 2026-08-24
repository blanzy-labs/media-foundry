#!/usr/bin/env python3
"""Validate approved MF-006 narration windows or preserve an explicit production-voice blocker."""

import argparse,json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--fixture",required=True); parser.add_argument("--manifest",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(); errors=[]; blockers=[]
    try:
        fixture=json.loads(Path(args.fixture).read_text()); manifest=json.loads(Path(args.manifest).read_text()); voice=fixture.get("voice_contract",{}); segments=manifest.get("segments",[]); cursor=0.0; beats={}
        for beat in fixture.get("beats",[]): beats[beat["id"]]={"start":cursor,"end":cursor+float(beat["duration"])}; cursor+=float(beat["duration"])
        if voice.get("status")=="BLOCKED_PRODUCTION_VOICE" and not segments: blockers.append("BLOCKED_PRODUCTION_VOICE")
        else:
            for segment in segments:
                beat=beats.get(segment.get("beat"),{}); start=float(segment.get("start",-1)); end=float(segment.get("end",-1))
                if not beat or start<float(beat.get("start",0)) or end>float(beat.get("end",0)) or start>=end: errors.append("PAGE_NARRATION_EXCEEDS_BEAT")
            combined=" ".join(str(item.get("text","")) for item in segments)
            if voice.get("required_final_line","").casefold() not in combined.casefold(): errors.append("FINAL_VOICE_LINE_MISSING")
        result={"slice":"MF-006","segments":segments,"blockers":blockers,"errors":errors,"checks":{"beat_fit":"PASS" if "PAGE_NARRATION_EXCEEDS_BEAT" not in errors else "FAIL","final_line":"BLOCKED_PRODUCTION_VOICE" if blockers else ("PASS" if "FINAL_VOICE_LINE_MISSING" not in errors else "FAIL")},"result":"PASS_WITH_BLOCKER" if blockers and not errors else ("PASS" if not errors else "FAIL")}
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as error: result={"slice":"MF-006","errors":[str(error)],"blockers":[],"result":"FAIL"}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKER"} else 1


if __name__=="__main__": raise SystemExit(main())
