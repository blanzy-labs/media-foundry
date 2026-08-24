#!/usr/bin/env python3
"""Prove MF-006R4 rejects preservation, pacing, activity, hierarchy, and CTA regressions."""

import argparse,copy,json,subprocess,tempfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    for n in ("repo_root","fixture","layout","execution","music_stem","music_reference","sfx_audio","sfx_report","mix","media","contract","output"): p.add_argument("--"+n.replace("_","-"),required=True)
    a=p.parse_args(); base=json.loads(Path(a.layout).read_text()); cases=[]
    mutations={
      "packets_leave_paths":lambda d:d["generated_scene"]["circuit_system"].update(packets_follow_defined_paths=False),
      "flow_before_draw":lambda d:d["generated_scene"]["circuit_system"].update(energy_flow_start=.2),
      "two_windows":lambda d:d["generated_scene"]["projected_data_window"].update(primary_window_count=2),
      "split_pages_return":lambda d:d["generated_scene"]["projected_data_window"].update(split_page_projection=True),
      "wavy_line_returns":lambda d:d["generated_scene"]["projected_data_window"].update(wavy_center_line=True),
      "yellow_circle_returns":lambda d:d["generated_scene"]["projected_data_window"].update(yellow_circular_graphic=True),
      "text_outside_screen":lambda d:d["generated_scene"]["projection_layout"]["story_text_bounds"][0].update(x=500),
      "typing_disabled":lambda d:d["generated_scene"]["projected_data_window"].update(typed_text=False),
      "new_screen_per_beat":lambda d:d["generated_scene"]["projected_data_window"].update(same_instance_all_beats=False),
      "activity_out_of_order":lambda d:d["generated_scene"]["screen_timeline"].update(activity_1=9.8),
      "activity_missing":lambda d:d["generated_scene"]["extended_record_activity"].update(record_activity_events=0),
      "micro_diagrams_missing":lambda d:d["generated_scene"]["extended_record_activity"].update(micro_diagrams=0),
      "screen_not_enlarged":lambda d:d["generated_scene"]["extended_record_activity"].update(screen_scale_story=1.0),
      "background_too_subtle":lambda d:d["generated_scene"]["background_cells"].update(noticeable_phone_brightness=False),
      "background_too_bright":lambda d:d["generated_scene"]["background_cells"].update(accent_ratio=.55),
      "center_cable_returns":lambda d:d["generated_scene"]["depth_system"].update(center_foreground_cable=True),
      "node_competes":lambda d:d["generated_scene"]["extended_record_activity"].update(node_post_projection_intensity=.8),
      "cta_hold_short":lambda d:d["generated_scene"]["extended_record_activity"].update(cta_hold=.4),
      "cta_not_typed":lambda d:d["generated_scene"]["extended_record_activity"].update(cta_typed=False),
    }
    with tempfile.TemporaryDirectory(prefix="mf006r4-failure-") as td:
        for name,mutate in mutations.items():
            data=copy.deepcopy(base); mutate(data); layout=Path(td)/f"{name}.json"; result=Path(td)/f"{name}-result.json"; motion=Path(td)/f"{name}-motion.json"; layout.write_text(json.dumps(data))
            cmd=["python3",str(Path(a.repo_root)/"scripts/validate_mf006r4_production.py"),"--project-root",a.repo_root,"--fixture",a.fixture,"--layout",str(layout),"--execution",a.execution,"--music-stem",a.music_stem,"--music-reference",a.music_reference,"--sfx-audio",a.sfx_audio,"--sfx-report",a.sfx_report,"--mix",a.mix,"--media",a.media,"--contract",a.contract,"--output",str(result),"--motion-timeline",str(motion)]
            run=subprocess.run(cmd,capture_output=True,text=True); rejected=run.returncode!=0 and json.loads(result.read_text()).get("result")=="FAIL"; cases.append({"case":name,"expected":"REJECT","actual":"REJECT" if rejected else "ACCEPT","result":"PASS" if rejected else "FAIL"})
    report={"slice":"MF-006R4","case_count":len(cases),"cases":cases,"result":"PASS" if all(c["result"]=="PASS" for c in cases) else "FAIL"}; Path(a.output).write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
