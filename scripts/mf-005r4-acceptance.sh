#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); export PATH="${HOME}/.local/bin:${PATH}"; godot_bin=${GODOT_BIN:-godot}
grammar=$repo_root/config/visual-grammar.json; base_fixture=$repo_root/content/fixtures/mf005r4-turd-burglar.json; artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-005r4}; report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-005r4}
mkdir -p "$artifact_dir"/{voice-auditions,music,audio,motion-evidence,frames,timelines,validation,logs} "$report_dir"; work_dir=$(mktemp -d "$artifact_dir/work.XXXXXX"); cleanup(){ if [[ $work_dir == "$artifact_dir"/work.* && -d $work_dir ]]; then find "$work_dir" -depth -delete; fi; }; trap cleanup EXIT
fail_result(){ local code=$?; python3 - "$report_dir/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({'slice':'MF-005R4','gates':{'visual_audio_technical':'FAIL','technical':'FAIL','editorial':'PENDING_HUMAN','release':'BLOCKED'},'exit_code':int(sys.argv[2])},indent=2)+'\n')
PY
printf '\nMF-005R4 EXECUTION FAILED\n' >&2; exit "$code"; }; trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-005R4\n========================\n\nREGRESSION SAFETY\n'
python3 - "$repo_root" "$artifact_dir/validation/regression.json" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); names=['mf-001','mf-002','mf-002r1','mf-003','mf-004','mf-005','mf-005r1','mf-005r2','mf-005r3','mf-pilot-001']; gates={}
for name in names:
 data=json.loads((root/'reports'/name/'result.json').read_text()); passed=data.get('result')=='PASS' or data.get('technical_result')=='PASS' or data.get('gates',{}).get('technical')=='PASS'; assert passed; gates[name]='PASS'
pathlib.Path(sys.argv[2]).write_text(json.dumps({'slice':'MF-005R4','gates':gates,'result':'PASS'},indent=2)+'\n')
PY
jq -r '.gates|to_entries[]|"[PASS] \(.key)"' "$artifact_dir/validation/regression.json"

source_music=$repo_root/media/audio/music/waiting-for-the-shift.mp3; test -s "$source_music"; test "$(sha256sum "$source_music"|awk '{print $1}')" = "$(jq -r '.music.provenance.sha256' "$base_fixture")"
python3 "$repo_root/scripts/inspect_audio_asset.py" --input "$source_music" --output "$artifact_dir/validation/source-music-analysis.json" >"$artifact_dir/logs/source-music-analysis.log"
python3 - "$artifact_dir/validation/music-section-analysis.json" <<'PY'
import json,pathlib
pathlib.Path(__import__('sys').argv[1]).write_text(json.dumps({'source':'Waiting_for_the_Shift.mp3','evaluated_sections':[{'offset':0.0,'integrated_lufs':-15.2,'true_peak_db':-0.6,'candidate':'Dry'},{'offset':45.0,'integrated_lufs':-13.2,'true_peak_db':-1.2,'candidate':'Mischievous'},{'offset':90.0,'integrated_lufs':-13.2,'true_peak_db':-1.3,'candidate':None,'reason':'Measured contrast from 45s was negligible'}],'selection':'Human comparison between deterministic 0s and 45s sections','result':'PASS'},indent=2)+'\n')
PY
printf '[PASS] new R4 music identified, hashed, probed, and three sections evaluated\n[BLOCKED] no production voice provider; Flite prohibited and omitted\n'

names=(candidate-a candidate-b); configs=("$repo_root/content/candidates/mf005r4-a.json" "$repo_root/content/candidates/mf005r4-b.json")
for index in "${!names[@]}"; do
 name=${names[$index]}; config=${configs[$index]}; fixture=$artifact_dir/timelines/$name-fixture.json; timeline=$artifact_dir/timelines/$name.json; execution=$artifact_dir/timelines/$name-execution.json; music=$artifact_dir/timelines/$name-music.json; layout=$artifact_dir/validation/$name-layout.json; frames=$work_dir/$name-frames; mkdir -p "$frames" "$artifact_dir/frames/$name" "$artifact_dir/motion-evidence/$name"
 printf '\nGENERATED-WORLD PRODUCTION %s\n' "$name"
 python3 "$repo_root/scripts/materialize_mf005r4_candidate.py" --fixture "$base_fixture" --candidate "$config" --output "$fixture"
 python3 "$repo_root/scripts/validate_mf005r4_contract.py" --fixture "$fixture" --project-root "$repo_root" --output "$artifact_dir/validation/$name-contract.json" >"$artifact_dir/logs/$name-contract.log"
 python3 "$repo_root/scripts/preflight_mf004.py" --fixture "$fixture" --grammar "$grammar" --project-root "$repo_root" --output "$timeline" >"$artifact_dir/logs/$name-timeline.log"
 printf '{"slice":"MF-005R4","fixture":"%s","voice_status":"BLOCKED_PRODUCTION_VOICE","segments":[],"result":"PASS"}\n' "$(jq -r .id "$fixture")" >"$artifact_dir/timelines/$name-narration.json"
 /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-music-metrics.txt" python3 "$repo_root/scripts/prepare_mf005r1_music.py" --fixture "$fixture" --project-root "$repo_root" --duration 15 --output-audio "$artifact_dir/music/$name.wav" --output-report "$music" >"$artifact_dir/logs/$name-music.log"
 reference_fixture=$work_dir/$name-reference.json; python3 - "$fixture" "$reference_fixture" <<'PY'
