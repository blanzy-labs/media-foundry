# MF-008B-R1 Evidence Summary

Technical result: **PASS**. Batch state: **COMPLETE**. Three of three jobs are `READY_FOR_REVIEW`. Human editorial/release status: **PENDING**.

The canonical scheduled run is `scheduled-run-002` under `/home/blanzy/media-foundry-output/mf008b-r1/directed-batch-001/`. It used OpenClaw's healthy scheduled-batch context, sequential execution, one frozen grammar, three bounded creative profiles, and three hash-bound approved music regions. No narration or publication occurred.

Acceptance summary:

- frozen grammar: `unknown_process_recovered_record_v2`
- source Git ref: `8f4cbae5e1125ae8b95f894f3f45dbab6a730a25`
- grammar file SHA-256: `a5020243b8687681a25ff9bd8e5d99b7aa2a523c489bec12bc0e19f720c11314`
- pinned renderer/control files: 15/15 PASS
- music catalog SHA-256: `e738ed273be867eca34ea677f1b469a62b049947f3007822b7233b6219410f4b`
- approved library observed at preflight: 4 tracks, 20 regions
- exactly three sequential jobs: PASS
- mechanism exclusivity: PASS for all jobs
- creative profiles loaded: PASS for all jobs
- music source hashes, approvals, cue bounds, offsets, fades, and mixes: PASS
- final audio/video decode and artifact hashes: PASS
- renderer state before/after: identical; renderer changes: 0
- published: 0

The first preliminary archive (`scheduled-run-001`) was cancelled before producing a candidate after unrelated stale host load caused a technical timeout. The orchestration timeout was increased, without renderer or creative changes, and the canonical run completed all jobs on attempt 1.

Compact evidence is in `artifacts/mf-008b-r1/`; full MP4s remain in the external archive.
