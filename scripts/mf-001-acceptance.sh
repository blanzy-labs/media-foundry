#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
fixture=${MF_FIXTURE:-$repo_root/content/fixtures/mf001-demo.json}
artifact_dir=${MF_ARTIFACT_DIR:-$repo_root/artifacts/mf-001}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-001}
work_dir=${MF_WORK_DIR:-$artifact_dir/work}
frames_dir=$work_dir/frames
final_media=$artifact_dir/mf001-demo.mp4
godot_bin=${GODOT_BIN:-godot}
mkdir -p "$artifact_dir" "$report_dir"

fail_result() {
  local code=$?
  python3 - "$report_dir/result.json" "$code" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True)
if not p.exists() or json.loads(p.read_text()).get("result") != "FAIL":
    p.write_text(json.dumps({"slice":"MF-001","render":"FAIL","validation":{},"result":"FAIL","exit_code":int(sys.argv[2])}, indent=2)+"\n")
PY
  printf '\nMF-001 RESULT: FAIL\n' >&2
  exit "$code"
}
trap fail_result ERR

printf 'MEDIA FOUNDRY — MF-001\n======================\n\nWORKSTATION\n'
"$repo_root/scripts/doctor.sh" | tee "$artifact_dir/doctor.log"
"$repo_root/scripts/doctor.sh" --json >"$artifact_dir/doctor.json"

printf '\nCONTENT\n'
python3 - "$fixture" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]); d=json.loads(p.read_text(encoding="utf-8"))
assert set(("id","template","format","intro","content","outro","audio")) <= d.keys()
assert d["template"] == "did_you_know"
assert d["format"] == {"width":1080,"height":1920,"fps":30,"duration_seconds":15}
assert all(isinstance(d[x]["text"], str) and d[x]["text"].strip() for x in ("intro","outro"))
assert all(isinstance(d["content"][x], str) and d["content"][x].strip() for x in ("headline","body"))
assert d["audio"]["enabled"] is True
print("[PASS] Fixture", p)
PY

if [[ ${MF_INJECT_RENDER_FAILURE:-0} == 1 ]]; then
  printf '[INJECTED] rendering failure\n' >&2
  false
fi

rm -rf "$work_dir"
mkdir -p "$frames_dir"

printf '\nAUDIO\n'
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i 'sine=frequency=105:sample_rate=48000:duration=15' \
  -f lavfi -i 'sine=frequency=440:sample_rate=48000:duration=0.22' \
  -f lavfi -i 'sine=frequency=660:sample_rate=48000:duration=0.32' \
  -filter_complex '[0:a]volume=0.018[bed];[1:a]volume=0.12,adelay=350|350[intro];[2:a]volume=0.08,adelay=12300|12300[outro];[bed][intro][outro]amix=inputs=3:normalize=0,alimiter=limit=0.8[a]' \
  -map '[a]' -t 15 -c:a pcm_s16le "$work_dir/audio.wav"
printf '[PASS] Deterministic audio source\n'

printf '\nRENDER\n'
"$godot_bin" --path "$repo_root/godot" --fixed-fps 30 -- \
  --fixture "$fixture" --output-dir "$frames_dir" >"$artifact_dir/render.log" 2>&1
frame_count=$(find "$frames_dir" -maxdepth 1 -name 'frame_*.png' -type f | wc -l)
[[ $frame_count -eq 450 ]]
grep -q 'MF_RENDER_COMPLETE frames=450' "$artifact_dir/render.log"
printf '[PASS] Godot composition and animation (%s frames)\n' "$frame_count"

if [[ ${MF_INJECT_MISSING_OUTPUT:-0} == 1 ]]; then
  rm -f "$final_media"
  python3 "$repo_root/scripts/validate_media.py" "$final_media" --ffprobe-json "$artifact_dir/ffprobe.json" --result-json "$report_dir/result.json"
fi

printf '\nFINALIZE\n'
ffmpeg -hide_banner -y -loglevel info \
  -framerate 30 -start_number 0 -i "$frames_dir/frame_%06d.png" -i "$work_dir/audio.wav" \
  -map 0:v:0 -map 1:a:0 -t 15 -vf 'scale=1080:1920:flags=lanczos,format=yuv420p' \
  -c:v libx264 -preset medium -crf 20 -threads 1 -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 160k -ar 48000 -movflags +faststart \
  -metadata creation_time='1970-01-01T00:00:00Z' "$final_media" >"$artifact_dir/ffmpeg.log" 2>&1
printf '[PASS] FFmpeg H.264/AAC finalization\n'

if [[ ${MF_INJECT_INVALID_MEDIA:-0} == 1 ]]; then
  printf 'not an mp4\n' >"$final_media"
fi

printf '\nVALIDATE\n'
python3 "$repo_root/scripts/validate_media.py" "$final_media" \
  --ffprobe-json "$artifact_dir/ffprobe.json" --result-json "$report_dir/result.json"

mkdir -p "$artifact_dir/frames"
ffmpeg -hide_banner -loglevel error -y -ss 1 -i "$final_media" -frames:v 1 "$artifact_dir/frames/intro.png"
ffmpeg -hide_banner -loglevel error -y -ss 7 -i "$final_media" -frames:v 1 "$artifact_dir/frames/content.png"
ffmpeg -hide_banner -loglevel error -y -ss 14 -i "$final_media" -frames:v 1 "$artifact_dir/frames/outro.png"
for evidence_frame in intro content outro; do
  [[ -s $artifact_dir/frames/$evidence_frame.png ]]
done
printf '[PASS] Intro, content, and outro evidence frames\n'

trap - ERR
printf '\nMF-001 RESULT: PASS\n'
