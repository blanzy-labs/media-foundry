#!/usr/bin/env python3
"""Controlled R3 production-quality and release-safeguard failures."""

import argparse,copy,json,subprocess,tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--repo-root",required=True); parser.add_argument("--artifacts",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(); root=Path(args.repo_root); a=Path(args.artifacts); valid_fixture=json.loads((a/"timelines/candidate-b-fixture.json").read_text()); results={}
    with tempfile.TemporaryDirectory(prefix="mf005r3-failures-") as directory:
        temp=Path(directory)
        def contract_case(name,fixture,expect_release_block=False):
            fixture_path=temp/f"{name}.json"; output=temp/f"{name}-contract.json"; fixture_path.write_text(json.dumps(fixture)); process=subprocess.run(["python3",str(root/"scripts/validate_mf005r3_contract.py"),"--fixture",str(fixture_path),"--output",str(output)],capture_output=True,text=True); payload=json.loads(output.read_text())
            passed=(process.returncode==0 and payload.get("gates",{}).get("release")=="BLOCKED_VOICE_ASSET") if expect_release_block else process.returncode!=0
            results[name]={"result":"PASS" if passed else "FAIL","observed":payload}
        missing_name=copy.deepcopy(valid_fixture); next(beat for beat in missing_name["beats"] if beat["id"]=="reveal")["narration"]["text"]="It is called the game."
        contract_case("spoken_product_name_missing",missing_name)
        contract_case("test_only_voice_not_release_eligible",copy.deepcopy(valid_fixture),True)

        def quality_case(name,mutate_fixture=lambda item:None,mutate_final=lambda item:None,mutate_layout=lambda item:None,use_reference_as_stem=False):
            fixture=copy.deepcopy(valid_fixture); final=json.loads((a/"validation/candidate-b-final-mix.json").read_text()); layout=json.loads((a/"validation/candidate-b-layout.json").read_text()); mutate_fixture(fixture); mutate_final(final); mutate_layout(layout)
            fixture_path=temp/f"{name}-fixture.json"; final_path=temp/f"{name}-final.json"; layout_path=temp/f"{name}-layout.json"; output=temp/f"{name}-quality.json"; fixture_path.write_text(json.dumps(fixture)); final_path.write_text(json.dumps(final)); layout_path.write_text(json.dumps(layout))
            stem=a/("audio/music/candidate-b-reference.wav" if use_reference_as_stem else "audio/music/candidate-b.wav")
            command=["python3",str(root/"scripts/validate_mf005r3_quality.py"),"--fixture",str(fixture_path),"--music-stem",str(stem),"--music-reference",str(a/"audio/music/candidate-b-reference.wav"),"--narration",str(a/"timelines/candidate-b-narration.json"),"--mix",str(a/"validation/candidate-b-mix.json"),"--mix-validation",str(final_path),"--layout",str(layout_path),"--contract",str(a/"validation/candidate-b-contract.json"),"--output",str(output)]
            process=subprocess.run(command,capture_output=True,text=True); payload=json.loads(output.read_text()); results[name]={"result":"PASS" if process.returncode!=0 else "FAIL","observed_errors":payload.get("errors",[])}
        quality_case("fade_missing",lambda item:item["music"].update(fade_in=0,fade_out=0),use_reference_as_stem=True)
        quality_case("final_loudness_outside_range",mutate_final=lambda item:item["loudness"].update(integrated_lufs=-20))
        quality_case("music_masks_narration",lambda item:item["music"].update(gain_db=0,narration_duck_db=-1))
        quality_case("outro_text_outside_readable_range",mutate_layout=lambda item:item["layout"]["beat_6"].update(status="FAIL",font_size=12))
    result={"slice":"MF-005R3","count":len(results),"cases":results,"result":"PASS" if len(results)==6 and all(item["result"]=="PASS" for item in results.values()) else "FAIL"}; output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
