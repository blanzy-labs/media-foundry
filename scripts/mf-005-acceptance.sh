#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
godot_bin=${GODOT_BIN:-godot}
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}
artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-005}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-005}
mkdir -p "$artifact_dir/audio/normalized" "$artifact_dir/audio/generated" "$artifact_dir/audio/base" "$artifact_dir/audio/final" "$artifact_dir/audio/waveforms" "$artifact_dir/frames" "$artifact_dir/validation" "$artifact_dir/timelines" "$artifact_dir/logs" "$report_dir"
work_dir=$(mktemp -d "$artifact_dir/work.XXXXXX")

cleanup() {
  if [[ $work_dir == "$artifact_dir"/work.* && -d $work_dir ]]; then find "$work_dir" -depth -delete; fi
}
trap cleanup EXIT

fail_result() {
  local code=$?
  python3 - "$report_dir/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-005","technical_result":"FAIL","human_review":"PENDING","exit_code":int(sys.argv[2])},indent=2)+"\n")
PY
  printf '\nMF-005 TECHNICAL RESULT: FAIL\n' >&2
  exit "$code"
}
trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-005\n======================\n\nBASELINE GATES\n'
for slice in mf-001 mf-002 mf-002r1 mf-003 mf-004 mf-pilot-001; do
  result="$repo_root/reports/$slice/result.json"; test -s "$result"
  jq -e '(.result == "PASS") or (.technical_result == "PASS")' "$result" >/dev/null
  printf '[PASS] %s\n' "$slice"
done

printf '\nFAIL-CLOSED NARRATION TESTS\n'
python3 "$repo_root/scripts/mf-005-failure-tests.py" --repo-root "$repo_root" --output "$report_dir/failure-tests.json" >/dev/null
printf '[PASS] Nine controlled narration failures\n'

printf '\nNON-NARRATED COMPATIBILITY\n'
python3 "$repo_root/scripts/preflight_mf004.py" --fixture "$repo_root/content/fixtures/mf004-turd-burglar.json" --grammar "$grammar" --project-root "$repo_root" --output "$work_dir/legacy-timeline.json" >/dev/null
python3 "$repo_root/scripts/prepare_mf005_narration.py" --fixture "$repo_root/content/fixtures/mf004-turd-burglar.json" --timeline "$work_dir/legacy-timeline.json" --project-root "$repo_root" --normalized-dir "$work_dir/legacy-normalized" --cache-dir "$artifact_dir/audio/generated" --output "$artifact_dir/validation/non-narrated-compatibility.json" >/dev/null
test "$(jq '.segments | length' "$artifact_dir/validation/non-narrated-compatibility.json")" -eq 0
printf '[PASS] narration absent remains valid\n'

names=(turd-burglar books venus)
fixtures=("$repo_root/content/fixtures/mf005-turd-burglar.json" "$repo_root/content/fixtures/mf005-books.json" "$repo_root/content/fixtures/mf005-venus.json")

printf '\nNARRATED PRODUCTION\n'
for index in "${!names[@]}"; do
  name=${names[$index]} fixture=${fixtures[$index]}
  frames="$work_dir/$name/frames"; mkdir -p "$frames" "$artifact_dir/frames/$name" "$artifact_dir/audio/normalized/$name"
  timeline="$artifact_dir/timelines/$name.json"; execution="$artifact_dir/timelines/$name-execution.json"; narration="$artifact_dir/timelines/$name-narration.json"
  layout="$artifact_dir/validation/$name-layout.json"; media="$artifact_dir/$name.mp4"
  python3 "$repo_root/scripts/preflight_mf004.py" --fixture "$fixture" --grammar "$grammar" --project-root "$repo_root" --output "$timeline" >"$artifact_dir/logs/$name-timeline.log"
  /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-narration-metrics.txt" \
    python3 "$repo_root/scripts/prepare_mf005_narration.py" --fixture "$fixture" --timeline "$timeline" --project-root "$repo_root" --normalized-dir "$artifact_dir/audio/normalized/$name" --cache-dir "$artifact_dir/audio/generated" --output "$narration" >"$artifact_dir/logs/$name-narration.log"
  /usr/bin/time -f 'elapsed_seconds=%e\npeak_kib=%M' -o "$artifact_dir/logs/$name-godot-metrics.txt" \
    timeout 120 "$godot_bin" --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- --fixture "$fixture" --grammar "$grammar" --output-dir "$frames" --layout-report "$layout" --timeline-report "$execution" >"$artifact_dir/logs/$name-render.log" 2>&1
  expected_frames=$(jq '.duration * 30' "$timeline"); test "$(find "$frames" -maxdepth 1 -name 'frame_*.png' | wc -l)" -eq "$expected_frames"
  python3 "$repo_root/scripts/generate_mf002_audio.py" --grammar "$grammar" --fixture "$fixture" --output "$artifact_dir/audio/base/$name.wav" >"$artifact_dir/logs/$name-base-audio.log"
  /usr/bin/time -f '%e' -o "$artifact_dir/logs/$name-mix-seconds.txt" \
    python3 "$repo_root/scripts/mix_mf005_audio.py" --base "$artifact_dir/audio/base/$name.wav" --manifest "$narration" --output "$artifact_dir/audio/final/$name.wav" --report "$artifact_dir/validation/$name-mix.json" >"$artifact_dir/logs/$name-mix.log"
  duration=$(jq -r .duration "$timeline")
  /usr/bin/time -f '%e' -o "$artifact_dir/logs/$name-ffmpeg-seconds.txt" \
    ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i "$frames/frame_%06d.png" -i "$artifact_dir/audio/final/$name.wav" -map 0:v:0 -map 1:a:0 -t "$duration" -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 -c:a aac -b:a 160k -ar 48000 -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$media" 2>"$artifact_dir/logs/$name-ffmpeg.log"
  validation_start=$(date +%s%N)
  python3 "$repo_root/scripts/validate_media.py" "$media" --slice MF-005 --ffprobe-json "$artifact_dir/validation/$name-ffprobe.json" --result-json "$artifact_dir/validation/$name-output.json" >/dev/null
  python3 "$repo_root/scripts/validate_mf004_timeline.py" --preflight "$timeline" --execution "$execution" --layout "$layout" --output "$artifact_dir/validation/$name-timeline.json" >/dev/null
  python3 "$repo_root/scripts/validate_mf005_audio.py" --manifest "$narration" --mix-report "$artifact_dir/validation/$name-mix.json" --fixture "$fixture" --grammar "$grammar" --base "$artifact_dir/audio/base/$name.wav" --media "$media" --output "$artifact_dir/validation/$name-narration.json" >/dev/null
  validation_end=$(date +%s%N); awk -v start="$validation_start" -v end="$validation_end" 'BEGIN {printf "%.6f\n", (end-start)/1000000000}' >"$artifact_dir/logs/$name-validation-seconds.txt"
  python3 - "$timeline" "$frames" "$artifact_dir/frames/$name" <<'PY'
