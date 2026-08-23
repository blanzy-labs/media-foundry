#!/usr/bin/env python3
"""Independently validate R4 world events, stem fades, physical SFX, and final audio."""

import argparse,json,math,re,subprocess
from pathlib import Path
from validate_mf005r3_quality import envelope_check,pcm


REQUIRED_COMPONENTS={"wall","lamp","toilet","character","turd","sack","punch_sign","title"}
REQUIRED_EVENTS={"camera_push","character_enters","toilet_reveal","turd_highlight","character_approaches","turd_grab","grab_impact","punch_sign","character_exits","title_reveal"}


def loudness(path):
    process=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-vn","-af","loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json","-f","null","-"],capture_output=True,text=True); blocks=re.findall(r'\{\s*"input_i".*?\}',process.stderr,re.DOTALL)
    if process.returncode or not blocks: raise ValueError("R4_AUDIO_FAILED: loudness analysis unavailable")
    data=json.loads(blocks[-1]); return {"integrated_lufs":float(data["input_i"]),"true_peak_db":float(data["input_tp"]),"loudness_range":float(data["input_lra"])}


def main():
    parser=argparse.ArgumentParser()
    for name in ("fixture","layout","execution","music","music_stem","music_reference","sfx_audio","mix","media","contract","output","motion_timeline"): parser.add_argument(f"--{name.replace('_','-')}",required=True)
    args=parser.parse_args(); errors=[]
    try:
        fixture=json.loads(Path(args.fixture).read_text()); layout=json.loads(Path(args.layout).read_text()); execution=json.loads(Path(args.execution).read_text()); music=json.loads(Path(args.music).read_text()); mix=json.loads(Path(args.mix).read_text()); contract=json.loads(Path(args.contract).read_text()); scene=layout.get("generated_scene",{})
        components=set(scene.get("components",[])); observed={item.get("id") for item in scene.get("observed_events",[])}; configured={item.get("id") for item in scene.get("configured_events",[])}
        if layout.get("result")!="PASS" or scene.get("result")!="PASS" or not REQUIRED_COMPONENTS<=components: errors.append("GENERATED_SCENE_INSTANTIATION_FAILED")
        if configured!=observed or not REQUIRED_EVENTS<=observed: errors.append("GENERATED_SCENE_EVENT_FAILED")
        if scene.get("continuous_scene",{}).get("duration",0)<5 or scene.get("text_only_full_frame_states",99)>2 or scene.get("external_static_media_primary") is not False: errors.append("PERSISTENT_WORLD_FAILED")
        if len(scene.get("camera_events",[]))<3: errors.append("CAMERA_EVENT_FAILED")
        stem,rate=pcm(Path(args.music_stem)); reference,_=pcm(Path(args.music_reference)); fade=envelope_check(stem,reference,float(fixture["music"]["fade_in"]),float(fixture["music"]["fade_out"]),rate)
        if fade.get("result")!="PASS": errors.append("HARD_MUSIC_CUT_FAILED")
        measured=loudness(Path(args.media))
        if not -17<=measured["integrated_lufs"]<=-15 or measured["true_peak_db"]>-1.0 or mix.get("clipped_samples")!=0: errors.append("FINAL_AUDIO_LIMIT_FAILED")
        cue_beats={beat["id"]:beat.get("audio_cue") for beat in fixture.get("beats",[]) if beat.get("audio_cue")}; event_map=fixture.get("sfx_event_map",{}); sfx_samples,sfx_rate=pcm(Path(args.sfx_audio)); cue_activity=[]; cursor=0.0
        for beat in fixture.get("beats",[]):
            if beat.get("audio_cue"):
                start=cursor+min(.12,float(beat["duration"])*.1); values=sfx_samples[round(start*sfx_rate):round(min(start+.2,15)*sfx_rate)]; level=20*math.log10(max(1e-7,math.sqrt(sum(item*item for item in values)/max(1,len(values))))); cue_activity.append({"beat":beat["id"],"cue":beat["audio_cue"],"physical_event":event_map.get(beat["id"]),"start":round(start,6),"measurement_seconds":.2,"rms_dbfs":round(level,3),"result":"PASS" if level>-35 else "FAIL"})
            cursor+=float(beat["duration"])
        if len(cue_beats)>4 or set(cue_beats)!=set(event_map) or any(event not in observed for event in event_map.values()) or any(item["result"]!="PASS" for item in cue_activity): errors.append("PHYSICAL_SFX_EVENT_FAILED")
        if music.get("source_sha256")!=fixture["music"]["provenance"]["sha256"] or music.get("selected_offset")!=fixture["music"]["selected_offset"]: errors.append("R4_MUSIC_SOURCE_FAILED")
        if contract.get("result") not in {"PASS","PASS_WITH_BLOCKER"}: errors.append("R4_CONTRACT_FAILED")
        blockers=list(contract.get("blockers",[])); events=scene.get("observed_events",[]); motion={"slice":"MF-005R4","candidate":fixture.get("candidate"),"continuous_scene":scene.get("continuous_scene"),"components":sorted(components),"events":events,"camera_events":scene.get("camera_events",[]),"text_hidden_question":"PENDING_HUMAN","result":"PASS" if not errors else "FAIL"}; Path(args.motion_timeline).parent.mkdir(parents=True,exist_ok=True); Path(args.motion_timeline).write_text(json.dumps(motion,indent=2)+"\n")
        subgate="PASS" if not errors else "FAIL"; result={"slice":"MF-005R4","candidate":fixture.get("candidate"),"checks":{"generated_scene":"PASS" if not any("INSTANTIATION" in item for item in errors) else "FAIL","scene_events":"PASS" if "GENERATED_SCENE_EVENT_FAILED" not in errors else "FAIL","persistent_world":"PASS" if not any("PERSISTENT" in item for item in errors) else "FAIL","camera":"PASS" if not any("CAMERA" in item for item in errors) else "FAIL","music_fades":"PASS" if fade.get("result")=="PASS" else "FAIL","physical_sfx":"PASS" if not any("SFX" in item for item in errors) else "FAIL","audio_limits":"PASS" if not any("AUDIO_LIMIT" in item for item in errors) else "FAIL","complete_decode":"PASS"},"fade_measurement":fade,"audio":measured,"music":{"offset":music.get("selected_offset"),"gain_db":music.get("gain_db"),"fade_in":music.get("fade_in"),"fade_out":music.get("fade_out")},"sfx":cue_activity,"gates":{"visual_audio_technical":subgate,"technical":"FAIL" if blockers else subgate,"editorial":"PENDING_HUMAN","release":"BLOCKED_PRODUCTION_VOICE" if blockers else "PENDING_HUMAN"},"blockers":blockers,"errors":errors,"candidate_valid":False if blockers or errors else True,"result":"PASS_WITH_BLOCKER" if blockers and not errors else subgate}
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as error: result={"slice":"MF-005R4","errors":[str(error)],"gates":{"technical":"FAIL"},"result":"FAIL"}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKER"} else 1


if __name__=="__main__": raise SystemExit(main())
