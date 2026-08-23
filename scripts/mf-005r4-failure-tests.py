#!/usr/bin/env python3
"""Controlled R4 generated-scene, music, voice, title, event, and fade failures."""

import argparse,copy,json,subprocess,tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--repo-root",required=True); parser.add_argument("--artifacts",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(); root=Path(args.repo_root); a=Path(args.artifacts); fixture=json.loads((a/"timelines/candidate-b-fixture.json").read_text()); results={}
    with tempfile.TemporaryDirectory(prefix="mf005r4-failures-") as directory:
        temp=Path(directory)
        def contract_case(name,mutate,expected):
            value=copy.deepcopy(fixture); mutate(value); source=temp/f"{name}.json"; report=temp/f"{name}-report.json"; source.write_text(json.dumps(value)); process=subprocess.run(["python3",str(root/"scripts/validate_mf005r4_contract.py"),"--fixture",str(source),"--project-root",str(root),"--output",str(report)],capture_output=True,text=True); payload=json.loads(report.read_text()); passed=process.returncode!=0 and any(expected in item for item in payload.get("errors",[])); results[name]={"result":"PASS" if passed else "FAIL","observed":payload.get("errors",[])}
        contract_case("static_media_primary",lambda value:value.update(media={"type":"screenshot","source":"media/screenshots/turd-burglar-gameplay.png"}),"STATIC_MEDIA_PRIMARY_FAILED")
        contract_case("new_music_missing",lambda value:value["music"].update(source=str(temp/"missing.mp3")),"NEW_MUSIC_ASSET_MISSING")
        contract_case("test_voice_release_candidate",lambda value:value["voice_contract"].update(status="READY",available_provider="local_ffmpeg_flite",test_voice_allowed=True),"TEST_VOICE_PROHIBITED")
        contract_case("product_name_not_displayed",lambda value:next(beat for beat in value["beats"] if beat["id"]=="reveal").update(text="THE GAME"),"PRODUCT_NAME_DISPLAY_FAILED")
        contract_case("product_name_not_spoken",lambda value:value["voice_contract"].update(status="READY",available_provider="approved_provider"),"PRODUCT_NAME_SPOKEN_FAILED")

        def production_case(name,fixture_mutate=lambda value:None,layout_mutate=lambda value:None,use_reference=False,expected=""):
            value=copy.deepcopy(fixture); layout=json.loads((a/"validation/candidate-b-layout.json").read_text()); fixture_mutate(value); layout_mutate(layout); fixture_path=temp/f"{name}-fixture.json"; layout_path=temp/f"{name}-layout.json"; report=temp/f"{name}-report.json"; fixture_path.write_text(json.dumps(value)); layout_path.write_text(json.dumps(layout)); stem=a/("music/candidate-b-reference.wav" if use_reference else "music/candidate-b.wav")
            command=["python3",str(root/"scripts/validate_mf005r4_production.py"),"--fixture",str(fixture_path),"--layout",str(layout_path),"--execution",str(a/"timelines/candidate-b-execution.json"),"--music",str(a/"timelines/candidate-b-music.json"),"--music-stem",str(stem),"--music-reference",str(a/"music/candidate-b-reference.wav"),"--sfx-audio",str(a/"audio/candidate-b-sfx.wav"),"--mix",str(a/"validation/candidate-b-mix.json"),"--media",str(a/"candidate-b.mp4"),"--contract",str(a/"validation/candidate-b-contract.json"),"--output",str(report),"--motion-timeline",str(temp/f"{name}-motion.json")]; process=subprocess.run(command,capture_output=True,text=True); payload=json.loads(report.read_text()); passed=process.returncode!=0 and any(expected in item for item in payload.get("errors",[])); results[name]={"result":"PASS" if passed else "FAIL","observed":payload.get("errors",[])}
        production_case("required_scene_event_absent",layout_mutate=lambda value:value["generated_scene"]["observed_events"].pop(),expected="GENERATED_SCENE_EVENT_FAILED")
        production_case("hard_music_cut",fixture_mutate=lambda value:value["music"].update(fade_in=0,fade_out=0),use_reference=True,expected="HARD_MUSIC_CUT_FAILED")
    result={"slice":"MF-005R4","count":len(results),"cases":results,"result":"PASS" if len(results)==7 and all(item["result"]=="PASS" for item in results.values()) else "FAIL"}; output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
