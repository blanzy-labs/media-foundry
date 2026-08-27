# MF-011 Runtime Boundary Correction

The preserved first campaign attempt ended `PARTIAL`: 10 jobs were attempted, 6 reached `READY_FOR_REVIEW`, and 4 exhausted their one permitted technical retry.

The cause was a preflight contract mismatch. Frozen grammar metadata and the inherited creative validator advertised 24–32 seconds, while the unchanged Godot production stage accepts 26–30 seconds. Jobs configured at 24, 25, 31, and 32 seconds therefore failed deterministically.

MF-011's new shared preflight was tightened to the existing 26–30-second renderer boundary, the four manifest timings and approved music subsections were shortened or extended within their approved cue bounds, and all ten timeline preflights were rerun before canonical Run 002.

- Run 001 archive: `/home/blanzy/media-foundry-output/mf011/unknown-process-v1/campaign-run-001`
- Run 001 state: `PARTIAL` (6/10 ready)
- Run 002 state: `COMPLETE` (10/10 ready)
- Renderer changes: `0`
- Visual grammar changes: `0`
- Music source/catalog changes: `0`

The failed attempt is retained as evidence rather than hidden or overwritten.
