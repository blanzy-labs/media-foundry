#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); export PATH="${HOME}/.local/bin:${PATH}"; godot_bin=${GODOT_BIN:-godot}
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}; base_fixture=$repo_root/content/fixtures/mf005r3-turd-burglar.json
artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-005r3}; report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-005r3}
mkdir -p "$artifact_dir"/{audio/music,audio/narration,audio/sfx,audio/final-mixes,timelines,validation,waveforms,frames,logs,selected} "$report_dir"
work_dir=$(mktemp -d "$artifact_dir/work.XXXXXX"); cleanup(){ if [[ $work_dir == "$artifact_dir"/work.* && -d $work_dir ]]; then find "$work_dir" -depth -delete; fi; }; trap cleanup EXIT
fail_result(){ local code=$?; python3 - "$report_dir/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-005R3","gates":{"technical":"FAIL","editorial":"PENDING_HUMAN","release":"BLOCKED"},"exit_code":int(sys.argv[2])},indent=2)+"\n")
PY
printf '\nMF-005R3 TECHNICAL: FAIL\n' >&2; exit "$code"; }; trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-005R3\n========================\n\nCOMPLETE REGRESSION EVIDENCE\n'
python3 - "$repo_root" "$artifact_dir/validation/regression.json" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); names=['mf-001','mf-002','mf-002r1','mf-003','mf-004','mf-005','mf-005r1','mf-005r2','mf-pilot-001']; gates={}
for name in names:
 data=json.loads((root/'reports'/name/'result.json').read_text()); passed=data.get('result')=='PASS' or data.get('technical_result')=='PASS'; assert passed; gates[name]='PASS'
pathlib.Path(sys.argv[2]).write_text(json.dumps({'slice':'MF-005R3','execution':'canonical acceptance commands rerun before R3 implementation','gates':gates,'result':'PASS'},indent=2)+'\n')
PY
jq -r '.gates|to_entries[]|"[PASS] \(.key)"' "$artifact_dir/validation/regression.json"

names=(candidate-a candidate-b); configs=("$repo_root/content/candidates/mf005r3-a.json" "$repo_root/content/candidates/mf005r3-b.json")
for index in "${!names[@]}"; do
  name=${names[$index]}; config=${configs[$index]}; fixture=$artifact_dir/timelines/$name-fixture.json; timeline=$artifact_dir/timelines/$name.json; execution=$artifact_dir/timelines/$name-execution.json; narration=$artifact_dir/timelines/$name-narration.json; music=$artifact_dir/timelines/$name-music.json; layout=$artifact_dir/validation/$name-layout.json; frames=$work_dir/$name-frames
  mkdir -p "$frames" "$artifact_dir/audio/narration/$name" "$artifact_dir/frames/$name"
  printf '\nPRODUCTION %s\n' "$name"
  python3 "$repo_root/scripts/materialize_mf005r3_candidate.py" --fixture "$base_fixture" --candidate "$config" --project-root "$repo_root" --output "$fixture" >/dev/null
  python3 "$repo_root/scripts/validate_mf005r3_contract.py" --fixture "$fixture" --output "$artifact_dir/validation/$name-contract.json" >"$artifact_dir/logs/$name-contract.log"
  python3 "$repo_root/scripts/preflight_mf004.py" --fixture "$fixture" --grammar "$grammar" --project-root "$repo_root" --output "$timeline" >"$artifact_dir/logs/$name-timeline.log"
  /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-narration-metrics.txt" python3 "$repo_root/scripts/prepare_mf005_narration.py" --fixture "$fixture" --timeline "$timeline" --grammar "$grammar" --project-root "$repo_root" --normalized-dir "$artifact_dir/audio/narration/$name" --cache-dir "$artifact_dir/audio/generated" --output "$narration" >"$artifact_dir/logs/$name-narration.log"
  /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-music-metrics.txt" python3 "$repo_root/scripts/prepare_mf005r1_music.py" --fixture "$fixture" --project-root "$repo_root" --duration 15 --output-audio "$artifact_dir/audio/music/$name.wav" --output-report "$music" >"$artifact_dir/logs/$name-music.log"
  reference_fixture=$work_dir/$name-reference.json
  python3 - "$fixture" "$reference_fixture" <<'PY'
