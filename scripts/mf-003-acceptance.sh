#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
godot_bin=${GODOT_BIN:-godot}
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}
artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-003}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-003}
mkdir -p "$artifact_dir" "$report_dir"
work_dir=$(mktemp -d "$artifact_dir/work.XXXXXX")
mkdir -p "$artifact_dir/frames" "$artifact_dir/normalized" "$artifact_dir/validation" "$artifact_dir/render-logs" "$artifact_dir/regression"

cleanup() {
  if [[ $work_dir == "$artifact_dir"/work.* && -d $work_dir ]]; then find "$work_dir" -depth -delete; fi
}
trap cleanup EXIT

fail_result() {
  local code=$?
  python3 - "$report_dir/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-003","technical_result":"FAIL","human_review":"PENDING","exit_code":int(sys.argv[2])},indent=2)+"\n")
PY
  printf '\nMF-003 TECHNICAL RESULT: FAIL\n' >&2
  exit "$code"
}
trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-003\n======================\n\nWORKSTATION\n'
"$repo_root/scripts/doctor.sh" | tee "$artifact_dir/doctor.log"
"$repo_root/scripts/doctor.sh" --json >"$artifact_dir/doctor.json"

printf '\nBASELINE GATES\n'
for result in "$repo_root/reports/mf-001/result.json" "$repo_root/reports/mf-002/result.json" "$repo_root/reports/mf-002r1/result.json"; do
  test -s "$result"
  jq -e '(.result == "PASS") or (.technical_result == "PASS")' "$result" >/dev/null
done
printf '[PASS] MF-001, MF-002, and MF-002R1 acceptance reports\n'

printf '\nFAIL-CLOSED MEDIA TESTS\n'
MF_GRAMMAR="$grammar" MF_REPORT_DIR="$report_dir" "$repo_root/scripts/mf-003-failure-tests.sh"

names=(image-fixture screenshot-fixture video-fixture)
fixtures=(
  "$repo_root/content/fixtures/mf003-image.json"
  "$repo_root/content/fixtures/mf003-screenshot.json"
  "$repo_root/content/fixtures/mf003-video.json"
)
layout_reports=()

printf '\nMEDIA INPUT / NORMALIZATION\n'
for index in "${!names[@]}"; do
  name=${names[$index]} fixture=${fixtures[$index]}
  normalized_args=()
  if [[ $name == video-fixture ]]; then normalized_args=(--normalized-dir "$work_dir/video-normalized"); fi
  python3 "$repo_root/scripts/prepare_mf003_media.py" --fixture "$fixture" --grammar "$grammar" --project-root "$repo_root" \
    "${normalized_args[@]}" --output "$artifact_dir/validation/$name-input.json" >"$artifact_dir/render-logs/$name-input.log"
  printf '[PASS] %s input contract and asset\n' "$name"
done
cp "$work_dir/video-normalized/frame_000000.png" "$artifact_dir/normalized/video-start.png"
cp "$work_dir/video-normalized/frame_000075.png" "$artifact_dir/normalized/video-middle.png"
cp "$work_dir/video-normalized/frame_000149.png" "$artifact_dir/normalized/video-end.png"
cp "$artifact_dir/validation/video-fixture-input.json" "$artifact_dir/normalized/manifest.json"

render_media_fixture() {
  local index=$1 name=${names[$1]} fixture=${fixtures[$1]}
  local frames="$work_dir/$name/frames" audio="$work_dir/$name/audio.wav"
  local layout="$artifact_dir/validation/$name-renderer.json" media="$artifact_dir/$name.mp4"
  local frame_args=()
  if [[ $name == video-fixture ]]; then frame_args=(--media-frames-dir "$work_dir/video-normalized"); fi
  mkdir -p "$frames"
  timeout 90 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- \
    --fixture "$fixture" --grammar "$grammar" --output-dir "$frames" --layout-report "$layout" "${frame_args[@]}" >"$artifact_dir/render-logs/$name-render.log" 2>&1
  test "$(find "$frames" -maxdepth 1 -type f -name 'frame_*.png' | wc -l)" -eq 450
  grep -q 'MF003_MEDIA_READY' "$artifact_dir/render-logs/$name-render.log"
  grep -q "MF002_RENDER_COMPLETE id=$name frames=450" "$artifact_dir/render-logs/$name-render.log"
  python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$audio" >"$artifact_dir/render-logs/$name-audio.log"
  ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$frames/frame_%06d.png" -i "$audio" \
    -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' \
    -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 \
    -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$media"
  python3 "$repo_root/scripts/validate_media.py" "$media" --slice MF-003 \
    --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-output.json" >/dev/null
  python3 "$repo_root/scripts/validate_mf003_render.py" --fixture "$fixture" --grammar "$grammar" \
    --input-report "$artifact_dir/validation/$name-input.json" --renderer-report "$layout" --output "$artifact_dir/validation/$name-slot.json" >/dev/null
  cp "$frames/frame_000225.png" "$artifact_dir/frames/$name-main.png"
  if [[ $name == video-fixture ]]; then
    cp "$frames/frame_000135.png" "$artifact_dir/frames/video-fixture-early.png"
    cp "$frames/frame_000240.png" "$artifact_dir/frames/video-fixture-late.png"
  fi
  layout_reports+=("$layout")
  printf '[PASS] %s render, slot geometry, MP4, and full decode\n' "$name"
}

