# MF-004 Beat Contract

MF-004 accepts a non-empty `beats` array. Timing is strictly sequential: each beat starts when the previous beat ends, and durations must sum exactly to `format.duration_seconds`. Configured videos are limited to 10–20 seconds; 15 seconds remains the default production target. Explicit start/end times, overlaps, and gaps are intentionally unsupported.

Supported types are `intro`, `statement`, `media`, `emphasis`, `reveal`, and `outro`. Supported transitions are `cut`, `scrappy_pop`, and `slide`; all use the shared ENTER/ACTIVE/EXIT lifecycle. Text beats are pre-fitted by the MF-002R1 safe-area system. Statements require at least 1.5 seconds, emphasis text is limited to 45 characters and at least 1 second, intro/outro require at least 1 second, and media requires at least 1.5 seconds.

Media beats use `media_ref`. A legacy single media object is named `default`; a fixture may instead identify one asset from a named media map. Preflight resolves every referenced file. Only one canonical media slot and one referenced asset per timeline are supported in this slice. Audio cues are selected from `intro_hit`, `text_pop`, `transition`, `emphasis`, and `outro_sting` and reuse the deterministic existing audio vocabulary.

Fixtures without `beats` use the unchanged legacy 15-second intro/content/outro path. Unknown types, malformed arrays, invalid durations, unsupported transitions or explicit timing, bad media/audio references, unreadable text density, or a duration-total mismatch fail before rendering.

Concise example:

```json
{
  "format": {"duration_seconds": 10},
  "media": {"type": "image", "source": "media/image.png"},
  "beats": [
    {"type": "intro", "text": "DID YOU KNOW?", "duration": 2},
    {"type": "media", "media_ref": "default", "duration": 5, "transition": "slide"},
    {"type": "outro", "text": "THE END", "duration": 3}
  ]
}
```
