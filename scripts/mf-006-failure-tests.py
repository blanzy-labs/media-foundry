#!/usr/bin/env python3
"""Controlled MF-006 failures for static cover, metadata, voice, sync, events, and fades."""

import argparse,copy,json,subprocess,tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--repo-root",required=True); parser.add_argument("--artifacts",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(); root=Path(args.repo_root); a=Path(args.artifacts); fixture=json.loads((root/"content/fixtures/mf006-dark-signal.json").read_text()); results={}
    with tempfile.TemporaryDirectory(prefix="mf006-failures-") as directory:
        temp=Path(directory)
        def contract_case(name,mutate,expected,expect_blocker=False):
            value=copy.deepcopy(fixture); mutate(value); source=temp/f"{name}.json"; report=temp/f"{name}-report.json"; source.write_text(json.dumps(value)); process=subprocess.run(["python3",str(root/"scripts/validate_mf006_contract.py"),"--fixture",str(source),"--project-root",str(root),"--output",str(report)],capture_output=True,text=True); payload=json.loads(report.read_text()); observed=payload.get("blockers",[]) if expect_blocker else payload.get("errors",[]); passed=(expected in observed) and (process.returncode==0 if expect_blocker else process.returncode!=0); results[name]={"result":"PASS" if passed else "FAIL","observed":observed}
        contract_case("static_book_cover",lambda value:value.update(media={"type":"image","source":"media/images/books-dark-signal.png"}),"STATIC_BOOK_COVER_PROHIBITED")
        contract_case("title_absent",lambda value:value["subject"].update(title=""),"APPROVED_BOOK_METADATA_FAILED")
        contract_case("author_absent",lambda value:value["subject"].update(author=""),"APPROVED_BOOK_METADATA_FAILED")
        contract_case("website_absent",lambda value:value["cta"].update(website=None),"BLOCKED_APPROVED_WEBSITE",True)
        contract_case("test_voice",lambda value:value["voice_contract"].update(status="READY",available_provider="local_ffmpeg_flite",test_voice_allowed=True,release_eligible=True),"TEST_ONLY_VOICE_PROHIBITED")
        contract_case("required_event_absent",lambda value:value["generated_scene"]["events"].pop(1),"REQUIRED_GENERATED_EVENT_MISSING")
        contract_case("hard_music_cut",lambda value:value["music"].update(fade_in=0,fade_out=0),"MUSIC_FADE_CONTRACT_FAILED")
        narration=copy.deepcopy(fixture); narration["voice_contract"].update(status="READY",available_provider="approved",release_eligible=True); fixture_path=temp/"narration-fixture.json"; manifest_path=temp/"narration-manifest.json"; report_path=temp/"narration-report.json"; fixture_path.write_text(json.dumps(narration)); manifest_path.write_text(json.dumps({"segments":[{"beat":"page_1","start":4.7,"end":7.4,"text":"Continue the adventure."}]})); process=subprocess.run(["python3",str(root/"scripts/validate_mf006_narration.py"),"--fixture",str(fixture_path),"--manifest",str(manifest_path),"--output",str(report_path)],capture_output=True,text=True); payload=json.loads(report_path.read_text()); results["page_narration_overrun"]={"result":"PASS" if process.returncode!=0 and "PAGE_NARRATION_EXCEEDS_BEAT" in payload.get("errors",[]) else "FAIL","observed":payload.get("errors",[])}
    result={"slice":"MF-006","count":len(results),"cases":results,"result":"PASS" if len(results)==8 and all(item["result"]=="PASS" for item in results.values()) else "FAIL"}; output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
