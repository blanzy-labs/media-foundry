# Approval Workflow

Human approval is explicit and hash-bound:

```bash
./scripts/music-catalog-approve.sh unknown-process abandoned_intake --reviewer NAME --note "Track approved"
./scripts/music-cue-approve.sh unknown-process abandoned_intake pursuit_a --reviewer NAME --note "Cue approved"
```

Reject a proposal without deleting its evidence:

```bash
./scripts/music-cue-reject.sh unknown-process abandoned_intake pursuit_a --reviewer NAME --note "Reason"
```

Edit metadata or bounds; every edit returns the region to `PENDING_APPROVAL`:

```bash
./scripts/music-cue-edit.sh unknown-process abandoned_intake pursuit_a \
  --usable-start 110 --usable-end 150 --preferred-entry 116 --preferred-exit 149 \
  --notes "Adjusted after listening"
```

List or query only approved, current regions:

```bash
./scripts/music-cue-list.sh --project unknown-process --approved
./scripts/music-catalog-query.sh unknown-process --require-approved-regions --mood pursuit --use-case tracking
```

Record a production subsection only after track and cue approval:

```bash
./scripts/music-cue-select.sh unknown-process abandoned_intake pursuit_a \
  --actual-start 116 --actual-end 138 --video-duration 22 --fade-in 0.5 --fade-out 1
```

The intended scheduled path is refresh → catalog validation → track eligibility → cue eligibility → creative-brief match → `READY`. Pending/rejected/stale approval states stop at `BLOCKED_APPROVAL`.
