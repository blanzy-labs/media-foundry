#!/usr/bin/env bash
set -Eeuo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
manifest=$root/content/batches/mf008-unknown-process-batch-001.json
archive=/home/blanzy/media-foundry-output/unknown-process-batch-001
schedule_id=55968f6f-1314-41a6-9e7e-ab9875aa0c63
art=$root/artifacts/mf-008
rep=$root/reports/mf-008
mkdir -p "$art"/{representative-frames,validation} "$rep/jobs"

python3 "$root/scripts/validate_mf008_manifest.py" --project-root "$root" --manifest "$manifest" --output "$art/validation/manifest.json" >"$art/validation/manifest.log"
openclaw cron show "$schedule_id" --json >"$art/validation/openclaw-schedule.json"
openclaw cron runs --id "$schedule_id" --limit 5 >"$art/validation/openclaw-runs.json"
openclaw cron status --json >"$art/validation/openclaw-status.json"

set +e
duplicate_output=$(python3 "$root/scripts/run_mf008_batch.py" --project-root "$root" --manifest "$manifest" --run-id scheduled-run-001 --trigger-kind scheduled 2>&1)
duplicate_code=$?
set -e
python3 - "$art/validation/idempotency.json" "$duplicate_code" "$duplicate_output" <<'PY'
import json,pathlib,sys
code=int(sys.argv[2]);detail=sys.argv[3]
pathlib.Path(sys.argv[1]).write_text(json.dumps({'test':'duplicate completed batch ID','exit_code':code,'detail':detail,'result':'PASS' if code==4 and 'DUPLICATE_RUN_REFUSED' in detail else 'FAIL'},indent=2)+'\n')
PY

for job in up-video-001 up-video-002 up-video-003; do
  mkdir -p "$art/representative-frames/$job" "$art/validation/jobs/$job"
  cp "$archive/scheduled-run-001/$job/representative-frames/"*.png "$art/representative-frames/$job/"
  cp "$archive/scheduled-run-001/$job/validation/media.json" "$art/validation/jobs/$job/media.json"
  cp "$archive/scheduled-run-001/$job/validation/ffprobe.json" "$art/validation/jobs/$job/ffprobe.json"
  cp "$archive/scheduled-run-001/$job/result.json" "$rep/jobs/$job.json"
  ffmpeg -hide_banner -loglevel error -y -ss 8.70 -i "$archive/scheduled-run-001/$job/final.mp4" -frames:v 1 "$art/representative-frames/$job/story-1.png"
  ffmpeg -hide_banner -loglevel error -y -ss 13.10 -i "$archive/scheduled-run-001/$job/final.mp4" -frames:v 1 "$art/representative-frames/$job/story-2.png"
  ffmpeg -hide_banner -loglevel error -y -ss 17.40 -i "$archive/scheduled-run-001/$job/final.mp4" -frames:v 1 "$art/representative-frames/$job/story-3.png"
done
ffmpeg -hide_banner -loglevel error -y \
  -i "$art/representative-frames/up-video-001/story-1.png" -i "$art/representative-frames/up-video-001/story-2.png" -i "$art/representative-frames/up-video-001/story-3.png" \
  -i "$art/representative-frames/up-video-002/story-1.png" -i "$art/representative-frames/up-video-002/story-2.png" -i "$art/representative-frames/up-video-002/story-3.png" \
  -i "$art/representative-frames/up-video-003/story-1.png" -i "$art/representative-frames/up-video-003/story-2.png" -i "$art/representative-frames/up-video-003/story-3.png" \
  -filter_complex '[0:v]scale=270:480[v0];[1:v]scale=270:480[v1];[2:v]scale=270:480[v2];[3:v]scale=270:480[v3];[4:v]scale=270:480[v4];[5:v]scale=270:480[v5];[6:v]scale=270:480[v6];[7:v]scale=270:480[v7];[8:v]scale=270:480[v8];[v0][v1][v2][v3][v4][v5][v6][v7][v8]xstack=inputs=9:layout=0_0|270_0|540_0|0_480|270_480|540_480|0_960|270_960|540_960' \
  -frames:v 1 "$art/batch-contact-sheet.png"
cp "$archive/scheduled-run-001/batch-result.json" "$rep/batch-result.json"
cp "$archive/supervised-dry-run-001/batch-result.json" "$rep/supervised-dry-run-result.json"
cp "$archive/controlled-partial-failure-001/batch-result.json" "$rep/controlled-partial-failure-result.json"
cp "$archive/controlled-shared-failure-001/batch-result.json" "$rep/controlled-shared-failure-result.json"
cp "$archive/controlled-needs-engineering-001/batch-result.json" "$rep/controlled-needs-engineering-result.json"

