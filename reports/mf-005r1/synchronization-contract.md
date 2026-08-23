# MF-005R1 Synchronization Contract

The beat timeline is authoritative for visual state, visible text/media, narration, cues, and music ducking. Strict production fixtures declare `narration_sync_policy: semantic_beat`; older MF-005 fixtures retain `legacy_window` compatibility.

Every narration segment is owned by its containing beat ID. For `cut`, visible content is active for the full beat. For `slide` and `scrappy_pop`, the active interval excludes the shared ENTER and EXIT lifecycle durations. Narration begins after active start plus `lead_in`, and must finish before active end minus `tail_out` and `pause_after`. Cross-beat narration is prohibited and fails with `NARRATION_BEAT_SYNC_FAILED`.

`semantic_target: text` requires non-empty visible text in a text-bearing beat; `semantic_target: media` requires a media beat and reference. The explicit beat ID supplies semantic pairing; no inferred similarity scoring occurs. `pause_after` reserves an intentional silent interval inside the owning beat. Production fixtures reject missing approved media and known MF-003 capability-test assets.
