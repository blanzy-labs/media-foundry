# MF-018B-R2 Evidence Summary

## Outcome

MF-018B-R2 produced a focused 14-second native-scene cleanup with exactly two visual changes: the right-side machine lever/valve assembly and its disconnected steam were removed, and the lower control-panel inner outline was removed while its face fill remained.

Independent validation reports `TECHNICAL_PASS`: 20 of 20 checks passed. Human review remains pending. The candidate is not release-ready or published, and no gameplay was implemented.

## Artifacts

- Preserved MF-018B-R1 baseline: `artifacts/mf-018b-r1/final-test.mp4`, SHA-256 `1910158da2dc5190626f3db55c682d0f44f2e87b0319334844c3f4b0aed10f56`
- R2 candidate: `artifacts/mf-018b-r2/final-test.mp4`, SHA-256 `0f9411777e1bd61b592e84ddf53d1c0c7f51e7b009aa51bb060c0e63c0c3e099`
- R2 native scene: `godot/mf018b_r2_pulp_scene.tscn`, SHA-256 `a8537d34ffb99e4c0b6b86f07312c391223e843acb0698c31f46503ff66c5dcb`
- Representative contact sheet: `artifacts/mf-018b-r2/representative-frames/contact-sheet.png`
- Lever-removal closeup: `artifacts/mf-018b-r2/closeups/right-machine-lever-removed.png`
- Panel-cleanup closeup: `artifacts/mf-018b-r2/closeups/control-panel-outline-removed.png`
- Preserved startup-controls closeup: `artifacts/mf-018b-r2/closeups/startup-controls-preserved.png`
- Static and eight-second motion comparisons: `artifacts/mf-018b-r2/comparison/`
- Machine-readable result: `reports/mf-018b-r2/result.json`

## Measured acceptance signals

- Four matched R1/R2 states contain zero changed pixels outside the two allowed cleanup regions.
- The panel region changes by 3,733–3,743 pixels in each matched state.
- The right-machine region changes by 4,332–7,437 pixels in each matched state.
- Matched gauge and upper-ring review regions are pixel-identical to R1.
- The R1 promo-driver SHA-256 remains `1a4f744aebd1e660ea3bd1cc41874c5d0f9d9651f7e22fe7a04cd248773040a7`.
- The R1 and R2 AAC audio streams have the same MD5: `f7b5cbdc40dc8096de8738c04ba2491f`.
- The final output is H.264/AAC, 768×1152, 30 fps, 420 frames, and 14.0 seconds.
