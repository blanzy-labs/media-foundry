#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}
fixture_dir=${MF_FIXTURE_DIR:-$repo_root/content/fixtures}
artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-002}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-002}
work_dir=${MF_WORK_DIR:-$artifact_dir/work}
godot_bin=${GODOT_BIN:-godot}
names=(fact turd-burglar general)
fixtures=("$fixture_dir/mf002-fact.json" "$fixture_dir/mf002-turd-burglar.json" "$fixture_dir/mf002-general.json")
mkdir -p "$artifact_dir/render-logs" "$artifact_dir/validation" "$artifact_dir/frames" "$report_dir"

fail_result() {
  local code=$?
  python3 - "$report_dir/result.json" "$code" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps({"slice":"MF-002","technical_result":"FAIL","human_review":"PENDING","exit_code":int(sys.argv[2])}, indent=2)+"\n")
PY
  printf '\nMF-002 TECHNICAL RESULT: FAIL\n' >&2
  exit "$code"
}
trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-002\n======================\n\nWORKSTATION\n'
"$repo_root/scripts/doctor.sh" | tee "$artifact_dir/doctor.log"
"$repo_root/scripts/doctor.sh" --json >"$artifact_dir/doctor.json"

printf '\nVISUAL GRAMMAR\n'
python3 "$repo_root/scripts/validate_mf002_contracts.py" --grammar "$grammar" \
  --fixtures "${fixtures[@]}" --project-root "$repo_root" --output "$artifact_dir/validation/structural.json"

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

  printf '\nFIXTURE %s\n' "${name^^}"
  python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$audio" | tee "$artifact_dir/render-logs/$name-audio.log"

  if [[ ${MF_INJECT_RENDER_FAILURE_AT:-} == "$name" ]]; then
    printf '[INJECTED] renderer failure for %s\n' "$name" >&2
    false
  fi
  if [[ ${MF_INJECT_MISSING_OUTPUT_AT:-} == "$name" ]]; then
    python3 "$repo_root/scripts/validate_media.py" "$media" --slice MF-002 --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-result.json"
  fi
  if [[ ${MF_INJECT_INVALID_MEDIA_AT:-} == "$name" ]]; then
    printf 'not an mp4\n' >"$media"
    python3 "$repo_root/scripts/validate_media.py" "$media" --slice MF-002 --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-result.json"
  fi

  timeout 90 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- \
    --fixture "$fixture" --grammar "$grammar" --output-dir "$frames_dir" >"$render_log" 2>&1
  frame_count=$(find "$frames_dir" -maxdepth 1 -type f -name 'frame_*.png' | wc -l)
  [[ $frame_count -eq 450 ]]
  grep -q "MF002_RENDER_COMPLETE id=$name frames=450" "$render_log"
  grep -q 'MF002_STRUCTURAL safe_area=PASS layers=workshop,sign,media,paper,tape,props' "$render_log"
  for stage in INTRO ENTER SETTLE EMPHASIS EXIT OUTRO; do grep -q "MF002_STAGE $stage" "$render_log"; done
  printf '[PASS] Shared Godot renderer (%s frames; all timeline stages)\n' "$frame_count"

  ffmpeg -hide_banner -y -loglevel info \
    -framerate 30 -start_number 0 -i "$frames_dir/frame_%06d.png" -i "$audio" \
    -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' \
    -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 \
    -c:a aac -b:a 160k -ar 48000 -movflags +faststart \
    -metadata creation_time='1970-01-01T00:00:00Z' "$media" >"$artifact_dir/render-logs/$name-ffmpeg.log" 2>&1

  python3 "$repo_root/scripts/validate_media.py" "$media" --slice MF-002 \
    --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-result.json" >/dev/null
  printf '[PASS] FFmpeg finalization and independent media validation\n'

  ffmpeg -hide_banner -loglevel error -y -ss 0.8 -i "$media" -frames:v 1 "$artifact_dir/frames/$name/intro.png"
  ffmpeg -hide_banner -loglevel error -y -ss 7.5 -i "$media" -frames:v 1 "$artifact_dir/frames/$name/main.png"
  ffmpeg -hide_banner -loglevel error -y -ss 14 -i "$media" -frames:v 1 "$artifact_dir/frames/$name/outro.png"
  for phase in intro main outro; do [[ -s $artifact_dir/frames/$name/$phase.png ]]; done
  printf '[PASS] Visual evidence frames\n'
done

