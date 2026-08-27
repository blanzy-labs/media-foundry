# MF-012R1 micro-variation contract

The contract is an optional `micro_variation` object on the existing indicator-pulse renderer. Omitting it preserves the legacy path.

Guardrails:

- 1–3 unique channels from `indicator_dots`, `background_tiles`, and `floating_ring_dot`.
- At most one major motion element and three simultaneous minor accents.
- Colors restricted to amber, purple, green, and blue.
- Reactive indicator events are short, independently scheduled, and non-chasing.
- Three to eight active tiles from 54 visible tiles (5–15%), with at most 0.12 overlay alpha and no protected-zone intersection.
- Ring radius 4–14 px, maximum configured speed 18 px/s, explicit path and safe rectangle, and no protected-zone intersection.
- Required positive seed, deterministic `mf012r1_lcg_v1` schedule, and a hash signature over the recorded schedule.
- Music on; SFX, ambient audio, and narration off.

The JSON schema is `schemas/mf012r1-micro-variation.schema.json`. Independent semantic checks are implemented in `scripts/validate_mf012r1.py`.

Protected regions cover the main projection/story text, CTA/URL/author block, and emitter/indicator row. Safe-zone failure is explicit and fail-closed.
