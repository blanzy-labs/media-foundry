#!/usr/bin/env python3
"""Fail-closed approved-copy and lower-right polish contract for MF-006R7."""
import argparse,hashlib,json
from pathlib import Path
from validate_mf006r1_contract import APPROVED,MUSIC,CANONICAL,PHRASES
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--project-root',required=True);p.add_argument('--output',required=True);a=p.parse_args();errors=[];blockers=[]
 try:
  f=json.loads(Path(a.fixture).read_text());root=Path(a.project_root);s=f.get('subject',{});copy=f.get('approved_copy',{});voice=f.get('voice_contract',{});music=f.get('music',{});types=[x.get('type') for x in f.get('generated_scene',{}).get('components',[])]
  if s.get('title')!='Unknown Process' or s.get('canonical_author')!='Robert C. Blanzy' or s.get('authoritative_url')!=CANONICAL:errors.append('METADATA_FAILED')
  if copy.get('synopsis')!=APPROVED or copy.get('sole_narrative_basis') is not True or f.get('page_phrases')!=PHRASES:errors.append('COPY_FAILED')
  if f.get('visual_strategy')!={'preference':'godot_lower_right_polish_refinement','fallback':'fail','static_book_cover_allowed':False}:errors.append('STRATEGY_FAILED')
  if f.get('format',{}).get('duration_seconds')!=28 or sum(float(x.get('duration',0)) for x in f.get('beats',[]))!=28:errors.append('TIMING_FAILED')
  if types.count('projected_data_window')!=1 or any(x in types for x in ('projected_codex','projection_plane','generated_book','electronic_platform')):errors.append('WINDOW_ARCHITECTURE_FAILED')
  if f.get('cta',{}).get('canonical_url')!=CANONICAL:errors.append('DESTINATION_FAILED')
  source=root/music.get('source','');
  if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=MUSIC or music.get('provenance',{}).get('sha256')!=MUSIC:errors.append('MUSIC_FAILED')
  if voice.get('status')=='BLOCKED_PRODUCTION_VOICE' and voice.get('available_provider') is None and voice.get('test_voice_allowed') is False:blockers.append('BLOCKED_PRODUCTION_VOICE')
  else:errors.append('VOICE_FAILED')
  result={'slice':'MF-006R7','checks':{'metadata':'PASS' if 'METADATA_FAILED' not in errors else 'FAIL','copy':'PASS' if 'COPY_FAILED' not in errors else 'FAIL','strategy':'PASS' if 'STRATEGY_FAILED' not in errors else 'FAIL','timing':'PASS' if 'TIMING_FAILED' not in errors else 'FAIL','single_window':'PASS' if 'WINDOW_ARCHITECTURE_FAILED' not in errors else 'FAIL','destination':'PASS' if 'DESTINATION_FAILED' not in errors else 'FAIL','music':'PASS' if 'MUSIC_FAILED' not in errors else 'FAIL','voice':'BLOCKED_PRODUCTION_VOICE'},'blockers':blockers,'errors':errors,'result':'PASS_WITH_BLOCKER' if blockers and not errors else ('PASS' if not errors else 'FAIL')}
 except (OSError,json.JSONDecodeError,TypeError,ValueError) as e:result={'slice':'MF-006R7','errors':[str(e)],'blockers':[],'result':'FAIL'}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['result'] in {'PASS','PASS_WITH_BLOCKER'} else 1
if __name__=='__main__':raise SystemExit(main())
