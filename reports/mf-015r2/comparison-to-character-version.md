# MF-015R2 comparison to character version

## Controlled variable

Candidate A is frozen MF-015R1 with the human observer. Candidate B is MF-015R2 with no human or humanoid replacement. Seed, reference, dimensions, runtime, timeline, words, card timing, palette, fonts, film settings, machine settings, and audio configuration are identical. The decoded audio PCM is bit-exact between candidates.

| Property | Candidate A: MF-015R1 | Candidate B: MF-015R2 |
| --- | --- | --- |
| Human observer | Present | Absent |
| Former foreground region | Human silhouette | Instrument bank, dial, lever, pipe and shadow |
| Story signal | Observer reacts to machine | Machine wakes and operates itself |
| Supporting motion | Character reaction and R1 machinery | Steam, arcs, sway, vibration, moving shadows and automatic control |
| Runtime | 30.0 s | 30.0 s |
| Decoded audio PCM SHA-256 | `416f77e922a303a27207b0d39c1823490678509815aa2ba3a6f05faf5bfe8bb9` | Same |

## Independent measurements

- Prior character-head reference: `435` gold pixels.
- Corresponding R2 samples: `15`, `0`, `11`, `16`, and `29` pixels across five machine states; all remain below ten percent of the character reference and are incidental machine/lighting pixels.
- Former-character region: mean luma `39.598`, standard deviation `26.711`; this is textured machinery and shadow rather than an empty field.
- Right/left luma ratio: `1.511`; composition retains deliberate asymmetry.
- Background and machine-room material-gradient retention: `98.14%` and `98.14%` (rounded).

## Review artifacts

- `artifacts/mf-015r2/before-after-comparison/character-vs-characterless.mp4`
- `artifacts/mf-015r2/before-after-comparison/charge-composition.png`
- `artifacts/mf-015r2/before-after-comparison/escalation-composition.png`

The deterministic evidence supports a technically fair A/B test. Whether absence creates stronger mystery, atmosphere, and release value is intentionally reserved for human review.
