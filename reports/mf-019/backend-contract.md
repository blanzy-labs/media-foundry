# MF-019 Backend Contract

## Sources

- Schema: `schemas/render-backend-v1.schema.json`
- Capability and failure registry: `config/render-backends.json`
- Contract implementation: `scripts/render_backend_contract.py`
- Controlled A/B manifest: `config/mf019-ab-render.json`

## Selection

The vocabulary is exactly `GODOT`, `BLENDER`, and `COMPARE`. If `render.backend` is absent, selection resolves to `GODOT`. `COMPARE` preserves Candidate A, creates Candidate B, applies shared finalization, and produces synchronized evidence.

No backend substitution is implicit. A failed requested Blender backend returns an actionable failure unless the manifest explicitly allows and names a fallback. Unsupported capabilities return `BACKEND_CAPABILITY_UNSUPPORTED`.

## Capabilities

| Backend | Declared purpose |
| --- | --- |
| GODOT | Native interactivity, game-ready scenes, fast batches, procedural UI, frame sequences, web-game precursors |
| BLENDER | Complex materials, volumetric lighting, character rigging capability, cinematic rendering, frame sequences, procedural scene building |
| COMPARE | Semantic A/B comparison, frame sequences, shared finalization |

The MF-019 Blender proof is cinematic-render-ready and is not interactive-ready. The preserved Godot candidate remains interactive-ready.

## Status and failure model

Nominal states are `BACKEND_PREFLIGHT`, `BUILDING_SCENE`, `RENDERING_FRAMES`, `VALIDATING_FRAMES`, `FINALIZING`, and `READY_FOR_REVIEW`. The completed run recorded exactly that order.

Failures include missing Blender, scene-build/render errors, incomplete sequences, unsupported capabilities or engines, missing templates, nonportable asset paths, silent fallback, and A/B audio/content mismatches. Each is tested in `reports/mf-019/failure-tests.json`.
