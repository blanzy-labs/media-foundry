# MF-012 renderer change summary

MF-012 makes one opt-in renderer extension and three narrow integration edits:

- `godot/activity_vocabulary_stage.gd` — new subject-agnostic activity stage with bounded primitive execution and drawing.
- `godot/mf002.gd` — recognizes and selects `godot_activity_vocabulary_v1`.
- `godot/lofi_book_stage.gd` — permits the 8–15 second duration only when `activity.demo` is true; legacy duration rules are unchanged.
- `godot/extended_data_window_stage.gd` — applies the same demonstration-only duration compatibility.

No renderer source changed during the canonical five-demo run. No fixture/video/title/character-specific branch was introduced. Music catalog, cue workflow, scheduler, orchestration, campaign-manifest architecture, text pipeline, and visual grammar were not changed by MF-012.
