# MF-006R7 Regression Summary

## MF-006R6 baseline

- Acceptance path: `scripts/mf-006r6-acceptance.sh`
- Expected status: `PASS_WITH_BLOCKER` / exit 3
- Observed status: `PASS_WITH_BLOCKER` / exit 3
- Technical validation: **PASS**
- Reproduced SHA-256: `ec24c997e7a6718d36ef4c5808c2227f8c072fcd079a184b1d8dc68cf22d9157`
- Known blockers: production voice, human editorial review, human release review

## MF-004

- Acceptance path: `scripts/mf-004-acceptance.sh`
- Observed status: **PASS** / exit 0
- Fixtures: `turd-burglar` PASS, `books` PASS, `venus` PASS
- Failure tests: **PASS**
- Venus SHA-256: `ef5c8d38114bd95bf313c47fef857521126afaf7edfb2c2f8ac020e496d73347`

## Conclusion

The R7-only composition polish did not alter the locked R6 candidate and did not regress the MF-004 production path.
