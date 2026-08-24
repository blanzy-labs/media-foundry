#!/usr/bin/env python3
"""Independently validate MF-006 scene events, low-res output, SFX, music, and gates."""

import argparse,json,math,re,subprocess,wave,struct
from pathlib import Path
from validate_mf005r3_quality import envelope_check,pcm

REQUIRED_COMPONENTS={"chamber","circuits","burst","platform","book","page_1","page_2","page_3","dissolve","lights"}
REQUIRED_EVENTS={"circuit_start","circuit_convergence","spark_burst","title_form","book_materialized","camera_push","book_open","page_turn_1","page_turn_2","page_turn_3","book_close","data_dissolve","camera_pull_back","cta_reveal"}


def loudness(path):
    process=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-vn","-af","loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json","-f","null","-"],capture_output=True,text=True); blocks=re.findall(r'\{\s*"input_i".*?\}',process.stderr,re.DOTALL)
    if process.returncode or not blocks: raise ValueError("MF006_AUDIO_FAILED")
    data=json.loads(blocks[-1]); return {"integrated_lufs":float(data["input_i"]),"true_peak_db":float(data["input_tp"]),"loudness_range":float(data["input_lra"])}


def rms_window(samples,rate,start,span):
    values=samples[round(start*rate):round((start+span)*rate)]; return 20*math.log10(max(1e-7,math.sqrt(sum(value*value for value in values)/max(1,len(values)))))


