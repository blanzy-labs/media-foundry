# MF-014R4 readability validation

The independent validator returned `TECHNICAL_PASS`. It reconstructs text masks from the declared strings and font rather than accepting the render stage's own judgment.

## Exact information and layout

- Tagline: `SUBJUGATE THE PLANET`, two lines.
- URL: `rcblanzy.com/books/unknown-process`, split at slash boundaries into three lines. Concatenating the rendered lines reproduces the exact URL.
- Both fields are engraved into the lower-right portion of the central plate and stop at normalized x = 0.635, before the right structural rail.

## Full-size measurements

| Element | Glyph height | Changed glyph ratio | Local luma contrast | Glyph p95 | R→L heat ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tagline | 47 px | 1.000 | 41.276 | 128 | 14.359 |
| URL | 69 px | 1.000 | 67.482 | 145 | 1.438 |

The right side is measurably hotter than the left during each sampled reveal, confirming the configured right-to-left thermal propagation.

## Reduced-size measurements

The complete final frame was downsampled to 360 px wide with Lanczos resampling before measurement.

| Element | Reduced glyph-block height | Local luma contrast | Glyph p95 |
| --- | ---: | ---: | ---: |
| Tagline | 23 px | 42.324 | 118 |
| URL | 33 px | 70.291 | 142 |

The reduced frame and a nearest-neighbor 3× inspection crop are in `artifacts/mf-014r4/mobile-readability/`. These metrics establish deterministic contrast and size acceptance; natural-language legibility remains a human approval item.

## Hierarchy and hold

- Tagline peak/final levels: 1.00 / 0.66.
- URL peak/final levels: 0.82 / 0.62.
- Final readable hold: 2.5 seconds.
- At luma >110, the title region contains 19,286 bright pixels versus 5,588 in the information region, a 3.451× dominance ratio.