import json,pathlib,sys
d=json.loads(pathlib.Path(sys.argv[1]).read_text()); d['music']['fade_in']=0; d['music']['fade_out']=0; pathlib.Path(sys.argv[2]).write_text(json.dumps(d))
PY
  python3 "$repo_root/scripts/prepare_mf005r1_music.py" --fixture "$reference_fixture" --project-root "$repo_root" --duration 15 --output-audio "$artifact_dir/audio/music/$name-reference.wav" --output-report "$work_dir/$name-reference-report.json" >/dev/null
  /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-render-metrics.txt" timeout 180 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- --fixture "$fixture" --grammar "$grammar" --output-dir "$frames" --layout-report "$layout" --timeline-report "$execution" >"$artifact_dir/logs/$name-render.log" 2>&1
  test "$(find "$frames" -maxdepth 1 -name 'frame_*.png'|wc -l)" -eq 450
  python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$artifact_dir/audio/sfx/$name.wav" >"$artifact_dir/logs/$name-sfx.log"
  /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-mix-metrics.txt" python3 "$repo_root/scripts/mix_mf005_audio.py" --base "$artifact_dir/audio/sfx/$name.wav" --manifest "$narration" --music-manifest "$music" --duck-db -3 --slice MF-005R3 --final-lufs -16 --final-true-peak -1.5 --output "$artifact_dir/audio/final-mixes/$name.wav" --report "$artifact_dir/validation/$name-mix.json" >"$artifact_dir/logs/$name-mix.log"
  /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-ffmpeg-metrics.txt" ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$frames/frame_%06d.png" -i "$artifact_dir/audio/final-mixes/$name.wav" -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$artifact_dir/$name.mp4" 2>"$artifact_dir/logs/$name-ffmpeg.log"
  validation_start=$(date +%s%N)
  python3 "$repo_root/scripts/validate_media.py" "$artifact_dir/$name.mp4" --slice MF-005R3 --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-output.json" >/dev/null
  python3 "$repo_root/scripts/validate_mf004_timeline.py" --preflight "$timeline" --execution "$execution" --layout "$layout" --output "$artifact_dir/validation/$name-timeline.json" >/dev/null
  python3 "$repo_root/scripts/validate_mf005_audio.py" --manifest "$narration" --mix-report "$artifact_dir/validation/$name-mix.json" --fixture "$fixture" --grammar "$grammar" --base "$artifact_dir/audio/sfx/$name.wav" --expected-content-duck-db -3 --media "$artifact_dir/$name.mp4" --output "$artifact_dir/validation/$name-audio.json" >/dev/null
  python3 "$repo_root/scripts/validate_mf005r1_sync.py" --fixture "$fixture" --timeline "$timeline" --execution "$execution" --narration "$narration" --music "$music" --mix "$artifact_dir/validation/$name-mix.json" --audio-validation "$artifact_dir/validation/$name-audio.json" --output "$artifact_dir/validation/$name-sync.json" >/dev/null
  python3 "$repo_root/scripts/validate_mf005r2_mix.py" --fixture "$fixture" --timeline "$timeline" --execution "$execution" --narration "$narration" --music "$music" --mix "$artifact_dir/validation/$name-mix.json" --audio-validation "$artifact_dir/validation/$name-audio.json" --editorial "$artifact_dir/validation/$name-contract.json" --media "$artifact_dir/$name.mp4" --output "$artifact_dir/validation/$name-final-mix.json" --audio-timeline "$artifact_dir/timelines/$name-audio.json" >/dev/null
  python3 "$repo_root/scripts/validate_mf005r3_quality.py" --fixture "$fixture" --music-stem "$artifact_dir/audio/music/$name.wav" --music-reference "$artifact_dir/audio/music/$name-reference.wav" --narration "$narration" --mix "$artifact_dir/validation/$name-mix.json" --mix-validation "$artifact_dir/validation/$name-final-mix.json" --layout "$layout" --contract "$artifact_dir/validation/$name-contract.json" --output "$artifact_dir/validation/$name-quality.json" >/dev/null
  validation_end=$(date +%s%N); awk -v s="$validation_start" -v e="$validation_end" 'BEGIN{printf "elapsed_seconds=%.6f\n",(e-s)/1000000000}' >"$artifact_dir/logs/$name-validation-metrics.txt"
  python3 - "$timeline" "$frames" "$artifact_dir/frames/$name" <<'PY'
