# MF-014 validation

## Technical result

**TECHNICAL_PASS**

- Source SHA-256 matches the preserved render-manifest identity.
- Idle frame is pixel-identical to the source after the deterministic 768-pixel-wide resize.
- Output is a fully decodable H.264 MP4 at 768 × 1154, 30 fps, 270 frames, and 9.000 seconds.
- Four paths satisfy the requested two-to-five path bound.
- Active traversal is independently measurable: 2.315% of pixels differ from idle by more than the threshold.
- Persistent aftermath is independently measurable: 3.582% of settled pixels remain changed.
- Active and settled coverage remain below the validator's bounded-noise limits.
- The render manifest explicitly records `published: false`.

Machine-readable details are in `reports/mf-014/result.json`.

## Visual acceptance review

| Question | Assessment |
|---|---|
| Heat burning into metal | PASS — white-hot fronts leave dark channels with warm rims. |
| Paths integrated into material | PASS FOR TEST — grooves and tempered edges remain after traversal. |
| Title remains dominant | PASS — no title reconstruction or broad cover layer is used. |
| Cinematic rather than gimmicky | PASS — restrained bloom and sparse sparks; no flames, HUD, or lens flare. |
| Clean enough for future use | PASS FOR REFINEMENT — the module is parameterized and the result is controlled. |
| Excessive visual noise avoided | PASS — four paths and locally bounded accents only. |
| Worth refining | YES — prioritize groove irregularity and localized heat distortion. |

The visual assessment is evidence-based but does not replace human creative approval. Final creative status remains **PENDING_HUMAN**.
