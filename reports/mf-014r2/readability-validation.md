# MF-014R2 readability validation

## Result

**PASS**

Measurements compare the final frame against the settled-title frame before supporting text appears. Glyph masks are independently reconstructed from the configured exact text, font, size, and position.

| Element | Glyph pixels | Changed glyph ratio | Mean pixel delta | Local luma contrast | Glyph luma P95 |
|---|---:|---:|---:|---:|---:|
| Tagline | 3,631 | 98.60% | 56.589 | 16.647 | 100 |
| Website | 1,931 | 84.93% | 36.981 | 28.662 | 100 |

The title-region luma P95 is 133, 33 levels above the brightest supporting-text P95. This preserves the requested title > tagline > website hierarchy in combination with type size and etch-intensity controls.

Supporting text changes 0.91% of the full frame, below the 3% clutter ceiling. The website finishes at 12.8 seconds and remains stable for the 2.2-second final reading hold.

Exact-copy checks pass:

- `SUBJUGATE THE PLANET`
- `rcblanzy.com/books/unknown-process`

These measurements establish technical readability at the rendered resolution. Perceived readability in the intended delivery context remains part of human review.