def main():
    parser=argparse.ArgumentParser()
    for name in ("fixture","layout","execution","narration","music","music_stem","music_reference","sfx_audio","sfx_report","mix","media","contract","output","motion_timeline"): parser.add_argument(f"--{name.replace('_','-')}",required=True)
    args=parser.parse_args(); errors=[]
    try:
        fixture=json.loads(Path(args.fixture).read_text()); layout=json.loads(Path(args.layout).read_text()); execution=json.loads(Path(args.execution).read_text()); narration=json.loads(Path(args.narration).read_text()); music=json.loads(Path(args.music).read_text()); mix=json.loads(Path(args.mix).read_text()); contract=json.loads(Path(args.contract).read_text()); sfx=json.loads(Path(args.sfx_report).read_text()); scene=layout.get("generated_scene",{})
        components=set(scene.get("components",[])); observed={item.get("id") for item in scene.get("observed_events",[])}; configured={item.get("id") for item in scene.get("configured_events",[])}
        if layout.get("result")!="PASS" or scene.get("result")!="PASS" or scene.get("strategy")!="godot_generated_scene" or not REQUIRED_COMPONENTS<=components: errors.append("GODOT_GENERATED_SCENE_FAILED")
        if configured!=observed or not REQUIRED_EVENTS<=observed: errors.append("REQUIRED_GENERATED_EVENT_MISSING")
        book=scene.get("generated_book",{})
        if book.get("title")!="Dark Signal" or book.get("author")!="R.C. Blanzy" or not all(book.get(key) is True for key in ("front_cover","back_cover","spine","page_block")) or int(book.get("independent_pages",0))<3: errors.append("GENERATED_BOOK_OBJECT_FAILED")
        if scene.get("static_book_cover_embedded") is not False or scene.get("external_static_media_primary") is not False: errors.append("STATIC_BOOK_COVER_PROHIBITED")
        if scene.get("continuous_scene",{}).get("duration",0)<17 or scene.get("text_hidden_motion_events",0)<10: errors.append("CONTINUOUS_MOTION_FAILED")
        if scene.get("internal_resolution")!={"width":540,"height":960}: errors.append("LOW_RES_RENDER_FAILED")
        if len(scene.get("camera_events",[]))<4: errors.append("CAMERA_LANGUAGE_FAILED")
        expected_beats={beat["id"] for beat in fixture["beats"]}; executed={beat.get("id") for beat in execution.get("beats",[])}
        if expected_beats!=executed: errors.append("TIMELINE_EXECUTION_FAILED")
        stem,rate=pcm(Path(args.music_stem)); reference,_=pcm(Path(args.music_reference)); fade=envelope_check(stem,reference,float(fixture["music"]["fade_in"]),float(fixture["music"]["fade_out"]),rate)
        if fade.get("result")!="PASS": errors.append("MUSIC_HARD_CUT")
        measured=loudness(Path(args.media))
        if not -17<=measured["integrated_lufs"]<=-15 or measured["true_peak_db"]>-1.0 or mix.get("clipped_samples")!=0: errors.append("LOUDNESS_PEAK_FAILED")
        samples,sfx_rate=pcm(Path(args.sfx_audio)); activity=[]
        for item in sfx.get("events",[]):
            level=rms_window(samples,sfx_rate,float(item["time"]),min(.3,float(item["duration"]))); status="PASS" if level>-42 and item.get("event") in observed else "FAIL"; activity.append({"id":item["id"],"event":item["event"],"time":item["time"],"rms_dbfs":round(level,3),"result":status})
        if len(activity)!=9 or any(item["result"]!="PASS" for item in activity): errors.append("PHYSICAL_SFX_FAILED")
        if narration.get("result") not in {"PASS","PASS_WITH_BLOCKER"}: errors.append("NARRATION_SYNC_FAILED")
        blockers=list(dict.fromkeys(list(contract.get("blockers",[]))+list(narration.get("blockers",[])))); visual_audio="PASS" if not errors else "FAIL"
        motion={"slice":"MF-006","continuous_scene":scene.get("continuous_scene"),"components":sorted(components),"events":scene.get("observed_events",[]),"camera_events":scene.get("camera_events",[]),"text_hidden_motion_events":scene.get("text_hidden_motion_events"),"result":visual_audio}; Path(args.motion_timeline).parent.mkdir(parents=True,exist_ok=True); Path(args.motion_timeline).write_text(json.dumps(motion,indent=2)+"\n")
        result={"slice":"MF-006","checks":{"generated_scene":"PASS" if "GODOT_GENERATED_SCENE_FAILED" not in errors else "FAIL","generated_book":"PASS" if "GENERATED_BOOK_OBJECT_FAILED" not in errors else "FAIL","events":"PASS" if "REQUIRED_GENERATED_EVENT_MISSING" not in errors else "FAIL","continuous_motion":"PASS" if "CONTINUOUS_MOTION_FAILED" not in errors else "FAIL","low_resolution":"PASS" if "LOW_RES_RENDER_FAILED" not in errors else "FAIL","camera":"PASS" if "CAMERA_LANGUAGE_FAILED" not in errors else "FAIL","timeline":"PASS" if "TIMELINE_EXECUTION_FAILED" not in errors else "FAIL","music_fades":"PASS" if fade.get("result")=="PASS" else "FAIL","physical_sfx":"PASS" if "PHYSICAL_SFX_FAILED" not in errors else "FAIL","loudness_peak":"PASS" if "LOUDNESS_PEAK_FAILED" not in errors else "FAIL","full_decode":"PASS"},"fade_measurement":fade,"audio":measured,"sfx":activity,"blockers":blockers,"errors":errors,"gates":{"visual_audio_technical":visual_audio,"technical":"FAIL" if blockers else visual_audio,"editorial":"BLOCKED_APPROVED_INPUTS" if blockers else "PENDING_HUMAN","release":"RELEASE_ELIGIBLE_NO" if blockers else "PENDING_HUMAN"},"candidate_valid":False if blockers or errors else True,"result":"PASS_WITH_BLOCKERS" if blockers and not errors else visual_audio}
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError,wave.Error) as error: result={"slice":"MF-006","errors":[str(error)],"gates":{"visual_audio_technical":"FAIL","technical":"FAIL","editorial":"BLOCKED","release":"RELEASE_ELIGIBLE_NO"},"result":"FAIL"}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKERS"} else 1


if __name__=="__main__": raise SystemExit(main())
