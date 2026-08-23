#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
godot_bin=${GODOT_BIN:-godot}
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}
artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-002r1}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-002r1}
mkdir -p "$artifact_dir" "$report_dir"
work_dir=$(mktemp -d "$artifact_dir/work.XXXXXX")
mkdir -p "$artifact_dir/layout" "$artifact_dir/regression" "$artifact_dir/stress-tests" "$artifact_dir/frames" "$artifact_dir/validation" "$artifact_dir/render-logs" "$report_dir"

cleanup() {
  if [[ $work_dir == "$artifact_dir"/work.* && -d $work_dir ]]; then
    find "$work_dir" -depth -delete
  fi
}
trap cleanup EXIT

fail_result() {
  local code=$?
  python3 - "$report_dir/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-002R1","technical_result":"FAIL","human_review":"PENDING","exit_code":int(sys.argv[2])},indent=2)+"\n")
PY
  printf '\nMF-002R1 TECHNICAL RESULT: FAIL\n' >&2
  exit "$code"
}
trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-002R1\n========================\n\nWORKSTATION\n'
"$repo_root/scripts/doctor.sh" | tee "$artifact_dir/doctor.log"
"$repo_root/scripts/doctor.sh" --json >"$artifact_dir/doctor.json"

printf '\nBEFORE EVIDENCE\n'
test -s "$artifact_dir/before/venus-problem.png"
test -s "$artifact_dir/before/venus-render.log"
printf '[PASS] Preserved pre-change Venus reproduction\n'

printf '\nFAIL-CLOSED TESTS\n'
MF_GRAMMAR="$grammar" MF_REPORT_DIR="$report_dir" "$repo_root/scripts/mf-002r1-failure-tests.sh"

regression_names=(fact turd-burglar general books mythadis venus)
regression_fixtures=(
  "$repo_root/content/fixtures/mf002-fact.json"
  "$repo_root/content/fixtures/mf002-turd-burglar.json"
  "$repo_root/content/fixtures/mf002-general.json"
  "$repo_root/content/fixtures/production-batch-001-books.json"
  "$repo_root/content/fixtures/production-batch-001-mythadis.json"
  "$repo_root/content/fixtures/production-batch-001-venus.json"
)
stress_names=(short normal long)
stress_fixtures=(
  "$repo_root/content/fixtures/mf002r1-stress-short.json"
  "$repo_root/content/fixtures/mf002r1-stress-normal.json"
  "$repo_root/content/fixtures/mf002r1-stress-long.json"
)
layout_reports=()

render_fixture() {
  local group=$1 name=$2 fixture=$3 make_video=$4
  local frames="$work_dir/$group-$name/frames"
  local layout="$artifact_dir/layout/$group-$name.json"
  local log="$artifact_dir/render-logs/$group-$name.log"
  mkdir -p "$frames"
  timeout 90 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- \
    --fixture "$fixture" --grammar "$grammar" --output-dir "$frames" --layout-report "$layout" >"$log" 2>&1
  test "$(find "$frames" -maxdepth 1 -type f -name 'frame_*.png' | wc -l)" -eq 450
  grep -q 'MF002_STRUCTURAL safe_area=PASS layers=workshop,sign,media,paper,tape,props layout=PASS' "$log"
  grep -q "MF002_RENDER_COMPLETE id=$(jq -r .id "$fixture") frames=450" "$log"
  cp "$frames/frame_000225.png" "$artifact_dir/$group/$name-main.png"
  layout_reports+=("$layout")
  if test "$make_video" = yes; then
    local audio="$work_dir/$group-$name/audio.wav" media="$artifact_dir/regression/$name.mp4"
    python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$audio" >"$artifact_dir/render-logs/$name-audio.log"
    ffmpeg -hide_banner -y -loglevel error -framerate 30 -start_number 0 -i "$frames/frame_%06d.png" -i "$audio" \
      -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' \
      -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 \
      -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$media"
    python3 "$repo_root/scripts/validate_media.py" "$media" --slice MF-002R1 \
      --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-result.json" >/dev/null
    cp "$artifact_dir/regression/$name-main.png" "$artifact_dir/frames/$name-main.png"
  fi
  printf '[PASS] %-10s %s\n' "$group" "$name"
}

printf '\nSTRESS FIXTURES\n'
for index in "${!stress_names[@]}"; do render_fixture stress-tests "${stress_names[$index]}" "${stress_fixtures[$index]}" no; done

printf '\nREGRESSION FIXTURES\n'
for index in "${!regression_names[@]}"; do render_fixture regression "${regression_names[$index]}" "${regression_fixtures[$index]}" yes; done

cp "$artifact_dir/regression/venus-main.png" "$artifact_dir/after/venus-corrected.png"
cp "$artifact_dir/layout/regression-venus.json" "$artifact_dir/after/venus-layout.json"

printf '\nINDEPENDENT GEOMETRY VALIDATION\n'
python3 "$repo_root/scripts/validate_mf002r1_layout.py" --grammar "$grammar" --reports "${layout_reports[@]}" --output "$artifact_dir/validation/layout.json" >"$artifact_dir/render-logs/layout-validation.log"
printf '[PASS] Renderer geometry independently checked for all passing fixtures\n'

python3 - "$artifact_dir" "$report_dir/result.json" <<'PY'
import hashlib,json,pathlib,sys
artifact=pathlib.Path(sys.argv[1]); videos={}
for name in ("fact","turd-burglar","general","books","mythadis","venus"):
    result=json.loads((artifact/"validation"/f"{name}-result.json").read_text())
    assert result["result"] == "PASS"
    videos[name]={"result":"PASS",**result["artifact"]}
layout=json.loads((artifact/"validation"/"layout.json").read_text()); assert layout["result"] == "PASS"
before=artifact/"before"/"venus-problem.png"; after=artifact/"after"/"venus-corrected.png"
out={"slice":"MF-002R1","layout":layout["layout"],"stress_tests":{"short":"PASS","normal":"PASS","long":"PASS","overflow":"EXPECTED_FAIL"},"failure_tests":"PASS","regressions":videos,"venus":{"before_sha256":hashlib.sha256(before.read_bytes()).hexdigest(),"after_sha256":hashlib.sha256(after.read_bytes()).hexdigest(),"layout":"PASS"},"technical_result":"PASS","human_review":"PENDING"}
pathlib.Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
PY

trap - ERR
printf '\nMF-002R1 TECHNICAL RESULT: PASS\nHUMAN VISUAL REVIEW: REQUIRED\n'