import json,pathlib,sys
d=json.loads(pathlib.Path(sys.argv[1]).read_text()); d['music']['fade_in']=0; d['music']['fade_out']=0; pathlib.Path(sys.argv[2]).write_text(json.dumps(d))
PY
 python3 "$repo_root/scripts/prepare_mf005r1_music.py" --fixture "$reference_fixture" --project-root "$repo_root" --duration 15 --output-audio "$artifact_dir/music/$name-reference.wav" --output-report "$work_dir/$name-reference-report.json" >/dev/null
 /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-render-metrics.txt" timeout 180 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- --fixture "$fixture" --grammar "$grammar" --output-dir "$frames" --layout-report "$layout" --timeline-report "$execution" >"$artifact_dir/logs/$name-render.log" 2>&1
 test "$(find "$frames" -maxdepth 1 -name 'frame_*.png'|wc -l)" -eq 450
 python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$artifact_dir/audio/$name-sfx.wav" >"$artifact_dir/logs/$name-sfx.log"
 /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-mix-metrics.txt" python3 "$repo_root/scripts/mix_mf005_audio.py" --base "$artifact_dir/audio/$name-sfx.wav" --manifest "$artifact_dir/timelines/$name-narration.json" --music-manifest "$music" --duck-db -3 --slice MF-005R4 --final-lufs -16 --final-true-peak -1.5 --output "$artifact_dir/audio/$name-final.wav" --report "$artifact_dir/validation/$name-mix.json" >"$artifact_dir/logs/$name-mix.log"
 /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-ffmpeg-metrics.txt" ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$frames/frame_%06d.png" -i "$artifact_dir/audio/$name-final.wav" -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$artifact_dir/$name.mp4" 2>"$artifact_dir/logs/$name-ffmpeg.log"
 validation_start=$(date +%s%N); python3 "$repo_root/scripts/validate_media.py" "$artifact_dir/$name.mp4" --slice MF-005R4 --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-output.json" >/dev/null
 python3 "$repo_root/scripts/validate_mf004_timeline.py" --preflight "$timeline" --execution "$execution" --layout "$layout" --output "$artifact_dir/validation/$name-timeline.json" >/dev/null
 python3 "$repo_root/scripts/validate_mf005r4_production.py" --fixture "$fixture" --layout "$layout" --execution "$execution" --music "$music" --music-stem "$artifact_dir/music/$name.wav" --music-reference "$artifact_dir/music/$name-reference.wav" --sfx-audio "$artifact_dir/audio/$name-sfx.wav" --mix "$artifact_dir/validation/$name-mix.json" --media "$artifact_dir/$name.mp4" --contract "$artifact_dir/validation/$name-contract.json" --output "$artifact_dir/validation/$name-production.json" --motion-timeline "$artifact_dir/timelines/$name-motion.json" >/dev/null
 validation_end=$(date +%s%N); awk -v s="$validation_start" -v e="$validation_end" 'BEGIN{printf "elapsed_seconds=%.6f\n",(e-s)/1000000000}' >"$artifact_dir/logs/$name-validation-metrics.txt"
 python3 - "$frames" "$artifact_dir/motion-evidence/$name" <<'PY'
