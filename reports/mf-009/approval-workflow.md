# MF-009 Approval Workflow

Refresh and validate:

```bash
./scripts/music-catalog-refresh.sh --json
./scripts/music-catalog-validate.sh --json
```

Approve an exact discovered source version:

```bash
./scripts/music-catalog-approve.sh unknown-process abandoned_intake \
  --reviewer "reviewer-name" --note "Approved for catalog use" --json
```

Reject while retaining history:

```bash
./scripts/music-catalog-reject.sh unknown-process abandoned_intake \
  --reviewer "reviewer-name" --note "Not a campaign fit" --json
```

Query production eligibility:

```bash
./scripts/music-catalog-query.sh unknown-process --json
./scripts/music-catalog-query.sh unknown-process --require-approved-regions --json
```

Approval recomputes the source SHA-256 and refuses missing or hash-mismatched files. It binds `approved_sha256` to the current bytes and records reviewer, note, timestamp, and history. Rejection clears production eligibility. A later byte change moves approval to `REVIEW_REQUIRED`; refresh never restores approval for different bytes.

Cue-region approval remains direct, human-reviewed catalog configuration in MF-009. Validation requires an approved region hash to equal the current approved track hash. The recommended next slice should add deterministic proposal and explicit region-approval commands without automatic approval.
