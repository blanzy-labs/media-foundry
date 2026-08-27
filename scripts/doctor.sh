#!/usr/bin/env bash
set -u

json_mode=false
case ${1:-} in
  "") ;;
  --json) json_mode=true ;;
  *) printf 'Usage: %s [--json]\n' "$0" >&2; exit 2 ;;
esac

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="${HOME}/.local/bin:${PATH}"
godot_bin=${GODOT_BIN:-godot}
records=$(mktemp)
trap 'rm -f "$records"' EXIT
required_failures=0

add_check() {
  local id=$1 label=$2 required=$3 status=$4 version=${5:-} detail=${6:-}
  python3 - "$id" "$label" "$required" "$status" "$version" "$detail" >>"$records" <<'PY'
import json, sys
print(json.dumps({"id":sys.argv[1], "label":sys.argv[2], "required":sys.argv[3]=="true", "status":sys.argv[4], "version":sys.argv[5], "detail":sys.argv[6]}))
PY
  if [[ $required == true && $status != PASS ]]; then required_failures=$((required_failures + 1)); fi
}

first_line() { "$@" 2>/dev/null | head -n 1 || true; }
os_name=$(sed -n 's/^PRETTY_NAME=//p' /etc/os-release | tr -d '"')
add_check os "Operating system" false INFO "$os_name" "$(uname -r)"
add_check architecture "Architecture" false INFO "$(uname -m)" ""

for tool in git python3 "$godot_bin" ffmpeg ffprobe; do
  case $tool in
    git) label=Git; version=$(first_line git --version) ;;
    python3) label=Python; version=$(first_line python3 --version) ;;
    "$godot_bin") label=Godot; version=$(first_line "$godot_bin" --version) ;;
    ffmpeg) label=FFmpeg; version=$(first_line ffmpeg -version) ;;
    ffprobe) label=FFprobe; version=$(first_line ffprobe -version) ;;
  esac
  if command -v "$tool" >/dev/null 2>&1; then
    add_check "${label,,}" "$label" true PASS "$version" "$(command -v "$tool")"
  else
    add_check "${label,,}" "$label" true FAIL "" "command not found"
  fi
done

if command -v gh >/dev/null 2>&1; then
  gh_version=$(first_line gh --version)
  if timeout 15 gh auth status >/dev/null 2>&1; then
    add_check github_cli "GitHub CLI" false READY "$gh_version" "authenticated"
  else
    add_check github_cli "GitHub CLI" false WARN "$gh_version" "installed but not authenticated"
  fi
else
  add_check github_cli "GitHub CLI" false INFO "" "not installed; not required to render"
fi

if command -v "$godot_bin" >/dev/null 2>&1; then
  smoke=$(timeout 30 "$godot_bin" --headless --path "$repo_root/godot" --script smoke.gd 2>&1 || true)
  if [[ $smoke == *MEDIA_FOUNDRY_GODOT_SMOKE_OK* ]]; then
    add_check godot_automation "Godot automation" true PASS "headless" "smoke marker observed"
  else
    add_check godot_automation "Godot automation" true FAIL "" "headless smoke failed"
  fi
  indicator_stage=$(timeout 30 "$godot_bin" --headless --path "$repo_root/godot" --script indicator_pulse_stage_headless.gd 2>&1 || true)
  if [[ $indicator_stage == *INDICATOR_PULSE_STAGE_HEADLESS_OK* ]] \
      && [[ $indicator_stage != *"doesn't inherit from SceneTree or MainLoop"* ]] \
      && [[ $indicator_stage != *"Can't load the script"* ]]; then
    add_check indicator_stage_component "Indicator stage runtime/harness separation" true PASS "Node2D + SceneTree harness" "headless load and subclass instantiation passed"
  else
    add_check indicator_stage_component "Indicator stage runtime/harness separation" true FAIL "" "headless indicator harness failed"
  fi
else
  add_check godot_automation "Godot automation" true FAIL "" "Godot unavailable"
  add_check indicator_stage_component "Indicator stage runtime/harness separation" true FAIL "" "Godot unavailable"
fi

if command -v ffmpeg >/dev/null 2>&1 && ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'libx264'; then
  add_check video_encoding "Video encoding (H.264)" true PASS "libx264" ""
else
  add_check video_encoding "Video encoding (H.264)" true FAIL "" "libx264 encoder unavailable"
fi
if command -v ffmpeg >/dev/null 2>&1 && ffmpeg -hide_banner -encoders 2>/dev/null | grep -qE '(^| )aac([[:space:]]|$)'; then
  add_check audio_encoding "Audio encoding (AAC)" true PASS "aac" ""
else
  add_check audio_encoding "Audio encoding (AAC)" true FAIL "" "AAC encoder unavailable"
fi

if command -v blender >/dev/null 2>&1; then
  blender_version=$(first_line blender --version)
  if timeout 30 blender --background --version >/dev/null 2>&1; then
    add_check blender "Blender (optional)" false READY "$blender_version" "CLI background mode available"
  else
    add_check blender "Blender (optional)" false WARN "$blender_version" "background mode failed"
  fi
else
  add_check blender "Blender (optional)" false INFO "not installed" "future asset-authoring capability; MF-001 unaffected"
fi

gpu=$(lspci 2>/dev/null | grep -Ei 'VGA compatible|3D controller|Display controller' | paste -sd ';' - || true)
display="DISPLAY=${DISPLAY:-unset}; WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset}; session=${XDG_SESSION_TYPE:-unset}"
add_check graphics "Graphics/display" false INFO "${gpu:-not reported}" "$display"
fonts=$(fc-list : family 2>/dev/null | sort -u | head -n 8 | paste -sd ',' - || true)
add_check fonts "Rendering fonts" false INFO "${fonts:-not reported}" "Godot bundled fallback font used by MF-001"
video_count=$(ffmpeg -hide_banner -encoders 2>/dev/null | awk '/^ V/{n++} END{print n+0}')
audio_count=$(ffmpeg -hide_banner -encoders 2>/dev/null | awk '/^ A/{n++} END{print n+0}')
add_check codecs "Codec inventory" false INFO "$video_count video / $audio_count audio encoders" "FFmpeg encoder inventory"

overall=PASS
(( required_failures > 0 )) && overall=FAIL
if $json_mode; then
  python3 - "$records" "$overall" <<'PY'
import json, platform, sys
checks=[json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]
print(json.dumps({"system":"Media Foundry", "result":sys.argv[2], "platform":{"system":platform.system(), "release":platform.release(), "machine":platform.machine()}, "checks":checks}, indent=2))
PY
else
  printf 'MEDIA FOUNDRY WORKSTATION\n=========================\n\n'
  while IFS= read -r row; do
    python3 - "$row" <<'PY'
import json, sys
c=json.loads(sys.argv[1]); print(f"{c['label']}\n[{c['status']}]" + (f" {c['version']}" if c['version'] else "") + (f"\n  {c['detail']}" if c['detail'] else "") + "\n")
PY
  done <"$records"
  printf 'MF WORKSTATION RESULT: %s\n' "$overall"
fi
[[ $overall == PASS ]]