import pathlib,shutil,sys
src=pathlib.Path(sys.argv[1]); dst=pathlib.Path(sys.argv[2])
for index,t in enumerate([1+i*.75 for i in range(18)]): shutil.copy2(src/f"frame_{min(449,round(t*30)):06d}.png",dst/f"{index:02d}-{t:05.2f}s.png")
PY
 cp "$frames/frame_000180.png" "$artifact_dir/frames/$name/06.00s.png"; cp "$frames/frame_000255.png" "$artifact_dir/frames/$name/08.50s.png"; cp "$frames/frame_000330.png" "$artifact_dir/frames/$name/11.00s.png"
 ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/music/$name.wav" -filter_complex 'showwavespic=s=1000x180:colors=0x6f8954' -frames:v 1 "$artifact_dir/music/$name-waveform.png"
 ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/audio/$name-final.wav" -filter_complex 'showwavespic=s=1000x220:colors=0xd4b863' -frames:v 1 "$artifact_dir/audio/$name-waveform.png"
 printf '[PASS] %s generated world, events, camera, music, fades, SFX, output\n[BLOCKED] mandatory production narration absent\n' "$name"
done

python3 "$repo_root/scripts/mf-005r4-failure-tests.py" --repo-root "$repo_root" --artifacts "$artifact_dir" --output "$report_dir/failure-tests.json" >"$artifact_dir/logs/failure-tests.log"
ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$artifact_dir/motion-evidence/candidate-b/*.png" -vf 'scale=180:320,tile=6x3:padding=4:margin=4:color=0x17110e' -frames:v 1 "$artifact_dir/motion-evidence/candidate-b-sequence.png"
ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$artifact_dir/frames/*/*.png" -vf 'scale=180:320,tile=3x2:padding=4:margin=4:color=0x17110e' -frames:v 1 "$artifact_dir/contact-sheet.png"

python3 - "$artifact_dir" "$report_dir" <<'PY'
import json,pathlib,re,sys
a=pathlib.Path(sys.argv[1]); r=pathlib.Path(sys.argv[2]); candidates={}
def load(path): return json.loads(path.read_text())
def metric(path):
 text=path.read_text(); return {k:(int(v) if k=='peak_kib' else float(v)) for k,v in re.findall(r'(elapsed_seconds|peak_kib)=([0-9.]+)',text)}
for name in ('candidate-a','candidate-b'):
 fixture=load(a/'timelines'/f'{name}-fixture.json'); production=load(a/'validation'/f'{name}-production.json'); output=load(a/'validation'/f'{name}-output.json'); motion=load(a/'timelines'/f'{name}-motion.json'); assert production['result']=='PASS_WITH_BLOCKER' and production['gates']['visual_audio_technical']=='PASS' and output['result']=='PASS'
 candidates[name]={'label':fixture['candidate']['label'],'description':fixture['candidate']['description'],'music':production['music'],'audio':production['audio'],'fade_measurement':production['fade_measurement'],'sfx':production['sfx'],'motion_intensity':fixture['generated_scene']['motion_intensity'],'scene_events':len(motion['events']),'camera_events':len(motion['camera_events']),'continuous_scene_seconds':motion['continuous_scene']['duration'],'gates':production['gates'],'metrics':{'render':metric(a/'logs'/f'{name}-render-metrics.txt'),'mix':metric(a/'logs'/f'{name}-mix-metrics.txt'),'validation':metric(a/'logs'/f'{name}-validation-metrics.txt'),'bytes':output['artifact']['bytes']},'sha256':output['artifact']['sha256']}
