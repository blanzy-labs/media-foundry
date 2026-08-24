#!/usr/bin/env python3
"""Prove the MF-006R1 production validator rejects causal/physical regressions."""

import argparse,copy,json,subprocess,tempfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    for n in ("repo_root","fixture","layout","execution","music_stem","music_reference","sfx_audio","sfx_report","mix","media","contract","output"): p.add_argument("--"+n.replace("_","-"),required=True)
    a=p.parse_args(); base=json.loads(Path(a.layout).read_text()); cases=[]
    mutations={
      "packets_leave_paths":lambda d:d["generated_scene"]["circuit_system"].update(packets_follow_defined_paths=False),
      "paths_miss_node":lambda d:d["generated_scene"]["circuit_system"].update(all_paths_terminate_at_central_node=False),
      "flow_before_draw":lambda d:d["generated_scene"]["circuit_system"].update(energy_flow_start=.2),
      "burst_before_buildup":lambda d:d["generated_scene"]["circuit_system"].update(burst=1.0),
      "ambiguous_platform_returns":lambda d:d["generated_scene"]["book_support"].update(legacy_ambiguous_platform_removed=False),
      "book_loses_spine":lambda d:d["generated_scene"]["generated_book"].update(spine=False),
      "static_cover_inserted":lambda d:d["generated_scene"].update(static_book_cover_embedded=True),
      "website_not_integrated":lambda d:d["generated_scene"]["cta"].update(world_integrated=False),
      "return_path_changed":lambda d:d["generated_scene"]["circuit_system"].update(return_energy_uses_same_paths=False),
    }
    with tempfile.TemporaryDirectory(prefix="mf006r1-failure-") as td:
        for name,mutate in mutations.items():
            data=copy.deepcopy(base); mutate(data); layout=Path(td)/f"{name}.json"; result=Path(td)/f"{name}-result.json"; motion=Path(td)/f"{name}-motion.json"; layout.write_text(json.dumps(data))
            cmd=["python3",str(Path(a.repo_root)/"scripts/validate_mf006r1_production.py"),"--fixture",a.fixture,"--layout",str(layout),"--execution",a.execution,"--music-stem",a.music_stem,"--music-reference",a.music_reference,"--sfx-audio",a.sfx_audio,"--sfx-report",a.sfx_report,"--mix",a.mix,"--media",a.media,"--contract",a.contract,"--output",str(result),"--motion-timeline",str(motion)]
            run=subprocess.run(cmd,capture_output=True,text=True); rejected=run.returncode!=0 and json.loads(result.read_text()).get("result")=="FAIL"; cases.append({"case":name,"expected":"REJECT","actual":"REJECT" if rejected else "ACCEPT","result":"PASS" if rejected else "FAIL"})
    report={"slice":"MF-006R1","case_count":len(cases),"cases":cases,"result":"PASS" if all(c["result"]=="PASS" for c in cases) else "FAIL"}; Path(a.output).write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
