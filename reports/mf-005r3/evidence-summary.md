# MF-005R3 Evidence Summary

Technical gate: **PASS**. Editorial gate: **PENDING_HUMAN**. Release gate: **BLOCKED_VOICE_ASSET**.

## Current-quality diagnosis

MF-005R2 is structurally strong but not release-ready: its fade checks proved configuration rather than the applied stem envelope, all seven beats carried SFX, pacing retained a template-like rhythm, the supplied music entered over only 0.45 seconds, and the available Flite narration is a regression voice rather than appropriate comedy casting. R3 corrects the measurable/configurable layers and makes the voice limitation a hard release safeguard.

The complete MF-001 through MF-005R2 and real-asset pilot regression reran successfully before R3 implementation. Two controlled candidates were produced without renderer changes. Actual music-stem fades were compared sample-by-sample with deterministic no-fade references; both envelopes pass. Narration timing, spoken/visual product naming, SFX activity, loudness, peak, tail safety, layout, and full decode pass.

The only available narration is the deterministic Flite regression voice. It is now explicitly `test_only` and `release_eligible: false`; therefore neither candidate may be called publishable or selected as Golden Production Baseline v1. Human reviewers may still compare pacing, music, fades, SFX, gameplay emphasis, branding, and ending quality.

- Candidates: `artifacts/mf-005r3/candidate-a.mp4`, `candidate-b.mp4`
- Comparison: `reports/mf-005r3/candidate-comparison.md`
- Editorial timelines: `reports/mf-005r3/editorial-timeline.md`
- Stem/final waveforms: `artifacts/mf-005r3/waveforms/`
- Machine validation: `artifacts/mf-005r3/validation/`
- Failure evidence: `reports/mf-005r3/failure-tests.json`
