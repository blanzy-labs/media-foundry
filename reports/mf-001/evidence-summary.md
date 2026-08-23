# MF-001 evidence summary

## Assessment

**PASS** — the structured fixture produced a real vertical MP4, independent media validation passed, representative frames were reviewed, and all controlled negative cases failed closed.

## Objective and architecture

MF-001 establishes `DATA -> TEMPLATE -> DETERMINISTIC RENDERER -> MEDIA PROCESSOR -> VALIDATOR -> ARTIFACT`. The fixture supplies content; a single Godot template supplies presentation and fixed-frame animation; FFmpeg supplies deterministic audio and final normalization; FFprobe and a separate full decode decide validity.

## Environment and prerequisites

- OS: Ubuntu 26.04 LTS, Linux 7.0.0-30-generic, x86_64
- Graphics/display: NVIDIA GeForce RTX 5070; Wayland session with X display compatibility
- Git: 2.53.0
- GitHub CLI: 2.46.0, authenticated as the Blanzy Labs account
- Python: 3.14.4
- Godot: 4.7.2 Standard, CLI/headless smoke PASS
- FFmpeg / FFprobe: 8.0.1
- H.264: `libx264` available
- AAC: native `aac` encoder available
- Fonts: system inventory recorded; renderer uses Godot's bundled fallback font
- Blender: 5.2.0 LTS is READY in the latest MF-001 regression run; it remains optional and unused by the render

The detailed machine-readable inventory is `artifacts/mf-001/doctor.json`. No packages were installed during the original MF-001 implementation. Blender was installed later, before the MF-002 regression run.

## Commands executed

```bash
./scripts/doctor.sh
./scripts/doctor.sh --json
godot --headless --path godot --editor --quit
./scripts/mf-001-acceptance.sh
./scripts/mf-001-failure-tests.sh
```

The acceptance script records the concrete Godot, FFmpeg, FFprobe, and decode stages in retained logs and reports.

## Render and validation result

- Godot composition: PASS, 450 fixed-index frames
- Deterministic audio: PASS, generated 48 kHz PCM source
- FFmpeg finalization: PASS, H.264/AAC MP4
- File/container: PASS
- Resolution/orientation: PASS, 1080×1920 vertical
- Duration/rate: PASS, 15.000 seconds at 30 fps
- Video/audio streams: PASS
- Full decode: PASS
- Artifact SHA-256: `3304f3f06ee58736cb53a4efd525da094407c6a5189e850f628f441fb0e69f60`
- Repeatability: PASS; a second complete acceptance run produced the identical SHA-256

Machine-readable details are in `reports/mf-001/result.json` and `artifacts/mf-001/ffprobe.json`.

## Failure-test result

**PASS: 5, FAIL: 0.** Controlled cases cover a missing fixture, injected render failure, missing output, deliberately invalid media, and standards-valid media that violates the MF-001 format contract. Isolated temporary directories prevent these tests from damaging the accepted artifact.

## Retained evidence

- `artifacts/mf-001/mf001-demo.mp4`
- `artifacts/mf-001/render.log`
- `artifacts/mf-001/ffmpeg.log`
- `artifacts/mf-001/ffprobe.json`
- `artifacts/mf-001/doctor.json`
- `artifacts/mf-001/frames/intro.png`
- `artifacts/mf-001/frames/content.png`
- `artifacts/mf-001/frames/outro.png`
- `reports/mf-001/result.json`
- `reports/mf-001/failure-tests.json`

## Repository state and limitations

The project is an independent Git repository on branch `main`. Source, scripts, configuration, compact logs, frames, and the 1.7 MB reference MP4 are retained; rebuildable raw frames and WAV audio are ignored.

Blender readiness is known and does not affect this slice. The current Godot capture path requires a display-backed render session because this Godot headless driver does not expose viewport pixels. Visual grammar is intentionally primitive and remains subject to human review and MF-002 refinement. No publishing or social-account access occurred.
