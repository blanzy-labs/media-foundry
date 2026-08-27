# MF-014 implementation notes

## Approach

`scripts/metal_circuit_burn_stage.py` implements a reusable deterministic `MetalCircuitBurnStage`. It composites directly over the supplied image and exposes normalized path geometry plus burn timing, speed, glow intensity, scorch intensity, duration, and output width through `BurnPath` and `BurnConfig`.

Each path is rendered in material order:

1. a broad, low-opacity heat-tempered fringe;
2. a narrow charred channel modulated by source luminance and deterministic grain;
3. offset groove shadow and copper-brown rim layers for an etched-depth illusion;
4. a short amber/white moving heat front;
5. no more than three sparse deterministic spark traces near an active front.

Four paths use intentional right-angle routing and approach the title from different parts of the plate. Their starts are staggered so the image does not ignite everywhere at once. A single bounded heat pulse warms the existing title region when the final path arrives; the title itself is neither redrawn nor replaced.

`scripts/run_mf014.py` streams raw deterministic frames directly to FFmpeg, avoiding a large intermediate frame cache. It packages the silent H.264 capability video, five representative phase frames, an ordered motion strip, the source copy, hashes, and a render manifest. Audio was intentionally omitted because this slice tests only the visual capability.

`scripts/validate_mf014.py` is separate from the renderer. It checks source identity, idle-frame pixel preservation, codec, duration, dimensions, frame count, full decode, path count, representative evidence, persistent aftermath, bounded visual coverage, and non-publication state.

## Bounded scope

This implementation does not add a generalized simulation system, physically based metal deformation, a particle engine, smoke volumes, or campaign integration. It does not modify the existing Godot renderer or any previous slice.

## Recommended refinement

For MF-014R1, retain the current timing and composition while adding slightly irregular groove-edge breakup and a very small localized refractive heat distortion immediately around each front. Those two refinements would improve material realism without adding more sparks, smoke, paths, or overall brightness.
