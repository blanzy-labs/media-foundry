# MF-012R1 renderer changes

MF-012R1 modifies only `godot/indicator_pulse_stage.gd` to recognize an optional, subject-agnostic `micro_variation` object and draw its bounded tile, indicator, and ring accents.

Defaults are unchanged when that object is absent. Both selected legacy fixtures were fully rerendered without micro controls; their archived phase-3 PNGs remained byte-identical.

Renderer changes during the production run: 0. Subject/title/video-specific branches: 0. Large crossing lines: 0. New central-web geometry: 0. Visual grammar changes: 0.
