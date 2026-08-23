# MF-PILOT-001 Evidence Summary

## Result

Technical result: **PASS**. Human result: **PENDING**.

Repeatable command: `./scripts/mf-pilot-001-acceptance.sh`

## Production results

All three real-asset videos rendered through the existing `mf002.tscn` shared renderer and MF-003 `ScrappyMediaSlot`. Each passed source-media inspection, provenance, responsive text layout, slot geometry, media visibility state, 1080×1920 output, 30fps, 15-second duration, H.264/AAC streams, and full decode.

| Subject | Real asset | Presentation | Result |
|---|---|---|---|
| Books | Dark Signal cover, 1920×2571 | image, contain, slow push | PASS |
| Turd Burglar | gameplay promo screenshot, 1672×941 | screenshot, contain, slow push | PASS |
| Mythadis | approved social card, 1200×630 | screenshot, contain, gentle pan | PASS |

See `asset-inventory.md` for discovery candidates, selection rationale, source locations, hashes, and documented absences.

## Renderer and configuration changes

Renderer files changed for the pilot: **0**.
Visual grammar/configuration files changed for the pilot: **0**.
Subject-specific renderer branches: **0**.

Production additions were exactly three structured fixtures, three byte-identical source asset imports, one pilot acceptance/evidence workflow, and the resulting evidence. No defect required a renderer refinement.

## Production effort

| Subject | Fixture | Asset | Godot render | Finalization | Validation | Peak Godot | Failed renders |
|---|---:|---:|---:|---:|---:|---:|---:|
| Books | 1 | 1 | 15.41s | 15.30s | 0.65s | 204,380 KiB | 0 |
| Turd Burglar | 1 | 1 | 21.21s | 15.00s | 0.64s | 204,004 KiB | 0 |
| Mythadis | 1 | 1 | 15.21s | 14.18s | 0.64s | 198,704 KiB | 0 |

All fixtures passed layout/media preflight and their first production render. There were no pilot render failures to diagnose.

## Regression results

The preserved baseline reports are PASS for MF-001, MF-002, MF-002R1, and MF-003. The pilot acceptance checks these gates and applies the unchanged MF-002R1 and MF-003 independent validators to every pilot fixture.

## Media observations and limitations

- No authentic Turd Burglar gameplay video was available, so the video preload memory path was not exercised. Video-specific memory observation is therefore not applicable.
- The portrait Dark Signal cover must be narrower in the landscape slot to preserve the complete title/author treatment. It remains intact, but human review must judge phone readability.
- The Turd Burglar screenshot is visually effective in contain mode; cover would crop either branding or HUD.
- No authentic Mythadis application/Mission Control export was available. The approved social card is honest and recognizable, but proves project artwork integration rather than application-screen integration.
- The current template presents the main headline, body, media, and emphasis within one content stage. It cannot create additional subject-specific beats without expanding the shared timeline, which was outside this pilot.

## Visual consistency

The contact sheet shows three substantially different subjects sharing the same workshop, battered media frame, paper note, tape label, typography, motion, intro/outro, and audio grammar. The media differentiates the subjects without making the batch look like three unrelated templates.

## Architecture assessment

For this pilot, `new video ≈ content + assets` is demonstrably true at renderer level:

```text
3 fixtures + 3 real assets
            ↓
unchanged shared renderer
            ↓
3 validated MP4s
```

The remaining work is editorial selection, writing, provenance, and human taste—not per-video software implementation.

## Evidence

- Contact sheet: `artifacts/mf-pilot-001/contact-sheet.png`
- Videos: `artifacts/mf-pilot-001/books.mp4`, `turd-burglar.mp4`, `mythadis.mp4`
- Intro/media/content/outro frames: `artifacts/mf-pilot-001/frames/<subject>/`
- Input, renderer, slot, layout, FFprobe, and output validation: `artifacts/mf-pilot-001/validation/`
- Timings and logs: `artifacts/mf-pilot-001/logs/`
- Machine result: `reports/mf-pilot-001/result.json`

## Recommendation

Technical recommendation: **PASS**. Proceed to human review of all three full MP4s. Do not mark the production pilot accepted until a human decides whether each video is genuinely postable.

If the batch passes human review, the next slice should be an editorial production refinement focused on configurable content beats/pacing—not a new visual template. If any asset fails human review, first revise only its content/crop/asset selection through the existing contract.
