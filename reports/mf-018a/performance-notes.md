# MF-018A Performance Notes

The final deterministic MF-018A run completed in 25,894 ms, including 360 Godot frame renders, video encoding, approved-audio muxing, evidence extraction, and hybrid/native comparison generation.

The recorded MF-017 reference run took 89,310 ms for its paired procedural/hybrid proof. MF-018A used 0.290× that elapsed time despite producing a 12-second final candidate rather than two four-second source proofs. The workloads are not identical, so this is directional rather than a benchmark.

Operationally, the native approach is practical for repeated campaign experiments:

- all visual elements are generated from one script and two declarative configs;
- no manual registration map is required;
- motion and layout parameters can be varied deterministically;
- temporary raw frames are discarded after encoding;
- output creation refuses overwrite and validates upstream hashes.

The main cost is creative rather than computational: achieving the hybrid plate's texture richness inside the native pipeline will require a focused materials and depth refinement.
