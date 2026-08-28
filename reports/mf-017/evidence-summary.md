# MF-017 evidence summary

## Outcome

`TECHNICAL_PASS` with `PRODUCTION_PLATE_PENDING` and human review pending. The development proof is valid, but the generated plate is `REVIEW_REQUIRED` and the system correctly reports `release_ready: false`. No full trailer was rendered and nothing was published.

- Strategy contract: `config/mf017-pulp-visual-source.json`
- Contract implementation: `scripts/visual_source_contract.py`
- CLI: `scripts/visual_source_validate.py`
- Schema: `schemas/mf017-visual-source.schema.json`
- Development plate: `media/visual/plates/mf017/pulp-lab-development-v1.png`
- Plate SHA-256: `5fa2143ec5a71b57307835bbfc09940adbbf48929cb90fd271e680053a924aa5`
- Provenance: generated with the built-in image-generation tool from the supplied cover as art-direction reference
- Seed for deterministic overlays: `1701957`

All independent checks and all 11 isolated failure/compatibility tests pass. The proof uses matched four-second, 30 fps, 768 × 1152 animations. Godot supplies the reactor hero, incandescent lamps, local source reaction, particles, and steam to both candidates.

The hybrid proof measures `1.310×` mean gradient, `1.489×` high-frequency detail, and `2.616×` quantized color diversity relative to the procedural proof. Both preserve MF-016 hero hierarchy, and both contain measurable local motion.

## Evidence

- Machine result: `reports/mf-017/result.json`
- Failure tests: `reports/mf-017/failure-tests.json`
- Proof manifest: `artifacts/mf-017/proof-manifest.json`
- Static comparison: `artifacts/mf-017/comparison/side-by-side.png`
- Motion comparison: `artifacts/mf-017/comparison/side-by-side.mp4`
- Human review: `reports/mf-017/human-review.md`
