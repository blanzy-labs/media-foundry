# MF-009 Catalog Schema and Field Ownership

Catalog: `config/music/catalog.json`
Schema: `schemas/music-catalog.schema.json`

Each record contains stable `id`, project-aware `qualified_id`, project, source path, discovery state, FFprobe technical metadata, integrity metadata, provenance, approval, editorial fields, cue regions, and lifecycle history.

## Machine-owned fields

- `id`, `qualified_id`, `project`, and `source`
- `discovery.status`, `first_discovered_at`, and `last_change`
- `technical` duration, codec, container, sample rate, channels, bitrate, and stream presence
- `integrity.sha256` and byte size
- lifecycle history entries created for source changes and missing assets

These fields are regenerated from filesystem bytes and FFprobe evidence. Refresh never reads them as human assertions.

## Human-owned fields

- `provenance`
- `approval`
- `editorial.mood_tags`, preferred uses, notes, and release eligibility
- `cue_regions`

Refresh preserves these fields. If source bytes change, prior approval is copied into history, track and cue approval hashes are cleared, and status becomes `REVIEW_REQUIRED`.

## Cue regions

Regions contain ID, usable start/end, optional preferred entry/exit, mood tags, notes, and a separate approval record bound to the current track hash. Overlap is allowed. Region length is independent of video length; downstream jobs may select a bounded subsection. Approved regions require an approved current track hash.
