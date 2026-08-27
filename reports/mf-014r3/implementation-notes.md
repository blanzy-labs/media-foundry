# MF-014R3 implementation notes

MF-014R3 is additive to MF-014R1 and does not import or reuse the R2 supporting-text stage. `scripts/metal_circuit_burn_stage_r3.py` subclasses the frozen R1 visual stage and adds two connected material operations: a permanent cold stamped state and a later thermal activation.

## Cold stamped state

The type mask is an internal geometry source, not the final appearance. The visible material is produced from:

- underlying plate pixels displaced one pixel horizontally and two vertically inside the recess;
- deterministic distress driven by the plate texture plus fixed-frequency wear variation;
- separate irregular upper shadow and lower metal-response edges;
- low-opacity char inside the depression.

Because both positive and negative edge changes exist before activation, the phrase behaves as a recessed surface feature rather than an element with zero opacity waiting to appear.

## Thermal activation

A short branch starts on an exact point from R1's existing `right_lower` circuit and approaches the top-right of the stamp. It uses the established hot-front treatment. The phrase then activates spatially from right to left: a narrow hot edge crosses the distressed recess, activated steel chars permanently, and a lower-energy copper rim remains after cooling. Reveal visibility is therefore caused by local material-state changes, not a uniform alpha fade.

## Configurability

`config/mf014r3-thermal-recessed-tagline.json` controls exact copy, display lines, lower-right position and bounds, scale, recess intensity, cold visibility, heat start, propagation, settle timing, active heat, final edge warmth, thermal-route geometry, and final hold.

The first R3 candidate proved thermal causality but failed final legibility. It is preserved at `/home/blanzy/media-foundry-output/mf014r3-pre-final-legibility-failure`. The canonical candidate uses a compact two-line stamp and a stronger permanent scorched rim; it passes material and readability validation without approaching title brightness.
