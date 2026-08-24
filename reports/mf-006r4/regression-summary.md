# MF-006R4 Regression Summary

## MF-006R3 preserved baseline

- Command: `scripts/mf-006r3-acceptance.sh`
- Expected exit: `3` (technical pass with production-voice and human-review blockers)
- Actual exit: `3`
- Visual/audio technical result: **PASS**
- Reproduced SHA-256: `0fc1a90b662693fda9f70c7cc445fd95316caba8221426be9f57b1c668474ba3`
- Preservation result: **PASS**

## Shared MF-004 path

- Command: `scripts/mf-004-acceptance.sh`
- Expected exit: `0`
- Actual exit: `0`
- Timeline/render/validation/contact sheet/failure tests: **PASS**
- Shared-renderer compatibility: **PASS**
- Human pacing review: **PENDING**

The R4-only 30-second allowance did not broaden duration acceptance for existing fixture strategies.
