# MF-007A Changed Files

## Source/configuration

- `.gitignore`
- `content/fixtures/mf007a-unknown-process-audio.json`
- `scripts/generate_mf007a_ambient.py`
- `scripts/validate_mf007a_production.py`
- `scripts/mf-007a-failure-tests.py`
- `scripts/mf-007a-acceptance.sh`

## Preserved/generated evidence

- `artifacts/mf-007a/candidate-a-music.mp4`
- `artifacts/mf-007a/candidate-b-ambient.mp4`
- `artifacts/mf-007a/timelines/ambient-events.json`
- `artifacts/mf-007a/timelines/audio-ab.json`
- `artifacts/mf-007a/validation/baseline.json`
- `artifacts/mf-007a/validation/candidate-a-ffprobe.json`
- `artifacts/mf-007a/validation/candidate-a-media.json`
- `artifacts/mf-007a/validation/candidate-b-ffprobe.json`
- `artifacts/mf-007a/validation/candidate-b-media.json`
- `artifacts/mf-007a/validation/human-review.json`
- `artifacts/mf-007a/validation/mix.json`
- `artifacts/mf-007a/validation/production.json`
- `artifacts/mf-007a/waveforms/ab-comparison.png`
- `artifacts/mf-007a/waveforms/candidate-a-music.png`
- `artifacts/mf-007a/waveforms/candidate-b-ambient.png`
- `reports/mf-007a/ambient-sound-contract.md`
- `reports/mf-007a/audio-ab-review.md`
- `reports/mf-007a/candidate-comparison.md`
- `reports/mf-007a/changed-files.md`
- `reports/mf-007a/evidence-summary.md`
- `reports/mf-007a/event-sfx-mapping.md`
- `reports/mf-007a/failure-tests.json`
- `reports/mf-007a/result.json`

Deterministic WAV stems and command logs under `artifacts/mf-007a/audio/` and `artifacts/mf-007a/logs/` are reproducible and ignored. Existing MF-006R8/R9 worktree changes were preserved. Godot, renderer, visual grammar, visual fixture, camera, and timeline-interpreter files changed by MF-007A: **none**.
