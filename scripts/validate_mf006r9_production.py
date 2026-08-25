#!/usr/bin/env python3
"""Validate R9 by preserving R8 and measuring an encoded indicator pulse."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
R8_HASH='8f1e515736baef3535d3686a699096e5bbd9cc22917447d3e0e6f3909ef67031'

def decoded_frame(path,time):
 run=subprocess.run(['ffmpeg','-v','error','-ss',str(time),'-i',str(path),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True)
 if run.returncode!=0 or len(run.stdout)!=1080*1920*3:raise ValueError('INDICATOR_FRAME_DECODE_FAILED')
 return run.stdout

def energy(frame,x,y,radius=9):
 total=0.0
 for py in range(y-radius,y+radius+1):
  for px in range(x-radius,x+radius+1):
   offset=(py*1080+px)*3;r,g,b=frame[offset:offset+3];total+=.2126*r+.7152*g+.0722*b
 return total

def tracked_energy(frame,x,y):
 return max(energy(frame,x+dx,y+dy) for dx in range(-8,9) for dy in range(-8,9))

def main():
 p=argparse.ArgumentParser()
 for n in ('project_root','fixture','layout','execution','music_stem','music_reference','sfx_audio','sfx_report','mix','media','contract','output','motion_timeline'):p.add_argument('--'+n.replace('_','-'),required=True)
 a=p.parse_args();errors=[]
 try:
  root=Path(a.project_root);layout=json.loads(Path(a.layout).read_text());scene=layout.get('generated_scene',{});pulse=scene.get('indicator_pulse',{});baseline=root/'artifacts/mf-006r8/candidate-a.mp4';actual=hashlib.sha256(baseline.read_bytes()).hexdigest() if baseline.is_file() else None
  if actual!=R8_HASH:errors.append('R8_BASELINE_PRESERVATION_FAILED')
  with tempfile.TemporaryDirectory(prefix='mf006r9-core-') as td:
   normalized=json.loads(json.dumps(layout));normalized['generated_scene']['strategy']='godot_integrated_lower_right_refinement';normalized_path=Path(td)/'layout.json';core_out=Path(td)/'result.json';core_motion=Path(td)/'motion.json';normalized_path.write_text(json.dumps(normalized));cmd=['python3',str(root/'scripts/validate_mf006r8_production.py'),'--project-root',str(root),'--fixture',a.fixture,'--layout',str(normalized_path),'--execution',a.execution,'--music-stem',a.music_stem,'--music-reference',a.music_reference,'--sfx-audio',a.sfx_audio,'--sfx-report',a.sfx_report,'--mix',a.mix,'--media',a.media,'--contract',a.contract,'--output',str(core_out),'--motion-timeline',str(core_motion)];run=subprocess.run(cmd,capture_output=True,text=True);core=json.loads(core_out.read_text())
  if run.returncode!=0 or core.get('gates',{}).get('visual_audio_technical')!='PASS':errors.append('R8_CORE_REGRESSION_FAILED')
  if scene.get('strategy')!='godot_indicator_pulse_refinement' or pulse.get('architectural_changes')!=0 or pulse.get('major_visual_redesign')!=0:errors.append('R9_STRATEGY_FAILED')
  if pulse.get('approved_indicator_count')!=4 or pulse.get('added_indicator_count')!=0 or pulse.get('removed_indicator_count')!=0 or pulse.get('positions_unchanged') is not True or pulse.get('color_family')!='yellow/orange':errors.append('FOUR_INDICATORS_FAILED')
  periods=pulse.get('periods_seconds',[]);offsets=pulse.get('phase_offsets_seconds',[]);durations=pulse.get('pulse_durations_seconds',[])
  if len(periods)!=4 or len(set(periods))!=4 or len(offsets)!=4 or len(set(offsets))!=4 or len(durations)!=4 or pulse.get('deterministic') is not True or pulse.get('irregular_timing') is not True or pulse.get('shared_period') is not False or pulse.get('all_synchronized') is not False:errors.append('IRREGULAR_TIMING_FAILED')
  if pulse.get('constant_blinking') is not False or pulse.get('chase_animation') is not False or pulse.get('maximum_individual_duty_cycle',1)>.12 or pulse.get('mean_individual_duty_cycle',1)>.1 or pulse.get('maximum_simultaneous_pulses',4)>2:errors.append('OCCASIONAL_BEHAVIOR_FAILED')
  if pulse.get('peak_overlay_alpha',1)>.3 or pulse.get('peak_radius',99)>pulse.get('base_radius',0)*1.35 or not all(pulse.get(k) is True for k in ('subordinate_to_projection','subordinate_to_node','subordinate_to_cta')):errors.append('INDICATOR_HIERARCHY_FAILED')
  if pulse.get('negative_space_unchanged') is not True or pulse.get('new_geometry')!=0 or pulse.get('custom_event_sequence') is not False:errors.append('NO_CLUTTER_FAILED')
  if pulse.get('timings_unchanged') is not True or pulse.get('audio_unchanged') is not True or pulse.get('new_sfx')!=0:errors.append('PRESERVATION_SCOPE_FAILED')
  rest=decoded_frame(Path(a.media),4.8);peak=decoded_frame(Path(a.media),5.4);centers=[(429,1473),(505,1472),(581,1472),(657,1471)];ratios=[tracked_energy(peak,x,y)/tracked_energy(rest,x,y) for x,y in centers];mean_ratio=sum(ratios[:2])/2;control_ratio=sum(ratios[2:])/2;measured=mean_ratio>1.07 and mean_ratio-control_ratio>.02
  if not measured:errors.append('ENCODED_PULSE_EVIDENCE_FAILED')
  evidence={'rest_time':4.8,'peak_time':5.4,'indicator_centers':centers,'tracking_radius_pixels':8,'sample_radius_pixels':9,'energy_ratios':[round(x,4) for x in ratios],'scheduled_pulse_mean_ratio':round(mean_ratio,4),'control_mean_ratio':round(control_ratio,4),'minimum_pulse_ratio':1.07,'minimum_pulse_over_control':.02,'result':'PASS' if measured else 'FAIL'}
  technical='PASS' if not errors else 'FAIL';mapping={'r8_baseline_preserved':'R8_BASELINE_PRESERVATION_FAILED','r8_core_validation':'R8_CORE_REGRESSION_FAILED','r9_strategy':'R9_STRATEGY_FAILED','four_indicators':'FOUR_INDICATORS_FAILED','irregular_timing':'IRREGULAR_TIMING_FAILED','occasional_behavior':'OCCASIONAL_BEHAVIOR_FAILED','indicator_hierarchy':'INDICATOR_HIERARCHY_FAILED','no_clutter':'NO_CLUTTER_FAILED','preservation_scope':'PRESERVATION_SCOPE_FAILED','encoded_pulse_evidence':'ENCODED_PULSE_EVIDENCE_FAILED'};result={'slice':'MF-006R9','checks':{k:'PASS' if v not in errors else 'FAIL' for k,v in mapping.items()}|{'full_decode':core.get('checks',{}).get('full_decode'),'audio':core.get('checks',{}).get('audio'),'cta':core.get('checks',{}).get('cta')},'baseline':{'path':'artifacts/mf-006r8/candidate-a.mp4','expected_sha256':R8_HASH,'actual_sha256':actual},'indicator_pulse':pulse,'encoded_pulse_evidence':evidence,'core_validation':core,'errors':errors,'gates':{'visual_audio_technical':technical,'production_voice':'BLOCKED','human_editorial':'PENDING_HUMAN','human_release':'PENDING_HUMAN','release':'RELEASE_ELIGIBLE_NO'},'result':'PASS_WITH_BLOCKER' if not errors else 'FAIL'};Path(a.motion_timeline).write_text(json.dumps({'slice':'MF-006R9','indicator_pulse':pulse,'encoded_pulse_evidence':evidence,'events':scene.get('observed_events'),'result':technical},indent=2)+'\n')
 except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError,ZeroDivisionError) as e:result={'slice':'MF-006R9','errors':[str(e)],'result':'FAIL'}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['result'] in {'PASS','PASS_WITH_BLOCKER'} else 1
if __name__=='__main__':raise SystemExit(main())
