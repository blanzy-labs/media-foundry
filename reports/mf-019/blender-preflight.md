# MF-019 Blender Preflight

Result: `PASS`

| Field | Recorded value |
| --- | --- |
| Executable | `/home/blanzy/.local/opt/blender-5.2.0/blender` |
| Blender | 5.2.0 LTS |
| Embedded Python | 3.13.13 |
| Available real-time engine | `BLENDER_EEVEE` |
| Selected engine | `BLENDER_EEVEE` |
| Device | `CPU_HEADLESS_DEFAULT` |
| FFmpeg / FFprobe | `/usr/bin/ffmpeg` / `/usr/bin/ffprobe` |
| Required font | `godot/fonts/Lato-Regular.ttf` |
| Elapsed | 602 ms |

The diagnostic passed binary discovery without assuming one installation path, version extraction, background execution, embedded Python, supported-engine discovery, font resolution, writable output, FFmpeg, and FFprobe.

The absolute executable path above is diagnostic evidence only. Project configuration, template dependencies, source assets, and output contracts remain project-relative.

Machine-readable evidence: `artifacts/mf-019/validation/blender-preflight.json`.
