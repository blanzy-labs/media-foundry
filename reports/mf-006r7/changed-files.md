# MF-006R7 Changed Files

This is the exact MF-006R7 slice manifest. Pre-existing uncommitted MF-006R3–R6 work and validation outputs are outside this list.

## Implementation and fixture

- `content/fixtures/mf006r7-unknown-process.json` — new R7 fixture; R6 timing, story, music, and SFX preserved
- `godot/lower_right_polish_stage.gd` — new R7-only visual stage
- `godot/mf002.gd` — route the R7 fixture to the R7 stage
- `godot/beat_timeline.gd` — recognize the R7 strategy in the existing extended timeline family
- `godot/lofi_book_stage.gd` — recognize the R7 strategy in existing duration handling
- `godot/projected_data_window_stage.gd` — recognize the R7 strategy in existing projected-window behavior
- `scripts/preflight_mf004.py` — recognize the R7 strategy in existing preflight rules
- `scripts/mf-006r7-acceptance.sh` — new R7 acceptance path
- `scripts/mf-006r7-failure-tests.py` — new R7 fail-closed mutation suite
- `scripts/validate_mf006r7_contract.py` — new R7 contract validator
- `scripts/validate_mf006r7_production.py` — new R7 production validator

Renderer architecture changes: **0**. Audio, narration, camera, runtime, beat timings, projected window, story content, and CTA timings changed: **0**.

## Baseline archive and progress index

- `artifacts/mf-006-history/iteration-07/README.md`
- `artifacts/mf-006-history/iteration-07/candidate.mp4` — relative symlink to the preserved R6 candidate
- `artifacts/mf-006-history/iteration-07/contact-sheet.png` — relative symlink to the preserved R6 contact sheet
- `artifacts/mf-006-history/current-baseline/README.md`
- `artifacts/mf-006-history/current-baseline/candidate.mp4` — updated relative symlink to R6
- `artifacts/mf-006-history/current-baseline/contact-sheet.png` — updated relative symlink to R6
- `reports/mf-006-history/progress-showcase.md`

## R7 review reports

- `reports/mf-006r7/evidence-summary.md`
- `reports/mf-006r7/result.json`
- `reports/mf-006r7/composition-polish-review.md`
- `reports/mf-006r7/release-review.md`
- `reports/mf-006r7/candidate-comparison.md`
- `reports/mf-006r7/failure-tests.json`
- `reports/mf-006r7/regression-summary.md`
- `reports/mf-006r7/changed-files.md`

## Generated R7 artifact tree

- `artifacts/mf-006r7/candidate-a.mp4`
- `artifacts/mf-006r7/contact-sheet.png`
- `artifacts/mf-006r7/audio/`: `final.wav`, `sfx.wav`
- `artifacts/mf-006r7/music/`: `production.wav`, `reference.wav`
- `artifacts/mf-006r7/frames/`: `00-ambient.png`, `01-overload.png`, `02-projection.png`, `03-simon.png`, `04-pair.png`, `05-biometric.png`, `06-return.png`, `07-cta-start.png`, `08-cta-packet.png`, `09-cta-lock.png`, `10-url.png`, `11-final.png`
- `artifacts/mf-006r7/motion-evidence/`: `00-000006.png`, `01-000049.png`, `02-000092.png`, `03-000135.png`, `04-000178.png`, `05-000221.png`, `06-000263.png`, `07-000306.png`, `08-000349.png`, `09-000392.png`, `10-000435.png`, `11-000478.png`, `12-000521.png`, `13-000564.png`, `14-000607.png`, `15-000650.png`, `16-000692.png`, `17-000735.png`, `18-000778.png`, `19-000821.png`, `sequence.png`
- `artifacts/mf-006r7/timelines/`: `execution.json`, `motion.json`, `music.json`, `narration.json`, `preflight.json`
- `artifacts/mf-006r7/validation/`: `contract.json`, `ffprobe.json`, `layout.json`, `mix.json`, `output.json`, `production.json`, `sfx.json`, `timeline.json`
- `artifacts/mf-006r7/logs/`: `contract.log`, `encode.log`, `failure-tests.log`, `mix.log`, `music.log`, `preflight.log`, `production.log`, `render-metrics.txt`, `render.log`, `sfx.log`

The MF-004 and MF-006R6 reruns also refreshed their normal generated reports/artifacts. Those are regression outputs, not R7 implementation changes.
