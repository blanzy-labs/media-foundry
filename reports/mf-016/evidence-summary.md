# MF-016 evidence summary

## Outcome

`TECHNICAL_PASS` with `COMPOSITION_PENDING`. Machine checks pass, but animation remains blocked until a human approves the static composition. No full video was rendered and nothing was published.

- Composition manifest: `config/mf016-pulp-composition.json`
- Config SHA-256: `53971df4c454268eb09c5d9715fae7fab6defd8979484888d318d643355b26ef`
- Schema: `schemas/mf016-composition.schema.json`
- Contract and gate: `scripts/composition_contract.py`
- Campaign integration CLI: `scripts/composition_gate.py`
- Seed: `1601957`

All 17 semantic-layout checks, 11 isolated contract tests, and 18 independent package checks passed. MF-015, MF-015R1, and MF-015R2 remain hash-identical to their frozen candidates.

## Static proof

Four deterministic 768 × 1152 keyframes cover dormant, wake, escalation, and peak states. The reactor/support brightness ratio rises from `1.410` to `1.977`, while the preserved negative-space region remains deliberately dark. The reactor is unobstructed in every state.

The corrected fixture removes the lower-left cross-scene pipe and pale rail/vertical-member system. It uses one properly placed analog control bank with breathing room instead of the additional crammed technology bank. No occupancy target was used.

## Evidence index

- Approval package: `artifacts/mf-016/composition-approval-package.json`
- Contact sheet: `artifacts/mf-016/composition-contact-sheet.png`
- Before/after: `artifacts/mf-016/before-after/problem-vs-corrected.png`
- Validator result: `reports/mf-016/result.json`
- Failure tests: `artifacts/mf-016/validation/failure-tests.json`
- Human review: `reports/mf-016/human-review.md`
