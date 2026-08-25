# MF-009 Git and Music Storage Policy

The three legacy music files at `media/audio/music/` root are already tracked in normal Git. MF-009 does not migrate or rewrite them.

Project-scoped masters under `media/audio/music/*/` are local-only immutable inputs and are ignored by `.gitignore`. The current four files total approximately 17 MB and were not added to Git history. The catalog, hashes, provenance, schemas, tools, and compact evidence remain source-controlled.

Consequences:

- refresh never transcodes, renames, moves, tags, or rewrites masters;
- another machine must provision authorized masters at the catalog paths;
- catalog validation reports `MISSING_LOCAL_ASSET` when a master is absent;
- a future explicit storage decision may migrate masters to Git LFS or an approved asset store without changing catalog identity.
