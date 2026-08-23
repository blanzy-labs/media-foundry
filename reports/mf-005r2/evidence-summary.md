# MF-005R2 Evidence Summary

## Result

Technical validation: **PASS**. Human audio/editorial review remains **PENDING**.

The supplied `Clockwork_Heist.mp3` is used verbatim as the source. Its first 15 seconds are selected deterministically, normalized to -24 LUFS, reduced by 3 dB, faded over 0.45/1.0 seconds, and ducked by 8 dB on the exact four narration windows. The completed mix targets -16 LUFS and -1.5 dBTP; measured output is -16.4 LUFS and -1.5 dBTP.

`It is called Turd Burglar.` now plays inside the active `TURD BURGLAR` reveal beat. Existing beat-derived intro, text, emphasis, transition, and outro cues remain present. Authentic gameplay media is unchanged. Visual renderer changes: **0**.

## Evidence

- Final candidate: `artifacts/mf-005r2/turd-burglar.mp4`
- Before/after videos and reveal comparison: `artifacts/mf-005r2/before-after/`
- Audio timeline: `artifacts/mf-005r2/timelines/turd-burglar-audio.json`
- Waveform/activity evidence: `artifacts/mf-005r2/audio/waveforms/`
- Independent validation: `artifacts/mf-005r2/validation/turd-burglar-final-mix.json`
- Controlled failures: `reports/mf-005r2/failure-tests.json`

Machine checks establish structure, timing, decoding, levels, and thresholds; they do not establish subjective mix quality. Review the final MP4 with sound enabled, ideally on a phone.
