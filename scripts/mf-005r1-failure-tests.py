#!/usr/bin/env python3
"""Controlled synchronization, music, and production-asset failures for MF-005R1."""

import argparse,copy,json,math,struct,subprocess,tempfile,wave
from pathlib import Path


def wav(path,seconds):
    with wave.open(str(path),"wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(48000)
        out.writeframes(b"".join(struct.pack("<h",round(math.sin(i/20)*7000)) for i in range(round(seconds*48000))))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--repo-root",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(); root=Path(args.repo_root)
    base=json.loads((root/"content/fixtures/mf005r1-turd-burglar.json").read_text()); results={}
    with tempfile.TemporaryDirectory(prefix="mf005r1-failures-") as directory:
        temp=Path(directory); long_audio=temp/"long.wav"; wav(long_audio,4.0); corrupt=temp/"corrupt.wav"; corrupt.write_bytes(b"bad")
        def timeline_for(name,fixture):
            fixture_path=temp/f"{name}.json"; timeline=temp/f"{name}-timeline.json"; fixture_path.write_text(json.dumps(fixture))
            process=subprocess.run(["python3",str(root/"scripts/preflight_mf004.py"),"--fixture",str(fixture_path),"--grammar",str(root/"config/visual-grammar.json"),"--project-root",str(root),"--output",str(timeline)],capture_output=True,text=True)
            return fixture_path,timeline,process.returncode
        def narration_case(name,mutate):
            fixture=copy.deepcopy(base); mutate(fixture); fixture_path,timeline,code=timeline_for(name,fixture); report=temp/f"{name}-report.json"
            process=subprocess.run(["python3",str(root/"scripts/prepare_mf005_narration.py"),"--fixture",str(fixture_path),"--timeline",str(timeline),"--grammar",str(root/"config/visual-grammar.json"),"--project-root",str(root),"--normalized-dir",str(temp/f"{name}-normalized"),"--cache-dir",str(temp/"cache"),"--output",str(report)],capture_output=True,text=True) if code==0 else None
            result=json.loads(report.read_text()) if process else {"result":"FAIL","error":"timeline unexpectedly failed"}; passed=process is not None and process.returncode!=0 and result.get("result")=="FAIL"
            results[name]={"result":"PASS" if passed else "FAIL","error":result.get("error","")}
        narration_case("narration_crosses_beat",lambda f:f["beats"][1]["narration"].update(source=str(long_audio)))
        narration_case("narration_starts_before_beat",lambda f:f["beats"][1]["narration"].update(lead_in=-0.1))
        narration_case("narration_ends_after_beat",lambda f:f["beats"][4]["narration"].update(source=str(long_audio)))
        def text_inactive(f): f["beats"][2]["narration"]={"source":str(root/"media/audio/narration/mf005/turd-media.wav"),"text":"About a dung beetle.","semantic_target":"text"}
        narration_case("narrated_text_not_active",text_inactive)
        narration_case("required_media_not_active",lambda f:f["beats"][1]["narration"].update(semantic_target="media"))
        narration_case("missing_production_media",lambda f:f["media"].update(source="media/images/mf003-still.png",provenance={"type":"deterministic_fixture"}))
        def music_case(name,mutate):
            fixture=copy.deepcopy(base); mutate(fixture); path=temp/f"{name}.json"; report=temp/f"{name}-music.json"; path.write_text(json.dumps(fixture))
            process=subprocess.run(["python3",str(root/"scripts/prepare_mf005r1_music.py"),"--fixture",str(path),"--project-root",str(root),"--duration","15","--output-audio",str(temp/f"{name}.wav"),"--output-report",str(report)],capture_output=True,text=True); result=json.loads(report.read_text()); passed=process.returncode!=0 and result.get("result")=="FAIL"; results[name]={"result":"PASS" if passed else "FAIL","error":result.get("error","")}
        music_case("missing_music_source",lambda f:f["music"].update(source=str(temp/"missing.wav")))
        music_case("invalid_music_audio",lambda f:f["music"].update(source=str(corrupt)))
        music_case("invalid_ducking_config",lambda f:f["music"].update(narration_duck_db=-40))
    result={"slice":"MF-005R1","tests":results,"result":"PASS" if all(item["result"]=="PASS" for item in results.values()) else "FAIL"}; output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
