# MF-018B Audio Events

## Delivered promo mix

- Source: `media/audio/music/unknown-process/Cold_Concrete_Anatomy.mp3`
- Track and `revelation_a` cue status: `APPROVED`
- Source SHA-256: `44a3b01e4039a7dab21170814cb75a6d662701182b548fab211f89e9922b8ecf`
- Excerpt: 5.0–19.0 seconds
- Measured: −16.03 LUFS integrated, −2.78 dBTP, 5.0 LU loudness range

The promo remains music-led and does not embed new dedicated SFX. This avoids introducing unapproved sources.

## Callable event inventory

- `machine_wake`
- `reactor_unstable`
- `critical_tease`
- `steam_release`
- `control_dial`
- `switch_toggle`
- `lever_clunk`

`reactor_unstable`, `critical_tease`, and `lever_clunk` emit through `audio_event_requested`. The remaining hooks are declared callable bindings for a future consumer. They currently resolve to the approved music asset as a package-safe fallback; a later audio-quality slice may bind approved object-specific SFX without changing the scene API.
