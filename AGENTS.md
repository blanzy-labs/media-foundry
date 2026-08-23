# Media Foundry Agent Guide

## Purpose and authority

Media Foundry is an AI-operated, human-directed deterministic media-production system.

- Humans retain product, creative, branding, and publication authority.
- AI agents may propose and implement work only inside the active slice.
- Deterministic tools and validators decide whether generated media is valid.
- Generated media is a candidate artifact until deterministic validation passes.

## Working rules

- Preserve deterministic behavior and reuse the existing project architecture.
- Do not claim success without executing the applicable validation.
- Generated output must never determine its own validity; use independent validation.
- Keep dependencies and slice scope as small as possible.
- Preserve logs, reports, and compact evidence needed to reproduce a result.
- Fail closed: a missing, malformed, or failed stage invalidates acceptance.
- Never bypass, reinterpret, or explain away failed validation.
- Do not publish externally, access social accounts, or make autonomous content decisions.
- Do not modify unrelated slices or build speculative platform abstractions.
- Never commit credentials, caches, or unreviewed large intermediate media.
