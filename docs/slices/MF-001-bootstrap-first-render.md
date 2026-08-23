# MF-001 — Bootstrap and deterministic first render

## Goal

Prove a complete data-to-validated-media slice before generalizing Media Foundry.

## Contract

- Input: `content/fixtures/mf001-demo.json`
- Template: `did_you_know`
- Composition: Godot 4 fixed-frame 2D renderer
- Audio: deterministic FFmpeg-generated, copyright-free tone bed and stings
- Finalization: FFmpeg H.264/AAC MP4
- Validation: independent FFprobe inspection and complete FFmpeg decode
- Output: `artifacts/mf-001/mf001-demo.mp4`

Changing fixture copy does not require a renderer change. Format and timing are deliberately strict for this first slice.

## Commands

```bash
./scripts/doctor.sh
./scripts/doctor.sh --json
./scripts/mf-001-acceptance.sh
./scripts/mf-001-failure-tests.sh
```

Acceptance is fail closed. Fault injection is limited to the failure-test harness and writes isolated temporary artifacts.

## Workstation modification record

No software was installed and no workstation configuration was changed for MF-001. Existing suitable Git, GitHub CLI, Python, Godot, FFmpeg, and FFprobe installations were reused. Blender was not installed because it is optional and does not participate in this render.

## Known limitation

Godot 4.7's headless display driver is sufficient for CLI smoke execution but does not expose a capturable viewport on this workstation. The actual frame render therefore uses the available local Wayland/X11 graphical session and GPU. A display-backed CI worker or virtual display is required for unattended rendering on a machine without a graphical session.
