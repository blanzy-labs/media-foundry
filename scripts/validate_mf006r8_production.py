#!/usr/bin/env python3
"""Validate R8 by preserving R7, retaining the R6 core, and proving integration."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
R7_HASH='0a8a2e2ae923ddc98a7411b9b0c449ce6b71b1dbb8d04e74aa6f6ac05c85f063'

def main():
 p=argparse.ArgumentParser()
 for n in ('project_root','fixture','layout','execution','music_stem','music_reference','sfx_audio','sfx_report','mix','media','contract','output','motion_timeline'):p.add_argument('--'+n.replace('_','-'),required=True)
 a=p.parse_args();errors=[]
 try:
  root=Path(a.project_root);layout=json.loads(Path(a.layout).read_text());scene=layout.get('generated_scene',{});integration=scene.get('lower_right_integration',{});circuit=scene.get('circuit_system',{});baseline=root/'artifacts/mf-006r7/candidate-a.mp4';actual=hashlib.sha256(baseline.read_bytes()).hexdigest() if baseline.is_file() else None
  if actual!=R7_HASH:errors.append('R7_BASELINE_PRESERVATION_FAILED')
  with tempfile.TemporaryDirectory(prefix='mf006r8-core-') as td:
   normalized=json.loads(json.dumps(layout));normalized['generated_scene']['strategy']='godot_final_polish_refinement';normalized_path=Path(td)/'layout.json';core_out=Path(td)/'result.json';core_motion=Path(td)/'motion.json';normalized_path.write_text(json.dumps(normalized));cmd=['python3',str(root/'scripts/validate_mf006r6_production.py'),'--project-root',str(root),'--fixture',a.fixture,'--layout',str(normalized_path),'--execution',a.execution,'--music-stem',a.music_stem,'--music-reference',a.music_reference,'--sfx-audio',a.sfx_audio,'--sfx-report',a.sfx_report,'--mix',a.mix,'--media',a.media,'--contract',a.contract,'--output',str(core_out),'--motion-timeline',str(core_motion)];run=subprocess.run(cmd,capture_output=True,text=True);core=json.loads(core_out.read_text())
  if run.returncode!=0 or core.get('gates',{}).get('visual_audio_technical')!='PASS':errors.append('R6_CORE_REGRESSION_FAILED')
  if scene.get('strategy')!='godot_integrated_lower_right_refinement' or integration.get('architectural_changes')!=0 or integration.get('major_visual_redesign')!=0:errors.append('R8_STRATEGY_FAILED')
  if integration.get('r7_separate_branch_removed') is not True or integration.get('added_network_path_count')!=1 or integration.get('total_network_path_count')!=7 or circuit.get('path_count')!=7:errors.append('SEPARATE_BRANCH_CORRECTION_FAILED')
  endpoint=integration.get('path_endpoint',{})
  if integration.get('path_point_count',0)<7 or integration.get('connects_directly_to_main_hub') is not True or endpoint!={'x':0,'y':125} or circuit.get('all_paths_terminate_at_central_node') is not True:errors.append('HUB_CONNECTIVITY_FAILED')
  if not all(integration.get(k) is True for k in ('uses_shared_circuit_collection','uses_shared_draw_logic','uses_shared_energy_logic')) or integration.get('dedicated_packet_sequence') is not False or integration.get('custom_corner_event_animation') is not False or integration.get('event_response')!='shared system behavior':errors.append('SHARED_SYSTEM_BEHAVIOR_FAILED')
  if integration.get('r7_standalone_cell_removed') is not True or integration.get('powered_cell_count')!=0:errors.append('POWERED_CELL_REMOVAL_FAILED')
  if integration.get('negative_space_ratio',0)<.5 or integration.get('second_focal_point') is not False or not all(integration.get(k) is True for k in ('subordinate_to_projection','subordinate_to_node','subordinate_to_cta')):errors.append('HIERARCHY_NEGATIVE_SPACE_FAILED')
  if integration.get('new_major_geometry')!=0:errors.append('MAJOR_GEOMETRY_FAILED')
  if integration.get('camera_unchanged') is not True or integration.get('timings_unchanged') is not True or integration.get('audio_unchanged') is not True or integration.get('new_sfx')!=0:errors.append('PRESERVATION_SCOPE_FAILED')
  technical='PASS' if not errors else 'FAIL';mapping={'r7_baseline_preserved':'R7_BASELINE_PRESERVATION_FAILED','r6_core_validation':'R6_CORE_REGRESSION_FAILED','r8_strategy':'R8_STRATEGY_FAILED','separate_branch_removed':'SEPARATE_BRANCH_CORRECTION_FAILED','hub_connectivity':'HUB_CONNECTIVITY_FAILED','shared_system_behavior':'SHARED_SYSTEM_BEHAVIOR_FAILED','powered_cell_decision':'POWERED_CELL_REMOVAL_FAILED','hierarchy_negative_space':'HIERARCHY_NEGATIVE_SPACE_FAILED','no_major_geometry':'MAJOR_GEOMETRY_FAILED','preservation_scope':'PRESERVATION_SCOPE_FAILED'};result={'slice':'MF-006R8','checks':{k:'PASS' if v not in errors else 'FAIL' for k,v in mapping.items()}|{'full_decode':core.get('checks',{}).get('full_decode'),'audio':core.get('checks',{}).get('loudness_peak'),'music_fades':core.get('checks',{}).get('music_fades'),'cta':core.get('checks',{}).get('cta_polish')},'baseline':{'path':'artifacts/mf-006r7/candidate-a.mp4','expected_sha256':R7_HASH,'actual_sha256':actual},'lower_right_integration':integration,'core_validation':core,'errors':errors,'gates':{'visual_audio_technical':technical,'production_voice':'BLOCKED','human_editorial':'PENDING_HUMAN','human_release':'PENDING_HUMAN','release':'RELEASE_ELIGIBLE_NO'},'result':'PASS_WITH_BLOCKER' if not errors else 'FAIL'};Path(a.motion_timeline).write_text(json.dumps({'slice':'MF-006R8','lower_right_integration':integration,'events':scene.get('observed_events'),'result':technical},indent=2)+'\n')
 except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError) as e:result={'slice':'MF-006R8','errors':[str(e)],'result':'FAIL'}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['result'] in {'PASS','PASS_WITH_BLOCKER'} else 1
if __name__=='__main__':raise SystemExit(main())
