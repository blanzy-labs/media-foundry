# MF-008C Mechanism Validation

| Fixture | Tracking | Classification/link | Biometric scan | Required events |
|---|---|---|---|---|
| `mf008c-tracking-pursuit` | PASS | NOT_RUN | NOT_RUN | `target_search`, `target_reacquire`, `target_lock` |
| `mf008c-classification-mystery` | NOT_RUN | PASS | NOT_RUN | `leo_resolve`, `zeph_resolve`, `bridge_attempt`, `bridge_stable` |
| `mf008c-biometric-revelation` | NOT_RUN | NOT_RUN | PASS | `biometric_scan`, `deep_scan`, `hidden_region`, `kill_switch_reveal` |

Every event was observed during its full 840-frame render. The independent output validator compared the requested fixture mechanism, exact event list, observed Godot report, and exclusivity matrix. All checks passed.

The renderer-source hash set was identical after every fixture:

- `godot/indicator_pulse_stage.gd`: `505e5b30000998786800356804832125abb656291a66a68d1a6f8449ed594051`
- `godot/lofi_book_stage.gd`: `0b2e1bf729c32c1cd6c52068def97cf71b04a266bef246093b0604a32f2dd950`
- `godot/mf002.gd`: `296d69385011454ad2aa1f0c15d8bb9043879178bf9c47513b50cdf4f63a4d76`
