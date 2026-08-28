# MF-020 Blockout Review

Result: `PASS` / detail rendering authorized.

The blockout uses simple geometry to establish a central reactor, left-foreground console, background columns/beams, containment scale, and the full single-camera path. Three static previews cover dormant, escalation, and final framing.

Checks passed:

- Reactor remains the clear central hero.
- Console is visible and secondary.
- Foreground, mid-ground, and background establish depth.
- No bright edge clutter or purposeless foreground crossing object was detected.
- Camera and escalation states are visually distinct.
- One 46 mm perspective camera performs a restrained push with a subtle rightward orbit.
- Three gauges, lever, mounted lamps, collar, and reactor are present in the purposeful blockout contract.

The first gate run correctly stopped on a provisional bright-pixel threshold. Visual inspection showed a readable hero, so the threshold was calibrated from 1,000 to 800 while the stronger minimum hero-luminance, console, edge-clutter, camera-path, and structure checks remained active. The gate was then rerun and passed before detail work.

Evidence: `artifacts/mf-020/blockout/` and `artifacts/mf-020/validation/blockout-gate.json`.
