# MF-012 changed-file inventory

## Renderer integration

- `godot/activity_vocabulary_stage.gd` (new)
- `godot/mf002.gd` (modified)
- `godot/lofi_book_stage.gd` (modified)
- `godot/extended_data_window_stage.gd` (modified)

## Activity contract and baseline

- `config/activity-vocabulary/visual-activity-v1.json`
- `config/production-baselines/mf011-golden.json`
- `schemas/mf012-activity.schema.json`

## Demonstration fixtures

- `content/fixtures/mf012/01-moving-target-pursuit.json`
- `content/fixtures/mf012/02-record-reconstruction.json`
- `content/fixtures/mf012/03-signal-bridge.json`
- `content/fixtures/mf012/04-override-reroute.json`
- `content/fixtures/mf012/05-cascade-failure.json`

## Automation and validation

- `scripts/build_mf012_demos.py`
- `scripts/run_mf012_demos.py`
- `scripts/validate_mf012_activity.py`
- `scripts/test_mf012_failures.py`
- `scripts/validate_mf012_regression.py`
- `scripts/package_mf012_evidence.py`

## Packaged evidence

- `reports/mf-012/` (10 report files, including this inventory)
- `artifacts/mf-012/demos/` (5 final demonstration MP4s)
- `artifacts/mf-012/representative-frames/` (20 representative PNGs)
- `artifacts/mf-012/motion-evidence/` (5 motion-strip PNGs)
- `artifacts/mf-012/validation/` (per-demo and aggregate machine evidence)
- `artifacts/mf-012/demo-contact-sheet.png`

No MF-012 change was made to the music catalog, cue-region workflow, batch scheduler, orchestration, campaign-manifest architecture, text pipeline, or `config/visual-grammar.json`.

MF-011 files visible in the working tree predate this slice and remain separate, uncommitted work; they are not counted as MF-012 changes here.
