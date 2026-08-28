# MF-020R2 lamp placement contract

The authoritative parameters are stored in `config/mf-bench-001.json` under `upper_ring_lamps`:

- Count: 9
- Host: `UpperRingAssembly`
- Arc root: `LampArcRoot`
- Host outer radius / lamp radius: 1.82 scene units
- Arc: 205 to 335 degrees inclusive
- Elevation: 0.0 scene units (the real cap plane)
- Bulb radius: 0.075
- Socket radius / depth: 0.095 / 0.42
- Minimum spacing margin: 0.03

For lamp `i`, `t = i / (count - 1)`, `angle = lerp(start, end, t)`, and the local anchor is `(cos(angle) * radius, sin(angle) * radius, elevation)`. No per-index offset, screen-space adjustment, positional jitter, placement animation, or camera-dependent correction exists.

Each lamp root rotates around local Z by its arc angle. Its shared cylindrical socket rotates 90 degrees around local Y and extends inward along the lamp root's local radial axis. The physical bulb and emissive center both use local origin `(0, 0, 0)`.
