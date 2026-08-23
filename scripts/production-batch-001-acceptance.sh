#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
grammar="$repo_root/config/visual-grammar.json"
artifact_dir=${BATCH_ARTIFACT_DIR:-$repo_root/artifacts/production-batch-001}
report_dir=${BATCH_REPORT_DIR:-$repo_root/reports/production-batch-001}
work_dir=${BATCH_WORK_DIR:-$artifact_dir/work}
godot_bin=${GODOT_BIN:-godot}
names=(books mythadis venus)
fixtures=("$repo_root/content/fixtures/production-batch-001-books.json" "$repo_root/content/fixtures/production-batch-001-mythadis.json" "$repo_root/content/fixtures/production-batch-001-venus.json")
declare -A render_ms=() total_ms=()
mkdir -p "$artifact_dir/render-logs" "$artifact_dir/validation" "$artifact_dir/frames" "$report_dir"

fail_result() {
  local code=$?
  python3 - "$report_dir/result.json" "$code" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps({"batch":"production-batch-001","technical_result":"FAIL","human_review":"PENDING","exit_code":int(sys.argv[2])}, indent=2)+"\n")
PY
  printf '\nPRODUCTION BATCH 001 RESULT: FAIL\n' >&2
  exit "$code"
}
trap fail_result ERR

printf 'MEDIA FOUNDRY — PRODUCTION BATCH 001\n====================================\n\nBASELINE\n'
"$repo_root/scripts/doctor.sh" | tee "$artifact_dir/doctor.log"
"$repo_root/scripts/doctor.sh" --json >"$artifact_dir/doctor.json"
python3 - "$repo_root/reports/mf-002/result.json" <<'PY'
import json, sys
r=json.load(open(sys.argv[1]))
assert r["technical_result"] == "PASS" and r["human_review"] == "PASS"
print("[PASS] MF-002 technical and human visual acceptance")
PY

printf '\nCONTENT CONTRACTS\n'
python3 "$repo_root/scripts/validate_production_batch.py" --grammar "$grammar" --fixtures "${fixtures[@]}" --output "$artifact_dir/validation/content-contract.json"

