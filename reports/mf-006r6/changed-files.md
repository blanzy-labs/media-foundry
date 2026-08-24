# MF-006R6 Changed Files

## Production source

- `content/fixtures/mf006r6-unknown-process.json`
- `godot/final_polish_stage.gd`
- `godot/mf002.gd`
- `godot/lofi_book_stage.gd`
- `godot/projected_data_window_stage.gd`
- `godot/beat_timeline.gd`
- `scripts/preflight_mf004.py`
- `scripts/generate_mf006_sfx.py`

Shared edits only register the named R6 strategy/events, preserve the existing scoped duration rules and one-window cable suppression, and add reusable low-fi confirmation sound types. Architectural changes: 0.

## Acceptance and validation

- `scripts/mf-006r6-acceptance.sh`
- `scripts/mf-006r6-failure-tests.py`
- `scripts/validate_mf006r6_contract.py`
- `scripts/validate_mf006r6_production.py`

## Preserved history

- `artifacts/mf-006-history/iteration-06/README.md`
- `artifacts/mf-006-history/iteration-06/candidate.mp4` and `contact-sheet.png` relative symlinks
- `artifacts/mf-006-history/current-baseline/README.md`
- `artifacts/mf-006-history/current-baseline/candidate.mp4` and `contact-sheet.png` now reference R5
- `reports/mf-006-history/progress-showcase.md`

## Generated R6 package

- `artifacts/mf-006r6/` — candidate, audio, frames, logs, motion evidence, music stems, timelines, and validation
- `reports/mf-006r6/` — evidence, motion/audio/final/release reviews, comparison, regressions, failure tests, changed files, and result

The existing stash and unrelated generated worktree changes were not applied, removed, staged, or committed.
