# MF-020 Evidence Summary

## Result

`TECHNICAL_PASS` — 27 of 27 independent checks passed. Creative acceptance remains `PENDING_HUMAN`; the artifact is not release-ready and was not published.

## Final proof

- Native Blender scene: `artifacts/mf-020/scene/cinematic-reactor-hero.blend`
- Final video: `artifacts/mf-020/final-test.mp4`
- Final SHA-256: `15456cdfcfdabc051f326d81fd44e7acc912ea3957ee5e34d1653c265dd0a058`
- Independent validation: `reports/mf-020/result.json`

The result is a single Blender-native perspective hero shot rather than a Godot comparison. A restrained camera push/orbit approaches a glass containment reactor while a lever, three gauges, warning lamps, pressure steam, seven energy filaments, an asymmetric motorized collar, local light, and contained sparks form one causal escalation.

## Stage evidence

- Concept: `reports/mf-020/shot-intent.md`
- Blockout: `artifacts/mf-020/blockout/`
- Detail: `artifacts/mf-020/previews/detail/`
- Lighting: `artifacts/mf-020/previews/lighting/`
- Animation/FX: `artifacts/mf-020/previews/fx/`
- Final keyframes: `artifacts/mf-020/representative-stills/`

The runtime status record proves the blockout gate completed before detail. Detail-to-lighting changed 622,519 pixels and lighting-to-FX changed 764,163 pixels, confirming separate production passes rather than renamed copies.

## Technical proof

- Blender 5.2.0 LTS / embedded Python 3.13.13 / `BLENDER_EEVEE` / CPU headless.
- Seed 200020, 16 samples, 768×1152, 30 fps, 10 seconds.
- Complete 300-frame PNG sequence; resume reused all 300 without rerendering.
- Full-power and final-hold cross-invocation frames are pixel-exact. The volumetric pressure frame differs by two pixels, within the recorded practical tolerance.
- Powered reactor-region luminance rises from 3.72 dormant to 42.99, with 46,874 bright pixels at full power.
- Final H.264/AAC MP4 contains 300 frames, 48 kHz approved audio, the Media Foundry-owned title, and fully decodes.

## Boundary

No Godot runtime or scene is required for the output. MF-020 does not implement comparison mode, gameplay, Blender-to-Godot export, multiple shots, a campaign, or publication.
