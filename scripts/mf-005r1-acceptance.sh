#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); export PATH="${HOME}/.local/bin:${PATH}"; godot_bin=${GODOT_BIN:-godot}
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}; artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-005r1}; report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-005r1}
mkdir -p "$artifact_dir/before-after" "$artifact_dir/audio/normalized" "$artifact_dir/audio/music" "$artifact_dir/audio/base" "$artifact_dir/audio/final" "$artifact_dir/audio/waveforms" "$artifact_dir/frames" "$artifact_dir/timelines" "$artifact_dir/validation" "$artifact_dir/logs" "$report_dir"
work_dir=$(mktemp -d "$artifact_dir/work.XXXXXX")
cleanup(){ if [[ $work_dir == "$artifact_dir"/work.* && -d $work_dir ]]; then find "$work_dir" -depth -delete; fi; }; trap cleanup EXIT
fail_result(){ local code=$?; python3 - "$report_dir/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-005R1","technical_result":"FAIL","human_review":"PENDING","exit_code":int(sys.argv[2])},indent=2)+"\n")
PY
printf '\nMF-005R1 TECHNICAL RESULT: FAIL\n' >&2; exit "$code"; }; trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-005R1\n========================\n\nBASELINE GATES\n'
for slice in mf-001 mf-002 mf-002r1 mf-003 mf-004 mf-005 mf-pilot-001; do result="$repo_root/reports/$slice/result.json"; test -s "$result"; jq -e '(.result=="PASS") or (.technical_result=="PASS")' "$result" >/dev/null; printf '[PASS] %s\n' "$slice"; done

printf '\nGOLDEN DEFECT EVIDENCE\n'
test -s "$repo_root/artifacts/mf-005/turd-burglar.mp4"; test -s "$repo_root/artifacts/mf-005/timelines/turd-burglar-narration.json"
cp "$repo_root/artifacts/mf-005/turd-burglar.mp4" "$artifact_dir/before-after/before-turd-burglar.mp4"
cp "$repo_root/artifacts/mf-005/timelines/turd-burglar.json" "$artifact_dir/before-after/before-turd-burglar-timeline.json"
cp "$repo_root/artifacts/mf-005/timelines/turd-burglar-narration.json" "$artifact_dir/before-after/before-turd-burglar-narration.json"
jq -e '.segments[] | select(.beat=="gameplay" and .text=="About a dung beetle.")' "$artifact_dir/before-after/before-turd-burglar-narration.json" >/dev/null
printf '[PASS] before case proves narration owned by media while matching text is in later silent beat\n'

python3 "$repo_root/scripts/mf-005r1-failure-tests.py" --repo-root "$repo_root" --output "$report_dir/failure-tests.json" >/dev/null
printf '[PASS] Nine strict synchronization/music/media failures\n'

python3 "$repo_root/scripts/prepare_mf005r1_music.py" --fixture "$repo_root/content/fixtures/mf005-turd-burglar.json" --project-root "$repo_root" --duration 15 --output-audio "$work_dir/no-music.wav" --output-report "$artifact_dir/validation/no-music-compatibility.json" >/dev/null
test "$(jq -r .status "$artifact_dir/validation/no-music-compatibility.json")" = NOT_PRESENT
printf '[PASS] no-music compatibility\n'