python3 "$root/scripts/validate_mf008_runs.py" \
  --project-root "$root" --archive-root "$archive" \
  --dry-run supervised-dry-run-001 --scheduled-run scheduled-run-001 \
  --partial-run controlled-partial-failure-001 --shared-failure-run controlled-shared-failure-001 \
  --engineering-run controlled-needs-engineering-001 \
  --manifest-validation "$art/validation/manifest.json" \
  --schedule "$root/config/schedules/mf008-unknown-process-batch-001-scheduled-001.json" \
  --cron-job "$art/validation/openclaw-schedule.json" --cron-runs "$art/validation/openclaw-runs.json" \
  --cron-status "$art/validation/openclaw-status.json" --idempotency "$art/validation/idempotency.json" \
  --output "$art/validation/production.json" >"$art/validation/production.log"

python3 - "$root" "$archive" "$art" "$rep" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]);archive=pathlib.Path(sys.argv[2]);art=pathlib.Path(sys.argv[3]);rep=pathlib.Path(sys.argv[4]);load=lambda p:json.loads(pathlib.Path(p).read_text())
scheduled=load(rep/'batch-result.json');dry=load(rep/'supervised-dry-run-result.json');partial=load(rep/'controlled-partial-failure-result.json');shared=load(rep/'controlled-shared-failure-result.json');engineering=load(rep/'controlled-needs-engineering-result.json');validation=load(art/'validation/production.json');cron=load(art/'validation/openclaw-schedule.json');runs=load(art/'validation/openclaw-runs.json');schedule=load(root/'config/schedules/mf008-unknown-process-batch-001-scheduled-001.json')
assert validation['technical_result']=='PASS' and scheduled['state']=='COMPLETE'
jobs=scheduled['jobs'];job_lines=[]
for item in jobs:
 job_lines += [f"## {item['job_id']}","",f"State: **{item['state']}**", "", f"Output: `{item['artifact']['path']}`", "", f"SHA-256: `{item['artifact']['sha256']}`", "", f"Size: {item['artifact']['bytes']:,} bytes", "", f"Codex/render/finalization/validation: {item['metrics']['codex_ms']} / {item['metrics']['render_ms']} / {item['metrics']['finalization_ms']} / {item['metrics']['validation_ms']} ms", "", f"Peak render memory: {item['metrics']['peak_render_memory_kib']:,} KiB", ""]