[[ -n $work_dir && $work_dir != / && ${#work_dir} -gt 10 ]]
rm -rf "$work_dir"
mkdir -p "$work_dir"

for index in "${!names[@]}"; do
  name=${names[$index]}
  fixture=${fixtures[$index]}
  frames_dir="$work_dir/$name/frames"
  audio="$work_dir/$name/audio.wav"
  media="$artifact_dir/$name.mp4"
  render_log="$artifact_dir/render-logs/$name.log"
  mkdir -p "$frames_dir" "$artifact_dir/frames/$name"
  rm -f "$media"
  total_start=$(date +%s%N)

  printf '\nVIDEO %s\n' "${name^^}"
  python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$audio" | tee "$artifact_dir/render-logs/$name-audio.log"
  render_start=$(date +%s%N)
  timeout 90 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- \
    --fixture "$fixture" --grammar "$grammar" --output-dir "$frames_dir" >"$render_log" 2>&1
  render_end=$(date +%s%N)
  render_ms[$name]=$(((render_end - render_start) / 1000000))
  frame_count=$(find "$frames_dir" -maxdepth 1 -type f -name 'frame_*.png' | wc -l)
  [[ $frame_count -eq 450 ]]
  grep -q "MF002_RENDER_COMPLETE id=$name frames=450" "$render_log"
  grep -q 'MF002_STRUCTURAL safe_area=PASS layers=workshop,sign,media,paper,tape,props' "$render_log"
  for stage in INTRO ENTER SETTLE EMPHASIS EXIT OUTRO; do grep -q "MF002_STAGE $stage" "$render_log"; done
  printf '[PASS] Shared renderer (%s frames, %s ms)\n' "$frame_count" "${render_ms[$name]}"

  ffmpeg -hide_banner -y -loglevel info \
    -framerate 30 -start_number 0 -i "$frames_dir/frame_%06d.png" -i "$audio" \
    -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' \
    -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 \
    -c:a aac -b:a 160k -ar 48000 -movflags +faststart \
    -metadata creation_time='1970-01-01T00:00:00Z' "$media" >"$artifact_dir/render-logs/$name-ffmpeg.log" 2>&1
  python3 "$repo_root/scripts/validate_media.py" "$media" --slice PRODUCTION-BATCH-001 \
    --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-result.json" >/dev/null

  ffmpeg -hide_banner -loglevel error -y -ss 0.8 -i "$media" -frames:v 1 "$artifact_dir/frames/$name/intro.png"
  ffmpeg -hide_banner -loglevel error -y -ss 7.5 -i "$media" -frames:v 1 "$artifact_dir/frames/$name/main.png"
  ffmpeg -hide_banner -loglevel error -y -ss 14 -i "$media" -frames:v 1 "$artifact_dir/frames/$name/outro.png"
  for phase in intro main outro; do [[ -s $artifact_dir/frames/$name/$phase.png ]]; done
  total_end=$(date +%s%N)
  total_ms[$name]=$(((total_end - total_start) / 1000000))
  printf '[PASS] Media validation and visual evidence (%s ms total)\n' "${total_ms[$name]}"
done

printf '\nCONTACT SHEET\n'
font="$repo_root/godot/fonts/Lato-Heavy.ttf"
ffmpeg -hide_banner -loglevel error -y \
  -i "$artifact_dir/frames/books/intro.png" -i "$artifact_dir/frames/books/main.png" -i "$artifact_dir/frames/books/outro.png" \
  -i "$artifact_dir/frames/mythadis/intro.png" -i "$artifact_dir/frames/mythadis/main.png" -i "$artifact_dir/frames/mythadis/outro.png" \
  -i "$artifact_dir/frames/venus/intro.png" -i "$artifact_dir/frames/venus/main.png" -i "$artifact_dir/frames/venus/outro.png" \
  -filter_complex \
  "[0:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='BOOKS / INTRO':x=12:y=450:fontsize=18:fontcolor=white[v0];[1:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='BOOKS / MAIN':x=12:y=450:fontsize=18:fontcolor=white[v1];[2:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='BOOKS / OUTRO':x=12:y=450:fontsize=18:fontcolor=white[v2];[3:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='MYTHADIS / INTRO':x=12:y=450:fontsize=18:fontcolor=white[v3];[4:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='MYTHADIS / MAIN':x=12:y=450:fontsize=18:fontcolor=white[v4];[5:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='MYTHADIS / OUTRO':x=12:y=450:fontsize=18:fontcolor=white[v5];[6:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='VENUS / INTRO':x=12:y=450:fontsize=18:fontcolor=white[v6];[7:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='VENUS / MAIN':x=12:y=450:fontsize=18:fontcolor=white[v7];[8:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='VENUS / OUTRO':x=12:y=450:fontsize=18:fontcolor=white[v8];[v0][v1][v2][v3][v4][v5][v6][v7][v8]xstack=inputs=9:layout=0_0|270_0|540_0|0_480|270_480|540_480|0_960|270_960|540_960[grid];[grid]pad=810:1510:0:70:color=0x17110e,drawtext=fontfile='$font':text='PRODUCTION BATCH 001 / VISUAL REVIEW':x=(w-text_w)/2:y=22:fontsize=27:fontcolor=0xf4df9d" \
  -frames:v 1 "$artifact_dir/contact-sheet.png"
contact_size=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$artifact_dir/contact-sheet.png")
[[ $contact_size == 810x1510 ]]
printf '[PASS] Nine-frame contact sheet (%s)\n' "$contact_size"

python3 - "$artifact_dir" "$report_dir/result.json" \
  "${render_ms[books]}" "${total_ms[books]}" "${render_ms[mythadis]}" "${total_ms[mythadis]}" "${render_ms[venus]}" "${total_ms[venus]}" <<'PY'
import json, pathlib, sys
artifact=pathlib.Path(sys.argv[1]); output=pathlib.Path(sys.argv[2]); timings=list(map(int,sys.argv[3:]))
videos={}
for index,name in enumerate(("books","mythadis","venus")):
    validation=json.loads((artifact/"validation"/f"{name}-result.json").read_text())
    assert validation["result"] == "PASS"
    videos[name]={"result":"PASS","bytes":validation["artifact"]["bytes"],"sha256":validation["artifact"]["sha256"],"godot_render_ms":timings[index*2],"total_production_ms":timings[index*2+1]}
result={"batch":"production-batch-001","grammar":"scrappy-diorama-v1","renderer":"godot/mf002.gd","content_contract":"PASS","videos":videos,"visual_evidence":{"frames":9,"contact_sheet":"PASS"},"renderer_changes":"reusable data-driven prop_board primitives and fixture-controlled outro tagline","external_assets":[],"technical_result":"PASS","human_review":"PENDING"}
output.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
PY

trap - ERR
printf '\nPRODUCTION BATCH 001 RESULT: PASS\nHUMAN VISUAL REVIEW: REQUIRED\n'
