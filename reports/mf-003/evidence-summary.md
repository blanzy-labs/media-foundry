# MF-003 Evidence Summary

## Result

Technical acceptance: **PASS**. Human visual review remains pending.

Repeatable command: `./scripts/mf-003-acceptance.sh`

## Implementation

MF-003 adds an optional media object to the existing fixture contract and one reusable `ScrappyMediaSlot`. The shared renderer selects the media branch when validated media is present and otherwise follows the unchanged primitive-visual path. No subject, fixture ID, or brand has custom renderer code.

Images and screenshots are loaded directly after independent format/dimension validation. MP4 sources are inspected with FFprobe and their requested time range is normalized by FFmpeg into a bounded 30fps sequence. Godot preloads the selected sequence and advances it from the existing content-stage entrance, avoiding decoder-dependent timing in headless production.

The canonical v1 treatment reuses the scratched metal frame, adds a dark inset, inner shadow, deterministic scratches, and restrained glass glare. Media remains legible inside a 360×252 safe rectangle. Captions use MF-002R1 responsive label fitting.

## Capability fixtures

| Fixture | Source | Behavior | Result |
|---|---|---|---|
| image-fixture | 800×800 PNG | contain, centered, slow push | PASS |
| screenshot-fixture | 1280×720 PNG | cover, top anchored, gentle pan | PASS |
| video-fixture | 640×360 MP4, 8 seconds | start 2s, select 5s, muted, cover | PASS |

Each produced a 15-second, 1080×1920, 30fps H.264/AAC MP4 and passed full decode, text layout, source/crop geometry, timeline, and media visibility-state validation.

## Regression results

- MF-001 acceptance: PASS.
- MF-002 acceptance, including reproducibility: PASS.
- MF-002R1 acceptance and all six production fixtures: PASS.
- MF-003 acceptance rechecked all six existing fixtures with no media: PASS.
- A full no-media fact video rerender and decode: PASS.

No suitable reviewed, relevant Turd Burglar/books/Mythadis source artwork was present under a source-media convention. Per scope, no branded artwork was fabricated. The three deterministic capability assets therefore provide the production-independent media proof.

## Failure tests

All required cases fail closed with `MEDIA_ASSET_FAILED` and stage-specific diagnostics:

- missing image
- corrupt image
- unsupported format
- missing video
- MP4 with no video stream
- invalid start offset
- requested clip beyond source duration
- malformed media configuration

Machine evidence is in `reports/mf-003/failure-tests.json`.

## Evidence

- Three-video contact sheet: `artifacts/mf-003/contact-sheet.png`
- Main frames: `artifacts/mf-003/frames/*-main.png`
- Video timing comparison: `artifacts/mf-003/frames/video-timing.png`
- Selected source frames and manifest: `artifacts/mf-003/normalized/`
- Input, slot, layout, FFprobe, and output results: `artifacts/mf-003/validation/`
- Final machine result: `reports/mf-003/result.json`

## Limitations

- One media asset is supported in the canonical main slot; there is no multi-slot editor or arbitrary compositing graph.
- Video inputs are muted, normalized to 30fps PNG frames, and held on their final selected frame after the requested segment ends.
- The bounded preload trades memory for deterministic playback; the five-second 640×360 fixture peaked near 210MB for the Godot process.
- Images use metadata-driven anchors only; there is no focal-point analysis.
- Validation proves structure, geometry, timing, and technical media integrity—not aesthetic or semantic quality.

## Recommendation

**Technical PASS; proceed to the MF-003 human review gate.** The next human-directed slice should be a real-asset production pilot (book, game, or Mythadis media) to validate content-authoring ergonomics before adding any broader timeline capability.
