# MF-016 validator results

## Results

- Semantic contract: 17/17 checks passed.
- Isolated failure/compatibility suite: 11/11 tests passed.
- Independent evidence validator: 18/18 checks passed.
- Overall: `TECHNICAL_PASS`.
- Composition state: `COMPOSITION_PENDING`.
- Animation: not authorized.

The rejection suite covers missing roles, missing purposes, `fill_empty_space`, unmotivated hero occlusion, unmotivated cross-scene lines, excessive support density, and pending human approval. Positive regressions cover intentional negative space, valid human authorization, simple-format compatibility, and complex-scene gate selection.

Independent visual metrics confirm pixel-identical deterministic rerendering, increasing state progression, hero brightness dominance, contact-sheet integrity, and absence of a generated video.

Canonical machine-readable results are in `reports/mf-016/result.json` and `artifacts/mf-016/validation/failure-tests.json`.
