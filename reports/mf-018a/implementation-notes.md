# MF-018A Implementation Notes

## Scene construction

`godot/mf018a_native_pulp_scene.gd` builds each frame from a deterministic native SVG scene graph and rasterizes it inside Godot. No painted plate or MF-017 image is loaded into the candidate.

The scene includes:

- a large center-right reactor shell, collar, clipped chamber, energy filaments, and heavy base;
- a left analog console with three physical gauge housings, pivoted needles, and six seated indicator lamps;
- ten warning lamps mounted in individual housings on the reactor ring;
- background cylinders, restrained catwalk geometry, a wall pipe, and a perspective floor deck;
- one valve-bound steam source, fourteen dust motes, local reactor illumination, and a 3.2% camera push;
- a limited yellow/cream, teal/blue-black, amber, and red palette with deterministic surface distress.

The energy graph is clipped to the reactor chamber. Lamp bulbs are emitted only after their housings are drawn, gauge needles rotate from fixed centers, and all environmental elements share the same camera transform.

## Determinism

- Seed: `1801957`
- Config: `config/mf018a-native-pulp-scene.json`
- Composition contract: `config/mf018a-native-composition.json`
- Frame schedule: 360 frames at 30 fps
- Timing, lamp sequence, gauges, pulse, steam, dust, camera movement, and audio excerpt are config-bound.
- Raw frames are temporary and are not retained.
- The runner refuses to overwrite an existing MF-018A artifact directory.
- Godot exit status, explicit error text, frame count, source hashes, and approval hashes are fail-closed.

## Scope

There is one camera, no character, no title system, no multi-angle edit, and no 30-second trailer. This keeps the experiment focused on native motion/layout coherence.
