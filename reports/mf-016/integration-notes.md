# MF-016 integration notes

## Production hook

Complex-scene jobs should call `scripts/composition_gate.py` after static-keyframe review and before animation frame generation. A blocked decision uses exit code `3` and the state `BLOCKED_COMPOSITION`.

The integration sequence is:

```text
job → composition build → static package → machine checks → human approval → gate CLI → animation
```

MF-016 deliberately does not rewrite existing campaign orchestration. Future complex formats can opt in with `complex_scene: true` or `composition.required: true`.

## Compatibility

Legacy/simple formats remain ungated unless they opt in. The test suite confirms that a simple title plate receives `COMPOSITION_NOT_REQUIRED`, while the MF-016 complex scene requires the gate. Existing audio, FFmpeg, Godot, title-card, campaign, and evidence paths were not modified.

## Migration

For a complex renderer:

1. Add a composition manifest using the v1 schema.
2. Generate three to five static states without invoking the full video path.
3. Save the contact sheet and object-purpose evidence.
4. Run machine validation.
5. Record human approval and reviewer identity.
6. Invoke the composition gate immediately before the renderer.

Do not infer approval from machine metrics or edit `gate.state` directly. Authorization is recomputed from the manifest.
