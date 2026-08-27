# Visual composition workflow

## Canonical principles

> No visual object without narrative, compositional, spatial, lighting, or atmospheric purpose.

> Do not solve emptiness by adding stuff.

> If a static frame does not work, animation is not authorized.

Complex scenes must pass through brief → semantic layout → static keyframes → machine validation → human review → animation. Motion, particles, lighting, and sound cannot rescue a weak static layout.

## When the gate applies

Set `complex_scene: true` or `composition.required: true` for scenes with multiple major environmental objects, foreground/midground/background layers, a procedural or animated hero, and substantial framing. Legacy and simple formats remain compatible and do not require the full contract unless opted in.

## Contract

Use `schemas/mf016-composition.schema.json` and the MF-016 manifest as the v1 example.

Each major object declares:

- stable `id`
- `semantic_role`
- one or more valid `purpose` values
- `visual_priority`
- `allowed_zone`
- normalized geometry
- `may_occlude` and `may_not_occlude`
- `remove_if_no_visual_purpose: true`

`fill_empty_space` is always invalid. Purely decorative objects deserve extra human scrutiny.

Semantic roles are `hero`, `primary_subject`, `support_subject`, `foreground_frame`, `background_structure`, `depth_element`, `light_source`, `story_prop`, `machine_support`, `atmosphere`, `text`, and `decorative`.

Valid purposes are `establish_scale`, `establish_depth`, `frame_hero`, `support_story`, `communicate_machine_state`, `provide_light`, `guide_eye`, `establish_location`, `create_foreground_depth`, and `support_perspective`.

## Zones and hierarchy

The v1 zone vocabulary is `hero_zone`, `support_zone`, `foreground_zone`, `background_zone`, `negative_space_zone`, `text_safe_zone`, and `no_occlusion_zone`. Coordinates are normalized to the canvas.

Every complex scene names a primary, secondary, and tertiary hierarchy. Hero and no-occlusion zones are protected by default. An overlapping object needs `occlusion_role: intentional`, a specific `occlusion_reason`, and permission for the exact protected zone.

Preserved negative space is a first-class element. Low occupancy, luma variance, edge density, and object count are advisory measurements—not proof of quality or failure.

## Guardrails

- Long line geometry crossing more than one major semantic zone requires explicit justification.
- Large, high-contrast foreground shapes require a framing, depth, or location purpose.
- Support zones declare recommended and hard capacity limits.
- Objects must remain inside their allowed zones and canvas bounds.
- Text-safe regions cannot be crossed by scene geometry.
- One strong support object is preferred to several unrelated props.

Potential tangent and perspective problems remain visible in the contact sheet for human judgment; v1 does not pretend these are solved by a brittle computer-vision score.

## Static keyframes and approval

Generate three to five keyframes that expose the important composition states. Review hero dominance, visual weight, foreground/background roles, occlusion, negative space, and whether the composition works without motion.

Machine success does not authorize animation. The manifest must also contain:

```json
{"approval": {"human_status": "APPROVED", "reviewer": "reviewer-id"}}
```

Run the integration hook before any complex-scene render:

```text
PYTHONPATH=scripts python3 scripts/composition_gate.py --manifest path/to/composition.json
```

Exit `0` authorizes animation. Exit `3` means `BLOCKED_COMPOSITION`. Production orchestration should call this before frame generation, not after audio or rendering.

## Repair workflow

Failures identify the appropriate layer: `COMPOSITION_OBJECT`, `COMPOSITION_OCCLUSION`, `COMPOSITION_HIERARCHY`, `COMPOSITION_DENSITY`, `COMPOSITION_PERSPECTIVE`, or `COMPOSITION_TEXT_SAFETY`.

Repair by removing or repositioning weak objects, resizing an existing support element, changing framing, or preserving negative space. Never add an object automatically. Any new object requires a declared purpose and must pass the gate again.

The approval package also exposes future critic categories: hierarchy, occlusion, balance, visual noise, depth, purpose, negative space, perspective, and readability. A future independent visual critic can consume these artifacts without changing v1 human authority.
