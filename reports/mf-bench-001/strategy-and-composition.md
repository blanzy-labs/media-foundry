# MF-BENCH-001 strategy and composition decision

## Decision

- Backend: `BLENDER`
- Visual-source strategy: `PROCEDURAL`
- Fallback: prohibited
- Reference use: art direction only; the cover is not embedded

The benchmark needs a new physical environment with a causal gauge, mounted relays, containment rings, internal energy, practical lighting, and a real pressure vent. Its illustration requirement is low because the reference supplies mood rather than pixels. Its geometric precision, motion, lighting, and depth requirements are high. The repository's formal source assessment therefore recommends `PROCEDURAL`.

Blender is selected from the existing backend contract because this is one non-interactive cinematic shot that benefits from procedural 3D construction, worn materials, perspective depth, transparent containment geometry, and bounded glow. Godot interactivity and A/B parity are not required.

## New scene layout

The composition is not copied from an existing artifact. A central-right self-starting induction chamber is the hero. An unattended witness console on the left is the only major support object. A mounted relay spine on the right communicates cause and effect. The upper-left inspection volume remains deliberately empty, and a shallow threshold establishes foreground depth without obstructing the chamber.

The machine sequence is:

```text
pilot signal -> gauge movement -> relay chain -> containment lamps -> internal process -> pressure vent -> identity
```

No human is present and no operator control initiates the sequence.

## Gate status

The semantic composition manifest passes machine validation, and the static package contains four states at 768x1152. The user rejected the first lamp composition and explicitly directed the focused MF-020R2 correction and affected-shot rerender. That rerender is a review candidate, not composition approval.

After the lamp correction, the broad static validator reports 10/11 checks and `BLOCKED_COMPOSITION`: `opening_hook_readable_not_dead_black` misses its bright-pixel threshold in the dormant frame. The focused slice does not change unrelated lighting to force that check green. Human review remains pending, and this report does not impersonate approval.
