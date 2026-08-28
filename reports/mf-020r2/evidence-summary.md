# MF-020R2 evidence summary

MF-020R2 is a focused geometry-level correction of the upper reactor-ring lamp array. The slice passes its independent alignment gate (18/18 checks) and final media gate (9/9 checks). The resulting candidate is `READY_FOR_HUMAN_REVIEW`; it is not approved, release-ready, or published.

## Root cause

The rejected implementation calculated an apparent screen-facing ellipse with explicit world-space coordinates: `x` and `z` varied by angle while every lamp used the same `y`. The lamps therefore were not registered to the real horizontal upper-ring plane and read as floating dots as perspective changed.

## Correction

One `upper_ring_lamps` parameter block now drives nine evenly spaced transforms in `UpperRingAssembly` local space. The hierarchy is `ReactorRoot -> UpperRingAssembly -> LampArcRoot -> UpperRingLamp_NN`. One shared bulb mesh and one shared socket mesh are instanced for all lamps. Each socket is oriented radially and penetrates the authoritative 1.82-unit cap surface; the emissive bulb remains at the lamp origin.

## Key evidence

- Debug arc: `artifacts/mf-020r2/debug/lamp-arc-overlay.png`
- High-resolution anchor close-up: `artifacts/mf-020r2/debug/anchor-closeup.png`
- Fixed-camera states: `artifacts/mf-020r2/proof/lamps-off.png`, `lamps-half.png`, `lamps-all.png`
- Rejected/corrected frames: `artifacts/mf-020r2/comparison/before.png`, `after.png`
- Side-by-side: `artifacts/mf-020r2/comparison/before-after.png`
- Final candidate: `artifacts/mf-020r2/final-test.mp4`
- Alignment result: `artifacts/mf-020r2/validation/alignment.json`
- Final validation: `artifacts/mf-020r2/validation/final.json`

The final artifact SHA-256 is `af74ae892c56bc1ac5c8790d4a36b2d8330d46175b2762ad98900d7617cdc6b8`.

## Scope boundary

The production camera, reactor design, lighting scheme, event timing, title behavior, and approved music selection were preserved. The earlier broad MF-BENCH-001 composition validator currently reports `BLOCKED_COMPOSITION` because its dormant-frame bright-pixel threshold fails. This is recorded without bypass; MF-020R2 changes no unrelated lighting to force that separate gate green.
