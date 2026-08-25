# MF-006R9 Regression Summary

## MF-006R8

- Acceptance path: `scripts/mf-006r8-acceptance.sh`
- Expected status: `PASS_WITH_BLOCKER` / exit 3
- Observed status: `PASS_WITH_BLOCKER` / exit 3
- Technical validation: **PASS**
- Reproduced SHA-256: `8f1e515736baef3535d3686a699096e5bbd9cc22917447d3e0e6f3909ef67031`

## MF-004

- Acceptance path: `scripts/mf-004-acceptance.sh`
- Observed status: **PASS** / exit 0
- Fixtures: `turd-burglar` PASS, `books` PASS, `venus` PASS
- Failure tests: **PASS**
- Venus SHA-256: `ef5c8d38114bd95bf313c47fef857521126afaf7edfb2c2f8ac020e496d73347`

## Conclusion

The R9 indicator-only overlay preserves R8 byte-for-byte and does not regress the shared MF-004 renderer path.
