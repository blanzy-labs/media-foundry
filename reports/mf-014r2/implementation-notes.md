# MF-014R2 implementation notes

MF-014R2 is an additive stage. It does not modify the R1 stage or configuration. `scripts/metal_circuit_burn_stage_r2.py` subclasses `RefinedMetalCircuitBurnStage`, renders R1 first, and applies supporting text only after the configured reveal times.

`config/mf014r2-etched-supporting-text.json` exposes exact text, font assets, normalized placement, type scale, reveal timing, etch intensity, supporting brightness, final hold, and the bounded music extension. Future supporting copy can use the same treatment without a general animation system.

The etched treatment has four glyph-local layers:

1. a shallow blurred undercut for contrast against variable corrosion;
2. a dark offset groove shadow;
3. source-texture-modulated recessed fill;
4. a thin upper-left metallic edge highlight.

A narrow highlight pass crosses the glyphs only during reveal. There is no neon glow, text panel, spray treatment, or projected UI layer.

The tagline is centered at 66.5% frame height using a 31 px narrow bold face. The website is centered slightly right at 86.5% using a 21 px narrow regular face. The website is smaller and uses lower etch intensity and edge brightness than the tagline.

`scripts/run_mf014r2.py` verifies frozen R1 hashes, loads the R1 configuration directly, extends only the total duration and approved cue endpoint, streams frames to H.264, and packages phase evidence. `scripts/validate_mf014r2.py` independently validates preservation, exact copy, timing, readability, hierarchy, coverage, media streams, approved music continuity, and final hold.

The first R2 candidate measured −17.66 LUFS and left the website marginal at review size. It was rejected before acceptance and preserved at `/home/blanzy/media-foundry-output/mf014r2-pre-readability-audio-validation-failure`. The canonical candidate uses a 21 px website and a −1.0 dB post-normalization gain setting, passing both readability and loudness gates.
