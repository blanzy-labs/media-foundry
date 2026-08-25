# MF-009 Evidence Summary

Technical result: **PASS**. Human workflow acceptance: **PENDING**.

`media/audio/music/<project>/` is now the automatic discovery root. The canonical refresh discovered all four Unknown Process masters, inspected them with FFprobe, hashed them with SHA-256, assigned deterministic project-aware IDs, and created `UNREVIEWED` records. No track or cue was automatically approved.

A second refresh produced an identical catalog hash and reported four unchanged tracks. Catalog validation passes with four non-eligible warnings and no errors. Production query returns an empty approved list. Four repeated live refreshes left all source hashes unchanged.

The isolated seven-test suite passes new-track discovery, second-run idempotency, unsupported-file ignore behavior, human-metadata preservation, approved-source change invalidation, missing approved assets, normalized-ID collision, corrupt audio, overlapping approved cue regions, invalid cue bounds, and rejection exclusion.

The OpenClaw integration point performs refresh → validation → requested-track eligibility. With no music request it remains `READY` despite four unreviewed tracks. Requesting `abandoned_intake` stops at `BLOCKED_APPROVAL` / `MUSIC_TRACK_NOT_APPROVED`.

The project music masters are local-only and ignored. Catalog/config/schema/evidence are source-controlled. A clone without masters will receive `MISSING_LOCAL_ASSET` rather than a downstream media error.
