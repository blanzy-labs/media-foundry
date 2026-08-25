# Cue-Region Contract

A cue region is a flexible approved range, not a fixed-duration clip. `usable_start` and `usable_end` define its allowed span; `preferred_entry` and `preferred_exit` are advisory musical points inside that span. Overlap with other regions is valid. Regions must be at least 10 seconds long and remain within the current track duration.

Each proposal records bounded mood and use-case tags, narration friendliness, intensity, deterministic analysis evidence, human notes/edit state, and an independent approval object. A proposal begins `PENDING_APPROVAL`. Track approval does not approve its regions. Region approval is allowed only when the track is approved and both approvals bind to the exact current source SHA-256.

Production selection uses `mf010_music_selection_v1` and records track ID/hash, region ID, approved bounds, actual start/end, video duration, fade-in, and fade-out. Actual offsets must remain inside the approved region; duration is flexible and is never required to equal the full cue-region length.

Allowed region states are `UNREVIEWED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, and `REVIEW_REQUIRED`. Source changes set both previously reviewed track and cue regions to `REVIEW_REQUIRED` and clear their approved hashes.
