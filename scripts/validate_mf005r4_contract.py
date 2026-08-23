#!/usr/bin/env python3
"""Validate the R4 generated-scene, supplied-music, editorial, and voice boundary."""

import argparse,hashlib,json
from pathlib import Path


EXPECTED_MUSIC="69cfdc1792c94af1c600fdd868bec87412f6fbdc9477aa94592548faccb2398e"


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--fixture",required=True); parser.add_argument("--project-root",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(); errors=[]; blockers=[]
    try:
        fixture=json.loads(Path(args.fixture).read_text()); strategy=fixture.get("visual_strategy",{}); scene=fixture.get("generated_scene",{}); voice=fixture.get("voice_contract",{}); music=fixture.get("music",{})
        if strategy.get("preference")!="generated_scene" or strategy.get("source_priority",[])[:2]!=["godot_procedural","godot_project_asset"]: errors.append("VISUAL_STRATEGY_FAILED: generated-scene priority is absent")
        if fixture.get("media") is not None or strategy.get("static_media_policy",{}).get("primary_storytelling") is not False: errors.append("STATIC_MEDIA_PRIMARY_FAILED: generated production silently uses static media")
        if float(scene.get("end",0))-float(scene.get("start",0))<5 or len(scene.get("components",[]))<8 or len(scene.get("events",[]))<8: errors.append("GENERATED_SCENE_CONFIG_FAILED: persistent world contract is incomplete")
        source=Path(music.get("source","")); source=source if source.is_absolute() else Path(args.project_root)/source
        if not source.is_file(): errors.append("NEW_MUSIC_ASSET_MISSING")
        elif hashlib.sha256(source.read_bytes()).hexdigest()!=EXPECTED_MUSIC or music.get("provenance",{}).get("sha256")!=EXPECTED_MUSIC: errors.append("NEW_MUSIC_ASSET_INVALID: supplied R4 hash differs")
        reveal=next((beat for beat in fixture.get("beats",[]) if beat.get("id")=="reveal"),{})
        spoken=fixture.get("creative_contract",{}).get("required_spoken",{}).get("product_name","")
        visual=fixture.get("creative_contract",{}).get("required_visual",{}).get("product_name","")
        if not visual or str(reveal.get("text","")).casefold()!=str(visual).casefold(): errors.append("PRODUCT_NAME_DISPLAY_FAILED")
        if voice.get("test_voice_allowed") is not False: errors.append("TEST_VOICE_PROHIBITED: release candidate permits regression voice")
        if voice.get("status")=="BLOCKED_PRODUCTION_VOICE" and voice.get("available_provider") is None: blockers.append("BLOCKED_PRODUCTION_VOICE")
        else:
            narration=" ".join(str((beat.get("narration") or {}).get("text","")) for beat in fixture.get("beats",[]))
            if not spoken or spoken.casefold() not in narration.casefold(): errors.append("PRODUCT_NAME_SPOKEN_FAILED")
        gates={"visual_contract":"PASS" if not any("VISUAL" in item or "STATIC" in item or "SCENE" in item for item in errors) else "FAIL","music_contract":"PASS" if not any("MUSIC" in item for item in errors) else "FAIL","displayed_product_name":"PASS" if not any("DISPLAY" in item for item in errors) else "FAIL","voice":"BLOCKED_PRODUCTION_VOICE" if blockers else ("PASS" if not any("VOICE" in item or "SPOKEN" in item for item in errors) else "FAIL")}
        result={"slice":"MF-005R4","fixture":fixture.get("id"),"checks":gates,"blockers":blockers,"errors":errors,"candidate_valid":False if blockers or errors else True,"result":"PASS_WITH_BLOCKER" if blockers and not errors else ("PASS" if not errors else "FAIL")}
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as error: result={"slice":"MF-005R4","errors":[str(error)],"result":"FAIL"}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"] in {"PASS","PASS_WITH_BLOCKER"} else 1


if __name__=="__main__": raise SystemExit(main())
