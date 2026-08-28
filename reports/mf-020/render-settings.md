# MF-020 Render Settings

| Setting | Value |
| --- | --- |
| Backend | `BLENDER` only |
| Blender | 5.2.0 LTS |
| Embedded Python | 3.13.13 |
| Engine | `BLENDER_EEVEE` |
| Device | `CPU_HEADLESS_DEFAULT` |
| Samples | 16 |
| Resolution | 768×1152 |
| Frame rate | 30 fps |
| Duration | 10.0 s |
| Frame count | 300 |
| Source format | 8-bit RGB PNG sequence |
| Camera | Perspective, 46 mm, single push/orbit |
| Seed | 200020 |
| Compositing | Bounded bloom/glow |

Template: `templates/blender/pulp-reactor-v1.blend`

Builder: `scripts/blender/build_cinematic_reactor.py`

Saved native scene: `artifacts/mf-020/scene/cinematic-reactor-hero.blend`

Frames are rendered before encoding. Existing valid frames are retained on resume; the recovery proof reused 300/300 frames in 554 ms and rendered zero replacements.
