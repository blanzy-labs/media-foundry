# MF-018B-R3 Evidence Summary

## Outcome

MF-018B-R3 produced a focused 14-second native-scene refinement. The existing upper-left dark surface now functions as a sequenced in-world display for `UNKNOWN PROCESS`, `TRY A WEB GAME`, and `rcblanzy.com/books/unknown-process`. The overall sloped console outline is complete, the prior lower rectangular border remains absent, and the unused L-shaped reactor pipe is removed.

Independent validation reports `TECHNICAL_PASS`: 24 of 24 checks passed. Human review remains pending. The candidate is not release-ready or published, and no gameplay was implemented.

## Artifacts

- Preserved R2 baseline: `artifacts/mf-018b-r2/final-test.mp4`, SHA-256 `0f9411777e1bd61b592e84ddf53d1c0c7f51e7b009aa51bb060c0e63c0c3e099`
- R3 candidate: `artifacts/mf-018b-r3/final-test.mp4`, SHA-256 `610ae3b11d3d70e8823876add19752421a8cb627872bc44bbfc07314c42af47a`
- R3 scene: `godot/mf018b_r3_pulp_scene.tscn`, SHA-256 `80c4e632e97a86e3ba68a548b1984d88f1aedc5f4bfe5de0175e9f36f814c711`
- Contact sheet: `artifacts/mf-018b-r3/representative-frames/contact-sheet.png`
- Information-display closeup: `artifacts/mf-018b-r3/closeups/upper-left-information-panel.png`
- Completed-outline closeup: `artifacts/mf-018b-r3/closeups/completed-control-panel-outline.png`
- Artifact-removal closeup: `artifacts/mf-018b-r3/closeups/l-shaped-artifact-removed.png`
- Static and eight-second motion comparisons: `artifacts/mf-018b-r3/comparison/`
- Machine-readable result: `reports/mf-018b-r3/result.json`

## Measured acceptance signals

- Title, CTA, and URL reveal at 7.10, 8.35, and 9.55 seconds.
- Complete messaging holds for 3.65 seconds before the 14-second endpoint.
- High-contrast display-pixel counts are 2,453 for the title, 758 for the CTA, and 1,116 for the URL.
- Matched R2/R3 frame changes have zero pixels outside the three requested regions.
- Gauges, dials, startup lever, all four dots, chamber, and upper ring are pixel-identical to R2 in the matched active frame.
- R2 and R3 use the identical AAC bitstream, MD5 `f7b5cbdc40dc8096de8738c04ba2491f`.
