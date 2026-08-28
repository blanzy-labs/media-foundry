# MF-018B-R4 Evidence Summary

## Outcome

MF-018B-R4 produced the requested final linework polish. The legacy partial teal perimeter beneath the R3 outline was suppressed, leaving one continuous closed perimeter around the sloped control-panel face. The panel shape, controls, information display, reactor, motion, and audio remain unchanged.

Independent validation reports `TECHNICAL_PASS`: 20 of 20 checks passed. Human ship review remains pending, so the candidate is not marked release-ready or published.

## Artifacts

- Preserved R3 baseline: `artifacts/mf-018b-r3/final-test.mp4`, SHA-256 `610ae3b11d3d70e8823876add19752421a8cb627872bc44bbfc07314c42af47a`
- R4 candidate: `artifacts/mf-018b-r4/final-test.mp4`, SHA-256 `930b0f8bcf264a1ec3af5778e92cdb1958a10de826a6b7c9d670fb88ffed7d2a`
- R4 scene: `godot/mf018b_r4_pulp_scene.tscn`, SHA-256 `90e3d617f22f4a7f173a396d0aaff26fcebd417b391089f0f3f5ef87c76a00d4`
- Contact sheet: `artifacts/mf-018b-r4/representative-frames/contact-sheet.png`
- Cleaned-panel closeup: `artifacts/mf-018b-r4/closeups/cleaned-control-panel.png`
- Problematic-edge closeup: `artifacts/mf-018b-r4/closeups/previously-problematic-left-edge.png`
- R3/R4 panel before-and-after: `artifacts/mf-018b-r4/comparison/r3-vs-r4-panel-closeup.png`
- Full-frame and motion comparisons: `artifacts/mf-018b-r4/comparison/`
- Machine-readable result: `reports/mf-018b-r4/result.json`

## Measured acceptance signals

- The generated SVG contains one clean perimeter and no legacy partial perimeter stroke.
- Teal linework pixels in the panel region decrease from 10,567 in R3 to 8,584 in R4, removing 1,983 pixels of doubled treatment.
- Three matched states contain zero changed pixels outside the control-panel outline region.
- Gauges, dials, startup lever, all four dots, information display, and reactor are pixel-identical to R3.
- R3 and R4 share the identical AAC bitstream, MD5 `f7b5cbdc40dc8096de8738c04ba2491f`.
