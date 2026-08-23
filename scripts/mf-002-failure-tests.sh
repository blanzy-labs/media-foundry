#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT
passed=0
failed=0

expect_failure() {
  local label=$1
  shift
  if "$@" >"$test_root/${label// /_}.log" 2>&1; then
    printf '[FAIL] %s (unexpected success)\n' "$label"
    failed=$((failed + 1))
  else
    printf '[PASS] %s failed closed\n' "$label"
    passed=$((passed + 1))
  fi
}

isolated_acceptance() {
  local name=$1
  shift
  env MF_ARTIFACT_DIR="$test_root/$name/artifacts" MF_REPORT_DIR="$test_root/$name/reports" MF_WORK_DIR="$test_root/$name/work" "$@" "$repo_root/scripts/mf-002-acceptance.sh"
}

printf 'MEDIA FOUNDRY — MF-002 FAILURE TESTS\n====================================\n'
printf '{}\n' >"$test_root/invalid-grammar.json"
expect_failure "invalid visual grammar" isolated_acceptance invalid_grammar MF_GRAMMAR="$test_root/invalid-grammar.json"
expect_failure "missing fixture set" isolated_acceptance missing_fixtures MF_FIXTURE_DIR="$test_root/no-fixtures"
expect_failure "rendering failure" isolated_acceptance render_failure MF_INJECT_RENDER_FAILURE_AT=fact
expect_failure "missing video" isolated_acceptance missing_video MF_INJECT_MISSING_OUTPUT_AT=fact
expect_failure "invalid media" isolated_acceptance invalid_media MF_INJECT_INVALID_MEDIA_AT=fact

mkdir -p "$test_root/validation"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i color=c=black:s=320x240:r=10:d=1 \
  -f lavfi -i sine=frequency=220:duration=1 -shortest -c:v libx264 -c:a aac "$test_root/validation/wrong.mp4"
expect_failure "technical validation rejection" python3 "$repo_root/scripts/validate_media.py" "$test_root/validation/wrong.mp4" --slice MF-002 \
  --ffprobe-json "$test_root/validation/probe.json" --result-json "$test_root/validation/result.json"

result=PASS
(( failed > 0 )) && result=FAIL
python3 - "$repo_root/reports/mf-002/failure-tests.json" "$result" "$passed" "$failed" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps({"slice":"MF-002","suite":"fail-closed","result":sys.argv[2],"passed":int(sys.argv[3]),"failed":int(sys.argv[4])}, indent=2)+"\n")
PY
printf '\nFailure tests: %s PASS, %s FAIL\nMF-002 FAILURE TEST RESULT: %s\n' "$passed" "$failed" "$result"
[[ $result == PASS ]]
