#!/usr/bin/env python3
"""Independently validate MF-006R5 investigation behavior, preservation, audio, and output."""

import argparse,json
from pathlib import Path
from validate_mf005r3_quality import envelope_check,pcm
from validate_mf006r4_production import BASELINES,loudness,rms,contained,sha

R5_BASELINES=BASELINES|{"MF-006R4":("artifacts/mf-006r4/candidate-a.mp4","3d2eb28237d657e150f89df9b8a97d764af5654eedd686de53970386da59ad71")}

def main():
    p=argparse.ArgumentParser()
    for n in ("project_root","fixture","layout","execution","music_stem","music_reference","sfx_audio","sfx_report","mix","media","contract","output","motion_timeline"):p.add_argument("--"+n.replace("_","-"),required=True)
    a=p.parse_args();errors=[]
    try:
        root=Path(a.project_root);f=json.loads(Path(a.fixture).read_text());layout=json.loads(Path(a.layout).read_text());execution=json.loads(Path(a.execution).read_text());contract=json.loads(Path(a.contract).read_text());mix=json.loads(Path(a.mix).read_text());sfx=json.loads(Path(a.sfx_report).read_text());scene=layout.get("generated_scene",{});circuit=scene.get("circuit_system",{});window=scene.get("projected_data_window",{});projection=scene.get("projection_layout",{});emitter=scene.get("projection_emitter",{});cells=scene.get("background_cells",{});depth=scene.get("depth_system",{});st=scene.get("screen_timeline",{});cta=scene.get("cta",{});live=scene.get("live_investigation",{});overload=scene.get("node_overload_refinement",{});duration=float(f.get("format",{}).get("duration_seconds",0))
        preservation=[]
        for name,(rel,expected) in R5_BASELINES.items():
            path=root/rel;actual=sha(path) if path.is_file() else None;ok=actual==expected;preservation.append({"slice":name,"path":rel,"expected_sha256":expected,"actual_sha256":actual,"result":"PASS" if ok else "FAIL"})
        if any(x["result"]!="PASS" for x in preservation):errors.append("BASELINE_PRESERVATION_FAILED")
        if not 26<=duration<=30:errors.append("RUNTIME_FAILED")
        causal=[circuit.get(k,-1) for k in ("paths_draw_start","paths_draw_complete","energy_flow_start","central_node_charge","overload","burst")]
        if not causal[0]<causal[1]<=causal[2]<causal[3]<causal[4]<causal[5]<st.get("initialize",-1):errors.append("SCREEN_CAUSAL_ORDER_FAILED")
        if circuit.get("path_count",0)<6 or not all(circuit.get(k) is True for k in ("packets_follow_defined_paths","all_paths_terminate_at_central_node","return_energy_uses_same_paths")):errors.append("PATH_FOLLOWING_FAILED")
        required_true=("persistent_instance","same_instance_all_beats","single_coherent_boundary","screen_behavior","typed_text","left_aligned_story_text","content_first","collapse_to_node")
        if window.get("primary_window_count")!=1 or not all(window.get(k) is True for k in required_true) or window.get("split_page_projection") is not False or window.get("book_metaphor") is not False:errors.append("SINGLE_PERSISTENT_WINDOW_FAILED")
        if window.get("wavy_center_line") is not False or window.get("yellow_circular_graphic") is not False or window.get("large_diagnostic_graphic") is not False:errors.append("REJECTED_CENTER_ELEMENTS_PRESENT")
        content=projection.get("content_bounds",{});texts=projection.get("story_text_bounds",[])
        if projection.get("all_story_text_inside_content") is not True or len(texts)!=3 or not all(contained(x,content) for x in texts) or projection.get("node_outside_content") is not True or projection.get("circuit_intensity_behind_window")!="suppressed":errors.append("PROJECTION_TEXT_SAFE_AREA_FAILED")
        if emitter.get("subordinate_to_window") is not True or scene.get("extended_record_activity",{}).get("node_post_projection_intensity",1)>.4:errors.append("EMITTER_HIERARCHY_FAILED")
        chains=[["query_1","typing_1","activity_1","confirm_1","lock_1","refresh_1"],["query_2","typing_2","activity_2","confirm_2","lock_2","refresh_2"],["query_3","typing_3","activity_3","confirm_3","lock_3","collapse"]]
        if any(not all(st.get(c[i],99)<st.get(c[i+1],-1) for i in range(len(c)-1)) for c in chains):errors.append("INVESTIGATION_EVENT_ORDER_FAILED")
        if live.get("single_window_preserved") is not True or live.get("animated_investigations")!=3 or live.get("query_events")!=3 or live.get("confirm_events")!=3 or live.get("discovery_before_confirmation") is not True or len(live.get("beat_behaviors",[]))!=3 or live.get("faux_ui_clutter") is not False:errors.append("LIVE_INVESTIGATION_FAILED")
        if not .3<=overload.get("added_emphasis",0)<=.7 or not .6<=overload.get("duration",0)<=1.0 or not all(overload.get(k) is True for k in ("extra_packet_cadence","brighter_node_pulse","tighter_energy_rings","environment_reaction")) or not st.get("overload_peak",99)<st.get("initialize",-1):errors.append("OVERLOAD_REFINEMENT_FAILED")
        counts=cells.get("counts",{});ratio=float(cells.get("accent_ratio",1))
        if cells.get("dark_majority",0)<=cells.get("accent_count",99) or not .18<=ratio<=.28 or not all(counts.get(k,0)>=2 for k in ("purple","green","blue")) or cells.get("green_phone_visible") is not True or cells.get("green_emphasis",0)<.28 or not all(cells.get(k) is True for k in ("overload_response","record_initialize_response","cta_response")):errors.append("COLOR_CELL_EMPHASIS_FAILED")
        if depth.get("layer_count",0)<4 or depth.get("center_foreground_cable") is not False:errors.append("CLEAN_DEPTH_FAILED")
        if scene.get("strategy")!="godot_live_investigation_refinement" or scene.get("generated_book") is not None or scene.get("projected_codex") is not None:errors.append("R5_STRATEGY_FAILED")
        if not all(cta.get(k) is True for k in ("world_integrated","live_investigation_system","final_resolved_signal","typed_reveal","url_stabilizes")) or not st.get("cta_energy",99)<st.get("cta_typing",-1)<st.get("cta_lock",-1) or cta.get("lock_event")!=st.get("cta_lock"):errors.append("CTA_SYSTEM_INTEGRATION_FAILED")
        configured={x.get("id") for x in scene.get("configured_events",[])};observed={x.get("id") for x in scene.get("observed_events",[])};required_events={f"record_{kind}_{index}" for kind in ("query","confirm","lock") for index in range(1,4)}|{"overload_peak","cta_lock","website_reveal"}
        if configured!=observed or not required_events<=observed:errors.append("EVENT_EXECUTION_FAILED")
        if layout.get("result")!="PASS" or scene.get("result")!="PASS" or scene.get("internal_resolution")!={"width":540,"height":960}:errors.append("LAYOUT_RENDER_FAILED")
        if {b["id"] for b in f["beats"]}!={b.get("id") for b in execution.get("beats",[])} or execution.get("result")!="PASS":errors.append("BEAT_TIMELINE_FAILED")
        stem,rate=pcm(Path(a.music_stem));ref,_=pcm(Path(a.music_reference));fade=envelope_check(stem,ref,float(f["music"]["fade_in"]),float(f["music"]["fade_out"]),rate)
        if fade.get("result")!="PASS":errors.append("MUSIC_HARD_CUT")
        samples,srate=pcm(Path(a.sfx_audio));activity=[]
        for item in sfx.get("events",[]):
            level=rms(samples,srate,float(item["time"]),min(.25,float(item["duration"])));ok=level>-45 and item.get("event") in observed;activity.append({"id":item["id"],"event":item["event"],"time":item["time"],"rms_dbfs":round(level,3),"result":"PASS" if ok else "FAIL"})
        if len(activity)!=12 or any(x["result"]!="PASS" for x in activity):errors.append("DISCOVERY_SFX_FAILED")
        measured=loudness(Path(a.media))
        if not -17<=measured["integrated_lufs"]<=-15 or measured["true_peak_db"]>-1 or mix.get("clipped_samples")!=0:errors.append("LOUDNESS_PEAK_FAILED")
        technical="PASS" if not errors else "FAIL";blockers=contract.get("blockers",[]);motion={"slice":"MF-006R5","circuit_system":circuit,"screen_timeline":st,"projected_data_window":window,"live_investigation":live,"node_overload_refinement":overload,"background_cells":cells,"cta":cta,"events":scene.get("observed_events"),"result":technical};Path(a.motion_timeline).parent.mkdir(parents=True,exist_ok=True);Path(a.motion_timeline).write_text(json.dumps(motion,indent=2)+"\n")
        mapping={"baseline_preservation":"BASELINE_PRESERVATION_FAILED","runtime":"RUNTIME_FAILED","causal_opening":"SCREEN_CAUSAL_ORDER_FAILED","path_following":"PATH_FOLLOWING_FAILED","single_persistent_window":"SINGLE_PERSISTENT_WINDOW_FAILED","rejected_elements_absent":"REJECTED_CENTER_ELEMENTS_PRESENT","text_inside_window":"PROJECTION_TEXT_SAFE_AREA_FAILED","emitter_hierarchy":"EMITTER_HIERARCHY_FAILED","investigation_event_order":"INVESTIGATION_EVENT_ORDER_FAILED","live_investigation":"LIVE_INVESTIGATION_FAILED","overload_refinement":"OVERLOAD_REFINEMENT_FAILED","color_cell_emphasis":"COLOR_CELL_EMPHASIS_FAILED","clean_depth":"CLEAN_DEPTH_FAILED","cta_system_integration":"CTA_SYSTEM_INTEGRATION_FAILED","timeline":"EVENT_EXECUTION_FAILED","music_fades":"MUSIC_HARD_CUT","discovery_sfx":"DISCOVERY_SFX_FAILED","loudness_peak":"LOUDNESS_PEAK_FAILED"}
        result={"slice":"MF-006R5","checks":{k:"PASS" if v not in errors else "FAIL" for k,v in mapping.items()}|{"full_decode":"PASS"},"preservation":preservation,"duration_seconds":duration,"fade_measurement":fade,"audio":measured,"sfx":activity,"blockers":blockers,"errors":errors,"gates":{"visual_audio_technical":technical,"production_voice":"BLOCKED" if blockers else "PASS","human_editorial":"PENDING_HUMAN","release":"RELEASE_ELIGIBLE_NO" if blockers else "PENDING_HUMAN"},"result":"PASS_WITH_BLOCKER" if blockers and not errors else technical}
    except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError) as e:result={"slice":"MF-006R5","errors":[str(e)],"gates":{"visual_audio_technical":"FAIL","release":"RELEASE_ELIGIBLE_NO"},"result":"FAIL"}
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result,indent=2));return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKER"} else 1

if __name__=="__main__":raise SystemExit(main())
