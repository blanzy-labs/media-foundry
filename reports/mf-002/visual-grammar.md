# Scrappy Diorama v1 visual grammar

## Identity

Media Foundry output should feel like a tiny, badly maintained indie-game workshop built from old signs, cheap props, tape, bolts, paper, and stubborn optimism. It is tactile, humorous, readable, and deliberately imperfect. The scene exists around the message; text is attached to physical surfaces instead of floating as ordinary UI.

The canonical machine-readable source is `config/visual-grammar.json`. This document explains the intent behind those constraints.

## Typography

The bundled type family is **Lato**, copyright Łukasz Dziedzic and distributed under SIL Open Font License 1.1. The repository retains Heavy and Regular weights plus the license notice.

- `INTRO`: Lato Heavy, 38 internal pixels, painted wooden sign.
- `HEADLINE`: Lato Heavy, 39 px, crooked paper note.
- `BODY`: Lato Regular, 23 px, short supporting copy on paper.
- `EMPHASIS`: Lato Heavy, 21 px, taped label with a punch motion.
- `LABEL`: Lato Heavy, 15 px, bolted metal plate.
- `OUTRO`: Lato Heavy, 42 px, painted workshop sign.

Copy must be short enough to remain readable at phone size. Hierarchy comes from weight, scale, contrast, and physical placement—not from decorative font proliferation.

## Surfaces and props

The v1 vocabulary is intentionally small: painted wood, paper notes, scratched metal plates, translucent tape, bolts, crates, a cable, a swaying lamp, and a worn workshop backing. Thick borders and offset shadows make shapes feel constructed. Coarse deterministic scratches and plank variation survive social compression better than fine photographic noise.

The reusable media frame accepts one of a small set of deterministic primitive illustrations. These are fixture data choices inside the shared renderer, not independent scenes.

## Motion

- `ENTER`: fast physical drop or decisive upward arrival.
- `SETTLE`: short back-ease overshoot with visible weight.
- `EMPHASIS`: brief 1.08× punch plus restrained idle wobble.
- `EXIT`: 0.32-second removal before the outro arrives.

The canonical intro slams a crooked wooden sign into the workshop, shakes on impact, throws fixed-seed dust, and settles. Environmental motion is restrained: a tiny camera drift/push, cable sway, lamp movement, and content-specific illustration motion.

## Timing

- 0.0–2.0 s: canonical intro and impact.
- 2.0–4.0 s: media stage enters and settles.
- 4.0–12.45 s: readable main content with an emphasis punch near 8 s.
- 12.45–12.8 s: decisive exit.
- 12.8–15.0 s: shared `(s)Crap²y Games` outro.

Every animation is derived from an integer frame index at 30 fps. There is no wall-clock timing.

## Audio

The grammar defines five generated, copyright-free cues: `INTRO_HIT`, `TEXT_POP`, `TRANSITION`, `EMPHASIS`, and `OUTRO_STING`. Short decaying tones and fixed-seed impact noise make them tactile and game-like. A very quiet workshop hum connects the phases. Frequencies, times, durations, and gains live in the grammar configuration.

## Controlled imperfection

Imperfection is explicit and reproducible: a global grammar seed, unique fixture seeds, −2° intro sign rotation, +1.1° headline rotation, uneven scratch coordinates, asymmetric prop placement, fixed label offsets, motion overshoot, and small bounded wobble. No uncontrolled random generator participates in rendering.

## Safe areas

The internal 540×960 composition reserves x=28–512 and y=48–912 for critical information, corresponding to 56–1024 and 96–1824 in the final 1080×1920 video. Text stays on high-contrast panels within this area. Crates, cables, grime, and lamp light may approach the edges because they are non-critical scenery.

## Anti-patterns

Avoid glossy gradients, pristine cards, glassmorphism, perfectly centered layouts, uniform easing, slow cinematic reveals, floating UI text, corporate music, generic stock illustrations, AI-video artifacts, excessive texture detail, long copy, and platform-specific calls to action. Do not turn the grammar into an exhaustive styling framework.

## Human gate

Technical validation proves structure and media integrity, not taste. A human reviewer decides whether the family is recognizably scrappy, readable, visually immediate, non-corporate, and good enough to post. MF-003 must not begin solely because MF-002 is technically green.
