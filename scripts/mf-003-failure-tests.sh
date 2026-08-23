#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-003}
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/mf-003-failures.XXXXXX")
mkdir -p "$report_dir" "$work_dir/assets"

cleanup() {
  if [[ $work_dir == "${TMPDIR:-/tmp}"/mf-003-failures.* && -d $work_dir ]]; then find "$work_dir" -depth -delete; fi
}
trap cleanup EXIT

printf 'corrupt image bytes\n' >"$work_dir/assets/corrupt.png"
printf 'unsupported fixture\n' >"$work_dir/assets/unsupported.gif"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=440:sample_rate=48000:duration=3' -vn -c:a aac "$work_dir/assets/audio-only.mp4"

python3 - "$repo_root/content/fixtures/mf003-image.json" "$repo_root/content/fixtures/mf003-video.json" "$work_dir" <<'PY'
import copy,json,pathlib,sys
image=json.loads(pathlib.Path(sys.argv[1]).read_text()); video=json.loads(pathlib.Path(sys.argv[2]).read_text()); out=pathlib.Path(sys.argv[3])
def emit(name,fixture):
    fixture["id"]=name; (out/f"{name}.json").write_text(json.dumps(fixture,indent=2)+"\n")
f=copy.deepcopy(image); f["media"]["source"]="media/images/definitely-missing.png"; emit("missing-image",f)
f=copy.deepcopy(image); f["media"]["source"]=str(out/"assets/corrupt.png"); emit("corrupt-image",f)
f=copy.deepcopy(image); f["media"]["source"]=str(out/"assets/unsupported.gif"); emit("unsupported-format",f)
f=copy.deepcopy(video); f["media"]["source"]="media/video/definitely-missing.mp4"; emit("missing-video",f)
f=copy.deepcopy(video); f["media"]["source"]=str(out/"assets/audio-only.mp4"); emit("no-video-stream",f)
f=copy.deepcopy(video); f["media"]["start_seconds"]=9; emit("invalid-start",f)
f=copy.deepcopy(video); f["media"]["start_seconds"]=6; f["media"]["duration_seconds"]=5; emit("clip-beyond-duration",f)
f=copy.deepcopy(image); f["media"].pop("fit"); f["media"]["required"]="yes"; emit("malformed-media",f)
PY

names=(missing-image corrupt-image unsupported-format missing-video no-video-stream invalid-start clip-beyond-duration malformed-media)
stages=(source_exists asset_readable supported_format source_exists video_stream start_offset clip_duration fit_mode)
for index in "${!names[@]}"; do
  name=${names[$index]} stage=${stages[$index]} output="$work_dir/$name-result.json"
  if python3 "$repo_root/scripts/prepare_mf003_media.py" --fixture "$work_dir/$name.json" --grammar "$grammar" --project-root "$repo_root" --output "$output" >"$work_dir/$name.log" 2>&1; then
    printf '[FAIL] %s unexpectedly passed\n' "$name" >&2; exit 1
  fi
  test "$(jq -r .result "$output")" = FAIL
  jq -e --arg stage "$stage" '.failures[] | select(.code=="MEDIA_ASSET_FAILED" and .stage==$stage and (.reason|length)>0)' "$output" >/dev/null
  printf '[PASS] %-23s failed closed at %s\n' "$name" "$stage"
done

python3 - "$report_dir/failure-tests.json" "${names[@]}" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-003","tests":{name:{"result":"PASS","expected":"MEDIA_ASSET_FAILED"} for name in sys.argv[2:]},"result":"PASS"},indent=2)+"\n")
PY
printf 'MF-003 FAILURE TESTS: PASS\n'
