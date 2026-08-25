#!/usr/bin/env python3
"""Fail-closed approved-copy and corrective-integration contract for MF-006R8."""
import argparse,copy,hashlib,json
from pathlib import Path
from validate_mf006r1_contract import APPROVED,MUSIC,CANONICAL,PHRASES

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--project-root',required=True);p.add_argument('--output',required=True);a=p.parse_args();errors=[];blockers=[]
 try:
  f=json.loads(Path(a.fixture).read_text());root=Path(a.project_root);baseline=json.loads((root/'content/fixtures/mf006r7-unknown-process.json').read_text());s=f.get('subject',{});approved=f.get('approved_copy',{});voice=f.get('voice_contract',{});music=f.get('music',{});types=[x.get('type') for x in f.get('generated_scene',{}).get('components',[])]
  if s.get('title')!='Unknown Process' or s.get('canonical_author')!='Robert C. Blanzy' or s.get('authoritative_url')!=CANONICAL:errors.append('METADATA_FAILED')
  if approved.get('synopsis')!=APPROVED or approved.get('sole_narrative_basis') is not True or f.get('page_phrases')!=PHRASES:errors.append('COPY_FAILED')
  if f.get('visual_strategy')!={'preference':'godot_integrated_lower_right_refinement','fallback':'fail','static_book_cover_allowed':False}:errors.append('STRATEGY_FAILED')
  if f.get('format',{}).get('duration_seconds')!=28 or sum(float(x.get('duration',0)) for x in f.get('beats',[]))!=28:errors.append('TIMING_FAILED')
  if types.count('projected_data_window')!=1 or any(x in types for x in ('projected_codex','projection_plane','generated_book','electronic_platform')):errors.append('WINDOW_ARCHITECTURE_FAILED')
  normalized=copy.deepcopy(f);normalized['id']=baseline['id'];normalized['visual_strategy']=baseline['visual_strategy'];normalized['visual']=baseline['visual']
  if normalized!=baseline:errors.append('R7_CONTENT_SCOPE_FAILED')
  source=root/music.get('source','')
  if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=MUSIC or music.get('provenance',{}).get('sha256')!=MUSIC:errors.append('MUSIC_FAILED')
  if voice.get('status')=='BLOCKED_PRODUCTION_VOICE' and voice.get('available_provider') is None and voice.get('test_voice_allowed') is False:blockers.append('BLOCKED_PRODUCTION_VOICE')
  else:errors.append('VOICE_FAILED')
  mapping={'metadata':'METADATA_FAILED','copy':'COPY_FAILED','strategy':'STRATEGY_FAILED','timing':'TIMING_FAILED','single_window':'WINDOW_ARCHITECTURE_FAILED','r7_content_scope':'R7_CONTENT_SCOPE_FAILED','music':'MUSIC_FAILED'};result={'slice':'MF-006R8','checks':{k:'PASS' if v not in errors else 'FAIL' for k,v in mapping.items()}|{'voice':'BLOCKED_PRODUCTION_VOICE'},'blockers':blockers,'errors':errors,'result':'PASS_WITH_BLOCKER' if blockers and not errors else ('PASS' if not errors else 'FAIL')}
 except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError) as e:result={'slice':'MF-006R8','errors':[str(e)],'blockers':[],'result':'FAIL'}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['result'] in {'PASS','PASS_WITH_BLOCKER'} else 1
if __name__=='__main__':raise SystemExit(main())
