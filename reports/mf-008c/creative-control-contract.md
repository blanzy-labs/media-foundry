# MF-008C Creative-Control Contract

Directed fixtures provide one inspectable `creative` object:

```json
{
  "mechanism": "tracking",
  "events": ["target_search", "target_reacquire", "target_lock"],
  "timing": {
    "intro_seconds": 5.4,
    "investigation_seconds": 13.2,
    "result_hold_seconds": 1.4,
    "cta_seconds": 8.0
  },
  "palette_profile": "pursuit",
  "camera_profile": "tight_pursuit",
  "node_profile": "urgent",
  "projection_profile": "warning_trace",
  "cta_profile": "warning",
  "audio_cue": "baseline_full"
}
```

Canonical mechanisms are `tracking`, `classification_link`, and `biometric_scan`. Palette, camera, node, projection, and CTA values are bounded enums in `schemas/mf008c-creative-control.schema.json`; arbitrary coordinates, colors, shaders, scene trees, and animation code are not exposed.

Timing consists of four sequential groups. Bounds are intro 5–7 seconds, investigation 10–14, result hold 1–3, CTA 5–8, total runtime 24–32, with the four values required to equal fixture duration. Mechanism event lists are exact contracts, and their generated event times must be ordered within the investigation interval.

Fixtures without `creative` use `baseline_compatibility` and preserve the inherited three-record behavior. Unknown capabilities fail as `NEEDS_ENGINEERING`; structurally known but unapproved cues fail as `BLOCKED_APPROVAL`.
