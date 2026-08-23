#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
godot_bin=${GODOT_BIN:-godot}
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}
artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-pilot-001}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-pilot-001}
mkdir -p "$artifact_dir" "$report_dir"
work_dir=$(mktemp -d "$artifact_dir/work.XXXXXX")
mkdir -p "$artifact_dir/frames" "$artifact_dir/validation" "$artifact_dir/logs"

cleanup() {
  if [[ $work_dir == "$artifact_dir"/work.* && -d $work_dir ]]; then find "$work_dir" -depth -delete; fi
}
trap cleanup EXIT

fail_result() {
  local code=$?
  python3 - "$report_dir/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-PILOT-001","technical_result":"FAIL","human_result":"PENDING","exit_code":int(sys.argv[2])},indent=2)+"\n")
PY
  printf '\nMF-PILOT-001 TECHNICAL RESULT: FAIL\n' >&2
  exit "$code"
}
trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-PILOT-001\n================================\n\nBASELINE\n'
for result in "$repo_root/reports/mf-001/result.json" "$repo_root/reports/mf-002/result.json" "$repo_root/reports/mf-002r1/result.json" "$repo_root/reports/mf-003/result.json"; do
  test -s "$result"
  jq -e '(.result == "PASS") or (.technical_result == "PASS")' "$result" >/dev/null
done
printf '[PASS] MF-001, MF-002, MF-002R1, MF-003\n'

subjects=(books turd-burglar mythadis)
ids=(pilot-books pilot-turd-burglar pilot-mythadis)
fixtures=(
  "$repo_root/content/fixtures/mf-pilot-001-books.json"
  "$repo_root/content/fixtures/mf-pilot-001-turd-burglar.json"
  "$repo_root/content/fixtures/mf-pilot-001-mythadis.json"
)
layout_reports=()

printf '\nREAL-ASSET PRODUCTION\n'
for index in "${!subjects[@]}"; do
  subject=${subjects[$index]} id=${ids[$index]} fixture=${fixtures[$index]}
  frames="$work_dir/$subject/frames" audio="$work_dir/$subject/audio.wav"
  renderer_report="$artifact_dir/validation/$subject-renderer.json"
  input_report="$artifact_dir/validation/$subject-input.json"
  output_report="$artifact_dir/validation/$subject-output.json"
  mkdir -p "$frames" "$artifact_dir/frames/$subject"

  validation_start=$(date +%s%N)
  python3 "$repo_root/scripts/prepare_mf003_media.py" --fixture "$fixture" --grammar "$grammar" --project-root "$repo_root" --output "$input_report" >"$artifact_dir/logs/$subject-input.log"
  validation_end=$(date +%s%N)
  input_validation_ns=$((validation_end-validation_start))

  /usr/bin/time -f 'render_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$subject-render-metrics.txt" \
    timeout 90 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- \
      --fixture "$fixture" --grammar "$grammar" --output-dir "$frames" --layout-report "$renderer_report" >"$artifact_dir/logs/$subject-render.log" 2>&1
  test "$(find "$frames" -maxdepth 1 -type f -name 'frame_*.png' | wc -l)" -eq 450
  grep -q "MF002_RENDER_COMPLETE id=$id frames=450" "$artifact_dir/logs/$subject-render.log"
  grep -q 'MF003_MEDIA_READY' "$artifact_dir/logs/$subject-render.log"

  python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$audio" >"$artifact_dir/logs/$subject-audio.log"
  /usr/bin/time -f 'finalization_seconds=%e' -o "$artifact_dir/logs/$subject-finalization-metrics.txt" \
    ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$frames/frame_%06d.png" -i "$audio" \
      -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' \
      -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 \
      -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$artifact_dir/$subject.mp4"

  validation_start=$(date +%s%N)
  python3 "$repo_root/scripts/validate_media.py" "$artifact_dir/$subject.mp4" --slice MF-PILOT-001 \
    --ffprobe-json "$artifact_dir/validation/$subject-ffprobe.json" --result-json "$output_report" >/dev/null
  python3 "$repo_root/scripts/validate_mf003_render.py" --fixture "$fixture" --grammar "$grammar" \
    --input-report "$input_report" --renderer-report "$renderer_report" --output "$artifact_dir/validation/$subject-slot.json" >/dev/null
  validation_end=$(date +%s%N)
  output_validation_ns=$((validation_end-validation_start))
  python3 - "$artifact_dir/logs/$subject-validation-metrics.json" "$input_validation_ns" "$output_validation_ns" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"input_validation_seconds":int(sys.argv[2])/1e9,"output_validation_seconds":int(sys.argv[3])/1e9,"total_validation_seconds":(int(sys.argv[2])+int(sys.argv[3]))/1e9},indent=2)+"\n")
