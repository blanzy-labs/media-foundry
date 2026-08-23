#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
godot_bin=${GODOT_BIN:-godot}
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}
fixture=$repo_root/content/fixtures/mf005r2-turd-burglar.json
artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-005r2}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-005r2}
mkdir -p "$artifact_dir"/{before-after,audio/source,audio/normalized,audio/base,audio/final,audio/waveforms,frames,timelines,validation,logs} "$report_dir"
work_dir=$(mktemp -d "$artifact_dir/work.XXXXXX")
cleanup(){ if [[ $work_dir == "$artifact_dir"/work.* && -d $work_dir ]]; then find "$work_dir" -depth -delete; fi; }
trap cleanup EXIT
fail_result(){ local code=$?; python3 - "$report_dir/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-005R2","technical_result":"FAIL","human_review":"PENDING","exit_code":int(sys.argv[2])},indent=2)+"\n")
PY
printf '\nMF-005R2 TECHNICAL RESULT: FAIL\n' >&2; exit "$code"; }
trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-005R2\n========================\n\nBASELINE GATES\n'
for slice in mf-001 mf-002 mf-002r1 mf-003 mf-004 mf-005 mf-005r1 mf-pilot-001; do
  result="$repo_root/reports/$slice/result.json"; test -s "$result"
  jq -e '(.result=="PASS") or (.technical_result=="PASS")' "$result" >/dev/null
  printf '[PASS] %s\n' "$slice"
done

printf '\nSUPPLIED MUSIC + EDITORIAL PREFLIGHT\n'
source_music=$repo_root/media/audio/music/clockwork-heist.mp3
test -s "$source_music"
test "$(sha256sum "$source_music" | awk '{print $1}')" = "$(jq -r '.music.provenance.sha256' "$fixture")"
cp "$source_music" "$artifact_dir/audio/source/clockwork-heist.mp3"
python3 "$repo_root/scripts/inspect_audio_asset.py" --input "$source_music" --output "$artifact_dir/validation/source-music-analysis.json" >"$artifact_dir/logs/source-music-analysis.log"
python3 "$repo_root/scripts/validate_mf005r2_editorial.py" --fixture "$fixture" --output "$artifact_dir/validation/turd-burglar-editorial.json" >"$artifact_dir/logs/editorial.log"
printf '[PASS] supplied asset readable, hash matched, provenance present\n[PASS] explicit editorial contract\n'

before=$repo_root/artifacts/mf-005r1/turd-burglar.mp4
test -s "$before"
cp "$before" "$artifact_dir/before-after/before-turd-burglar.mp4"

timeline=$artifact_dir/timelines/turd-burglar.json
execution=$artifact_dir/timelines/turd-burglar-execution.json
narration=$artifact_dir/timelines/turd-burglar-narration.json
music=$artifact_dir/timelines/turd-burglar-music.json
layout=$artifact_dir/validation/turd-burglar-layout.json
frames=$work_dir/frames
mkdir -p "$frames" "$artifact_dir/audio/normalized/narration"

