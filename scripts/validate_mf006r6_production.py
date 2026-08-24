#!/usr/bin/env python3
"""Independently validate MF-006R6 final motion/projection/audio polish."""
import argparse,json
from pathlib import Path
from validate_mf005r3_quality import envelope_check,pcm
from validate_mf006r4_production import loudness,rms,contained,sha
from validate_mf006r5_production import R5_BASELINES

BASELINES=R5_BASELINES|{'MF-006R5':('artifacts/mf-006r5/candidate-a.mp4','a936792251d0356ab6eaa4670fc4586512e3ab23790d4868f0adc423dfe12c82')}
def main():
 p=argparse.ArgumentParser()
 for n in ('project_root','fixture','layout','execution','music_stem','music_reference','sfx_audio','sfx_report','mix','media','contract','output','motion_timeline'):p.add_argument('--'+n.replace('_','-'),required=True)
 a=p.parse_args();errors=[]
 try:
  root=Path(a.project_root);f=json.loads(Path(a.fixture).read_text());layout=json.loads(Path(a.layout).read_text());execution=json.loads(Path(a.execution).read_text());contract=json.loads(Path(a.contract).read_text());mix=json.loads(Path(a.mix).read_text());sfx=json.loads(Path(a.sfx_report).read_text());scene=layout.get('generated_scene',{});circuit=scene.get('circuit_system',{});window=scene.get('projected_data_window',{});projection=scene.get('projection_layout',{});depth=scene.get('depth_system',{});st=scene.get('screen_timeline',{});cells=scene.get('background_cells',{});cta=scene.get('cta',{});motion=scene.get('final_motion_polish',{});physical=scene.get('projection_physicality',{});transitions=scene.get('record_transitions',{});overload=scene.get('node_overload_refinement',{});av=scene.get('audio_visual_contract',{});duration=float(f.get('format',{}).get('duration_seconds',0))
  preservation=[]
  for name,(rel,expected) in BASELINES.items():path=root/rel;actual=sha(path) if path.is_file() else None;preservation.append({'slice':name,'path':rel,'expected_sha256':expected,'actual_sha256':actual,'result':'PASS' if actual==expected else 'FAIL'})
  if any(x['result']!='PASS' for x in preservation):errors.append('BASELINE_PRESERVATION_FAILED')
  if duration!=28:errors.append('RUNTIME_FAILED')
  causal=[circuit.get(k,-1) for k in ('paths_draw_start','paths_draw_complete','energy_flow_start','central_node_charge','overload','burst')]
  if not causal[0]<causal[1]<=causal[2]<causal[3]<causal[4]<causal[5]<st.get('initialize',-1):errors.append('CAUSAL_OPENING_FAILED')
  if circuit.get('path_count',0)<6 or not all(circuit.get(k) is True for k in ('packets_follow_defined_paths','all_paths_terminate_at_central_node','return_energy_uses_same_paths')):errors.append('PATH_FOLLOWING_FAILED')
  if window.get('primary_window_count')!=1 or not all(window.get(k) is True for k in ('persistent_instance','same_instance_all_beats','single_coherent_boundary','typed_text','content_first')):errors.append('SINGLE_WINDOW_FAILED')
  if any(window.get(k) is not False for k in ('split_page_projection','book_metaphor','wavy_center_line','yellow_circular_graphic','large_diagnostic_graphic')):errors.append('REJECTED_CLUTTER_PRESENT')
  content=projection.get('content_bounds',{});texts=projection.get('story_text_bounds',[])
  if projection.get('all_story_text_inside_content') is not True or len(texts)!=3 or not all(contained(x,content) for x in texts):errors.append('TEXT_SAFE_AREA_FAILED')
  simon=motion.get('simon',{});pair=motion.get('leo_zeph',{});bio=motion.get('biometrics',{})
  if not all(simon.get(k) is True for k in ('moving_acquisition','completion_state','subtle_hold_motion')) or not all(pair.get(k) is True for k in ('traveling_bridge_signal','stable_connection')) or pair.get('pulse_count') not in (2,3) or not all(bio.get(k) is True for k in ('scan_traversal','completion_illumination')) or bio.get('hidden_segment_count')!=1:errors.append('INVESTIGATION_MOTION_FAILED')
  if motion.get('architectural_changes')!=0 or motion.get('new_visual_metaphors')!=0 or not overload.get('capacity_acceleration') or overload.get('r6_pulse_events')!=2 or overload.get('environment_reaction') is not True:errors.append('OVERLOAD_POLISH_FAILED')
  if cells.get('breathing_count',0)<5 or cells.get('breathing_count',99)>8 or cells.get('deterministic_phase_offsets') is not True or cells.get('hierarchy_subordinate') is not True or cells.get('green_emphasis',0)<.3 or not all(cells.get('counts',{}).get(k,0)>=2 for k in ('purple','green','blue')):errors.append('CELL_POLISH_FAILED')
  if physical.get('edge_shimmer') is not True or physical.get('scanline_drift') is not True or physical.get('brightness_variation_max',1)>.04 or physical.get('text_transform_jitter')!=0 or physical.get('reading_phase_stable') is not True:errors.append('PROJECTION_PHYSICALITY_FAILED')
  if transitions.get('completion_holds')!=3 or transitions.get('reset_events')!=2 or transitions.get('same_surface') is not True or transitions.get('supporting_data_decay') is not True or transitions.get('blank_interval_max',1)>.2:errors.append('RECORD_TRANSITION_FAILED')
  if not all(cta.get(k) is True for k in ('energy_packets_visible','packets_follow_defined_paths','text_then_url','typed_reveal','url_stabilizes','final_resolved_signal')) or cta.get('packet_paths')!=2 or cta.get('final_hold',0)<3 or cta.get('final_stable_time',99)>=duration-3:errors.append('CTA_POLISH_FAILED')
  configured={x.get('id') for x in scene.get('configured_events',[])};observed={x.get('id') for x in scene.get('observed_events',[])};required={'overload_pulse_1','overload_pulse_2','record_hold_1','record_reset_1','record_hold_2','record_reset_2','record_hold_3','cta_lock'}
  if configured!=observed or not required<=observed:errors.append('EVENT_EXECUTION_FAILED')
  if layout.get('result')!='PASS' or scene.get('result')!='PASS' or scene.get('strategy')!='godot_final_polish_refinement' or depth.get('center_foreground_cable') is not False:errors.append('LAYOUT_STRATEGY_FAILED')
  if {b['id'] for b in f['beats']}!={b.get('id') for b in execution.get('beats',[])} or execution.get('result')!='PASS':errors.append('BEAT_TIMELINE_FAILED')
  stem,rate=pcm(Path(a.music_stem));ref,_=pcm(Path(a.music_reference));fade=envelope_check(stem,ref,float(f['music']['fade_in']),float(f['music']['fade_out']),rate)
  if fade.get('result')!='PASS':errors.append('MUSIC_HARD_CUT')
  samples,srate=pcm(Path(a.sfx_audio));activity=[]
  for item in sfx.get('events',[]):level=rms(samples,srate,float(item['time']),min(.25,float(item['duration'])));ok=level>-45 and item.get('event') in observed;activity.append({'id':item['id'],'event':item['event'],'type':item['type'],'time':item['time'],'rms_dbfs':round(level,3),'result':'PASS' if ok else 'FAIL'})
  expected_types={'target_lock','bridge_lock','hidden_reveal','overload_rise','projection_refresh','cta_resolve'}
  if len(activity)!=13 or any(x['result']!='PASS' for x in activity) or not expected_types<={x['type'] for x in activity}:errors.append('EVENT_SPECIFIC_SFX_FAILED')
  if av.get('production_narration_alignment')!='BLOCKED_PRODUCTION_VOICE':errors.append('NARRATION_GATE_FAILED')
  measured=loudness(Path(a.media))
  if not -17<=measured['integrated_lufs']<=-15 or measured['true_peak_db']>-1 or mix.get('clipped_samples')!=0:errors.append('LOUDNESS_PEAK_FAILED')
  technical='PASS' if not errors else 'FAIL';blockers=contract.get('blockers',[]);motion_report={'slice':'MF-006R6','final_motion_polish':motion,'projection_physicality':physical,'record_transitions':transitions,'node_overload_refinement':overload,'background_cells':cells,'cta':cta,'events':scene.get('observed_events'),'result':technical};Path(a.motion_timeline).parent.mkdir(parents=True,exist_ok=True);Path(a.motion_timeline).write_text(json.dumps(motion_report,indent=2)+'\n')
  mapping={'baseline_preservation':'BASELINE_PRESERVATION_FAILED','runtime':'RUNTIME_FAILED','causal_opening':'CAUSAL_OPENING_FAILED','path_following':'PATH_FOLLOWING_FAILED','single_window':'SINGLE_WINDOW_FAILED','rejected_clutter_absent':'REJECTED_CLUTTER_PRESENT','text_safe_area':'TEXT_SAFE_AREA_FAILED','investigation_motion':'INVESTIGATION_MOTION_FAILED','overload_polish':'OVERLOAD_POLISH_FAILED','cell_polish':'CELL_POLISH_FAILED','projection_physicality':'PROJECTION_PHYSICALITY_FAILED','record_transitions':'RECORD_TRANSITION_FAILED','cta_polish':'CTA_POLISH_FAILED','event_execution':'EVENT_EXECUTION_FAILED','layout_strategy':'LAYOUT_STRATEGY_FAILED','music_fades':'MUSIC_HARD_CUT','event_specific_sfx':'EVENT_SPECIFIC_SFX_FAILED','narration_gate':'NARRATION_GATE_FAILED','loudness_peak':'LOUDNESS_PEAK_FAILED'}
  result={'slice':'MF-006R6','checks':{k:'PASS' if v not in errors else 'FAIL' for k,v in mapping.items()}|{'full_decode':'PASS','narration_alignment':'BLOCKED_PRODUCTION_VOICE'},'preservation':preservation,'duration_seconds':duration,'fade_measurement':fade,'audio':measured,'sfx':activity,'blockers':blockers,'errors':errors,'gates':{'visual_audio_technical':technical,'production_voice':'BLOCKED' if blockers else 'PASS','human_editorial':'PENDING_HUMAN','human_release':'PENDING_HUMAN','release':'RELEASE_ELIGIBLE_NO'},'result':'PASS_WITH_BLOCKER' if blockers and not errors else technical}
 except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError) as e:result={'slice':'MF-006R6','errors':[str(e)],'gates':{'visual_audio_technical':'FAIL','release':'RELEASE_ELIGIBLE_NO'},'result':'FAIL'}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['result'] in {'PASS','PASS_WITH_BLOCKER'} else 1
if __name__=='__main__':raise SystemExit(main())
