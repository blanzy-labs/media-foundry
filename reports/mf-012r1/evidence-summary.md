# MF-012R1 evidence summary

Technical result: **TECHNICAL_PASS**. Human creative review: **PENDING_HUMAN**. Publication count: **0**.

| Pair | Treatment | Channels | Seed | Active tiles | Indicators | Ring | Refined SHA-256 |
|---|---|---|---:|---|---|---|---|
| video-01 | restrained | `indicator_dots`, `background_tiles` | 121201 | 3 (5.6%) | stable_indicators | disabled | `8439ed7fe925ae5f25cfd6eba850fa56d1aa858b12e76e9a8bd9fb897bfb31a5` |
| video-02 | reactive | `indicator_dots`, `background_tiles`, `floating_ring_dot` | 121202 | 5 (9.3%) | reactive_colored_indicators | slow_hover | `6cec1371761738b0c579054418dde2666105485afdc34c1cf067ed1103071403` |

Both refined outputs preserve their source runtime, frame count, wording, beat timing, CTA, title, author, URL, music configuration, track, approved cue, actual offsets, gain, fades, and music-only policy. The original AAC packet payload and decoded audio hashes are identical in each A/B pair.

Both configurations pass safe-zone and motion-budget validation. Both rendered frame trees reproduce byte-identically on a second run. Both original fixtures still reproduce their archived MF-011 phase-3 frame byte-for-byte without micro controls. Six required failure cases pass.

No behavior is yet production-approved because human review is pending. Large crossing tracers, central-web geometry, screen-wide flashes, and motion over text were excluded by design and are recorded as rejected/noisy patterns.

Recommendation: hold the five-video test. If human review approves at least two behavior types and both pairs remain cleaner and more distinctive, test stable/reactive indicators and sparse tile shifts broadly; keep the ring/dot conditional on its cursor-like-motion review.

The initial unsupported headless attempt is preserved outside the repository at `/home/blanzy/media-foundry-output/mf012r1/guardrailed-micro-variation/run-000-headless-failure` and was not used as acceptance evidence.
