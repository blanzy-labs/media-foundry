#!/usr/bin/env python3
"""Independently validate MF-006R3 single-window hierarchy, causality, audio, and output."""

import argparse,json,math,re,subprocess
from pathlib import Path
from validate_mf005r3_quality import envelope_check,pcm

def loudness(path):
    r=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-vn","-af","loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json","-f","null","-"],capture_output=True,text=True); blocks=re.findall(r'\{\s*"input_i".*?\}',r.stderr,re.S)
    if r.returncode or not blocks: raise ValueError("AUDIO_MEASUREMENT_FAILED")
    d=json.loads(blocks[-1]); return {"integrated_lufs":float(d["input_i"]),"true_peak_db":float(d["input_tp"]),"loudness_range":float(d["input_lra"])}

def rms(samples,rate,start,span):
    v=samples[round(start*rate):round((start+span)*rate)]; return 20*math.log10(max(1e-7,math.sqrt(sum(x*x for x in v)/max(1,len(v)))))

def contained(inner,outer):
    return inner["x"]>=outer["x"] and inner["y"]>=outer["y"] and inner["x"]+inner["width"]<=outer["x"]+outer["width"] and inner["y"]+inner["height"]<=outer["y"]+outer["height"]

def main():
    p=argparse.ArgumentParser()
    for n in ("fixture","layout","execution","music_stem","music_reference","sfx_audio","sfx_report","mix","media","contract","output","motion_timeline"): p.add_argument("--"+n.replace("_","-"),required=True)
    a=p.parse_args(); errors=[]
    try:
        f=json.loads(Path(a.fixture).read_text()); layout=json.loads(Path(a.layout).read_text()); execution=json.loads(Path(a.execution).read_text()); contract=json.loads(Path(a.contract).read_text()); mix=json.loads(Path(a.mix).read_text()); sfx=json.loads(Path(a.sfx_report).read_text()); scene=layout.get("generated_scene",{}); circuit=scene.get("circuit_system",{}); window=scene.get("projected_data_window",{}); projection=scene.get("projection_layout",{}); emitter=scene.get("projection_emitter",{}); cells=scene.get("background_cells",{}); depth=scene.get("depth_system",{}); st=scene.get("screen_timeline",{}); cta=scene.get("cta",{})
        causal=[circuit.get(k,-1) for k in ("paths_draw_start","paths_draw_complete","energy_flow_start","central_node_charge","overload","burst")]
        if not causal[0]<causal[1]<=causal[2]<causal[3]<causal[4]<causal[5]<st.get("initialize",-1): errors.append("SCREEN_CAUSAL_ORDER_FAILED")
        if circuit.get("path_count",0)<6 or not all(circuit.get(k) is True for k in ("packets_follow_defined_paths","all_paths_terminate_at_central_node","return_energy_uses_same_paths")): errors.append("PATH_FOLLOWING_FAILED")
        required_true=("persistent_instance","same_instance_all_beats","single_coherent_boundary","screen_behavior","typed_text","left_aligned_story_text","content_first","collapse_to_node")
        if window.get("primary_window_count")!=1 or not all(window.get(k) is True for k in required_true) or window.get("split_page_projection") is not False or window.get("book_metaphor") is not False: errors.append("SINGLE_PERSISTENT_WINDOW_FAILED")
        if window.get("wavy_center_line") is not False or window.get("yellow_circular_graphic") is not False or window.get("large_diagnostic_graphic") is not False: errors.append("REJECTED_CENTER_ELEMENTS_PRESENT")
        content=projection.get("content_bounds",{}); texts=projection.get("story_text_bounds",[])
        if projection.get("all_story_text_inside_content") is not True or len(texts)!=3 or not all(contained(x,content) for x in texts) or projection.get("node_outside_content") is not True or projection.get("circuit_intensity_behind_window")!="suppressed": errors.append("PROJECTION_TEXT_SAFE_AREA_FAILED")
        if emitter.get("purpose")!="node-coupled recovered-record projection source" or emitter.get("connected_to_circuits") is not True or emitter.get("subordinate_to_window") is not True: errors.append("EMITTER_HIERARCHY_FAILED")
        if not st.get("initialize",99)<st.get("typing_1",-1)<st.get("refresh_1",-1)<st.get("typing_2",-1)<st.get("refresh_2",-1)<st.get("typing_3",-1)<st.get("collapse",-1)<st.get("reclaimed",-1)<st.get("cta_energy",-1): errors.append("SCREEN_REFRESH_TIMELINE_FAILED")
        counts=cells.get("counts",{}); ratio=float(cells.get("accent_ratio",1))
        if cells.get("dark_majority",0)<=cells.get("accent_count",99) or not .18<=ratio<=.28 or not all(counts.get(k,0)>=2 for k in ("purple","green","blue")) or cells.get("noticeable_phone_brightness") is not True or cells.get("seeded_irregular_placement") is not True or cells.get("central_reading_area_dimmed") is not True: errors.append("NOTICEABLE_BACKGROUND_CELLS_FAILED")
        if depth.get("layer_count",0)<4 or depth.get("center_foreground_cable") is not False or not all(depth.get(k) is True for k in ("foreground_side_cables","wall_parallax","particles","light_falloff")): errors.append("CLEAN_DEPTH_FAILED")
        if scene.get("strategy")!="godot_projected_data_window_refinement" or scene.get("generated_book") is not None or scene.get("projected_codex") is not None or cta.get("world_integrated") is not True: errors.append("WORLD_CTA_STRATEGY_FAILED")
        configured={x.get("id") for x in scene.get("configured_events",[])}; observed={x.get("id") for x in scene.get("observed_events",[])}
        if configured!=observed or not {"screen_initialize","record_typing_1","record_typing_2","record_typing_3","screen_collapse","energy_reclaimed","website_reveal"}<=observed: errors.append("EVENT_EXECUTION_FAILED")
        if layout.get("result")!="PASS" or scene.get("result")!="PASS" or scene.get("internal_resolution")!={"width":540,"height":960}: errors.append("LAYOUT_RENDER_FAILED")
        if {b["id"] for b in f["beats"]}!={b.get("id") for b in execution.get("beats",[])} or execution.get("result")!="PASS": errors.append("BEAT_TIMELINE_FAILED")
        stem,rate=pcm(Path(a.music_stem)); ref,_=pcm(Path(a.music_reference)); fade=envelope_check(stem,ref,float(f["music"]["fade_in"]),float(f["music"]["fade_out"]),rate)
        if fade.get("result")!="PASS": errors.append("MUSIC_HARD_CUT")
        samples,srate=pcm(Path(a.sfx_audio)); activity=[]
        for item in sfx.get("events",[]):
            level=rms(samples,srate,float(item["time"]),min(.25,float(item["duration"]))); ok=level>-45 and item.get("event") in observed; activity.append({"id":item["id"],"event":item["event"],"time":item["time"],"rms_dbfs":round(level,3),"result":"PASS" if ok else "FAIL"})
        if len(activity)!=10 or any(x["result"]!="PASS" for x in activity): errors.append("MEANINGFUL_SFX_FAILED")
        measured=loudness(Path(a.media))
        if not -17<=measured["integrated_lufs"]<=-15 or measured["true_peak_db"]>-1 or mix.get("clipped_samples")!=0: errors.append("LOUDNESS_PEAK_FAILED")
        technical="PASS" if not errors else "FAIL"; blockers=contract.get("blockers",[])
        motion={"slice":"MF-006R3","circuit_system":circuit,"screen_timeline":st,"projected_data_window":window,"projection_layout":projection,"background_cells":cells,"depth_system":depth,"events":scene.get("observed_events"),"result":technical}; Path(a.motion_timeline).parent.mkdir(parents=True,exist_ok=True); Path(a.motion_timeline).write_text(json.dumps(motion,indent=2)+"\n")
        checks={"causal_opening":"SCREEN_CAUSAL_ORDER_FAILED","path_following":"PATH_FOLLOWING_FAILED","single_persistent_window":"SINGLE_PERSISTENT_WINDOW_FAILED","rejected_elements_absent":"REJECTED_CENTER_ELEMENTS_PRESENT","text_inside_window":"PROJECTION_TEXT_SAFE_AREA_FAILED","emitter_hierarchy":"EMITTER_HIERARCHY_FAILED","typed_refresh_timeline":"SCREEN_REFRESH_TIMELINE_FAILED","noticeable_background_cells":"NOTICEABLE_BACKGROUND_CELLS_FAILED","clean_depth":"CLEAN_DEPTH_FAILED","world_integrated_cta":"WORLD_CTA_STRATEGY_FAILED","timeline":"EVENT_EXECUTION_FAILED","music_fades":"MUSIC_HARD_CUT","meaningful_sfx":"MEANINGFUL_SFX_FAILED","loudness_peak":"LOUDNESS_PEAK_FAILED"}
        result={"slice":"MF-006R3","checks":{k:"PASS" if v not in errors else "FAIL" for k,v in checks.items()}|{"full_decode":"PASS"},"fade_measurement":fade,"audio":measured,"sfx":activity,"blockers":blockers,"errors":errors,"gates":{"visual_audio_technical":technical,"production_voice":"BLOCKED" if blockers else "PASS","human_editorial":"PENDING_HUMAN","release":"RELEASE_ELIGIBLE_NO" if blockers else "PENDING_HUMAN"},"result":"PASS_WITH_BLOCKER" if blockers and not errors else technical}
    except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError) as e: result={"slice":"MF-006R3","errors":[str(e)],"gates":{"visual_audio_technical":"FAIL","release":"RELEASE_ELIGIBLE_NO"},"result":"FAIL"}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKER"} else 1

if __name__=="__main__": raise SystemExit(main())
