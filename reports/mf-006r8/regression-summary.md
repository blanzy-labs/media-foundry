# MF-006R8 Regression Summary

## MF-006R7

- Acceptance path: `scripts/mf-006r7-acceptance.sh`
- Expected status: `PASS_WITH_BLOCKER` / exit 3
- Observed status: `PASS_WITH_BLOCKER` / exit 3
- Technical validation: **PASS**
- Reproduced SHA-256: `0a8a2e2ae923ddc98a7411b9b0c449ce6b71b1dbb8d04e74aa6f6ac05c85f063`

## MF-004

- Acceptance path: `scripts/mf-004-acceptance.sh`
- Observed status: **PASS** / exit 0
- Fixtures: `turd-burglar` PASS, `books` PASS, `venus` PASS
- Failure tests: **PASS**
- Venus SHA-256: `ef5c8d38114bd95bf313c47fef857521126afaf7edfb2c2f8ac020e496d73347`

## Conclusion

The R8 correction preserves the R7 baseline byte-for-byte and does not regress the shared MF-004 renderer path.
