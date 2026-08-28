# MF-018B-R1 Evidence Summary

## Outcome

MF-018B-R1 produced a focused 14-second native-scene refinement with a cleaner upper ring, corrected four-dot device, and externally controllable startup chain. Independent validation reports `TECHNICAL_PASS`: 27 of 27 checks passed.

Human review remains pending. The candidate is not release-ready or published, and no gameplay was implemented.

## Artifacts

- Preserved MF-018B baseline: `artifacts/mf-018b/final-test.mp4`, SHA-256 `f629364bf73ebb9a16b181ea43221530ed428f009f2e1093a572447d5ca20d42`
- Refined candidate: `artifacts/mf-018b-r1/final-test.mp4`, SHA-256 `1910158da2dc5190626f3db55c682d0f44f2e87b0319334844c3f4b0aed10f56`
- R1 native scene: `godot/mf018b_r1_pulp_scene.tscn`, SHA-256 `9a60b061a6a51d698f97c932253914cf452eb64d2d7923cf5839a7da2376ff31`
- R1 handoff manifest: `handoff/playable-scene/mf018b-r1/manifest.json`, SHA-256 `dcf9670970fccc4797d0adb49a69e60162213838fff3ec43fb72f0ee163f0a94`
- Representative contact sheet: `artifacts/mf-018b-r1/representative-frames/contact-sheet.png`
- Closeups: `artifacts/mf-018b-r1/closeups/`
- Static and eight-second motion comparison: `artifacts/mf-018b-r1/comparison/`
- Independent result: `reports/mf-018b-r1/result.json`

## Measured acceptance signals

- Six linked ring indicators replace the prior twelve large housings.
- Minimum linked-indicator center distance is 41.477 px against a 26 px non-overlap requirement.
- Minimum linked-to-small-detail distance is 31.059 px against an 18 px separation requirement.
- Four-dot spacing is 46 px with 11 px housings.
- The fourth dot retains 19.13 px clearance from the sloped lower border.
- Red lever-knob centroid moves 43.03 px right and 42.99 px down, matching the vertical-to-horizontal 90° rotation.
- Gauge-region mean change after startup is 5.974 code values.
- Blue, green, and yellow states are independently detected.
- Ring activation pixels rise from 259 at the yellow frame to 755 after the linked-ring start.
