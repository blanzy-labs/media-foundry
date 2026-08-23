#!/usr/bin/env python3
"""Independently validate MF-005R1 semantic ownership and audiovisual timeline evidence."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True); parser.add_argument("--timeline", required=True); parser.add_argument("--execution", required=True)
    parser.add_argument("--narration", required=True); parser.add_argument("--music", required=True); parser.add_argument("--mix", required=True); parser.add_argument("--audio-validation", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); errors = []
    try:
        fixture=json.loads(Path(args.fixture).read_text()); timeline=json.loads(Path(args.timeline).read_text()); execution=json.loads(Path(args.execution).read_text()); narration=json.loads(Path(args.narration).read_text()); music=json.loads(Path(args.music).read_text()); mix=json.loads(Path(args.mix).read_text()); audio=json.loads(Path(args.audio_validation).read_text())
        if fixture.get("narration_sync_policy") != "semantic_beat" or any(item.get("result") != "PASS" for item in (timeline,execution,narration,music,mix,audio)):
            errors.append("strict synchronization inputs did not all pass")
        beats={item["id"]:item for item in timeline.get("beats",[])}; executed={item["id"]:item for item in execution.get("beats",[])}
        segments=[]
        for segment in narration.get("segments",[]):
            beat=beats.get(segment.get("beat")); observed=executed.get(segment.get("beat"))
            if beat is None or observed is None: errors.append(f"narration owner {segment.get('beat')} is not an executed beat"); continue
            if segment["start"] < segment["active_start"] or segment["end"] > segment["active_end"] or segment["end"] > segment["speech_window_end"]:
                errors.append(f"narration escapes active semantic beat {segment['beat']}")
            target=segment.get("semantic_target")
            if target == "text" and segment.get("text_active") is not True: errors.append(f"visible text is not active for {segment['beat']}")
            if target == "media" and segment.get("media_active") is not True: errors.append(f"required media is not active for {segment['beat']}")
            segments.append({"beat":segment["beat"],"beat_start":beat["start"],"beat_end":beat["end"],"active_start":segment["active_start"],"active_end":segment["active_end"],"narration_start":segment["start"],"narration_end":segment["end"],"pause_after":segment["pause_after"],"semantic_target":target,"status":"PASS"})
        if music.get("status") != "PASS" or music.get("activity",{}).get("start") != 0.0 or music.get("activity",{}).get("end") != timeline.get("duration"):
            errors.append("ambient music does not span the full production")
        if mix.get("music",{}).get("status") != "PASS" or len(mix.get("ducking_windows",[])) != len(segments):
            errors.append("music mixing or narration duck windows differ from narration")
        forbidden={"mf003-still.png","mf003-wide.png","mf003-clip.mp4"}; media_source=Path(fixture.get("media",{}).get("source",""))
        if fixture.get("production_media_required") and (media_source.name in forbidden or fixture.get("media",{}).get("required") is not True): errors.append("production media safeguard failed")
        result={"slice":"MF-005R1","fixture":fixture.get("id"),"checks":{"beat_ownership":"PASS" if not any("owner" in item for item in errors) else "FAIL","semantic_interval":"PASS" if not any("escapes" in item for item in errors) else "FAIL","text_media_alignment":"PASS" if not any("not active" in item for item in errors) else "FAIL","continuous_music":"PASS" if not any("full production" in item for item in errors) else "FAIL","ducking_windows":"PASS" if not any("duck windows" in item for item in errors) else "FAIL","sfx_activity":audio.get("checks",{}).get("existing_cues","FAIL"),"production_media":"PASS" if not any("production media" in item for item in errors) else "FAIL"},"timeline":{"beats":list(beats.values()),"narration":segments,"music":music.get("activity"),"ducking":mix.get("ducking_windows"),"sfx":audio.get("cue_activity",[])},"errors":errors,"result":"PASS" if not errors and audio.get("checks",{}).get("existing_cues")=="PASS" else "FAIL"}
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as error:
        result={"slice":"MF-005R1","errors":[str(error)],"result":"FAIL"}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"]=="PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
