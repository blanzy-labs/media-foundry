#!/usr/bin/env python3
"""Prove the MF-006R2 validator rejects center-concept and depth regressions."""

import argparse,copy,json,subprocess,tempfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    for n in ("repo_root","fixture","layout","execution","music_stem","music_reference","sfx_audio","sfx_report","mix","media","contract","output"): p.add_argument("--"+n.replace("_","-"),required=True)
    a=p.parse_args(); base=json.loads(Path(a.layout).read_text()); cases=[]
    mutations={
      "packets_leave_paths":lambda d:d["generated_scene"]["circuit_system"].update(packets_follow_defined_paths=False),
      "flow_before_draw":lambda d:d["generated_scene"]["circuit_system"].update(energy_flow_start=.2),
      "projection_before_burst":lambda d:d["generated_scene"]["projection_timeline"].update(emission=1.4),
      "physical_book_returns":lambda d:d["generated_scene"]["projected_codex"].update(physical_standing_book=True),
      "projection_detached":lambda d:d["generated_scene"]["projected_codex"].update(origin="screen-overlay"),
      "emitter_disconnected":lambda d:d["generated_scene"]["projection_emitter"].update(connected_to_circuits=False),
      "beats_not_distinct":lambda d:d["generated_scene"]["projected_codex"].update(story_beats=["same","same","same"]),
      "collapse_missing":lambda d:d["generated_scene"]["projected_codex"].update(collapse_to_node=False),
      "accent_cells_excessive":lambda d:d["generated_scene"]["background_cells"].update(accent_ratio=.65),
      "depth_removed":lambda d:d["generated_scene"]["depth_system"].update(foreground_cables=False),
      "cta_overlay":lambda d:d["generated_scene"]["cta"].update(world_integrated=False),
    }
    with tempfile.TemporaryDirectory(prefix="mf006r2-failure-") as td:
        for name,mutate in mutations.items():
            data=copy.deepcopy(base); mutate(data); layout=Path(td)/f"{name}.json"; result=Path(td)/f"{name}-result.json"; motion=Path(td)/f"{name}-motion.json"; layout.write_text(json.dumps(data))
            cmd=["python3",str(Path(a.repo_root)/"scripts/validate_mf006r2_production.py"),"--fixture",a.fixture,"--layout",str(layout),"--execution",a.execution,"--music-stem",a.music_stem,"--music-reference",a.music_reference,"--sfx-audio",a.sfx_audio,"--sfx-report",a.sfx_report,"--mix",a.mix,"--media",a.media,"--contract",a.contract,"--output",str(result),"--motion-timeline",str(motion)]
            run=subprocess.run(cmd,capture_output=True,text=True); rejected=run.returncode!=0 and json.loads(result.read_text()).get("result")=="FAIL"; cases.append({"case":name,"expected":"REJECT","actual":"REJECT" if rejected else "ACCEPT","result":"PASS" if rejected else "FAIL"})
    report={"slice":"MF-006R2","case_count":len(cases),"cases":cases,"result":"PASS" if all(c["result"]=="PASS" for c in cases) else "FAIL"}; Path(a.output).write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
