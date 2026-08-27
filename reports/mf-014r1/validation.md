# MF-014R1 validation

## Result

**TECHNICAL_PASS**

- MF-014 video and source hashes remain unchanged.
- The idle frame is pixel-identical to the deterministically resized source plate.
- Six configured paths begin outside the viewport and finish inside the bounded title region.
- Six distinct start times provide controlled stagger; every traversal completes by 6.4 seconds.
- Title heat starts during convergence, reaches peak at 8.2 seconds, holds for 1.0 second, settles to configured level 0.5 by 10.4 seconds, and holds for 1.6 seconds.
- Measured title-region red intensity is 93.250 at peak versus 83.285 settled; settled and final differ by only 0.264, confirming the held ending.
- Final MP4 is H.264/AAC, 768 × 1154, 30 fps, 360 frames, and 12.000 seconds; full decode passes.
- Approved track and cue hashes/bounds pass against the current catalog.
- Audio passes at −16.07 LUFS, −3.95 dBTP, and 4.2 LU loudness range.
- No output was published.

Machine-readable details are in `reports/mf-014r1/result.json`.

## Visual assessment

**READY_FOR_HUMAN_REVIEW**

The left/right/top/bottom arrivals visibly extend from beyond frame. Six paths are materially stronger than MF-014's four without creating intersections or a dense circuit-board field. They occupy more negative space, so the human reviewer should specifically judge whether the increase is appropriately dramatic or one path too many.

The title remains the warmest broad element at peak and clearly reduces into a still-active residual state. The final paths remain darker than the title and read as scorched channels. Music supports the pacing by staying restrained during entry and rising with the hero event.

These observations do not constitute human creative approval.
