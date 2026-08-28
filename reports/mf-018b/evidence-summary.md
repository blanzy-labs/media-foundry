# MF-018B Evidence Summary

## Outcome

MF-018B produced a refined 14-second Godot-native pulp promo and a portable `playable_scene_package_v1` handoff. Independent validation reports `TECHNICAL_PASS`; human review remains pending and the candidate is not release-ready or published.

## Primary evidence

- MF-018A preserved baseline: `artifacts/mf-018a/godot-native-pulp-scene.mp4`, SHA-256 `a6507e574567dd2b041981ac5f51ca7123dc700636e6cd394ccbb086d19c549b`
- MF-018B promo: `artifacts/mf-018b/final-test.mp4`, SHA-256 `f629364bf73ebb9a16b181ea43221530ed428f009f2e1093a572447d5ca20d42`
- Native scene: `godot/mf018b_pulp_scene.tscn`, SHA-256 `1e4df3528e96bf5a8db019d059b60aa57e4b337e4dad4c882f74ce176215c48b`
- Handoff manifest: `handoff/playable-scene/mf018b/manifest.json`, SHA-256 `b9f25ff451c503537f0b9b3565d81d954f297b85c16640b2086404b7dd9afe55`
- Independent result: `reports/mf-018b/result.json`
- Representative contact sheet: `artifacts/mf-018b/representative-frames/contact-sheet.png`
- Interaction diagnostic: `artifacts/mf-018b/interaction-diagnostic/controls-and-state.png`
- MF-018A/B static and motion comparisons: `artifacts/mf-018b/comparison/`

## Verified signals

- The base `.tscn` loads with the promo driver absent.
- Four interaction nodes resolve and seven setter/signal checks fire in Godot.
- All 17 semantic composition checks pass for dormant, stable, unstable, and critical review states.
- Reactor hero luminance rises from 1.197× support luminance when dormant to 1.510× when critical.
- New yellow-energy pixels bind to the chamber at a measured 26.26× ratio versus the adjacent region.
- Lamp pixels localize to the physical reactor ring and console regions.
- Diagnostic cyan markings are absent from the promo.
- Seven of seven malformed handoff packages fail with the expected actionable error.

## Interpretation

The deterministic measurements establish greater native visual complexity without a motion-coherence regression. They do not replace human judgment about pulp character, control design, or whether this world should become a reusable production scene.
