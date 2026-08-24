#!/usr/bin/env python3
"""Fail-closed approved-copy and extended recovered-record contract for MF-006R4."""

import argparse,hashlib,json
from pathlib import Path
from validate_mf006r1_contract import APPROVED,MUSIC,CANONICAL,PHRASES

PREFERENCE="godot_extended_data_window_refinement"

def main():
    p=argparse.ArgumentParser(); p.add_argument("--fixture",required=True); p.add_argument("--project-root",required=True); p.add_argument("--output",required=True); a=p.parse_args(); errors=[]; blockers=[]
    try:
        f=json.loads(Path(a.fixture).read_text()); root=Path(a.project_root); s=f.get("subject",{}); copy=f.get("approved_copy",{}); strategy=f.get("visual_strategy",{}); cta=f.get("cta",{}); voice=f.get("voice_contract",{}); music=f.get("music",{}); scene=f.get("generated_scene",{}); duration=f.get("format",{}).get("duration_seconds")
        if s.get("title")!="Unknown Process" or s.get("canonical_author")!="Robert C. Blanzy" or s.get("author")!="R.C. Blanzy" or s.get("book_number")!=1 or s.get("authoritative_url")!=CANONICAL: errors.append("APPROVED_METADATA_FAILED")
        if copy.get("synopsis")!=APPROVED or copy.get("sole_narrative_basis") is not True or copy.get("invented_plot_details") is not False or f.get("page_phrases")!=PHRASES: errors.append("APPROVED_COPY_FAILED")
        if strategy!={"preference":PREFERENCE,"fallback":"fail","static_book_cover_allowed":False} or f.get("media") is not None: errors.append("EXTENDED_DATA_WINDOW_STRATEGY_REQUIRED")
        if not isinstance(duration,(int,float)) or not 26<=duration<=30 or abs(sum(float(b.get("duration",0)) for b in f.get("beats",[]))-duration)>1e-6: errors.append("EXTENDED_DURATION_FAILED")
        types=[x.get("type") for x in scene.get("components",[])]; serialized=json.dumps(f).casefold()
        if types.count("projected_data_window")!=1 or any(x in types for x in ("projected_codex","projection_plane","generated_book","book_generation_cradle","electronic_platform")): errors.append("SINGLE_WINDOW_COMPONENT_FAILED")
        if any(ext in serialized for ext in ('.png"','.jpg"','.jpeg"')): errors.append("STATIC_COVER_PROHIBITED")
        if cta.get("canonical_url")!=CANONICAL or cta.get("display_url")!="rcblanzy.com/books/unknown-process": errors.append("APPROVED_DESTINATION_FAILED")
        if voice.get("test_voice_allowed") is not False or voice.get("release_eligible") is not False or any(b.get("narration") is not None for b in f.get("beats",[])): errors.append("TEST_VOICE_PROHIBITED")
        if voice.get("status")=="BLOCKED_PRODUCTION_VOICE" and voice.get("available_provider") is None: blockers.append("BLOCKED_PRODUCTION_VOICE")
        else: errors.append("VOICE_CONTRACT_INVALID")
        source=root/music.get("source","")
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=MUSIC or music.get("provenance",{}).get("sha256")!=MUSIC: errors.append("SUPPLIED_MUSIC_INVALID")
        events={x.get("id"):x.get("time") for x in scene.get("events",[])}
        required={"path_draw_start","paths_drawn","energy_flow","central_node_charge","overload","spark_burst","screen_initialize","record_typing_1","record_activity_1","record_lock_1","screen_refresh_1","record_typing_2","record_activity_2","record_lock_2","screen_refresh_2","record_typing_3","record_activity_3","record_lock_3","screen_collapse","energy_reclaimed","return_energy","cta_energy","cta_typing","website_reveal"}
        if not required<=events.keys(): errors.append("EXTENDED_EVENT_CONTRACT_FAILED")
        elif not (events["record_typing_1"]<events["record_activity_1"]<events["record_lock_1"]<events["screen_refresh_1"]<events["record_typing_2"]<events["record_activity_2"]<events["record_lock_2"]<events["screen_refresh_2"]<events["record_typing_3"]<events["record_activity_3"]<events["record_lock_3"]<events["screen_collapse"]<events["cta_typing"]<events["website_reveal"]<=duration-2): errors.append("EXTENDED_EVENT_ORDER_FAILED")
        checks={"metadata":"APPROVED_METADATA_FAILED","approved_copy":"APPROVED_COPY_FAILED","extended_duration":"EXTENDED_DURATION_FAILED","single_data_window":"SINGLE_WINDOW_COMPONENT_FAILED","event_pacing":"EXTENDED_EVENT_ORDER_FAILED","destination":"APPROVED_DESTINATION_FAILED","music":"SUPPLIED_MUSIC_INVALID"}
        result={"slice":"MF-006R4","approved_source":{"url":CANONICAL,"organization":"Robert C. Blanzy","retrieval_date":s.get("retrieval_date"),"title":"Unknown Process","author":"Robert C. Blanzy","series":"The Second Presence","book_number":1,"synopsis_sha256":hashlib.sha256(APPROVED.encode()).hexdigest()},"duration_seconds":duration,"checks":{k:"PASS" if v not in errors else "FAIL" for k,v in checks.items()}|{"voice":"BLOCKED_PRODUCTION_VOICE"},"blockers":blockers,"errors":errors,"result":"PASS_WITH_BLOCKER" if blockers and not errors else ("PASS" if not errors else "FAIL")}
    except (OSError,json.JSONDecodeError,TypeError,ValueError) as e: result={"slice":"MF-006R4","errors":[str(e)],"blockers":[],"result":"FAIL"}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKER"} else 1

if __name__=="__main__": raise SystemExit(main())