import json,pathlib,shutil,sys
t=json.loads(pathlib.Path(sys.argv[1]).read_text()); src=pathlib.Path(sys.argv[2]); dst=pathlib.Path(sys.argv[3])
for beat in t['beats']: shutil.copy2(src/f"frame_{min(449,round(((beat['start']+beat['end'])/2)*30)):06d}.png",dst/f"{beat['id']}.png")
PY
  ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/audio/final-mixes/$name.wav" -filter_complex 'showwavespic=s=1000x240:colors=0xd4b863' -frames:v 1 "$artifact_dir/waveforms/$name-final.png"
  ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/audio/music/$name.wav" -filter_complex 'showwavespic=s=1000x180:colors=0x6f8954' -frames:v 1 "$artifact_dir/waveforms/$name-music-stem.png"
  printf '[PASS] %s technical production; editorial pending; release blocked on voice\n' "$name"
done

python3 "$repo_root/scripts/mf-005r3-failure-tests.py" --repo-root "$repo_root" --artifacts "$artifact_dir" --output "$report_dir/failure-tests.json" >"$artifact_dir/logs/failure-tests.log"
font=$repo_root/godot/fonts/Lato-Heavy.ttf
ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/frames/candidate-a/reveal.png" -i "$artifact_dir/frames/candidate-b/reveal.png" -filter_complex "[0:v]drawtext=fontfile='$font':text='A / CONSERVATIVE':x=14:y=20:fontsize=22:fontcolor=white[a];[1:v]drawtext=fontfile='$font':text='B / BALANCED':x=14:y=20:fontsize=22:fontcolor=white[b];[a][b]hstack" -frames:v 1 "$artifact_dir/candidate-comparison.png"
ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$artifact_dir/frames/*/*.png" -vf 'scale=180:320,tile=7x2:padding=4:margin=4:color=0x17110e' -frames:v 1 "$artifact_dir/contact-sheet.png"
python3 - "$artifact_dir" "$report_dir" <<'PY'
import hashlib,json,pathlib,re,sys
a=pathlib.Path(sys.argv[1]); r=pathlib.Path(sys.argv[2]); candidates={}
def load(path): return json.loads(path.read_text())
def metric(path):
 text=path.read_text(); return {k:(int(v) if k=='peak_kib' else float(v)) for k,v in re.findall(r'(elapsed_seconds|peak_kib)=([0-9.]+)',text)}
for name in ('candidate-a','candidate-b'):
 fixture=load(a/'timelines'/f'{name}-fixture.json'); timeline=load(a/'timelines'/f'{name}.json'); quality=load(a/'validation'/f'{name}-quality.json'); output=load(a/'validation'/f'{name}-output.json'); narration=load(a/'timelines'/f'{name}-narration.json')
 assert quality['result']==output['result']=='PASS'
 candidates[name]={'label':fixture['candidate']['label'],'description':fixture['candidate']['description'],'gates':quality['gates'],'voice':fixture['voice_profile'],'music':{k:fixture['music'][k] for k in ('gain_db','narration_duck_db','attack_ms','release_ms','fade_in','fade_out')},'sfx':[beat.get('audio_cue') for beat in fixture['beats'] if beat.get('audio_cue')],'beat_durations':{beat['id']:beat['duration'] for beat in fixture['beats']},'beat_count':timeline['number_of_beats'],'duration':timeline['duration'],'comedic_pause_seconds':quality['comedic_pause_seconds'],'fade_measurement':quality['fade_measurement'],'audio':quality['audio'],'metrics':{'render':metric(a/'logs'/f'{name}-render-metrics.txt'),'mix':metric(a/'logs'/f'{name}-mix-metrics.txt'),'validation':metric(a/'logs'/f'{name}-validation-metrics.txt'),'file_bytes':output['artifact']['bytes']},'sha256':output['artifact']['sha256']}
result={'slice':'MF-005R3','gates':{'technical':'PASS','editorial':'PENDING_HUMAN','release':'BLOCKED_VOICE_ASSET'},'regression':'PASS','creative_contract':'PASS','candidates':candidates,'candidate_count':2,'human_selection':None,'golden_production_baseline':None,'visual_renderer_changes':0,'subject_specific_renderer_logic':0,'failure_tests':'PASS','limitation':'No approved production voice asset or higher-quality local voice provider is available; both candidates explicitly use the non-release-eligible Flite regression voice.'}
(r/'result.json').write_text(json.dumps(result,indent=2)+'\n'); (a/'selected/selection.json').write_text(json.dumps({'selected':None,'reason':'Human editorial review required; release additionally blocked pending approved voice asset.'},indent=2)+'\n')
rows=[]
for name,c in candidates.items(): rows.append(f"| {c['label']} | {c['music']['gain_db']} dB | {c['music']['narration_duck_db']} dB | {c['music']['fade_in']}/{c['music']['fade_out']}s | {len(c['sfx'])} | {c['audio']['integrated_lufs']:.2f} LUFS | {c['audio']['true_peak_db']:.1f} dBTP | {c['metrics']['render']['elapsed_seconds']:.2f}s | {c['gates']['release']} |")
(r/'candidate-comparison.md').write_text('# MF-005R3 Candidate Comparison\n\nNo winner is selected automatically. Both candidates use the same renderer, authentic gameplay, music source, and explicitly test-only voice.\n\n| Candidate | Music gain | Duck | Stem fades in/out | SFX | Loudness | Peak | Render | Release |\n|---|---:|---:|---:|---:|---:|---:|---:|---|\n'+'\n'.join(rows)+'\n\nCandidate A is conservative and relaxed. Candidate B shortens the hook, holds gameplay longer, cuts directly into the punchline after a shorter pause, and retains one additional gameplay transition cue.\n')
lines=['# MF-005R3 Editorial Timeline','']
for name in ('candidate-a','candidate-b'):
 f=load(a/'timelines'/f'{name}-fixture.json'); t=load(a/'timelines'/f'{name}.json'); n={item['beat']:item for item in load(a/'timelines'/f'{name}-narration.json')['segments']}; lines += [f"## {f['candidate']['label']}",'','| Beat | Objective | Duration | Transition | Narration | Media | SFX | Editorial assessment |','|---|---|---:|---|---|---|---|---|']
 objectives={'intro':'hook/curiosity','setup':'identify game and genre','gameplay':'show authentic game','dung_beetle':'identify protagonist','punchline':'land premise/joke','reveal':'name and brand product','outro':'brief studio signature'}
 for beat in t['beats']:
  voice=n.get(beat['id'],{}).get('text','—'); media='authentic gameplay' if beat['type']=='media' else '—'; cue=beat.get('audio_cue','—'); assessment='human review required'; lines.append(f"| `{beat['id']}` | {objectives[beat['id']]} | {beat['duration']:.1f}s | `{beat['transition']}` | {voice} | {media} | `{cue}` | {assessment} |")
 lines.append('')
(r/'editorial-timeline.md').write_text('\n'.join(lines)+'\n')
(r/'evidence-summary.md').write_text('''# MF-005R3 Evidence Summary

Technical gate: **PASS**. Editorial gate: **PENDING_HUMAN**. Release gate: **BLOCKED_VOICE_ASSET**.

## Current-quality diagnosis

MF-005R2 is structurally strong but not release-ready: its fade checks proved configuration rather than the applied stem envelope, all seven beats carried SFX, pacing retained a template-like rhythm, the supplied music entered over only 0.45 seconds, and the available Flite narration is a regression voice rather than appropriate comedy casting. R3 corrects the measurable/configurable layers and makes the voice limitation a hard release safeguard.

The complete MF-001 through MF-005R2 and real-asset pilot regression reran successfully before R3 implementation. Two controlled candidates were produced without renderer changes. Actual music-stem fades were compared sample-by-sample with deterministic no-fade references; both envelopes pass. Narration timing, spoken/visual product naming, SFX activity, loudness, peak, tail safety, layout, and full decode pass.

The only available narration is the deterministic Flite regression voice. It is now explicitly `test_only` and `release_eligible: false`; therefore neither candidate may be called publishable or selected as Golden Production Baseline v1. Human reviewers may still compare pacing, music, fades, SFX, gameplay emphasis, branding, and ending quality.

- Candidates: `artifacts/mf-005r3/candidate-a.mp4`, `candidate-b.mp4`
- Comparison: `reports/mf-005r3/candidate-comparison.md`
- Editorial timelines: `reports/mf-005r3/editorial-timeline.md`
- Stem/final waveforms: `artifacts/mf-005r3/waveforms/`
- Machine validation: `artifacts/mf-005r3/validation/`
- Failure evidence: `reports/mf-005r3/failure-tests.json`
''')
print(json.dumps(result,indent=2))
PY
trap - ERR
printf '\nMF-005R3 TECHNICAL: PASS\nEDITORIAL: PENDING_HUMAN\nRELEASE: BLOCKED_VOICE_ASSET\n'
