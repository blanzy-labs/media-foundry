# MF-006R1 Changed Files

## Implementation and content

- `content/fixtures/mf006r1-unknown-process.json` — approved Unknown Process content, canonical destination, music/voice provenance, causal events, page beats, and SFX map.
- `godot/mf002.gd` — routes the explicit refinement preference to its stage; no timeline, grammar, validation, or renderer architecture redesign.
- `godot/lofi_book_stage.gd` — admits the documented cradle and causal event vocabulary while preserving the MF-006 stage.
- `godot/causal_book_stage.gd` — MF-006R1-specific causal circuits, central buildup/burst, physical book/pages, cradle, return flow, and integrated CTA.
- `scripts/generate_mf006_sfx.py` — adds deterministic circuit-draw, energy-flow, overload, and CTA-energy cues; existing cue behavior is unchanged.
- `scripts/validate_mf006r1_contract.py` — fail-closed approved-copy/provenance/destination/music/voice contract.
- `scripts/validate_mf006r1_production.py` — independent causality, physicality, CTA, timeline, audio, and media checks.
- `scripts/mf-006r1-failure-tests.py` — nine negative regression safeguards.
- `scripts/mf-006r1-acceptance.sh` — reproducible production and evidence path.

## Generated MF-006R1 evidence

- `artifacts/mf-006r1/candidate-a.mp4`
- `artifacts/mf-006r1/contact-sheet.png`
- `artifacts/mf-006r1/before-after.png`
- `artifacts/mf-006r1/audio/final.wav`
- `artifacts/mf-006r1/audio/sfx.wav`
- `artifacts/mf-006r1/music/production.wav`
- `artifacts/mf-006r1/music/reference.wav`
- `artifacts/mf-006r1/frames/` — 12 selected editorial frames.
- `artifacts/mf-006r1/motion-evidence/` — 20 sequential frames plus tiled sequence.
- `artifacts/mf-006r1/logs/` — contract, preflight, render, music, SFX, mix, encode, production, failure-test, and performance logs.
- `artifacts/mf-006r1/timelines/` — preflight, execution, music, narration-blocker, and motion evidence.
- `artifacts/mf-006r1/validation/` — contract, layout, timeline, SFX, mix, media, ffprobe, and production results.
- `reports/mf-006r1/result.json`
- `reports/mf-006r1/evidence-summary.md`
- `reports/mf-006r1/editorial-review.md`
- `reports/mf-006r1/visual-causality-notes.md`
- `reports/mf-006r1/candidate-comparison.md`
- `reports/mf-006r1/failure-tests.json`
- `reports/mf-006r1/changed-files.md`

The compatibility runs also refreshed existing generated MF-004 and MF-006 artifacts/reports. They are validation outputs, not MF-006R1 implementation changes. Unrelated pre-existing worktree changes were preserved.
