# MF-014R1 implementation notes

MF-014R1 is additive. It does not modify `scripts/metal_circuit_burn_stage.py`, the MF-014 source copy, or any MF-014 evidence. `scripts/metal_circuit_burn_stage_r1.py` subclasses the baseline stage so the established material layers—tempered fringe, char channel, groove shadow, copper rim, moving hot core, bloom, and restrained sparks—remain unchanged.

`config/mf014r1-circuit-burn.json` is the complete bounded presentation configuration. It exposes:

- deterministic seed and output format;
- six path origins, normalized geometry, start times, and durations;
- global burn speed and burn/glow intensities;
- title start, rise, peak, peak hold, settle level, and settle duration;
- approved music catalog selection, cue bounds, fades, loudness target, and post-normalization trim.

Every path's first point lies 12% beyond its nominated viewport edge. The burn stage clips naturally at the image boundary, so the first visible energy is already arriving from an unseen continuation rather than igniting on a border marker.

The title uses an independent physical-feeling envelope: smoothstep rise, constant peak hold, smoothstep settle, then a constant residual level. A 1.5% deterministic thermal flutter affects only the composited warmth, not the configured envelope.

`scripts/run_mf014r1.py` fails closed if the MF-014 source/video hashes change, if the configured track or cue is not approved for the current source hash, or if cue offsets escape approved bounds. It streams visual frames to deterministic H.264, applies music-only editorial treatment, and records final audio measurements.

`scripts/validate_mf014r1.py` independently checks the baseline, source, configuration, paths, timing, title contract, catalog approval/hash, cue bounds, audio/video streams, full decode, loudness, evidence pixels, observed peak/settle hierarchy, final residual hold, and non-publication state.

The initial R1 encoding measured −13.57 LUFS and was rejected before acceptance. It is preserved outside the repository at `/home/blanzy/media-foundry-output/mf014r1-pre-audio-validation-failure`. The canonical output adds a documented −2.5 dB post-normalization trim and passes at −16.07 LUFS.