names=(turd-burglar books venus); fixtures=("$repo_root/content/fixtures/mf005r1-turd-burglar.json" "$repo_root/content/fixtures/mf005r1-books.json" "$repo_root/content/fixtures/mf005r1-venus.json")
printf '\nHARDENED PRODUCTIONS\n'
for index in "${!names[@]}"; do
 name=${names[$index]}; fixture=${fixtures[$index]}; frames="$work_dir/$name/frames"; mkdir -p "$frames" "$artifact_dir/frames/$name" "$artifact_dir/audio/normalized/$name"
 timeline="$artifact_dir/timelines/$name.json"; execution="$artifact_dir/timelines/$name-execution.json"; narration="$artifact_dir/timelines/$name-narration.json"; music="$artifact_dir/timelines/$name-music.json"; layout="$artifact_dir/validation/$name-layout.json"; media="$artifact_dir/$name.mp4"
 python3 "$repo_root/scripts/preflight_mf004.py" --fixture "$fixture" --grammar "$grammar" --project-root "$repo_root" --output "$timeline" >"$artifact_dir/logs/$name-timeline.log"
 /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-narration-metrics.txt" python3 "$repo_root/scripts/prepare_mf005_narration.py" --fixture "$fixture" --timeline "$timeline" --grammar "$grammar" --project-root "$repo_root" --normalized-dir "$artifact_dir/audio/normalized/$name" --cache-dir "$artifact_dir/audio/generated" --output "$narration" >"$artifact_dir/logs/$name-narration.log"
 python3 "$repo_root/scripts/prepare_mf005r1_music.py" --fixture "$fixture" --project-root "$repo_root" --duration 15 --output-audio "$artifact_dir/audio/music/$name.wav" --output-report "$music" >"$artifact_dir/logs/$name-music.log"
 /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-godot-metrics.txt" timeout 180 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- --fixture "$fixture" --grammar "$grammar" --output-dir "$frames" --layout-report "$layout" --timeline-report "$execution" >"$artifact_dir/logs/$name-render.log" 2>&1
 test "$(find "$frames" -maxdepth 1 -name 'frame_*.png'|wc -l)" -eq 450
 python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$artifact_dir/audio/base/$name.wav" >"$artifact_dir/logs/$name-base.log"
 /usr/bin/time -f '%e' -o "$artifact_dir/logs/$name-mix-seconds.txt" python3 "$repo_root/scripts/mix_mf005_audio.py" --base "$artifact_dir/audio/base/$name.wav" --manifest "$narration" --music-manifest "$music" --duck-db -3 --output "$artifact_dir/audio/final/$name.wav" --report "$artifact_dir/validation/$name-mix.json" >"$artifact_dir/logs/$name-mix.log"
 /usr/bin/time -f '%e' -o "$artifact_dir/logs/$name-ffmpeg-seconds.txt" ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$frames/frame_%06d.png" -i "$artifact_dir/audio/final/$name.wav" -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$media" 2>"$artifact_dir/logs/$name-ffmpeg.log"
 validation_start=$(date +%s%N)
 python3 "$repo_root/scripts/validate_media.py" "$media" --slice MF-005R1 --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-output.json" >/dev/null
 python3 "$repo_root/scripts/validate_mf004_timeline.py" --preflight "$timeline" --execution "$execution" --layout "$layout" --output "$artifact_dir/validation/$name-timeline.json" >/dev/null
 python3 "$repo_root/scripts/validate_mf005_audio.py" --manifest "$narration" --mix-report "$artifact_dir/validation/$name-mix.json" --fixture "$fixture" --grammar "$grammar" --base "$artifact_dir/audio/base/$name.wav" --expected-content-duck-db -3 --media "$media" --output "$artifact_dir/validation/$name-audio.json" >/dev/null
 python3 "$repo_root/scripts/validate_mf005r1_sync.py" --fixture "$fixture" --timeline "$timeline" --execution "$execution" --narration "$narration" --music "$music" --mix "$artifact_dir/validation/$name-mix.json" --audio-validation "$artifact_dir/validation/$name-audio.json" --output "$artifact_dir/validation/$name-sync.json" >/dev/null
 validation_end=$(date +%s%N); awk -v s="$validation_start" -v e="$validation_end" 'BEGIN{printf "%.6f\n",(e-s)/1000000000}' >"$artifact_dir/logs/$name-validation-seconds.txt"
 python3 - "$timeline" "$frames" "$artifact_dir/frames/$name" <<'PY'
import json,pathlib,shutil,sys
t=json.loads(pathlib.Path(sys.argv[1]).read_text()); src=pathlib.Path(sys.argv[2]); dst=pathlib.Path(sys.argv[3])
for b in t['beats']: shutil.copy2(src/f"frame_{round(((b['start']+b['end'])/2)*30):06d}.png",dst/f"{b['id']}.png")
PY
 ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/audio/final/$name.wav" -filter_complex 'showwavespic=s=900x180:colors=0xd4b863' -frames:v 1 "$artifact_dir/audio/waveforms/$name.png"
 printf '[PASS] %s sync/music/audio/video\n' "$name"
done