printf '\nPRODUCTION\n'
python3 "$repo_root/scripts/preflight_mf004.py" --fixture "$fixture" --grammar "$grammar" --project-root "$repo_root" --output "$timeline" >"$artifact_dir/logs/timeline.log"
/usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/narration-metrics.txt" python3 "$repo_root/scripts/prepare_mf005_narration.py" --fixture "$fixture" --timeline "$timeline" --grammar "$grammar" --project-root "$repo_root" --normalized-dir "$artifact_dir/audio/normalized/narration" --cache-dir "$artifact_dir/audio/generated" --output "$narration" >"$artifact_dir/logs/narration.log"
/usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/music-metrics.txt" python3 "$repo_root/scripts/prepare_mf005r1_music.py" --fixture "$fixture" --project-root "$repo_root" --duration 15 --output-audio "$artifact_dir/audio/normalized/clockwork-heist-bed.wav" --output-report "$music" >"$artifact_dir/logs/music.log"
/usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/godot-metrics.txt" timeout 180 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- --fixture "$fixture" --grammar "$grammar" --output-dir "$frames" --layout-report "$layout" --timeline-report "$execution" >"$artifact_dir/logs/render.log" 2>&1
test "$(find "$frames" -maxdepth 1 -name 'frame_*.png' | wc -l)" -eq 450
python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$artifact_dir/audio/base/turd-burglar.wav" >"$artifact_dir/logs/base-audio.log"
/usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/mix-metrics.txt" python3 "$repo_root/scripts/mix_mf005_audio.py" --base "$artifact_dir/audio/base/turd-burglar.wav" --manifest "$narration" --music-manifest "$music" --duck-db -3 --slice MF-005R2 --final-lufs -16 --final-true-peak -1.5 --output "$artifact_dir/audio/final/turd-burglar.wav" --report "$artifact_dir/validation/turd-burglar-mix.json" >"$artifact_dir/logs/mix.log"
/usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/ffmpeg-metrics.txt" ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$frames/frame_%06d.png" -i "$artifact_dir/audio/final/turd-burglar.wav" -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$artifact_dir/turd-burglar.mp4" 2>"$artifact_dir/logs/ffmpeg.log"
printf '[PASS] narration, music, visual frames, cues, and final mix assembled\n'

printf '\nINDEPENDENT VALIDATION\n'
validation_start=$(date +%s%N)
python3 "$repo_root/scripts/validate_media.py" "$artifact_dir/turd-burglar.mp4" --slice MF-005R2 --ffprobe-json "$artifact_dir/validation/turd-burglar-ffprobe.json" --result-json "$artifact_dir/validation/turd-burglar-output.json" >/dev/null
python3 "$repo_root/scripts/validate_mf004_timeline.py" --preflight "$timeline" --execution "$execution" --layout "$layout" --output "$artifact_dir/validation/turd-burglar-timeline.json" >/dev/null
python3 "$repo_root/scripts/validate_mf005_audio.py" --manifest "$narration" --mix-report "$artifact_dir/validation/turd-burglar-mix.json" --fixture "$fixture" --grammar "$grammar" --base "$artifact_dir/audio/base/turd-burglar.wav" --expected-content-duck-db -3 --media "$artifact_dir/turd-burglar.mp4" --output "$artifact_dir/validation/turd-burglar-audio.json" >/dev/null
python3 "$repo_root/scripts/validate_mf005r1_sync.py" --fixture "$fixture" --timeline "$timeline" --execution "$execution" --narration "$narration" --music "$music" --mix "$artifact_dir/validation/turd-burglar-mix.json" --audio-validation "$artifact_dir/validation/turd-burglar-audio.json" --output "$artifact_dir/validation/turd-burglar-sync.json" >/dev/null
python3 "$repo_root/scripts/validate_mf005r2_mix.py" --fixture "$fixture" --timeline "$timeline" --execution "$execution" --narration "$narration" --music "$music" --mix "$artifact_dir/validation/turd-burglar-mix.json" --audio-validation "$artifact_dir/validation/turd-burglar-audio.json" --editorial "$artifact_dir/validation/turd-burglar-editorial.json" --media "$artifact_dir/turd-burglar.mp4" --output "$artifact_dir/validation/turd-burglar-final-mix.json" --audio-timeline "$artifact_dir/timelines/turd-burglar-audio.json" >/dev/null
python3 "$repo_root/scripts/mf-005r2-failure-tests.py" --repo-root "$repo_root" --artifacts "$artifact_dir" --output "$report_dir/failure-tests.json" >"$artifact_dir/logs/failure-tests.log"
validation_end=$(date +%s%N)
awk -v s="$validation_start" -v e="$validation_end" 'BEGIN{printf "elapsed_seconds=%.6f\n",(e-s)/1000000000}' >"$artifact_dir/logs/validation-metrics.txt"
printf '[PASS] streams, decode, timeline, narration, SFX, ducking, fades, loudness, peak\n[PASS] eight controlled failures\n'

