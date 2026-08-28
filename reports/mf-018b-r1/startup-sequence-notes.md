# MF-018B-R1 Startup Sequence

The base scene exposes `startup_progress`, `indicator_stage`, and `linked_ring_activation` as normalized external variables. The removable promo driver sequences them; no gameplay rule is embedded in the scene.

## Timeline

1. 0.0–1.15 s: dormant scene and vertical startup lever.
2. 1.15–2.25 s: red-knob lever rotates approximately 90° right.
3. 1.75 s: gauges begin responding while the lever is moving.
4. 2.75 s: four-dot blue wake sequence begins.
5. 4.15 s: four-dot progression changes to green.
6. 5.45 s: all four indicators reach yellow.
7. 5.72 s: six linked ring indicators begin ordered illumination.
8. 6.05 s onward: reactor energy escalates through stable, unstable, and critical states.

The strict timestamp ordering is independently validated. The yellow review frame precedes visible linked-ring growth, while the next ring frame gains 496 orange activation pixels.

## External signals

R1 adds:

- `startup_progress_changed`
- `indicator_stage_changed`
- `linked_ring_activation_changed`
- `startup_initiated`
- `yellow_trigger_reached`

The base scene loads and all new setters/signals operate with the promo driver absent.

## Audio timing

The approved `Cold Concrete Anatomy` mix remains unchanged at −16.03 LUFS and −2.78 dBTP. Event markers were remapped to the new startup chain, including lever clunk, gauge wake, colored stages, yellow trigger, and linked ring. No unapproved or dedicated SFX were added.
