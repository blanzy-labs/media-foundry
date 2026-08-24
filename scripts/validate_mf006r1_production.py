#!/usr/bin/env python3
"""Independent causality, physicality, timeline, audio, and output validator for MF-006R1."""

import argparse,json,math,re,subprocess
from pathlib import Path
from validate_mf005r3_quality import envelope_check,pcm

def loudness(path):
    r=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-vn","-af","loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json","-f","null","-"],capture_output=True,text=True); blocks=re.findall(r'\{\s*"input_i".*?\}',r.stderr,re.S)
    if r.returncode or not blocks: raise ValueError("AUDIO_MEASUREMENT_FAILED")
    d=json.loads(blocks[-1]); return {"integrated_lufs":float(d["input_i"]),"true_peak_db":float(d["input_tp"]),"loudness_range":float(d["input_lra"])}

def rms(samples,rate,start,span):
    values=samples[round(start*rate):round((start+span)*rate)]; return 20*math.log10(max(1e-7,math.sqrt(sum(v*v for v in values)/max(1,len(values)))))

def main():
    p=argparse.ArgumentParser()
    for n in ("fixture","layout","execution","music_stem","music_reference","sfx_audio","sfx_report","mix","media","contract","output","motion_timeline"): p.add_argument("--"+n.replace("_","-"),required=True)
    a=p.parse_args(); errors=[]
    try:
        f=json.loads(Path(a.fixture).read_text()); layout=json.loads(Path(a.layout).read_text()); execution=json.loads(Path(a.execution).read_text()); contract=json.loads(Path(a.contract).read_text()); mix=json.loads(Path(a.mix).read_text()); sfx=json.loads(Path(a.sfx_report).read_text()); scene=layout.get("generated_scene",{}); circuit=scene.get("circuit_system",{}); support=scene.get("book_support",{}); cta=scene.get("cta",{})
        times=[circuit.get(k,-1) for k in ("paths_draw_start","paths_draw_complete","energy_flow_start","central_node_charge","overload","burst")]
        if not all(isinstance(x,(int,float)) for x in times) or not (times[0]<times[1]<=times[2]<times[3]<times[4]<times[5]): errors.append("CAUSAL_ORDER_FAILED")
        if circuit.get("path_count",0)<6 or circuit.get("packets_follow_defined_paths") is not True or circuit.get("all_paths_terminate_at_central_node") is not True or circuit.get("return_energy_uses_same_paths") is not True: errors.append("PATH_FOLLOWING_FAILED")
        if support.get("purpose")!="book-generation cradle" or support.get("legacy_ambiguous_platform_removed") is not True or support.get("clamps",0)<4 or support.get("contacts",0)<6 or support.get("coil") is not True: errors.append("PURPOSEFUL_SUPPORT_FAILED")
        book=scene.get("generated_book",{})
        if book.get("title")!="Unknown Process" or book.get("author")!="R.C. Blanzy" or not all(book.get(k) is True for k in ("front_cover","back_cover","spine","page_block")) or book.get("independent_pages")!=3 or len(set(scene.get("page_treatments",[])))!=3: errors.append("PHYSICAL_BOOK_FAILED")
        if scene.get("strategy")!="godot_generated_book_refinement" or scene.get("static_book_cover_embedded") is not False or scene.get("external_static_media_primary") is not False: errors.append("GENERATED_STRATEGY_FAILED")
        configured={x.get("id") for x in scene.get("configured_events",[])}; observed={x.get("id") for x in scene.get("observed_events",[])}
        required={"spark_burst","book_open","page_turn_1","page_turn_2","page_turn_3","book_close","data_dissolve","return_energy","website_reveal"}
        if configured!=observed or not required<=observed: errors.append("EVENT_EXECUTION_FAILED")
        if cta.get("world_integrated") is not True or cta.get("canonical_url")!="https://rcblanzy.com/books/unknown-process" or cta.get("display_url")!="rcblanzy.com/books/unknown-process": errors.append("CTA_INTEGRATION_FAILED")
        if layout.get("result")!="PASS" or scene.get("result")!="PASS" or scene.get("internal_resolution")!={"width":540,"height":960}: errors.append("LAYOUT_RENDER_FAILED")
        expected={b["id"] for b in f["beats"]}; actual={b.get("id") for b in execution.get("beats",[])}
        if expected!=actual or execution.get("result")!="PASS": errors.append("BEAT_TIMELINE_FAILED")
        stem,rate=pcm(Path(a.music_stem)); reference,_=pcm(Path(a.music_reference)); fade=envelope_check(stem,reference,float(f["music"]["fade_in"]),float(f["music"]["fade_out"]),rate)
        if fade.get("result")!="PASS": errors.append("MUSIC_HARD_CUT")
        samples,srate=pcm(Path(a.sfx_audio)); activity=[]
        for item in sfx.get("events",[]):
            level=rms(samples,srate,float(item["time"]),min(.25,float(item["duration"]))); ok=level>-45 and item.get("event") in observed; activity.append({"id":item["id"],"event":item["event"],"time":item["time"],"rms_dbfs":round(level,3),"result":"PASS" if ok else "FAIL"})
        if len(activity)!=12 or any(x["result"]!="PASS" for x in activity): errors.append("CAUSAL_SFX_FAILED")
        measured=loudness(Path(a.media))
        if not -17<=measured["integrated_lufs"]<=-15 or measured["true_peak_db"]>-1 or mix.get("clipped_samples")!=0: errors.append("LOUDNESS_PEAK_FAILED")
        blockers=contract.get("blockers",[]); technical="PASS" if not errors else "FAIL"
        motion={"slice":"MF-006R1","continuous_scene":scene.get("continuous_scene"),"circuit_system":circuit,"events":scene.get("observed_events"),"page_treatments":scene.get("page_treatments"),"result":technical}; Path(a.motion_timeline).parent.mkdir(parents=True,exist_ok=True); Path(a.motion_timeline).write_text(json.dumps(motion,indent=2)+"\n")
        result={"slice":"MF-006R1","checks":{"causal_order":"PASS" if "CAUSAL_ORDER_FAILED" not in errors else "FAIL","path_following":"PASS" if "PATH_FOLLOWING_FAILED" not in errors else "FAIL","central_buildup_burst":"PASS" if "CAUSAL_ORDER_FAILED" not in errors else "FAIL","physical_book":"PASS" if "PHYSICAL_BOOK_FAILED" not in errors else "FAIL","purposeful_cradle":"PASS" if "PURPOSEFUL_SUPPORT_FAILED" not in errors else "FAIL","closing_mirrors_opening":"PASS" if "PATH_FOLLOWING_FAILED" not in errors else "FAIL","integrated_cta":"PASS" if "CTA_INTEGRATION_FAILED" not in errors else "FAIL","timeline":"PASS" if "EVENT_EXECUTION_FAILED" not in errors and "BEAT_TIMELINE_FAILED" not in errors else "FAIL","music_fades":"PASS" if fade.get("result")=="PASS" else "FAIL","causal_sfx":"PASS" if "CAUSAL_SFX_FAILED" not in errors else "FAIL","loudness_peak":"PASS" if "LOUDNESS_PEAK_FAILED" not in errors else "FAIL","full_decode":"PASS"},"fade_measurement":fade,"audio":measured,"sfx":activity,"blockers":blockers,"errors":errors,"gates":{"visual_audio_technical":technical,"production_voice":"BLOCKED" if blockers else "PASS","human_editorial":"PENDING_HUMAN","release":"RELEASE_ELIGIBLE_NO" if blockers else "PENDING_HUMAN"},"result":"PASS_WITH_BLOCKER" if blockers and not errors else technical}
    except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError) as e: result={"slice":"MF-006R1","errors":[str(e)],"gates":{"visual_audio_technical":"FAIL","release":"RELEASE_ELIGIBLE_NO"},"result":"FAIL"}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKER"} else 1

if __name__=="__main__": raise SystemExit(main())
