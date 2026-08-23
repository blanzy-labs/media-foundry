#!/usr/bin/env python3
"""Validate R3 creative intent and release-eligibility asset safeguards."""

import argparse,json
from pathlib import Path


MESSAGES={"this_is_a_game","stealth_game","dung_beetle_protagonist","steals_turds","product_name"}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--fixture",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(); errors=[]
    try:
        fixture=json.loads(Path(args.fixture).read_text()); contract=fixture.get("creative_contract",{}); voice=fixture.get("voice_profile",{}); beats={beat["id"]:beat for beat in fixture.get("beats",[])}
        if contract.get("objective")!="promote_game" or contract.get("subject")!={"name":"Turd Burglar","type":"game"} or set(contract.get("required_messages",[]))!=MESSAGES: errors.append("CREATIVE_CONTRACT_FAILED: objective, subject, or messages are incomplete")
        owners=contract.get("message_beats",{})
        if any(owners.get(message) not in beats for message in MESSAGES): errors.append("CREATIVE_CONTRACT_FAILED: required message ownership is incomplete")
        reveal=beats.get(owners.get("product_name"),{}); spoken=contract.get("required_spoken",{}).get("product_name",""); visual=contract.get("required_visual",{}).get("product_name","")
        if not spoken or spoken.casefold() not in str((reveal.get("narration") or {}).get("text","")).casefold(): errors.append("EDITORIAL_REQUIREMENT_FAILED: required_spoken: product_name")
        if not visual or visual.casefold()!=str(reveal.get("text","")).casefold(): errors.append("EDITORIAL_REQUIREMENT_FAILED: required_visual: product_name")
        if not isinstance(voice.get("character"),list) or voice.get("energy") not in {"low","medium","high"} or not voice.get("delivery"): errors.append("VOICE_PROFILE_FAILED: editorial voice intent is incomplete")
        narration=[beat["narration"] for beat in beats.values() if beat.get("narration")]
        voice_release=voice.get("release_eligible") is True and voice.get("asset_class") in {"approved","production"} and all(item.get("provenance",{}).get("release_eligible") is True for item in narration)
        if voice.get("asset_class")=="test_only" and voice.get("release_eligible") is not False: errors.append("VOICE_ASSET_CLASS_FAILED: test-only voice must explicitly be non-release-eligible")
        media=fixture.get("media",{}); music=fixture.get("music",{})
        if media.get("provenance",{}).get("release_eligible") is not True or music.get("provenance",{}).get("release_eligible") is not True: errors.append("PRODUCTION_ASSET_FAILED: approved media/music classification missing")
        checks={"creative_contract":"PASS" if not any("CREATIVE" in item for item in errors) else "FAIL","spoken_product_name":"PASS" if not any("required_spoken" in item for item in errors) else "FAIL","visual_product_name":"PASS" if not any("required_visual" in item for item in errors) else "FAIL","voice_profile":"PASS" if not any("VOICE_PROFILE" in item for item in errors) else "FAIL","voice_classification":"PASS" if not any("VOICE_ASSET_CLASS" in item for item in errors) else "FAIL","production_media_music":"PASS" if not any("PRODUCTION_ASSET" in item for item in errors) else "FAIL"}
        result={"slice":"MF-005R3","fixture":fixture.get("id"),"checks":checks,"voice":{"provider":voice.get("provider"),"voice":voice.get("voice"),"asset_class":voice.get("asset_class"),"release_eligible":voice_release,"limitation":voice.get("limitation")},"gates":{"technical":"PASS" if not errors else "FAIL","editorial":"PENDING_HUMAN","release":"PENDING_HUMAN" if voice_release else "BLOCKED_VOICE_ASSET"},"errors":errors,"result":"PASS" if not errors else "FAIL"}
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as error: result={"slice":"MF-005R3","errors":[str(error)],"result":"FAIL"}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
