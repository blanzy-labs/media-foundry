#!/usr/bin/env python3
"""Fail-closed approved-copy, destination, generated-world, music, and voice contract for MF-006R1."""

import argparse, hashlib, json
from pathlib import Path

APPROVED = "Framed, hunted, and stripped of his old life, Simon is forced on the run alongside two impossible targets: Leo, a bio-engineered boy acting as a living data bridge, and Zeph, a hunted AI kernel evolving at a terrifying speed. Pursued by the Syndicate—a cabal of global elites using bleeding-edge technology to subjugate the planet—Simon realizes he isn't just a protector. He carries the ultimate weapon. Locked within his own biometrics is the kill-switch to a digital empire. To survive, Simon must navigate a deadly maze of corporate black-ops and untethered artificial intelligence, or watch humanity be quietly enslaved by an unseen hand."
MUSIC = "69cfdc1792c94af1c600fdd868bec87412f6fbdc9477aa94592548faccb2398e"
CANONICAL = "https://rcblanzy.com/books/unknown-process"
PHRASES = ["SIMON IS BEING HUNTED", "TWO IMPOSSIBLE TARGETS", "KILL-SWITCH IN HIS BIOMETRICS"]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--fixture",required=True); p.add_argument("--project-root",required=True); p.add_argument("--output",required=True); a=p.parse_args(); errors=[]; blockers=[]
    try:
        f=json.loads(Path(a.fixture).read_text()); root=Path(a.project_root); subject=f.get("subject",{}); copy=f.get("approved_copy",{}); cta=f.get("cta",{}); voice=f.get("voice_contract",{}); music=f.get("music",{}); strategy=f.get("visual_strategy",{})
        if subject.get("title")!="Unknown Process" or subject.get("canonical_author")!="Robert C. Blanzy" or subject.get("author")!="R.C. Blanzy" or subject.get("book_number")!=1 or subject.get("authoritative_url")!=CANONICAL: errors.append("APPROVED_METADATA_FAILED")
        if copy.get("synopsis")!=APPROVED or copy.get("sole_narrative_basis") is not True or copy.get("invented_plot_details") is not False: errors.append("APPROVED_COPY_FAILED")
        if f.get("page_phrases")!=PHRASES or any(not 3<=len(x.split())<=5 for x in f.get("page_phrases",[])): errors.append("PAGE_PHRASES_FAILED")
        narration=voice.get("narration_text","").casefold()
        for token in ("simon","leo","zeph","living data bridge","ai kernel","biometrics","kill-switch","digital empire","continue the adventure"):
            if token not in narration: errors.append("NARRATION_DERIVATION_FAILED"); break
        if strategy!={"preference":"godot_generated_book_refinement","fallback":"fail","static_book_cover_allowed":False} or f.get("media") is not None: errors.append("GENERATED_REFINEMENT_REQUIRED")
        serialized=json.dumps(f).casefold()
        if any(ext in serialized for ext in ('.png"','.jpg"','.jpeg"')): errors.append("STATIC_COVER_PROHIBITED")
        if cta.get("canonical_url")!=CANONICAL or cta.get("website")!=CANONICAL or cta.get("display_url")!="rcblanzy.com/books/unknown-process": errors.append("APPROVED_DESTINATION_FAILED")
        if voice.get("test_voice_allowed") is not False or voice.get("release_eligible") is not False: errors.append("TEST_VOICE_PROHIBITED")
        if voice.get("status")=="BLOCKED_PRODUCTION_VOICE" and voice.get("available_provider") is None: blockers.append("BLOCKED_PRODUCTION_VOICE")
        else: errors.append("VOICE_CONTRACT_INVALID")
        if any(beat.get("narration") is not None for beat in f.get("beats",[])): errors.append("UNAPPROVED_NARRATION_PRESENT")
        source=root/music.get("source","")
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=MUSIC or music.get("provenance",{}).get("sha256")!=MUSIC: errors.append("SUPPLIED_MUSIC_INVALID")
        ids={e.get("id") for e in f.get("generated_scene",{}).get("events",[])}
        required={"path_draw_start","paths_drawn","energy_flow","central_node_charge","overload","spark_burst","title_form","book_materialized","book_open","page_turn_1","page_turn_2","page_turn_3","book_close","data_dissolve","return_energy","cta_energy","website_reveal"}
        if not required<=ids: errors.append("CAUSAL_EVENT_CONTRACT_FAILED")
        result={"slice":"MF-006R1","approved_source":{"url":CANONICAL,"organization":"Robert C. Blanzy","retrieval_date":subject.get("retrieval_date"),"title":"Unknown Process","author":"Robert C. Blanzy","series":"The Second Presence","book_number":1,"synopsis_sha256":hashlib.sha256(APPROVED.encode()).hexdigest()},"checks":{"metadata":"PASS" if not any("METADATA" in x for x in errors) else "FAIL","approved_copy":"PASS" if "APPROVED_COPY_FAILED" not in errors else "FAIL","destination":"PASS" if "APPROVED_DESTINATION_FAILED" not in errors else "FAIL","generated_only":"PASS" if not any("COVER" in x or "REFINEMENT" in x for x in errors) else "FAIL","music":"PASS" if "SUPPLIED_MUSIC_INVALID" not in errors else "FAIL","voice":"BLOCKED_PRODUCTION_VOICE"},"blockers":blockers,"errors":errors,"result":"PASS_WITH_BLOCKER" if blockers and not errors else ("PASS" if not errors else "FAIL")}
    except (OSError,json.JSONDecodeError,TypeError,ValueError) as e: result={"slice":"MF-006R1","errors":[str(e)],"blockers":[],"result":"FAIL"}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKER"} else 1

if __name__=="__main__": raise SystemExit(main())
