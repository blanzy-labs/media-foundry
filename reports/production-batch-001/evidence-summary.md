# Production Batch 001 — Books, Mythadis, and Venus

## Assessment

**TECHNICAL PASS / HUMAN REVIEW PENDING.** The accepted `scrappy-diorama-v1` grammar and shared MF-002 renderer produced three independently valid videos for creative promotion, research technology, and educational space content.

The output remains recognizably Media Foundry across all three subjects. Content is fixture data; there are no books, Mythadis, or space scenes or renderers.

## Fixtures created

- `content/fixtures/production-batch-001-books.json`
- `content/fixtures/production-batch-001-mythadis.json`
- `content/fixtures/production-batch-001-venus.json`

Each fixture supplies copy, a deterministic seed, palette, label, outro tagline, and a list of generic physical props. All three select the existing `scrappy_diorama` template and the same `prop_board` media region.

## Content and source decisions

No approved R.C. Blanzy cover artwork was found in accessible project assets. The books video therefore uses clearly illustrative battered books, a glowing note, and no fabricated cover or title.

Mythadis uses the canonical local project positioning, “coordinate intelligence—not just computation,” expressed through a question/plan/evidence field board rather than a futuristic AI interface.

The Venus fixture records [NASA Science's Venus facts](https://science.nasa.gov/venus/venus-facts/) as its source. The video uses the concise approximate values requested: a 243-Earth-day rotation relative to the stars and a roughly 225-Earth-day orbit.

## Renderer changes

The shared `godot/mf002.gd` renderer gained one reusable, data-driven `prop_board` illustration mode with nine generic prop primitives:

- glow
- book
- note
- connecting line
- droplet
- planet
- star
- counter
- telescope

It also gained a fixture-controlled outro tagline and moved the shared top-left tape to the paper edge after visual review showed overlap with wide headlines. The net renderer change is 89 added and 2 removed lines. No subject-specific scene, script, renderer, template, external service, or AI-video system was added.

## Assets used

- Existing bundled Lato Heavy and Regular fonts under OFL-1.1
- Existing scrappy workshop, sign, paper, metal, tape, crate, cable, lamp, motion, and audio grammar
- Deterministic Godot-drawn physical props
- No external raster images, book covers, generated video, or branded asset fabrication

## Technical validation

Every video independently passed MP4 readability, 1080×1920 resolution, vertical orientation, 15.000-second duration, 30 fps, H.264 video, AAC audio, and complete FFmpeg decode.

The complete MF-002 acceptance suite was also rerun against the enhanced renderer in isolated temporary directories. All original fixtures, contact-sheet generation, validation, and the byte-identical repeat-render gate passed without modifying the accepted MF-002 evidence package.

| Video | Size | Godot render | Full production | SHA-256 |
|---|---:|---:|---:|---|
| books | 2,317,925 bytes | 11.217 s | 25.517 s | `f14bbb02cc8f879030d9d7767ec2f02d95db8cbda7d66c6c1bfc7ad57eee4c82` |
| mythadis | 2,462,806 bytes | 11.418 s | 25.533 s | `1f5e1e47d251898dfd0daf2ed29685d909a639ded1d8314c943f16c2c7acb47c` |
| venus | 2,557,720 bytes | 11.117 s | 25.327 s | `e9f47a505ee2546f4aa4f3635623556a4f4156e9e972ad409919ea7465a38950` |

Full production time includes audio generation, Godot frames, H.264/AAC encoding, independent validation, full decode, and three evidence-frame extractions. Timing is workstation-specific.

## Evaluation

- **Consistency:** PASS. Workshop, physical surfaces, typography, intro, outro, motion, and audio remain visibly shared.
- **Flexibility:** PASS with a small reusable capability addition. One prop vocabulary covers books, an investigation board, and an observatory.
- **Content separation:** PASS. Copy and prop composition live in JSON; presentation stays in the shared renderer and grammar.
- **Visual interest:** PASS for structural review. Books glow, notes/droplet bob, stars pulse, Venus wobbles, and the telescope sways in addition to stage motion.
- **Phone readability:** PASS for implementation review after moving tape away from headline text. Human review remains authoritative.
- **Production effort:** Three fixtures, one 89-line net renderer enhancement, one content validator, and one batch acceptance/evidence script. No bespoke media code was required.

## Evidence

- `artifacts/production-batch-001/books.mp4`
- `artifacts/production-batch-001/mythadis.mp4`
- `artifacts/production-batch-001/venus.mp4`
- `artifacts/production-batch-001/contact-sheet.png`
- `artifacts/production-batch-001/frames/{books,mythadis,venus}/{intro,main,outro}.png`
- `artifacts/production-batch-001/render-logs/`
- `artifacts/production-batch-001/validation/`
- `reports/production-batch-001/result.json`

## Limitations

- The books video cannot show real cover identity until approved artwork is supplied.
- The prop board is intentionally iconographic; it cannot yet ingest arbitrary approved images or screenshots.
- All six MF-002-era videos share the same workshop stage, which strongly supports recognition but may eventually constrain variety.
- The Venus wording uses “day” for the sidereal rotation period, matching the requested/NASA shorthand; a Venus solar day is a different value.
- The renderer still requires a display-backed Godot worker for frame capture.

## Content-driven assessment

Media Foundry is becoming genuinely content-driven: all three subjects use the same template, renderer, timing, animation system, audio system, finalizer, validator, and evidence flow. The batch did require one reusable media-region capability because the original three fixed illustration modes could not honestly represent these subjects. Future videos expressible with the nine prop primitives should now approach fixture-only production. Approved image/screenshot ingestion remains the clearest next capability boundary, but it was deliberately not implemented here.