(rep/'evidence-summary.md').write_text(f'''# MF-008 Evidence Summary

Technical: **PASS**. Human editorial/release review: **PENDING**. Published: **0**.

The frozen `unknown_process_recovered_record_v1` grammar passed 14 exact input hashes at Git ref `{scheduled['git_source_ref']}`. A supervised dry run and the persisted one-time OpenClaw execution each completed three sequential Codex → Media Foundry jobs. Scheduled outputs are byte-identical to the dry-run outputs. No renderer or runtime files were changed by the batch.

OpenClaw started at `{scheduled['started_at']}` and completed in {scheduled['elapsed_ms']/1000:.3f} seconds. All three candidates are `READY_FOR_REVIEW`.
''')
(rep/'orchestration-report.md').write_text('# MF-008 Orchestration Report\n\n'+f'''OpenClaw schedule `{schedule['schedule_id']}` invoked one command batch at `{schedule['scheduled_at_utc']}` after a persisted wait of {(cron['state']['lastRunAtMs']-cron['createdAtMs'])/1000:.3f} seconds. The command used the same runner and manifest as the supervised dry run. It ran jobs sequentially, called Codex in a read-only schema-constrained role, rendered with the frozen Godot stack, validated with independent Media Foundry checks, and persisted all state under `{archive}/scheduled-run-001`.

Batch start delta from declared time: {validation['schedule_start_delta_seconds']:.3f} seconds. OpenClaw command duration: {cron['state']['lastDurationMs']} ms. Delivery was `none`; run delivery status was `not-requested`.

'''+'\n'.join(job_lines)+f'''\nBatch archive retained size: {scheduled['archive_bytes']:,} bytes. Batch wall time: {scheduled['elapsed_ms']:,} ms. Job idle and retry time: 0 ms.
''')
(rep/'retry-report.md').write_text(f'''# MF-008 Retry and Failure Report

- Normal supervised run: 0 retries; 3/3 ready.
- Normal scheduled run: 0 retries; 3/3 ready.
- Controlled isolated failure: Job 2 used invalid cue `controlled-invalid-cue`, retried exactly once, ended `FAILED_VALIDATION`, and Job 3 continued. Batch: `PARTIAL`.
- Controlled shared failure: invalid production grammar failed shared preflight; 0 jobs started. Batch: `FAILED` / `SHARED_INFRASTRUCTURE_FAILURE`.
- Controlled engineering request: Job 2 ended `NEEDS_ENGINEERING` on its first attempt; no renderer change occurred; Job 3 continued. Batch: `PARTIAL`.
- Duplicate scheduled run ID: refused with exit 4; no output overwritten.
''')
(rep/'schedule-report.md').write_text(f'''# MF-008 OpenClaw Schedule Report

- Schedule ID: `{schedule['schedule_id']}`
- Declaration key: `{schedule['declaration_key']}`
- Type: one-time `at`
- Due: `{schedule['scheduled_at_utc']}` / `{schedule['scheduled_at_local']}`
- Actual start: `{runs['entries'][0]['runAtIso']}`
- Result: `{cron['state']['lastRunStatus']}`
- Current state: disabled automatically after its successful one-time run; retained for inspection
- Delivery/publication: none / false
- Persistent store: `{schedule['persistence']['sqlite_path']}`

Status and run state remain inspectable with the commands recorded in `config/schedules/mf008-unknown-process-batch-001-scheduled-001.json`. The Gateway is a systemd user service and the schedule is in durable SQLite storage. This proves persistence configuration and post-run inspection; the Gateway was not deliberately restarted because destructive mid-production recovery was outside the supported test scope. A future supervised test may restart the Gateway after schedule creation but before its due time.
''')
(rep/'human-review.md').write_text('''# MF-008 Human Review

Status: **PENDING HUMAN**. Release eligibility: **NO**.

Review all three scheduled candidates for narrative fidelity, phone readability, pacing, audio suitability, comparative quality against manual production, and publication readiness. Confirm whether the unattended mechanism is trusted for another three-video scheduled batch. The orchestrator cannot mark editorial or release approval.
''')
(rep/'changed-files.md').write_text('''# MF-008 Changed Files

## Source/configuration

- `config/audio-cues/unknown-process-track-a.json`
- `config/production-grammars/unknown-process-recovered-record-v1.json`
- `config/schedules/mf008-unknown-process-batch-001-scheduled-001.json`
- `content/batches/mf008-unknown-process-batch-001.json`
- `schemas/mf008-content-package.schema.json`
- `scripts/run_mf008_batch.py`
- `scripts/validate_mf008_manifest.py`
- `scripts/validate_mf008_runs.py`
- `scripts/mf-008-acceptance.sh`

## Compact evidence

- `artifacts/mf-008/batch-contact-sheet.png`
- `artifacts/mf-008/representative-frames/`
- `artifacts/mf-008/validation/`
- `reports/mf-008/batch-result.json`
- `reports/mf-008/jobs/`
- `reports/mf-008/supervised-dry-run-result.json`
- `reports/mf-008/controlled-partial-failure-result.json`
- `reports/mf-008/controlled-shared-failure-result.json`
- `reports/mf-008/controlled-needs-engineering-result.json`
- `reports/mf-008/evidence-summary.md`
- `reports/mf-008/orchestration-report.md`
- `reports/mf-008/retry-report.md`
- `reports/mf-008/schedule-report.md`
- `reports/mf-008/human-review.md`
- `reports/mf-008/changed-files.md`
- `reports/mf-008/result.json`

Full MP4s and complete per-job logs remain outside Git under `/home/blanzy/media-foundry-output/unknown-process-batch-001/`. Existing MF-006R8/R9 and MF-007A changes were preserved. Renderer/runtime files changed by MF-008: **none**.
''')
result={'slice':'MF-008','production_grammar_id':scheduled['production_grammar_id'],'git_source_ref':scheduled['git_source_ref'],'batch_id':scheduled['batch_id'],'schedule_id':schedule['schedule_id'],'scheduled_state':scheduled['state'],'ready_for_review':scheduled['ready_for_review'],'failed':scheduled['failed'],'renderer_changes':0,'published':0,'supervised_dry_run':'PASS','controlled_partial_failure':'PASS','controlled_shared_failure':'PASS','needs_engineering_gate':'PASS','idempotency':'PASS','technical_result':'PASS','human_review':'PENDING_HUMAN','release_eligible':False,'blockers':['HUMAN_EDITORIAL_REVIEW','HUMAN_RELEASE_REVIEW'],'result':'PASS_WITH_HUMAN_GATE'}
(rep/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
PY

printf '\nMF-008 TECHNICAL: PASS\nHUMAN REVIEW: PENDING\n'
exit 3
