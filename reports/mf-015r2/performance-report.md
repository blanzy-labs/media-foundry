# MF-015R2 performance report

| Candidate | Render time | Relative to R1 |
| --- | ---: | ---: |
| MF-015R1 | 160,940 ms (160.94 s) | 1.0000x |
| MF-015R2 | 213,741 ms (213.74 s) | 1.3281x |

R2 added `52,801 ms`, a `32.81%` increase. It remains below the validator's `1.5x` practical campaign-render ceiling.

The incremental cost comes from additional alpha compositing and per-frame drawing for two vapor sources, sparse particles, light spill/shadow response, cable and containment movement, arcs, and the foreground instrument layer. Resolution, frame rate, runtime, encode profile, and total frame count are unchanged.

Final artifact size is `19,956,915` bytes. Full audio/video decode succeeded.
