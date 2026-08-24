#!/usr/bin/env python3
"""Fail-closed approved-copy and final-polish contract for MF-006R6."""
import argparse,hashlib,json
from pathlib import Path
from validate_mf006r1_contract import APPROVED,MUSIC,CANONICAL,PHRASES

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--project-root',required=True);p.add_argument('--output',required=True);a=p.parse_args();errors=[];blockers=[]
 try:
  f=json.loads(Path(a.fixture).read_text());root=Path(a.project_root);s=f.get('subject',{});copy=f.get('approved_copy',{});strategy=f.get('visual_strategy',{});cta=f.get('cta',{});voice=f.get('voice_contract',{});music=f.get('music',{});scene=f.get('generated_scene',{});duration=f.get('format',{}).get('duration_seconds')
  if s.get('title')!='Unknown Process' or s.get('canonical_author')!='Robert C. Blanzy' or s.get('author')!='R.C. Blanzy' or s.get('book_number')!=1 or s.get('authoritative_url')!=CANONICAL:errors.append('APPROVED_METADATA_FAILED')
  if copy.get('synopsis')!=APPROVED or copy.get('sole_narrative_basis') is not True or copy.get('invented_plot_details') is not False or f.get('page_phrases')!=PHRASES:errors.append('APPROVED_COPY_FAILED')
  if strategy!={'preference':'godot_final_polish_refinement','fallback':'fail','static_book_cover_allowed':False} or f.get('media') is not None:errors.append('FINAL_POLISH_STRATEGY_REQUIRED')
  if duration!=28 or abs(sum(float(b.get('duration',0)) for b in f.get('beats',[]))-duration)>1e-6:errors.append('RUNTIME_PRESERVATION_FAILED')
  types=[x.get('type') for x in scene.get('components',[])];serialized=json.dumps(f).casefold()
  if types.count('projected_data_window')!=1 or any(x in types for x in ('projected_codex','projection_plane','generated_book','book_generation_cradle','electronic_platform')):errors.append('SINGLE_WINDOW_COMPONENT_FAILED')
  if any(ext in serialized for ext in ('.png"','.jpg"','.jpeg"')):errors.append('STATIC_COVER_PROHIBITED')
  if cta.get('canonical_url')!=CANONICAL or cta.get('display_url')!='rcblanzy.com/books/unknown-process':errors.append('APPROVED_DESTINATION_FAILED')
  if voice.get('test_voice_allowed') is not False or voice.get('release_eligible') is not False or any(b.get('narration') is not None for b in f.get('beats',[])):errors.append('TEST_VOICE_PROHIBITED')
  if voice.get('status')=='BLOCKED_PRODUCTION_VOICE' and voice.get('available_provider') is None:blockers.append('BLOCKED_PRODUCTION_VOICE')
  else:errors.append('VOICE_CONTRACT_INVALID')
  source=root/music.get('source','')
  if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=MUSIC or music.get('provenance',{}).get('sha256')!=MUSIC:errors.append('SUPPLIED_MUSIC_INVALID')
  events={x.get('id'):x.get('time') for x in scene.get('events',[])};required={'overload_pulse_1','overload_pulse_2','record_hold_1','record_reset_1','record_hold_2','record_reset_2','record_hold_3','cta_energy','cta_typing','cta_lock','website_reveal'}
  if not required<=events.keys():errors.append('POLISH_EVENT_CONTRACT_FAILED')
  elif not (events['record_lock_1']<events['record_hold_1']<events['record_reset_1']<events['screen_refresh_1']<events['record_query_2'] and events['record_lock_2']<events['record_hold_2']<events['record_reset_2']<events['screen_refresh_2']<events['record_query_3'] and events['record_lock_3']<events['record_hold_3']<events['screen_collapse'] and events['cta_energy']<events['cta_typing']<events['cta_lock']<events['website_reveal']<=duration-2):errors.append('POLISH_EVENT_ORDER_FAILED')
  result={'slice':'MF-006R6','duration_seconds':duration,'approved_source':{'url':CANONICAL,'organization':'Robert C. Blanzy','retrieval_date':s.get('retrieval_date'),'synopsis_sha256':hashlib.sha256(APPROVED.encode()).hexdigest()},'checks':{'metadata':'PASS' if 'APPROVED_METADATA_FAILED' not in errors else 'FAIL','approved_copy':'PASS' if 'APPROVED_COPY_FAILED' not in errors else 'FAIL','runtime':'PASS' if 'RUNTIME_PRESERVATION_FAILED' not in errors else 'FAIL','single_window':'PASS' if 'SINGLE_WINDOW_COMPONENT_FAILED' not in errors else 'FAIL','polish_events':'PASS' if not any('POLISH_EVENT' in x for x in errors) else 'FAIL','destination':'PASS' if 'APPROVED_DESTINATION_FAILED' not in errors else 'FAIL','music':'PASS' if 'SUPPLIED_MUSIC_INVALID' not in errors else 'FAIL','voice':'BLOCKED_PRODUCTION_VOICE'},'blockers':blockers,'errors':errors,'result':'PASS_WITH_BLOCKER' if blockers and not errors else ('PASS' if not errors else 'FAIL')}
 except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError) as e:result={'slice':'MF-006R6','errors':[str(e)],'blockers':[],'result':'FAIL'}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['result'] in {'PASS','PASS_WITH_BLOCKER'} else 1
if __name__=='__main__':raise SystemExit(main())
