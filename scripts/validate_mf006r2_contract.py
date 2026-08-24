#!/usr/bin/env python3
"""Fail-closed approved-copy, projected-codex, destination, music, and voice contract."""

import argparse,hashlib,json
from pathlib import Path
from validate_mf006r1_contract import APPROVED,MUSIC,CANONICAL,PHRASES

def main():
    p=argparse.ArgumentParser(); p.add_argument("--fixture",required=True); p.add_argument("--project-root",required=True); p.add_argument("--output",required=True); a=p.parse_args(); errors=[]; blockers=[]
    try:
        f=json.loads(Path(a.fixture).read_text()); root=Path(a.project_root); s=f.get("subject",{}); copy=f.get("approved_copy",{}); strategy=f.get("visual_strategy",{}); cta=f.get("cta",{}); voice=f.get("voice_contract",{}); music=f.get("music",{})
        if s.get("title")!="Unknown Process" or s.get("canonical_author")!="Robert C. Blanzy" or s.get("author")!="R.C. Blanzy" or s.get("book_number")!=1 or s.get("authoritative_url")!=CANONICAL: errors.append("APPROVED_METADATA_FAILED")
        if copy.get("synopsis")!=APPROVED or copy.get("sole_narrative_basis") is not True or copy.get("invented_plot_details") is not False or f.get("page_phrases")!=PHRASES: errors.append("APPROVED_COPY_FAILED")
        if strategy!={"preference":"godot_projected_codex_refinement","fallback":"fail","static_book_cover_allowed":False} or f.get("media") is not None: errors.append("PROJECTED_CODEX_REQUIRED")
        components={x.get("type") for x in f.get("generated_scene",{}).get("components",[])}
        if "generated_book" in components or "book_generation_cradle" in components or "electronic_platform" in components or not {"projected_codex","projection_emitter","projection_plane","powered_cells"}<=components: errors.append("PHYSICAL_BOOK_CENTER_PROHIBITED")
        if any(ext in json.dumps(f).casefold() for ext in ('.png"','.jpg"','.jpeg"')): errors.append("STATIC_COVER_PROHIBITED")
        if cta.get("canonical_url")!=CANONICAL or cta.get("display_url")!="rcblanzy.com/books/unknown-process": errors.append("APPROVED_DESTINATION_FAILED")
        if voice.get("test_voice_allowed") is not False or voice.get("release_eligible") is not False or any(b.get("narration") is not None for b in f.get("beats",[])): errors.append("TEST_VOICE_PROHIBITED")
        if voice.get("status")=="BLOCKED_PRODUCTION_VOICE" and voice.get("available_provider") is None: blockers.append("BLOCKED_PRODUCTION_VOICE")
        else: errors.append("VOICE_CONTRACT_INVALID")
        source=root/music.get("source","")
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=MUSIC or music.get("provenance",{}).get("sha256")!=MUSIC: errors.append("SUPPLIED_MUSIC_INVALID")
        ids={x.get("id") for x in f.get("generated_scene",{}).get("events",[])}; required={"path_draw_start","paths_drawn","energy_flow","central_node_charge","overload","spark_burst","projection_emission","title_stabilized","codex_unfold","projection_beat_1","projection_beat_2","projection_beat_3","projection_collapse","energy_reclaimed","return_energy","cta_energy","website_reveal"}
        if not required<=ids: errors.append("PROJECTION_EVENT_CONTRACT_FAILED")
        result={"slice":"MF-006R2","approved_source":{"url":CANONICAL,"organization":"Robert C. Blanzy","retrieval_date":s.get("retrieval_date"),"title":"Unknown Process","author":"Robert C. Blanzy","series":"The Second Presence","book_number":1,"synopsis_sha256":hashlib.sha256(APPROVED.encode()).hexdigest()},"checks":{"metadata":"PASS" if "APPROVED_METADATA_FAILED" not in errors else "FAIL","approved_copy":"PASS" if "APPROVED_COPY_FAILED" not in errors else "FAIL","projected_codex_only":"PASS" if not any("BOOK_CENTER" in x or "CODEX_REQUIRED" in x or "COVER" in x for x in errors) else "FAIL","destination":"PASS" if "APPROVED_DESTINATION_FAILED" not in errors else "FAIL","music":"PASS" if "SUPPLIED_MUSIC_INVALID" not in errors else "FAIL","voice":"BLOCKED_PRODUCTION_VOICE"},"blockers":blockers,"errors":errors,"result":"PASS_WITH_BLOCKER" if blockers and not errors else ("PASS" if not errors else "FAIL")}
    except (OSError,json.JSONDecodeError,TypeError,ValueError) as e: result={"slice":"MF-006R2","errors":[str(e)],"blockers":[],"result":"FAIL"}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKER"} else 1

if __name__=="__main__": raise SystemExit(main())
