# MF-015R1 implementation notes

## Architecture

`PulpTrailerRefinementStage` subclasses the reusable MF-015 renderer. The base stage now exposes figure drawing as an overridable component, allowing R1 to replace only the character while retaining the editorial and machine systems.

The MF-015 runner also accepts a configuration-declared stage class and validates an optional frozen prior artifact. This keeps refinements format-driven rather than branching on the book title.

## Character construction

The refined figure uses discrete anatomical and clothing shapes: planted legs, feet, long coat, waist, lapels, shoulder line, neck, profile head, ear, brow, articulated arms, elbow, palm, and fingers. Reactor intensity controls a restrained recoil, balance shift, arm lift, and warm rim exposure.

## Materiality

- Grain `0.055 → 0.075`
- Weave `1 → 2 px`
- Dust `8 → 12` marks per frame
- Registration peak `2 → 3 px`
- Edge wear `18 → 25`
- Added fixed paper-fiber plate, halftone-like ink breaks, machinery grime, flaking marks, and selected yellow/teal stress separation

## Environment and reactor

Four depth layers add distant vessels, vertical pipe runs, curved supports, cross-braced catwalk detail, and sagging cable. The reactor gains deterministic asymmetric plasma bodies and warm spill without changing its intensity timeline.

## Determinism

- Seed: `1501957`
- Raw sequence SHA-256: `2d28c5cef474c6b9d5841036ca175a32d0d9b26be0e83e7ac9185fae7a28e57d`
- All twelve representative frames rerender pixel-identically.

## Reproduction

```bash
PYTHONPATH=scripts python3 scripts/run_mf015.py --project-root . --config config/mf015r1-pulp-material-refinement.json --artifacts artifacts/mf-015r1
PYTHONPATH=scripts python3 scripts/validate_mf015r1.py --project-root . --output reports/mf-015r1/result.json
```
