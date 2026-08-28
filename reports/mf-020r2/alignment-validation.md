# MF-020R2 alignment validation

Independent validator: `scripts/validate_mf020r2.py`

Result: **PASS — 18/18 checks**

- Observed center spacing: 0.514452827 to 0.514452866 units
- Maximum spacing variation: 0.000000039374 units
- Required non-overlap distance: greater than 0.18 units
- Maximum radial deviation: 0.000000052 units
- Lamp overlap count: 0
- Protected-detail intersection count: 0
- Maximum glow-anchor delta: 0.0
- Maximum position drift across off/half/all/camera-end: 0.0
- Active lamps at proof states: 0 / 5 / 9

The final media validator `scripts/validate_mf020r2_final.py` passes 9/9 checks, including immutable render fingerprints, a complete 600-frame sequence, H.264/AAC media contracts, full decode, unchanged approved music provenance, bounded loudness, and complete review evidence.
