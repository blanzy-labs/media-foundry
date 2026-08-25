# MF-009 Scheduled-Batch Integration

OpenClaw should invoke this at batch start:

```bash
python3 scripts/music_catalog_batch_preflight.py \
  --project-root . \
  --project unknown-process \
  --request approved_track_id@approved_region_id \
  --output <run-directory>/music-catalog-preflight.json
```

The hook performs catalog refresh, catalog validation, and request eligibility in that order. Multiple `--request` values are supported. A request may omit `@region` for workflows that permit whole-track use.

New `UNREVIEWED` files are reported but do not block jobs using other approved music. Requested unreviewed/rejected tracks or unapproved regions produce `BLOCKED_APPROVAL`. Changed formerly approved sources produce `MUSIC_TRACK_REVIEW_REQUIRED`. Missing assets, unknown IDs, stale hashes, or invalid catalog data fail validation.

Existing batches are not automatically migrated in MF-009. Their next manifest revision should replace direct source/cue trust with this preflight and retain its JSON in the run evidence directory.