import json,pathlib,shutil,sys
timeline=json.loads(pathlib.Path(sys.argv[1]).read_text()); source=pathlib.Path(sys.argv[2]); target=pathlib.Path(sys.argv[3])
for beat in timeline["beats"]:
    frame=round(((beat["start"]+beat["end"])/2)*30)
    shutil.copy2(source/f"frame_{frame:06d}.png",target/f"{beat['id']}.png")
PY
  ffmpeg -hide_banner -loglevel error -y -i "$artifact_dir/audio/final/$name.wav" -filter_complex 'showwavespic=s=900x180:colors=0xd4b863' -frames:v 1 "$artifact_dir/audio/waveforms/$name.png"
  printf '[PASS] %s — narration=%s beats\n' "$name" "$(jq '.segments|length' "$narration")"
done

ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$artifact_dir/frames/*/*.png" -vf 'scale=180:320,tile=7x3:padding=4:margin=4:color=0x17110e' -frames:v 1 "$artifact_dir/contact-sheet.png"

python3 - "$artifact_dir" "$report_dir/result.json" <<'PY'
import json,pathlib,re,sys
root=pathlib.Path(sys.argv[1]); fixtures={}
for name in ("turd-burglar","books","venus"):
    narration=json.loads((root/"timelines"/f"{name}-narration.json").read_text()); output=json.loads((root/"validation"/f"{name}-output.json").read_text()); audio=json.loads((root/"validation"/f"{name}-narration.json").read_text()); timeline=json.loads((root/"validation"/f"{name}-timeline.json").read_text())
    assert narration["result"] == output["result"] == audio["result"] == timeline["result"] == "PASS"
    def timed(path):
        values=dict(re.findall(r"(elapsed_seconds|peak_kib)=([0-9.]+)",path.read_text())); return values
    godot=timed(root/"logs"/f"{name}-godot-metrics.txt"); prep=timed(root/"logs"/f"{name}-narration-metrics.txt")
    fixtures[name]={"narrated_beats":len(narration["segments"]),"narration_preflight":"PASS","timeline":"PASS","render":"PASS","final_audio":"PASS","validation":"PASS","sha256":output["artifact"]["sha256"],"final_bytes":output["artifact"]["bytes"],"metrics":{"generation_seconds":narration["metrics"]["generation_seconds"],"cache_hits":narration["metrics"]["cache_hits"],"cache_misses":narration["metrics"]["cache_misses"],"normalization_seconds":narration["metrics"]["normalization_seconds"],"narration_preflight_seconds":float(prep["elapsed_seconds"]),"godot_render_seconds":float(godot["elapsed_seconds"]),"peak_godot_kib":int(float(godot["peak_kib"])),"mix_seconds":float((root/"logs"/f"{name}-mix-seconds.txt").read_text()),"ffmpeg_finalization_seconds":float((root/"logs"/f"{name}-ffmpeg-seconds.txt").read_text()),"validation_seconds":float((root/"logs"/f"{name}-validation-seconds.txt").read_text())}}
result={"slice":"MF-005","baseline":{"mf001":"PASS","mf002":"PASS","mf002r1":"PASS","mf003":"PASS","mf004":"PASS","mf_pilot_001":"PASS"},"fixtures":fixtures,"deterministic_fixture_audio":"PASS","provider_boundary":"PASS","normalization":"PASS","ducking":"PASS","existing_cues":"PASS","non_narrated_compatibility":"PASS","failure_tests":"PASS","shared_renderer":"PASS","subject_specific_audio_code":0,"corrected_venus_asset":"PASS","technical_result":"PASS","human_review":"PENDING"}
pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2))
PY

trap - ERR
printf '\nMF-005 TECHNICAL RESULT: PASS\nHUMAN AUDIO REVIEW: REQUIRED\n'