printf '\nCONTACT SHEET\n'
font="$repo_root/godot/fonts/Lato-Heavy.ttf"
ffmpeg -hide_banner -loglevel error -y \
  -i "$artifact_dir/frames/fact/intro.png" -i "$artifact_dir/frames/fact/main.png" -i "$artifact_dir/frames/fact/outro.png" \
  -i "$artifact_dir/frames/turd-burglar/intro.png" -i "$artifact_dir/frames/turd-burglar/main.png" -i "$artifact_dir/frames/turd-burglar/outro.png" \
  -i "$artifact_dir/frames/general/intro.png" -i "$artifact_dir/frames/general/main.png" -i "$artifact_dir/frames/general/outro.png" \
  -filter_complex \
  "[0:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='FACT / INTRO':x=12:y=450:fontsize=18:fontcolor=white[v0];[1:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='FACT / MAIN':x=12:y=450:fontsize=18:fontcolor=white[v1];[2:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='FACT / OUTRO':x=12:y=450:fontsize=18:fontcolor=white[v2];[3:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='TURD BURGLAR / INTRO':x=12:y=450:fontsize=16:fontcolor=white[v3];[4:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='TURD BURGLAR / MAIN':x=12:y=450:fontsize=16:fontcolor=white[v4];[5:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='TURD BURGLAR / OUTRO':x=12:y=450:fontsize=16:fontcolor=white[v5];[6:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='GENERAL / INTRO':x=12:y=450:fontsize=18:fontcolor=white[v6];[7:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='GENERAL / MAIN':x=12:y=450:fontsize=18:fontcolor=white[v7];[8:v]scale=270:480,drawbox=y=440:w=270:h=40:color=black@0.75:t=fill,drawtext=fontfile='$font':text='GENERAL / OUTRO':x=12:y=450:fontsize=18:fontcolor=white[v8];[v0][v1][v2][v3][v4][v5][v6][v7][v8]xstack=inputs=9:layout=0_0|270_0|540_0|0_480|270_480|540_480|0_960|270_960|540_960[grid];[grid]pad=810:1510:0:70:color=0x17110e,drawtext=fontfile='$font':text='MF-002 VISUAL GRAMMAR REVIEW':x=(w-text_w)/2:y=22:fontsize=28:fontcolor=0xf4df9d" \
  -frames:v 1 "$artifact_dir/contact-sheet.png"
contact_size=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$artifact_dir/contact-sheet.png")
[[ $contact_size == 810x1510 ]]
printf '[PASS] Nine-frame review sheet (%s)\n' "$contact_size"

printf '\nREPRODUCIBILITY\n'
repro_frames="$work_dir/repro-fact/frames"
repro_media="$work_dir/repro-fact/fact.mp4"
mkdir -p "$repro_frames"
timeout 90 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- \
  --fixture "${fixtures[0]}" --grammar "$grammar" --output-dir "$repro_frames" >"$artifact_dir/render-logs/fact-repro.log" 2>&1
[[ $(find "$repro_frames" -maxdepth 1 -type f -name 'frame_*.png' | wc -l) -eq 450 ]]
ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$repro_frames/frame_%06d.png" -i "$work_dir/fact/audio.wav" \
  -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' \
  -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$repro_media"
canonical_hash=$(sha256sum "$artifact_dir/fact.mp4" | awk '{print $1}')
repro_hash=$(sha256sum "$repro_media" | awk '{print $1}')
[[ $canonical_hash == "$repro_hash" ]]
printf '[PASS] Same fixture produced identical SHA-256 %s\n' "$canonical_hash"

python3 - "$artifact_dir" "$report_dir/result.json" "$canonical_hash" <<'PY'
import json, pathlib, sys
artifact=pathlib.Path(sys.argv[1]); videos={}
for name in ("fact", "turd-burglar", "general"):
    result=json.loads((artifact / "validation" / f"{name}-result.json").read_text())
    assert result["result"] == "PASS"
    videos[name]={"result":"PASS", "sha256":result["artifact"]["sha256"], "bytes":result["artifact"]["bytes"]}
out={"slice":"MF-002", "grammar":"scrappy-diorama-v1", "structural_validation":"PASS", "videos":videos, "visual_evidence":{"frames":9,"contact_sheet":"PASS"}, "reproducibility":{"result":"PASS","fixture":"fact","sha256":sys.argv[3]}, "technical_result":"PASS", "human_review":"PENDING"}
path=pathlib.Path(sys.argv[2]); path.write_text(json.dumps(out, indent=2)+"\n")
print(json.dumps(out, indent=2))
PY

trap - ERR
printf '\nMF-002 TECHNICAL RESULT: PASS\nHUMAN VISUAL REVIEW: REQUIRED\n'