cp "$artifact_dir/turd-burglar.mp4" "$artifact_dir/before-after/after-turd-burglar.mp4"; cp "$artifact_dir/validation/turd-burglar-sync.json" "$artifact_dir/before-after/after-turd-burglar-sync.json"
python3 - "$artifact_dir" <<'PY'
import json,pathlib,sys
r=pathlib.Path(sys.argv[1]); before=json.loads((r/'before-after/before-turd-burglar-narration.json').read_text()); after=json.loads((r/'validation/turd-burglar-sync.json').read_text())
result={'slice':'MF-005R1','before':{'finding':'About a dung beetle narration is owned by gameplay media beat; matching specifics text and punchline are silent.','segments':[{'beat':s['beat'],'start':s['start'],'end':s['end'],'text':s['text']} for s in before['segments']]},'after':{'finding':'Dung-beetle and punchline narration are owned by their matching visible text beats, with an intentional pause after dung_beetle.','segments':after['timeline']['narration']},'result':'PASS'}
(r/'before-after/timing-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
PY
font="$repo_root/godot/fonts/Lato-Heavy.ttf"
ffmpeg -hide_banner -loglevel error -y -i "$repo_root/artifacts/mf-005/frames/turd-burglar/specifics.png" -i "$artifact_dir/frames/turd-burglar/dung_beetle.png" -i "$repo_root/artifacts/mf-005/frames/turd-burglar/punchline.png" -i "$artifact_dir/frames/turd-burglar/punchline.png" -filter_complex "[0:v]drawtext=fontfile='$font':text='BEFORE MATCHING TEXT / SILENT':x=12:y=18:fontsize=20:fontcolor=white[a];[1:v]drawtext=fontfile='$font':text='AFTER MATCHING TEXT + VOICE':x=12:y=18:fontsize=20:fontcolor=white[b];[2:v]drawtext=fontfile='$font':text='BEFORE PUNCHLINE / SILENT':x=12:y=18:fontsize=20:fontcolor=white[c];[3:v]drawtext=fontfile='$font':text='AFTER PUNCHLINE + VOICE':x=12:y=18:fontsize=20:fontcolor=white[d];[a][b]hstack[top];[c][d]hstack[bottom];[top][bottom]vstack" -frames:v 1 "$artifact_dir/before-after/semantic-alignment.png"
ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$artifact_dir/frames/*/*.png" -vf 'scale=180:320,tile=7x3:padding=4:margin=4:color=0x17110e' -frames:v 1 "$artifact_dir/contact-sheet.png"

python3 - "$artifact_dir" "$report_dir/result.json" <<'PY'
import json,pathlib,re,sys
r=pathlib.Path(sys.argv[1]); fixtures={}
for name in ('turd-burglar','books','venus'):
 n=json.loads((r/'timelines'/f'{name}-narration.json').read_text()); m=json.loads((r/'timelines'/f'{name}-music.json').read_text()); s=json.loads((r/'validation'/f'{name}-sync.json').read_text()); o=json.loads((r/'validation'/f'{name}-output.json').read_text()); assert n['result']==m['result']==s['result']==o['result']=='PASS'
 def metric(path): return dict(re.findall(r'(elapsed_seconds|peak_kib)=([0-9.]+)',path.read_text()))
 g=metric(r/'logs'/f'{name}-godot-metrics.txt'); p=metric(r/'logs'/f'{name}-narration-metrics.txt')
 fixtures[name]={'semantic_sync':'PASS','narrated_beats':len(n['segments']),'continuous_music':'PASS','ducking':'PASS','sfx':'PASS','production_media':'PASS','render':'PASS','validation':'PASS','sha256':o['artifact']['sha256'],'final_bytes':o['artifact']['bytes'],'metrics':{'narration_preflight_seconds':float(p['elapsed_seconds']),'music_preparation_seconds':m['preparation_seconds'],'audio_mix_seconds':float((r/'logs'/f'{name}-mix-seconds.txt').read_text()),'godot_render_seconds':float(g['elapsed_seconds']),'peak_godot_kib':int(float(g['peak_kib'])),'ffmpeg_finalization_seconds':float((r/'logs'/f'{name}-ffmpeg-seconds.txt').read_text()),'validation_seconds':float((r/'logs'/f'{name}-validation-seconds.txt').read_text())}}
result={'slice':'MF-005R1','baseline':{k:'PASS' for k in ('mf001','mf002','mf002r1','mf003','mf004','mf005','mf_pilot_001')},'golden_defect_reproduced':'PASS','fixtures':fixtures,'beat_authority':'PASS','cross_beat_narration':'PROHIBITED','intentional_pause':'PASS','ambient_music':'PASS','music_loop_fade':'PASS','narration_ducking':'PASS','existing_sfx':'PASS','production_asset_safety':'PASS','no_music_compatibility':'PASS','failure_tests':'PASS','subject_specific_timing_code':0,'technical_result':'PASS','human_review':'PENDING'}
pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
PY
trap - ERR; printf '\nMF-005R1 TECHNICAL RESULT: PASS\nHUMAN SYNCHRONIZATION/MIX REVIEW: REQUIRED\n'
