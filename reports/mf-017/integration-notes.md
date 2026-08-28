# MF-017 integration notes

The intended production order is brief → visual-source assessment → asset resolution → semantic composition → MF-016 static gate → animation. Source validation and composition validation are independent gates.

The pulp proof binds the exact committed MF-016 manifest hash and reruns all 17 semantic checks. The MF-017 brief records MF-016 human approval; the source strategy does not rewrite or bypass that contract.

Godot executes the matched animated overlays through `godot/mf017_visual_source_proof.gd`. The headless proof rasterizes deterministic SVG overlays and alpha-composites them into each source plate. The harness fails on nonzero exit, `SCRIPT ERROR`, or any Godot `ERROR`, even if files were written.

Simple scenes can remain `PROCEDURAL` without plate fields. Existing media-slot and screenshot workflows can map to `AUTHENTIC_MEDIA`; MF-017 does not duplicate those ingestion systems.

Release use remains blocked until the development plate is reviewed or replaced with an approved production plate whose approved hash matches the file.
