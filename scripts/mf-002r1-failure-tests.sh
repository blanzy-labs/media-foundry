#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
godot_bin=${GODOT_BIN:-godot}
base_grammar=${MF_GRAMMAR:-$repo_root/config/visual-grammar.json}
report_dir=${MF_REPORT_DIR:-$repo_root/reports/mf-002r1}
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/mf-002r1-failures.XXXXXX")
mkdir -p "$report_dir"

cleanup() {
  if [[ $work_dir == "${TMPDIR:-/tmp}"/mf-002r1-failures.* && -d $work_dir ]]; then
    find "$work_dir" -depth -delete
  fi
}
trap cleanup EXIT

python3 - "$base_grammar" "$work_dir" <<'PY'
import copy, json, pathlib, sys
grammar=json.loads(pathlib.Path(sys.argv[1]).read_text())
out=pathlib.Path(sys.argv[2])
cases={}
g=copy.deepcopy(grammar); g["typography"]["safe_areas"].pop("HEADLINE_SAFE_AREA"); cases["missing-safe-area"]=g
g=copy.deepcopy(grammar); g["typography"]["roles"]["HEADLINE"]["min_font_size"]=50; cases["malformed-layout"]=g
g=copy.deepcopy(grammar); g["typography"]["safe_areas"]["HEADLINE_SAFE_AREA"]["height"]=34; cases["minimum-exhaustion"]=g
for name, value in cases.items():
    (out/f"{name}.json").write_text(json.dumps(value, indent=2)+"\n")
PY

run_expected_failure() {
  local name=$1 fixture=$2 grammar=$3 expected=$4
  local output="$work_dir/$name-output" log="$work_dir/$name.log"
  mkdir -p "$output"
  if "$godot_bin" --headless --path "$repo_root/godot" --fixed-fps 30 res://mf002.tscn -- \
      --fixture "$fixture" --grammar "$grammar" --output-dir "$output" --validate-layout-only >"$log" 2>&1; then
    printf '[FAIL] %s unexpectedly passed\n' "$name" >&2
    return 1
  fi
  grep -q "$expected" "$log"
  test -s "$output/layout-validation.json"
  test "$(jq -r .result "$output/layout-validation.json")" = FAIL
  printf '[PASS] %-24s rejected with %s\n' "$name" "$expected"
}

run_expected_failure oversized-headline "$repo_root/content/fixtures/mf002r1-stress-overflow.json" "$base_grammar" HEADLINE_LAYOUT_FAILED
run_expected_failure malformed-layout "$repo_root/content/fixtures/mf002r1-stress-normal.json" "$work_dir/malformed-layout.json" HEADLINE_LAYOUT_FAILED
run_expected_failure missing-safe-area "$repo_root/content/fixtures/mf002r1-stress-normal.json" "$work_dir/missing-safe-area.json" CONFIG_LAYOUT_FAILED
run_expected_failure minimum-exhaustion "$repo_root/content/fixtures/mf002r1-stress-normal.json" "$work_dir/minimum-exhaustion.json" HEADLINE_LAYOUT_FAILED

python3 - "$report_dir/failure-tests.json" <<'PY'
import json, pathlib, sys
result={"slice":"MF-002R1","result":"PASS","tests":{
 "oversized_headline":{"result":"PASS","expected":"HEADLINE_LAYOUT_FAILED"},
 "malformed_layout_configuration":{"result":"PASS","expected":"HEADLINE_LAYOUT_FAILED"},
 "missing_safe_area":{"result":"PASS","expected":"CONFIG_LAYOUT_FAILED"},
 "minimum_font_size_exhaustion":{"result":"PASS","expected":"HEADLINE_LAYOUT_FAILED"}}}
pathlib.Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+"\n")
PY

printf 'MF-002R1 FAILURE TESTS: PASS\n'
