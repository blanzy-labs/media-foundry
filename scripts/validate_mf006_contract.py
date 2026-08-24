#!/usr/bin/env python3
"""Fail-closed MF-006 approved-content, generated-book, music, voice, and CTA contract."""

import argparse,hashlib,json
from pathlib import Path

EXPECTED_MUSIC="69cfdc1792c94af1c600fdd868bec87412f6fbdc9477aa94592548faccb2398e"
APPROVED_DESCRIPTION="The strangest AI conversations aren't happening in labs. They're happening in fiction."


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--fixture",required=True); parser.add_argument("--project-root",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(); errors=[]; blockers=[]
    try:
        fixture=json.loads(Path(args.fixture).read_text()); root=Path(args.project_root); subject=fixture.get("subject",{}); strategy=fixture.get("visual_strategy",{}); voice=fixture.get("voice_contract",{}); cta=fixture.get("cta",{}); music=fixture.get("music",{})
        if strategy.get("preference")!="godot_generated_scene" or strategy.get("fallback")!="fail": errors.append("GENERATED_SCENE_REQUIRED")
        if fixture.get("media") is not None or strategy.get("static_book_cover_allowed") is not False: errors.append("STATIC_BOOK_COVER_PROHIBITED")
        serialized=json.dumps(fixture).casefold()
        if "books-dark-signal.png" in serialized or any(token in serialized for token in (".jpg\"",".jpeg\"",".png\"")): errors.append("STATIC_BOOK_COVER_PROHIBITED")
        if subject.get("type")!="book" or subject.get("title")!="Dark Signal" or subject.get("author")!="R.C. Blanzy" or subject.get("book_number")!=2: errors.append("APPROVED_BOOK_METADATA_FAILED")
        if not subject.get("metadata_provenance") or fixture.get("approved_copy",{}).get("description")!=APPROVED_DESCRIPTION or fixture.get("approved_copy",{}).get("invented_plot_details") is not False: errors.append("APPROVED_COPY_FAILED")
        phrases=fixture.get("page_phrases",[])
        if len(phrases)!=3 or any(not 3<=len(str(value).split())<=7 for value in phrases): errors.append("PAGE_PHRASE_CONTRACT_FAILED")
        if cta.get("text")!="Continue the adventure": errors.append("CTA_TEXT_FAILED")
        if not cta.get("website"): blockers.append("BLOCKED_APPROVED_WEBSITE")
        if voice.get("test_voice_allowed") is not False or voice.get("release_eligible") is not False: errors.append("TEST_ONLY_VOICE_PROHIBITED")
        if voice.get("status")=="BLOCKED_PRODUCTION_VOICE" and voice.get("available_provider") is None: blockers.append("BLOCKED_PRODUCTION_VOICE")
        else:
            narration=" ".join(str((beat.get("narration") or {}).get("text","")) for beat in fixture.get("beats",[]))
            if voice.get("required_final_line","").casefold() not in narration.casefold(): errors.append("FINAL_VOICE_LINE_MISSING")
        if any(beat.get("narration") is not None for beat in fixture.get("beats",[])) and blockers: errors.append("UNAPPROVED_NARRATION_PRESENT")
        source=Path(music.get("source","")); source=source if source.is_absolute() else root/source
        if not source.is_file(): errors.append("SUPPLIED_MUSIC_MISSING")
        elif hashlib.sha256(source.read_bytes()).hexdigest()!=EXPECTED_MUSIC or music.get("provenance",{}).get("sha256")!=EXPECTED_MUSIC: errors.append("SUPPLIED_MUSIC_INVALID")
        if not .8<=float(music.get("fade_in",0))<=1.5 or not 1.2<=float(music.get("fade_out",0))<=2.0: errors.append("MUSIC_FADE_CONTRACT_FAILED")
        events={item.get("id") for item in fixture.get("generated_scene",{}).get("events",[])}
        required={"circuit_convergence","spark_burst","book_materialized","book_open","page_turn_1","page_turn_2","page_turn_3","book_close","data_dissolve","cta_reveal"}
        if not required<=events: errors.append("REQUIRED_GENERATED_EVENT_MISSING")
        result={"slice":"MF-006","fixture":fixture.get("id"),"checks":{"approved_metadata":"PASS" if not any("METADATA" in item or "COPY" in item for item in errors) else "FAIL","generated_strategy":"PASS" if not any("SCENE" in item or "STATIC" in item for item in errors) else "FAIL","music":"PASS" if not any("MUSIC" in item for item in errors) else "FAIL","voice":"BLOCKED_PRODUCTION_VOICE" if "BLOCKED_PRODUCTION_VOICE" in blockers else "PASS","website":"BLOCKED_APPROVED_WEBSITE" if "BLOCKED_APPROVED_WEBSITE" in blockers else "PASS"},"blockers":blockers,"errors":errors,"candidate_valid":False if blockers or errors else True,"result":"PASS_WITH_BLOCKERS" if blockers and not errors else ("PASS" if not errors else "FAIL")}
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as error: result={"slice":"MF-006","errors":[str(error)],"blockers":[],"result":"FAIL"}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKERS"} else 1


if __name__=="__main__": raise SystemExit(main())