PY

  cp "$frames/frame_000024.png" "$artifact_dir/frames/$subject/intro.png"
  cp "$frames/frame_000135.png" "$artifact_dir/frames/$subject/media.png"
  cp "$frames/frame_000225.png" "$artifact_dir/frames/$subject/content.png"
  cp "$frames/frame_000420.png" "$artifact_dir/frames/$subject/outro.png"
  layout_reports+=("$renderer_report")
  printf '[PASS] %-13s real asset → shared renderer → validated MP4\n' "$subject"
done

python3 "$repo_root/scripts/validate_mf002r1_layout.py" --grammar "$grammar" --reports "${layout_reports[@]}" --output "$artifact_dir/validation/text-layout.json" >/dev/null
printf '[PASS] Aggregate MF-002R1 text geometry\n'

printf '\nCONTACT SHEET\n'
font="$repo_root/godot/fonts/Lato-Heavy.ttf"
ffmpeg -hide_banner -loglevel error -y \
  -i "$artifact_dir/frames/books/content.png" -i "$artifact_dir/frames/turd-burglar/content.png" -i "$artifact_dir/frames/mythadis/content.png" \
  -filter_complex \
  "[0:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.78:t=fill,drawtext=fontfile='$font':text='BOOKS / DARK SIGNAL':x=10:y=450:fontsize=17:fontcolor=white[v0];[1:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.78:t=fill,drawtext=fontfile='$font':text='TURD BURGLAR':x=10:y=450:fontsize=18:fontcolor=white[v1];[2:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.78:t=fill,drawtext=fontfile='$font':text='MYTHADIS':x=10:y=450:fontsize=18:fontcolor=white[v2];[v0][v1][v2]hstack=inputs=3[grid];[grid]pad=810:550:0:70:color=0x17110e,drawtext=fontfile='$font':text='MF-PILOT-001 / REAL ASSETS':x=(w-text_w)/2:y=22:fontsize=28:fontcolor=0xf4df9d" \
  -frames:v 1 "$artifact_dir/contact-sheet.png"
test "$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$artifact_dir/contact-sheet.png")" = 810x550
printf '[PASS] Three-subject contact sheet\n'

python3 - "$artifact_dir" "$report_dir/result.json" <<'PY'
import json,pathlib,sys
artifact=pathlib.Path(sys.argv[1]); results={}; effort={}
assets={
 "books":{"source":"media/images/books-dark-signal.png","sha256":"4546678c906bb0a6065c25a5d61da76a5bd89bfcd02e3fa13b2a0aebb0ce7af5","dimensions":"1920x2571"},
 "turd-burglar":{"source":"media/screenshots/turd-burglar-gameplay.png","sha256":"c88faab6a331679b62c344b08a7e84f067965d38e5601e4e1a30c1c744967abe","dimensions":"1672x941"},
 "mythadis":{"source":"media/screenshots/mythadis-social-card.png","sha256":"5a05967c156a0e11945554dc10d33e02310882d4219e7dfbe3132e75595c7fb1","dimensions":"1200x630"}}
for subject in assets:
    output=json.loads((artifact/"validation"/f"{subject}-output.json").read_text()); slot=json.loads((artifact/"validation"/f"{subject}-slot.json").read_text())
    assert output["result"] == slot["result"] == "PASS"
    render=dict(line.split("=",1) for line in (artifact/"logs"/f"{subject}-render-metrics.txt").read_text().splitlines())
    final=dict(line.split("=",1) for line in (artifact/"logs"/f"{subject}-finalization-metrics.txt").read_text().splitlines())
    validation=json.loads((artifact/"logs"/f"{subject}-validation-metrics.json").read_text())
    results[subject]={"render":"PASS","media":"PASS","layout":"PASS","output":"PASS","sha256":output["artifact"]["sha256"]}
    effort[subject]={"content_fixtures_created":1,"source_assets_added":1,"renderer_files_changed":0,"configuration_files_changed":0,"render_seconds":float(render["render_seconds"]),"finalization_seconds":float(final["finalization_seconds"]),"validation_seconds":validation["total_validation_seconds"],"peak_godot_kib":int(render["peak_kib"]),"failed_render_attempts":0,"failures":[]}
result={"slice":"MF-PILOT-001","baseline":{"mf001":"PASS","mf002":"PASS","mf002r1":"PASS","mf003":"PASS"},"assets":assets,"videos":results,"production_effort":effort,"renderer_changes":[],"text_layout":"PASS","contact_sheet":"PASS","technical_result":"PASS","human_result":"PENDING"}
pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2))
PY

trap - ERR
printf '\nMF-PILOT-001 TECHNICAL RESULT: PASS\nHUMAN REVIEW: REQUIRED\n'
