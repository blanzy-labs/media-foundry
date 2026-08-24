#!/usr/bin/env python3
"""Validate R7 by preserving the complete R6 gate and adding composition checks."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
R6_HASH='ec24c997e7a6718d36ef4c5808c2227f8c072fcd079a184b1d8dc68cf22d9157'
def main():
 p=argparse.ArgumentParser()
 for n in ('project_root','fixture','layout','execution','music_stem','music_reference','sfx_audio','sfx_report','mix','media','contract','output','motion_timeline'):p.add_argument('--'+n.replace('_','-'),required=True)
 a=p.parse_args();errors=[]
 try:
  root=Path(a.project_root);layout=json.loads(Path(a.layout).read_text());scene=layout.get('generated_scene',{});lr=scene.get('lower_right_composition',{});baseline=root/'artifacts/mf-006r6/candidate-a.mp4';actual=hashlib.sha256(baseline.read_bytes()).hexdigest() if baseline.is_file() else None
  if actual!=R6_HASH:errors.append('R6_BASELINE_PRESERVATION_FAILED')
  with tempfile.TemporaryDirectory(prefix='mf006r7-core-') as td:
   normalized=json.loads(json.dumps(layout));normalized['generated_scene']['strategy']='godot_final_polish_refinement';normalized_path=Path(td)/'layout.json';core_out=Path(td)/'result.json';core_motion=Path(td)/'motion.json';normalized_path.write_text(json.dumps(normalized));cmd=['python3',str(root/'scripts/validate_mf006r6_production.py'),'--project-root',str(root),'--fixture',a.fixture,'--layout',str(normalized_path),'--execution',a.execution,'--music-stem',a.music_stem,'--music-reference',a.music_reference,'--sfx-audio',a.sfx_audio,'--sfx-report',a.sfx_report,'--mix',a.mix,'--media',a.media,'--contract',a.contract,'--output',str(core_out),'--motion-timeline',str(core_motion)];run=subprocess.run(cmd,capture_output=True,text=True);core=json.loads(core_out.read_text())
  if run.returncode!=0 or core.get('gates',{}).get('visual_audio_technical')!='PASS':errors.append('R6_CORE_REGRESSION_FAILED')
  if scene.get('strategy')!='godot_lower_right_polish_refinement' or lr.get('architectural_changes')!=0 or lr.get('major_visual_redesign')!=0:errors.append('R7_STRATEGY_FAILED')
  if lr.get('secondary_branch_count')!=1 or lr.get('branch_point_count',0)<5 or not 2<=lr.get('branch_thickness',0)<lr.get('main_branch_thickness',0):errors.append('LOWER_RIGHT_BRANCH_FAILED')
  if lr.get('maximum_packet_count',99)>2 or lr.get('ambient_packet_count')!=1 or lr.get('packet_duty_cycle',1)>.3 or lr.get('direction')!='inward/upward toward central system':errors.append('RESTRAINED_ENERGY_FAILED')
  if lr.get('powered_cell_count')!=1 or lr.get('powered_cell_color') not in ('purple','green','blue') or lr.get('powered_cell_resting_alpha',1)>.2:errors.append('POWERED_CELL_FAILED')
  if lr.get('negative_space_ratio',0)<.5 or lr.get('brightness_ratio',1)>.4 or not all(lr.get(k) is True for k in ('no_major_geometry','subordinate_to_projection','subordinate_to_node','subordinate_to_cta')) or lr.get('second_focal_point') is not False:errors.append('HIERARCHY_NEGATIVE_SPACE_FAILED')
  if not all(lr.get(k) is True for k in ('overload_response','projection_response','cta_response','cta_orange_participation')):errors.append('EVENT_RESPONSE_FAILED')
  if lr.get('camera_unchanged') is not True or lr.get('timings_unchanged') is not True or scene.get('audio_visual_contract',{}).get('lower_right_new_sfx')!=0:errors.append('PRESERVATION_SCOPE_FAILED')
  technical='PASS' if not errors else 'FAIL';checks={'r6_baseline_preserved':'R6_BASELINE_PRESERVATION_FAILED','r6_core_validation':'R6_CORE_REGRESSION_FAILED','r7_strategy':'R7_STRATEGY_FAILED','lower_right_branch':'LOWER_RIGHT_BRANCH_FAILED','restrained_energy':'RESTRAINED_ENERGY_FAILED','powered_cell':'POWERED_CELL_FAILED','hierarchy_negative_space':'HIERARCHY_NEGATIVE_SPACE_FAILED','event_response':'EVENT_RESPONSE_FAILED','preservation_scope':'PRESERVATION_SCOPE_FAILED'};result={'slice':'MF-006R7','checks':{k:'PASS' if v not in errors else 'FAIL' for k,v in checks.items()}|{'full_decode':core.get('checks',{}).get('full_decode'),'audio':core.get('checks',{}).get('loudness_peak'),'music_fades':core.get('checks',{}).get('music_fades')},'baseline':{'path':'artifacts/mf-006r6/candidate-a.mp4','expected_sha256':R6_HASH,'actual_sha256':actual},'lower_right_composition':lr,'core_validation':core,'errors':errors,'gates':{'visual_audio_technical':technical,'production_voice':'BLOCKED','human_editorial':'PENDING_HUMAN','human_release':'PENDING_HUMAN','release':'RELEASE_ELIGIBLE_NO'},'result':'PASS_WITH_BLOCKER' if not errors else 'FAIL'};Path(a.motion_timeline).write_text(json.dumps({'slice':'MF-006R7','lower_right_composition':lr,'events':scene.get('observed_events'),'result':technical},indent=2)+'\n')
 except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError) as e:result={'slice':'MF-006R7','errors':[str(e)],'result':'FAIL'}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['result'] in {'PASS','PASS_WITH_BLOCKER'} else 1
if __name__=='__main__':raise SystemExit(main())
