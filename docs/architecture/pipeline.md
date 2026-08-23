# Deterministic media pipeline

## Authority boundary

Media Foundry separates generation from validation. Godot and FFmpeg produce a candidate artifact; FFprobe plus a complete FFmpeg decode independently determine whether that candidate is valid. A failed required check produces `FAIL` and cannot be overridden by an agent claim.

```text
content/fixtures/mf001-demo.json
              |
              v
templates/did-you-know + godot/main.gd
              |
              v
450 deterministic 540x960 PNG frames at 30 fps
              |
              +---- deterministic generated WAV
              |
              v
FFmpeg scale, H.264 encode, AAC encode, MP4 mux
              |
              v
artifacts/mf-001/mf001-demo.mp4 (candidate)
              |
              v
FFprobe structure checks + FFmpeg full decode
              |
              v
reports/mf-001/result.json -> PASS or FAIL
```

## Determinism

Timing is an integer frame index, not wall-clock time. The fixture fixes 450 frames, 30 fps, and 15 seconds. Godot draws every visual from fixture data and fixed arithmetic. FFmpeg uses a fixed filter graph, single-threaded H.264 encoding, fixed GOP settings, and a fixed creation timestamp. Intermediate frames and audio are rebuildable and ignored; the compact final artifact, logs, probe data, and representative frames are retained as evidence.

The internal 540×960 canvas keeps rendering lightweight. FFmpeg is the canonical normalizer and scales the candidate to the contract's 1080×1920 output.

## Scope

MF-001 has one content contract and one template. The capability registry is metadata, not a plugin framework. There is no runtime dependency on Game Foundry and no `foundry-core`. Publishing, research, voice synthesis, multiple templates, and batch execution remain outside this slice.
