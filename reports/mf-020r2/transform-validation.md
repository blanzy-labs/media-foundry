# MF-020R2 transform validation

Every lamp record in `artifacts/mf-020r2/proof/scene-contract.json` contains its generated angle, local/world position, local rotation, scale, parent, bulb parent, shared mesh names, and glow delta.

Validated invariants:

- Every lamp parent is `LampArcRoot`.
- Every bulb parent is its matching `UpperRingLamp_NN` root.
- All lamp scales are `(1, 1, 1)`.
- All lamps share `UpperRingLampSharedBulbMesh` and `UpperRingLampSharedSocketMesh`.
- All positions are identical across off, partial, full, and production-camera-end samples.
- The fixed proof camera has no animation.
- Activation changes material emission only.
- Production camera movement does not alter any lamp world transform.
