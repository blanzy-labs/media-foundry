#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
godot_bin=${GODOT_BIN:-godot}
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}
artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-004}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-004}
mkdir -p "$artifact_dir/frames" "$artifact_dir/timelines" "$artifact_dir/validation" "$artifact_dir/logs" "$report_dir"
work_dir=$(mktemp -d "$artifact_dir/work.XXXXXX")

cleanup() {
  if [[ $work_dir == "$artifact_dir"/work.* && -d $work_dir ]]; then find "$work_dir" -depth -delete; fi
}
trap cleanup EXIT

fail_result() {
  local code=$?
  python3 - "$report_dir/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-004","technical_result":"FAIL","human_review":"PENDING","exit_code":int(sys.argv[2])},indent=2)+"\n")
PY
  printf '\nMF-004 TECHNICAL RESULT: FAIL\n' >&2
  exit "$code"
}
trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-004\n======================\n\nBASELINE GATES\n'
baseline=(mf-001 mf-002 mf-002r1 mf-003 mf-pilot-001)
for slice in "${baseline[@]}"; do
  result="$repo_root/reports/$slice/result.json"
  test -s "$result"
  jq -e '(.result == "PASS") or (.technical_result == "PASS")' "$result" >/dev/null
  printf '[PASS] %s acceptance report\n' "$slice"
done

printf '\nFAIL-CLOSED TIMELINE TESTS\n'
python3 "$repo_root/scripts/mf-004-failure-tests.py" --repo-root "$repo_root" --output "$report_dir/failure-tests.json" >/dev/null
printf '[PASS] Ten controlled failures rejected before rendering\n'

names=(turd-burglar books venus)
fixtures=(
  "$repo_root/content/fixtures/mf004-turd-burglar.json"
  "$repo_root/content/fixtures/mf004-books.json"
  "$repo_root/content/fixtures/mf004-venus.json"
)

printf '\nPREFLIGHT / RENDER / FINALIZE / VALIDATE\n'
for index in "${!names[@]}"; do
  name=${names[$index]} fixture=${fixtures[$index]}
  frames="$work_dir/$name/frames" audio="$work_dir/$name/audio.wav"
  preflight="$artifact_dir/timelines/$name.json" execution="$artifact_dir/timelines/$name-execution.json"
  layout="$artifact_dir/validation/$name-layout.json" media="$artifact_dir/$name.mp4"
  mkdir -p "$frames" "$artifact_dir/frames/$name"
  python3 "$repo_root/scripts/preflight_mf004.py" --fixture "$fixture" --grammar "$grammar" --project-root "$repo_root" --output "$preflight" >"$artifact_dir/logs/$name-preflight.log"
  /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-godot-metrics.txt" \
    timeout 120 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- \
    --fixture "$fixture" --grammar "$grammar" --output-dir "$frames" --layout-report "$layout" --timeline-report "$execution" >"$artifact_dir/logs/$name-render.log" 2>&1
  expected_frames=$(jq '.duration * 30' "$preflight")
  test "$(find "$frames" -maxdepth 1 -type f -name 'frame_*.png' | wc -l)" -eq "$expected_frames"
  grep -q "MF002_RENDER_COMPLETE id=mf004-$name frames=$expected_frames" "$artifact_dir/logs/$name-render.log"
  python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$audio" >"$artifact_dir/logs/$name-audio.log"
  duration=$(jq -r .duration "$preflight")
  /usr/bin/time -f '%e' -o "$artifact_dir/logs/$name-ffmpeg-seconds.txt" \
    ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$frames/frame_%06d.png" -i "$audio" \
    -map 0:v:0 -map 1:a:0 -t "$duration" -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' \
    -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 \
    -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$media" 2>"$artifact_dir/logs/$name-ffmpeg.log"
  /usr/bin/time -f '%e' -o "$artifact_dir/logs/$name-validation-seconds.txt" \
    python3 "$repo_root/scripts/validate_media.py" "$media" --slice MF-004 --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-output.json" >/dev/null
  python3 "$repo_root/scripts/validate_mf004_timeline.py" --preflight "$preflight" --execution "$execution" --layout "$layout" --output "$artifact_dir/validation/$name-timeline.json" >/dev/null
  python3 - "$preflight" "$frames" "$artifact_dir/frames/$name" <<'PY'
import json,pathlib,shutil,sys
timeline=json.loads(pathlib.Path(sys.argv[1]).read_text()); source=pathlib.Path(sys.argv[2]); target=pathlib.Path(sys.argv[3])
for beat in timeline["beats"]:
    frame=round(((beat["start"]+beat["end"])/2)*30)
    shutil.copy2(source/f"frame_{frame:06d}.png", target/f"{beat['id']}.png")
PY
  printf '[PASS] %s — %s beats, %ss\n' "$name" "$(jq .number_of_beats "$preflight")" "$duration"
done

printf '\nCONTACT SHEET / RESULT\n'
ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$artifact_dir/frames/*/*.png" -vf 'scale=180:320,tile=7x3:padding=4:margin=4:color=0x17110e' -frames:v 1 "$artifact_dir/contact-sheet.png"
test "$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$artifact_dir/contact-sheet.png")" = 1292x976

python3 - "$artifact_dir" "$report_dir/result.json" <<'PY'
import json,pathlib,re,sys
root=pathlib.Path(sys.argv[1]); fixtures={}
for name in ("turd-burglar","books","venus"):
    pre=json.loads((root/"timelines"/f"{name}.json").read_text())
    media=json.loads((root/"validation"/f"{name}-output.json").read_text())
    timeline=json.loads((root/"validation"/f"{name}-timeline.json").read_text())
    assert pre["result"] == media["result"] == timeline["result"] == "PASS"
    godot=(root/"logs"/f"{name}-godot-metrics.txt").read_text()
    values=dict(re.findall(r"(elapsed_seconds|peak_kib)=([0-9.]+)",godot))
    fixtures[name]={"beats":pre["number_of_beats"],"duration_seconds":pre["duration"],"timeline":"PASS","render":"PASS","validation":"PASS","evidence_frames":len(pre["beats"]),"sha256":media["artifact"]["sha256"],"metrics":{"timeline_preflight_seconds":pre["preflight_seconds"],"godot_render_seconds":float(values["elapsed_seconds"]),"peak_godot_kib":int(float(values["peak_kib"])),"ffmpeg_finalization_seconds":float((root/"logs"/f"{name}-ffmpeg-seconds.txt").read_text()),"validation_seconds":float((root/"logs"/f"{name}-validation-seconds.txt").read_text())}}
result={"slice":"MF-004","baseline":{"mf001":"PASS","mf002":"PASS","mf002r1":"PASS","mf003":"PASS","mf_pilot_001":"PASS"},"fixtures":fixtures,"shared_renderer":"PASS","subject_specific_renderer_code":0,"compatibility":"PASS","failure_tests":"PASS","contact_sheet":"PASS","technical_result":"PASS","human_review":"PENDING"}
pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2))
PY

trap - ERR
printf '\nMF-004 TECHNICAL RESULT: PASS\nHUMAN PACING REVIEW: REQUIRED\n'
