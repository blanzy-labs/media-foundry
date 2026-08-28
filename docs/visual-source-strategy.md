# Visual source strategy

## Canonical rules

> Godot is an animator/compositor first; it does not need to be the illustrator for every scene.

> Use a strong visual source when visual richness matters.

> Prefer HYBRID when a rich scene also requires meaningful motion.

> Do not animate a static image as a substitute for creating an animated scene.

> Never silently downgrade the visual-source strategy.

Visual-source assessment occurs before asset resolution and the MF-016 composition build. A plate does not bypass semantic layout or human composition approval.

## Strategies

- `PROCEDURAL`: geometric precision, repeated instruments, data/UI structures, circuits, gauges, abstract machinery, particles, typography, and animation-first scenes.
- `PLATE`: painterly or illustrative richness, organic complexity, worn surfaces, dense period environments, or primarily static artistic compositions.
- `HYBRID`: a strong plate supplies environment and material richness while Godot/compositing supplies meaningful local animation, light, atmosphere, and interaction.
- `AUTHENTIC_MEDIA`: the actual screenshot, photograph, cover, document, gameplay capture, or product image is itself required evidence.

Ratings are deliberately bounded to `LOW`, `MEDIUM`, or `HIGH` across surface complexity, illustration complexity, character complexity, geometric precision, motion, lighting, depth, and authenticity. Quality intent is `FAST`, `STANDARD`, or `CINEMATIC`; it controls sourcing discipline, not particle count.

## Decision guidance

- High authenticity → `AUTHENTIC_MEDIA`.
- High illustration/surface complexity with medium/high motion or lighting → `HYBRID`.
- High illustration/surface complexity with low motion → `PLATE`.
- Low illustration complexity with high geometric precision and meaningful motion → `PROCEDURAL`.

These are explainable heuristics, not mathematical artistic truth. A human may override the recommendation with a strategy and explicit reason.

## Plate contract

A plate records its source path and type, dimensions, aspect ratio, provenance, SHA-256, crop policy, safe/protected zones, animated regions, layer plan, and approval object. Allowed approval states are `UNREVIEWED`, `APPROVED`, `REJECTED`, and `REVIEW_REQUIRED`.

An approved plate is immutable by hash. A mismatch changes its effective state to `REVIEW_REQUIRED`. Production cannot use an unapproved plate. Development proofs may use a review-required plate but must report `PRODUCTION_PLATE_PENDING` and remain release-blocked.

`PLATE` and `HYBRID` jobs fail with `MISSING_APPROVED_PLATE` when the asset is absent. `AUTHENTIC_MEDIA` fails with `MISSING_AUTHENTIC_MEDIA`. No strategy may silently resolve to another strategy.

Fallback requires an explicit policy such as:

```json
{"fallback": {"allowed": true, "strategies": ["PROCEDURAL"]}}
```

## Hybrid layer planning

Define what remains static and what may move. For the pulp proof, the plate supplies the room and surfaces; Godot owns the reactor hero; compositing owns incandescent lamps, light response, steam, particles, and film behavior. Animated regions use deterministic bounds or masks. Automatic segmentation is outside v1.

Avoid constant whole-plate movement. A subtle camera push or tiny parallax may support a shot, but local motion and integrated light must carry the scene.

## Production integration

Run source validation before MF-016 composition generation:

```text
PYTHONPATH=scripts python3 scripts/visual_source_validate.py \
  --project-root . --config path/to/visual-source.json --output path/to/result.json
```

Then resolve assets, build semantic layout, generate static keyframes, and invoke the MF-016 gate. Source validation cannot approve composition, and composition approval cannot approve an unreviewed plate.