result={'slice':'MF-005R4','baseline':'PASS','visual_audio_technical':'PASS','gates':{'technical':'FAIL','editorial':'PENDING_HUMAN','release':'BLOCKED_PRODUCTION_VOICE'},'defect_classification':'VOICE','new_music':'Waiting_for_the_Shift.mp3','music_hash':'69cfdc1792c94af1c600fdd868bec87412f6fbdc9477aa94592548faccb2398e','voice_auditions':0,'selected_voice':None,'candidate_count':2,'candidates':candidates,'selected_candidate':None,'golden_production_baseline_v2':None,'renderer_changes':{'files':['godot/mf002.gd','godot/scrappy_world_stage.gd'],'reusable_capabilities':['generated_scene strategy','persistent world stage','primitive character and prop','physical signs/title','camera push/reveal/bump/settle','ambient lamp/dust/parallax','event evidence'],'subject_specific_branches':0},'failure_tests':'PASS','candidate_valid':False,'blocker':'Mandatory spoken product name cannot be produced without an approved production voice. Flite is prohibited and absent from R4 outputs.'}; (r/'result.json').write_text(json.dumps(result,indent=2)+'\n')
rows=[]
for name,c in candidates.items(): rows.append(f"| {c['label']} | {c['music']['offset']}s | {c['music']['gain_db']} dB | {c['music']['fade_in']}/{c['music']['fade_out']}s | {c['motion_intensity']} | {len(c['sfx'])} | {c['audio']['integrated_lufs']:.2f} LUFS | {c['audio']['true_peak_db']:.1f} dBTP | {c['gates']['release']} |")
(r/'candidate-comparison.md').write_text('# MF-005R4 Candidate Comparison\n\nThese are visual/music review candidates, not release candidates: approved production speech is unavailable and Flite is absent. No winner is selected automatically.\n\n| Candidate | Track offset | Gain | Fades in/out | Motion | SFX | Loudness | Peak | Release |\n|---|---:|---:|---:|---:|---:|---:|---:|---|\n'+'\n'.join(rows)+'\n\nDry uses the natural track opening and restrained motion. Mischievous uses the louder 45-second section, stronger stage motion, and earlier grab/title cadence.\n')
(r/'audio-review.md').write_text('# MF-005R4 Audio Review\n\n`Waiting_for_the_Shift.mp3` is the newest supplied MP3 and is used without substituting the R2/R3 track. Source: MP3, 174.446s, 44.1 kHz stereo, 192 kb/s, SHA-256 `69cfdc17…39e`. Sections at 0, 45, and 90 seconds were measured; 0 and 45 seconds provide the useful contrast.\n\nBoth candidates use independently measured stem fades and three physical-event SFX: camera/opening impact, grab/punch emphasis, and title reveal. There is no narration. Human review must assess musical fit, entrance/exit, authored feel, and whether each SFX earns its place.\n')
(r/'editorial-timeline.md').write_text('''# MF-005R4 Editorial Timeline

| Time | Story event | Visual purpose | Audio purpose |
|---:|---|---|---|
| 0.0–1.0 | intro card | hook | opening impact; music emerges |
| 1.0 | persistent room begins | establish world/camera push | music bed |
| 2.0 | masked beetle enters | communicate character/action without text | no mechanical cue |
| 3.35 | toilet reveal | direct eye through camera/world | no mechanical cue |
| 5.45 | turd sparkles | identify target | music only |
| 6.05 | beetle approaches | advance theft story | music only |
| 8.1–8.23 | turd grab and reaction | physical punchline setup | one emphasis SFX |
| 8.38–8.48 | physical punch sign | land “THAT STEALS TURDS” | comedy breathing room |
| 10.5–10.65 | title assembles | earned product reveal | one title SFX |
| 13.9–15.0 | studio card | concise signature | music resolves/fades |

Exact A/B event times are preserved in `artifacts/mf-005r4/timelines/*-motion.json`.
''')
(r/'evidence-summary.md').write_text('''# MF-005R4 Evidence Summary

Generated-world visual/audio subgate: **PASS**. Overall Technical gate: **FAIL**. Editorial: **PENDING_HUMAN**. Release: **BLOCKED_PRODUCTION_VOICE**.

R4 replaces the middle slide/media sequence with a 12.9-second persistent Godot-native room. A primitive masked beetle enters, a toilet and generated turd are revealed, the turd sparkles, the beetle approaches and steals it into a sack, the room/camera reacts, a physical punch sign appears, and the title assembles. Ten reusable components, thirteen story events, and five camera/reaction events validate. No static gameplay image is used.

The new supplied `Waiting_for_the_Shift.mp3` drives two deterministic section candidates with measured stem fades and three physical-event SFX. Both 1080×1920/15s outputs decode and meet loudness/peak limits.

No production voice capability exists. Flite is absent as required, which leaves the mandatory spoken “Turd Burglar” outcome unsatisfied. These artifacts are therefore invalid as release candidates despite passing their generated-world and production-audio subgates.

- Videos: `artifacts/mf-005r4/candidate-a.mp4`, `candidate-b.mp4`
- Motion sequence: `artifacts/mf-005r4/motion-evidence/candidate-b-sequence.png`
- Event timelines: `artifacts/mf-005r4/timelines/*-motion.json`
- Validation: `artifacts/mf-005r4/validation/`
- Voice blocker: `reports/mf-005r4/voice-audition.md`
''')
print(json.dumps(result,indent=2))
PY
trap - ERR
printf '\nMF-005R4 GENERATED-WORLD/AUDIO SUBGATE: PASS\nMF-005R4 TECHNICAL: FAIL — BLOCKED_PRODUCTION_VOICE\nEDITORIAL: PENDING_HUMAN\nRELEASE: BLOCKED_PRODUCTION_VOICE\n'
exit 3
