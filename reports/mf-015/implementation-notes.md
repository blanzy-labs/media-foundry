# MF-015 implementation notes

## Reusable scene system

MF-015 introduces a configurable `PulpTrailerStage` rather than a single hardcoded cover animation. The configuration supplies card content, timing, palette, typefaces, scene intensity, machine thresholds, film treatment, and final-card information.

Reusable renderer concepts include:

- distressed printed intertitles with automatic width fitting;
- hard-cut timeline dispatch;
- analog gauges with intensity-driven needles;
- threshold-driven incandescent warning lamps;
- reactor chamber, pulse, and deterministic filaments;
- intensity-driven silhouette reaction;
- final pulp title/author/CTA composition;
- seeded weave, exposure variation, grain, dust, scratches, edge wear, and sparse registration drift.

No branch depends on the literal book title. Subject-specific language lives in `config/mf015-pulp-trailer.json`.

## Visual relationship to the cover

The cover supplies black, cream, yellow, teal, red, and amber direction; condensed oblique display typography; battered print texture; analog industrial machinery; an illuminated cylindrical chamber; and a foreground human silhouette. The cover is never used as a full-screen scene or Ken Burns source.

## Motion hierarchy

The reactor is dominant. Lamps and gauges provide secondary escalation. The silhouette reacts after intensity 0.52. Film imperfections remain subtle and environmental architecture stays mostly fixed.

## Determinism

- Seed: `1501957`.
- Raw frame sequence SHA-256: `455eb8d135bb5fa1c3cf211b161d24486e5235f7d87e9082a9253193e1f028da`.
- The validator independently rerendered all twelve representative frames; every frame matched pixel-for-pixel.

## Reproduction

```bash
python3 scripts/run_mf015.py --project-root .
PYTHONPATH=scripts python3 scripts/validate_mf015.py --project-root . --output reports/mf-015/result.json
```

The runner refuses to overwrite an existing artifact directory.
