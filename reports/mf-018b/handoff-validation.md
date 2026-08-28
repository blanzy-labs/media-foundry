# MF-018B Handoff Validation

The portable handoff manifest passes all contract checks:

- package identity and contract version;
- unique interaction IDs and complete metadata;
- declared node-path resolution;
- six valid normalized state variables and matching setters/signals;
- four-state vocabulary;
- eleven valid semantic signal names;
- seven resolved audio-event hooks;
- relative project paths only, with no `..`, drive paths, or absolute local paths;
- all assets present with matching SHA-256 and byte size;
- promo driver removable from the base scene;
- zero Game Foundry or external-plugin dependency;
- ownership boundary and no gameplay scope leak;
- base scene API present.

The Godot standalone probe loads the base scene without the promo driver, resolves four interaction nodes, invokes six state setters plus one control setter, observes seven signals, and confirms state persistence.

## Failure tests

All seven required negative cases fail closed with the expected code:

1. duplicate interaction ID → `DUPLICATE_INTERACTION_ID`
2. missing interaction node → `MISSING_INTERACTION_NODE`
3. invalid state variable → `INVALID_STATE_VARIABLE`
4. missing audio hook → `MISSING_AUDIO_HOOK`
5. absolute local path → `ABSOLUTE_OR_UNSAFE_PATH`
6. base-scene promo dependency → `PROMO_DEPENDENCY_IN_BASE_SCENE`
7. unresolved asset → `UNRESOLVED_OR_CHANGED_ASSET`

Machine-readable evidence is in `artifacts/mf-018b/validation/handoff-validation.json` and `reports/mf-018b/failure-tests.json`.
