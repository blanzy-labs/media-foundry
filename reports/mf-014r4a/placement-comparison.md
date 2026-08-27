# MF-014R4A placement comparison

| Element | R4 center | R4A center | Normalized delta | Pixel delta |
| --- | --- | --- | --- | --- |
| Tagline | `(0.500, 0.750)` | `(0.560, 0.750)` | `(+0.060, 0)` | `(+46.08 px, 0)` |
| Website | `(0.495, 0.845)` | `(0.555, 0.845)` | `(+0.060, 0)` | `(+46.08 px, 0)` |

The information region moved from `[0.32, 0.69, 0.635, 0.91]` to `[0.38, 0.69, 0.695, 0.91]`.

## Safety measurements

| Element | Final glyph bounds | Right margin | Clipped | Glyphs below luma 60 |
| --- | --- | ---: | --- | ---: |
| Tagline | `(313, 839)–(545, 885)` | 222 px | No | 0% |
| Website | `(329, 941)–(523, 1009)` | 244 px | No | 0% |

The obstruction measurement tests the actual rendered glyph pixels against the rail/texture beneath them. No glyph pixels fall below the visibility threshold.

## Comparison assets

- `artifacts/mf-014r4a/before-after-comparison/final-placement.png`
- `artifacts/mf-014r4a/before-after-comparison/r4-vs-r4a.mp4`

The comparison shows the same animation and treatment with the supporting block translated rightward.