printf '\nEVIDENCE\n'
cp "$artifact_dir/turd-burglar.mp4" "$artifact_dir/before-after/after-turd-burglar.mp4"
python3 - "$timeline" "$frames" "$artifact_dir/frames" <<'PY'
import json,pathlib,shutil,sys
t=json.loads(pathlib.Path(sys.argv[1]).read_text()); src=pathlib.Path(sys.argv[2]); dst=pathlib.Path(sys.argv[3])
for beat in t['beats']:
    frame=min(449,round(((beat['start']+beat['end'])/2)*30)); shutil.copy2(src/f"frame_{frame:06d}.png",dst/f"{beat['id']}.png")
PY
ffmpeg -hide_banner -loglevel error -y -ss 12.25 -i "$artifact_dir/before-after/before-turd-burglar.mp4" -frames:v 1 "$artifact_dir/before-after/before-reveal.png"
font=$repo_root/godot/fonts/Lato-Heavy.ttf
ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/before-after/before-reveal.png" -i "$artifact_dir/frames/reveal.png" -filter_complex "[0:v]scale=540:960,drawtext=fontfile='$font':text='BEFORE / MF-005R1 BED':x=16:y=24:fontsize=24:fontcolor=white[a];[1:v]drawtext=fontfile='$font':text='AFTER / SUPPLIED MIX + SPOKEN NAME':x=16:y=24:fontsize=24:fontcolor=white[b];[a][b]hstack" -frames:v 1 "$artifact_dir/before-after/reveal-comparison.png"
ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/audio/final/turd-burglar.wav" -filter_complex 'showwavespic=s=1000x240:colors=0xd4b863' -frames:v 1 "$artifact_dir/audio/waveforms/final-mix.png"
ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$artifact_dir/frames/*.png" -vf 'scale=180:320,tile=7x1:padding=4:margin=4:color=0x17110e' -frames:v 1 "$artifact_dir/contact-sheet.png"
python3 - "$artifact_dir/timelines/turd-burglar-audio.json" "$artifact_dir/audio/waveforms/activity.svg" <<'PY'
import html,json,pathlib,sys
d=json.loads(pathlib.Path(sys.argv[1]).read_text()); width=1000; scale=width/d['duration']; rows=[('MUSIC',[d['music']],'#77674d'),('VOICE',d['narration'],'#d4b863'),('DUCK',d['ducking'],'#8d4d42'),('SFX',d['sfx'],'#6f8954')]
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width+120}" height="220" viewBox="0 0 {width+120} 220"><rect width="100%" height="100%" fill="#17110e"/>']
for row,(label,items,color) in enumerate(rows):
 y=20+row*48; parts.append(f'<text x="8" y="{y+20}" fill="#f1eadb" font-family="sans-serif" font-size="15">{label}</text>')
 for item in items:
  start=float(item.get('start',0)); end=float(item.get('end',start+0.12)); parts.append(f'<rect x="{100+start*scale:.2f}" y="{y}" width="{max(2,(end-start)*scale):.2f}" height="28" rx="3" fill="{color}"/><title>{html.escape(str(item.get("beat",label)))} {start:.3f}–{end:.3f}s</title>')
parts.append('</svg>'); pathlib.Path(sys.argv[2]).write_text(''.join(parts)+'\n')
PY

python3 - "$artifact_dir" "$report_dir" <<'PY'
import json,pathlib,re,sys
a=pathlib.Path(sys.argv[1]); r=pathlib.Path(sys.argv[2])
def load(path): return json.loads(path.read_text())
def metrics(name):
 text=(a/'logs'/name).read_text(); return {key:(int(value) if key=='peak_kib' else float(value)) for key,value in re.findall(r'(elapsed_seconds|peak_kib)=([0-9.]+)',text)}
source=load(a/'validation/source-music-analysis.json'); music=load(a/'timelines/turd-burglar-music.json'); mix=load(a/'validation/turd-burglar-mix.json'); final=load(a/'validation/turd-burglar-final-mix.json'); output=load(a/'validation/turd-burglar-output.json'); narration=load(a/'timelines/turd-burglar-narration.json')
production_metrics={'source_music_duration_seconds':source['duration_seconds'],'source_format':f"{source['container']}/{source['codec']}",'selected_source_offset_seconds':music['selected_offset'],'loop_count':music['loop_count'],'normalized_music_generation_seconds':music['preparation_seconds'],'narration_preflight':metrics('narration-metrics.txt'),'music_preparation':metrics('music-metrics.txt'),'audio_mix':metrics('mix-metrics.txt'),'godot_render':metrics('godot-metrics.txt'),'ffmpeg_finalization':metrics('ffmpeg-metrics.txt'),'validation':metrics('validation-metrics.txt'),'final_mp4_bytes':output['artifact']['bytes']}
result={'slice':'MF-005R2','baseline':{key:'PASS' for key in ('mf001','mf002','mf002r1','mf003','mf004','mf005','mf005r1','mf_pilot_001')},'supplied_music':{'filename':'Clockwork_Heist.mp3','sha256':source['sha256'],'provenance':'user_supplied_generated','analysis':source},'editorial_contract':'PASS','spoken_product_name':'PASS','spoken_visual_alignment':'PASS','continuous_music':'PASS','ducking_from_narration':'PASS','fade_in':'PASS','fade_out':'PASS','existing_sfx':'PASS','authentic_game_media':'PASS','final_loudness':final['loudness'],'full_decode':'PASS','failure_tests':'PASS','visual_renderer_changes':0,'subject_specific_audio_engine_code':0,'metrics':production_metrics,'technical_result':'PASS','human_review':'PENDING'}
(r/'result.json').write_text(json.dumps(result,indent=2)+'\n')
summary=f'''# MF-005R2 Evidence Summary

## Result

Technical validation: **PASS**. Human audio/editorial review remains **PENDING**.

The supplied `Clockwork_Heist.mp3` is used verbatim as the source. Its first 15 seconds are selected deterministically, normalized to -24 LUFS, reduced by 3 dB, faded over 0.45/1.0 seconds, and ducked by 8 dB on the exact four narration windows. The completed mix targets -16 LUFS and -1.5 dBTP; measured output is {final['loudness']['integrated_lufs']:.1f} LUFS and {final['loudness']['true_peak_db']:.1f} dBTP.

`It is called Turd Burglar.` now plays inside the active `TURD BURGLAR` reveal beat. Existing beat-derived intro, text, emphasis, transition, and outro cues remain present. Authentic gameplay media is unchanged. Visual renderer changes: **0**.

## Evidence

- Final candidate: `artifacts/mf-005r2/turd-burglar.mp4`
- Before/after videos and reveal comparison: `artifacts/mf-005r2/before-after/`
- Audio timeline: `artifacts/mf-005r2/timelines/turd-burglar-audio.json`
- Waveform/activity evidence: `artifacts/mf-005r2/audio/waveforms/`
- Independent validation: `artifacts/mf-005r2/validation/turd-burglar-final-mix.json`
- Controlled failures: `reports/mf-005r2/failure-tests.json`

Machine checks establish structure, timing, decoding, levels, and thresholds; they do not establish subjective mix quality. Review the final MP4 with sound enabled, ideally on a phone.
'''
(r/'evidence-summary.md').write_text(summary)
print(json.dumps(result,indent=2))
PY
trap - ERR
printf '\nMF-005R2 TECHNICAL RESULT: PASS\nHUMAN AUDIO/EDITORIAL REVIEW: REQUIRED\n'