printf '\nMEDIA FIXTURE RENDERS\n'
for index in "${!names[@]}"; do render_media_fixture "$index"; done

printf '\nNO-MEDIA BATCH COMPATIBILITY\n'
legacy_names=(fact turd-burglar general books mythadis venus)
legacy_fixtures=(
  "$repo_root/content/fixtures/mf002-fact.json" "$repo_root/content/fixtures/mf002-turd-burglar.json" "$repo_root/content/fixtures/mf002-general.json"
  "$repo_root/content/fixtures/production-batch-001-books.json" "$repo_root/content/fixtures/production-batch-001-mythadis.json" "$repo_root/content/fixtures/production-batch-001-venus.json"
)
for index in "${!legacy_names[@]}"; do
  name=${legacy_names[$index]} fixture=${legacy_fixtures[$index]} output="$work_dir/legacy-$name"
  mkdir -p "$output"
  "$godot_bin" --headless --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- --fixture "$fixture" --grammar "$grammar" --output-dir "$output" --validate-layout-only >"$artifact_dir/render-logs/legacy-$name.log" 2>&1
  test "$(jq -r .media.status "$output/layout-validation.json")" = NOT_PRESENT
  layout_reports+=("$output/layout-validation.json")
done
printf '[PASS] Six existing fixtures accept media:null/equivalent\n'

# Full no-media regression proves the additive branch still emits validated media.
legacy_frames="$work_dir/legacy-fact-full/frames"; legacy_audio="$work_dir/legacy-fact-full/audio.wav"
mkdir -p "$legacy_frames"
timeout 90 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- --fixture "${legacy_fixtures[0]}" --grammar "$grammar" --output-dir "$legacy_frames" >"$artifact_dir/render-logs/legacy-fact-full.log" 2>&1
python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "${legacy_fixtures[0]}" --output "$legacy_audio" >/dev/null
ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$legacy_frames/frame_%06d.png" -i "$legacy_audio" -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' -c:v libx264 -preset medium -crf 20 -threads 1 -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$artifact_dir/regression/fact-no-media.mp4"
python3 "$repo_root/scripts/validate_media.py" "$artifact_dir/regression/fact-no-media.mp4" --slice MF-003 --ffprobe-json "$artifact_dir/validation/fact-no-media-ffprobe.json" --result-json "$artifact_dir/validation/fact-no-media-output.json" >/dev/null
printf '[PASS] Full no-media regression render and decode\n'

python3 "$repo_root/scripts/validate_mf002r1_layout.py" --grammar "$grammar" --reports "${layout_reports[@]}" --output "$artifact_dir/validation/text-layout.json" >/dev/null

printf '\nCONTACT SHEET\n'
font="$repo_root/godot/fonts/Lato-Heavy.ttf"
ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/frames/image-fixture-main.png" -i "$artifact_dir/frames/screenshot-fixture-main.png" -i "$artifact_dir/frames/video-fixture-main.png" -filter_complex \
  "[0:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='STILL / CONTAIN':x=10:y=450:fontsize=18:fontcolor=white[v0];[1:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='SCREENSHOT / COVER':x=10:y=450:fontsize=17:fontcolor=white[v1];[2:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='VIDEO / OFFSET CLIP':x=10:y=450:fontsize=17:fontcolor=white[v2];[v0][v1][v2]hstack=inputs=3[grid];[grid]pad=810:550:0:70:color=0x17110e,drawtext=fontfile='$font':text='MF-003 MEDIA SLOT REVIEW':x=(w-text_w)/2:y=22:fontsize=28:fontcolor=0xf4df9d" -frames:v 1 "$artifact_dir/contact-sheet.png"
test "$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$artifact_dir/contact-sheet.png")" = 810x550
printf '[PASS] Three-fixture contact sheet\n'

python3 - "$artifact_dir" "$report_dir/result.json" <<'PY'
import json,pathlib,sys
artifact=pathlib.Path(sys.argv[1]); fixtures={}
for name in ("image-fixture","screenshot-fixture","video-fixture"):
    output=json.loads((artifact/"validation"/f"{name}-output.json").read_text()); slot=json.loads((artifact/"validation"/f"{name}-slot.json").read_text())
    assert output["result"] == slot["result"] == "PASS"
    fixtures[name]={"media_input":"PASS","media_slot":"PASS","output":"PASS","sha256":output["artifact"]["sha256"]}
legacy=json.loads((artifact/"validation"/"fact-no-media-output.json").read_text()); assert legacy["result"] == "PASS"
result={"slice":"MF-003","baseline":{"mf001":"PASS","mf002":"PASS","mf002r1":"PASS"},"fixtures":fixtures,"fit_modes":{"contain":"PASS","cover":"PASS"},"video_timing":"PASS","failure_tests":"PASS","no_media_compatibility":"PASS","contact_sheet":"PASS","technical_result":"PASS","human_review":"PENDING"}
pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2))
PY

trap - ERR
printf '\nMF-003 TECHNICAL RESULT: PASS\nHUMAN VISUAL REVIEW: REQUIRED\n'
