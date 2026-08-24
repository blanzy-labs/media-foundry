# MF-006 Post-Change Regression

Executed after the MF-006 renderer and duration-validator changes on 2026-08-24:

- MF-001: PASS
- MF-002: PASS
- MF-002R1: PASS
- MF-003: PASS
- MF-004: PASS
- MF-005: PASS
- MF-005R1: PASS
- MF-005R2: PASS
- MF-005R3: PASS
- MF-PILOT-001: PASS
- MF-005R4 generated-world/audio subgate: PASS; release remains intentionally blocked on production voice

The first R1 attempt timed out because three orphaned Godot layout-validation workers from prior runs had consumed CPU continuously for 17–23 hours. Those exact stale processes were terminated. R1, R2, R3, and R4 were rerun under normal resources and passed their applicable gates. No validation threshold or timeout was weakened.
