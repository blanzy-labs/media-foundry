# MF-008B-R2 Evidence Summary

Technical result: **PASS**. Human A/B decision: **PENDING**.

Three byte-preserved MF-008B-R1 controls and three music-only variants are archived under `/home/blanzy/media-foundry-output/mf008b-r2/music-only-ab-001/`. Candidate B was created by stream-copying the exact Candidate A H.264 video and replacing only the audio stream. No picture render occurred.

For all three pairs:

- Candidate A full-file SHA-256 exactly matches its R1 candidate
- A/B video-stream SHA-256 is byte-identical
- frame count, frame rate, runtime, representative decoded frame, music track, cue region, offsets, gain, and fades match
- Candidate A SFX events: 13
- Candidate B SFX events: 0
- Candidate B audio sources: one approved R1 music stem; no ambience, narration, or new audio event
- full audio/video decode: PASS
- loudness difference: 0.4–0.9 LU
- renderer changes: 0
- visual changes: 0
- published: 0

Candidate B inherits Candidate A's measured master-stage loudness parameters. It was not independently normalized to win through extra loudness. Compact waveform, timeline, representative-frame, and validation evidence is under `artifacts/mf-008b-r2/`.

The three stale, regenerable MF-006R5/R6/R7 frame scratch directories in `/tmp` were deleted after the temporary filesystem quota was reached. No repository evidence, source master, or archived production candidate was removed.
