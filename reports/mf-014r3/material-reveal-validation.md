# MF-014R3 material reveal validation

## Result

**PASS**

### Cold physical state

The cold frame is compared with the frozen R1 idle frame using an independently reconstructed phrase mask.

| Metric | Result |
|---|---:|
| Mean glyph delta | 6.263 |
| Changed glyph ratio | 24.204% |
| Full-frame changed ratio | 0.158% |
| Highlighted edge ratio | 31.491% |
| Shadowed edge ratio | 44.804% |

The low whole-frame coverage and mixed-sign edge response support a barely visible recessed state rather than absent text or a flat opacity layer.

### Heat propagation

At the representative thermal frame, the right half of the phrase differs from cold by 47.662 levels versus 9.506 on the left, a 5.014× ratio. This independently confirms the configured right-to-left material propagation rather than a uniform fade.

The four-point thermal route begins at `(0.84, 0.60)`, an exact point on the frozen R1 lower-right circuit. It starts when the title settle completes and overlaps the phrase activation window.

### Settled stamp

| Metric | Result |
|---|---:|
| Changed glyph ratio from cold | 79.525% |
| Local luma contrast | 6.830 |
| Tagline glyph luma P95 | 66 |
| Title-region luma P95 | 133 |
| Added full-frame coverage | 0.344% |

The final stamp is readable but remains substantially quieter than the title. Its permanent dark interior and irregular warm rim remain through the 1.75-second final hold.

Technical measurements establish the intended state changes; whether the result fully escapes a typographic reading remains a human creative judgment.
