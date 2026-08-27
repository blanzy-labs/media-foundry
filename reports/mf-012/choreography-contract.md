# MF-012 choreography contract

The activity layer is additive to existing palette, camera-profile, node, projection, CTA, timeline, music, and text controls. Historical fixtures without `activity` continue through the legacy/default selection path.

## Contract

An activity demonstration declares `version`, `demo`, one `dominant_activity`, zero to two `supporting_activities`, an approved `opening_choreography`, an approved `camera_choreography`, declared `targets`, `spatial_behavior`, `text_behavior`, and an ordered `sequence`.

Each sequence event accepts only `id`, `type`, `target`, `start`, `duration`, `intensity`, `repeat`, `origin`, `destination`, and `overlap`. Validators fail closed on unknown fields/types, missing targets, invalid timing, out-of-order entries, unsatisfied dependencies, unsupported families, excessive complexity, and unknown opening/camera profiles. Deliberate overlap is required for the demonstrations. Controlled movement derives from the fixture seed.

The JSON contract is defined by `schemas/mf012-activity.schema.json`; the authoritative vocabulary is `config/activity-vocabulary/visual-activity-v1.json`.

## Composition examples

```yaml
dominant_activity: pursuit
opening_choreography: target_already_moving
camera_choreography: lateral_track
sequence:
  - target_acquire
  - target_move
  - target_escape
  - target_reacquire
  - tracker_converge
  - target_lock
```

```yaml
dominant_activity: reconstruction
opening_choreography: corrupt_record_resolve
camera_choreography: reveal_from_detail
sequence:
  - fragment_spawn
  - fragment_drift
  - fragment_align
  - record_reconstruct
```

Future campaign manifests can record the dominant/supporting activities and opening/camera choreography per job. This enables a later advisory or validator that rejects repeated adjacent openings unless explicitly approved; MF-012 does not alter the existing campaign-manifest architecture.
