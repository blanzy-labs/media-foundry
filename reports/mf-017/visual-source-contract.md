# MF-017 visual-source contract

The contract supports `PROCEDURAL`, `PLATE`, `HYBRID`, and `AUTHENTIC_MEDIA`, bounded `LOW`/`MEDIUM`/`HIGH` requirements, `FAST`/`STANDARD`/`CINEMATIC` quality intent, reasoned human override, explicit fallback, immutable source hashes, approval states, crop/safe-zone policy, animated regions, and layer ownership.

Fail-closed states include:

| Condition | Result |
| --- | --- |
| Complex scene missing strategy | `BLOCKED_VISUAL_SOURCE` |
| Unknown strategy | `BLOCKED_VISUAL_SOURCE` |
| Required plate missing | `MISSING_APPROVED_PLATE` |
| Approved plate hash changed | `REVIEW_REQUIRED` |
| Unreviewed plate requested for production | `BLOCKED_APPROVAL` |
| Undeclared strategy fallback | `SILENT_STRATEGY_FALLBACK_PROHIBITED` |
| Authentic source missing | `MISSING_AUTHENTIC_MEDIA` |

The current development plate is intentionally `REVIEW_REQUIRED`. Its hash, provenance, dimensions, prompt, reference hash, protected regions, animated regions, and ownership plan are recorded in the config and plate metadata.
