# MF-019 Performance Report

| Measure | Godot Candidate A | Blender Candidate B |
| --- | ---: | ---: |
| Recorded total | 41,829 ms | 102,823 ms |
| Preflight | Not available for reused baseline | 602 ms |
| Static build/render | Not available | 1,964 ms |
| Scene build | Not available | 360 ms |
| Frame render | Not available | 97,153 ms |
| Finalization | Not available | 2,744 ms |
| Final MP4 | 2,563,750 bytes | 991,231 bytes |
| Temporary frames | 0 bytes retained for reused artifact | 340,916,063 bytes |
| Peak memory | Not available | 859,348 KB |

The Blender recorded total was approximately 2.46× the prior Godot total. This is a tradeoff measurement, not a failure criterion. The Godot stage timings and peak memory cannot be reconstructed from the reused approved artifact and are reported as unavailable rather than estimated.

The resume proof scanned and reused all 420 valid PNGs, rendered zero frames, and completed in 348 ms. The primary Blender run rendered 420 frames with no resumed frames.

Machine-readable evidence: `artifacts/mf-019/validation/performance.json` and `artifacts/mf-019/validation/blender-resume-performance.json`.
