# MF-008C Cue-Map Status

| Cue | Status | Offset | Duration | Use |
|---|---|---:|---:|---|
| `baseline_full` | APPROVED | 0.0 s | 28.0 s | Used by all three engineering proofs |
| `pursuit` | PENDING_APPROVAL | null | 28.0 s | Blocked |
| `investigation` | PENDING_APPROVAL | null | 28.0 s | Blocked |
| `revelation` | PENDING_APPROVAL | null | 28.0 s | Blocked |

No musical cut points were invented. Existing `baseline_full` production remains compatible. A directed job requiring any pending cue fails preflight as `BLOCKED_APPROVAL` with `AUDIO_CUE_NOT_APPROVED`; it does not fall back silently.
