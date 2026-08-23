# MF-002R1 Layout Validation

## Governing invariant

For each dynamic text instance, `rendered_text_rect ⊆ assigned_safe_rect`. Independent acceptance also checks that fixed safe areas are contained by their declared panels, derived safe areas remain inside their fixture-declared decoration containers, font sizes and line counts remain within role constraints, and configured major regions do not intersect.

## Fitting order

1. Load the role's preferred font size and preferred line spacing.
2. Wrap using Godot's loaded font metrics and the assigned safe width.
3. Measure maximum line width and total block height.
4. Decrease the size by one pixel down to the configured minimum.
5. Repeat the bounded size sequence at the configured minimum line spacing.
6. Accept the first contained rectangle, or fail before rendering with an actionable diagnostic.

No branch truncates, clips, hides, or rewrites fixture content. Each attempt is bounded by `typography.max_fit_iterations` (32).

## Authoritative regions

The fixed regions are `INTRO_SAFE_AREA`, `INTRO_LABEL_SAFE_AREA`, `HEADLINE_SAFE_AREA`, `BODY_SAFE_AREA`, `EMPHASIS_SAFE_AREA`, `LABEL_SAFE_AREA`, `OUTRO_SAFE_AREA`, and `OUTRO_LABEL_SAFE_AREA`. Note and counter labels/values use the template's three declared derived safe-area rules.

The configured collision checks cover headline/body within the content note and body/emphasis in stage coordinates. Decorative note/counter content is independently constrained to its own container.

## Machine-readable evidence

- Aggregate validation: `artifacts/mf-002r1/validation/layout.json`
- Per-fixture geometry: `artifacts/mf-002r1/layout/*.json`
- Failure evidence: `reports/mf-002r1/failure-tests.json`
- Final result: `reports/mf-002r1/result.json`

Aggregate result: **PASS** for intro, headline, body, emphasis, labels, outro, and overlap checks across nine passing fixtures. The deliberate overflow fixture returned the expected `HEADLINE_LAYOUT_FAILED` result.

## Debug inspection

Passing `--debug-layout` draws green safe rectangles and red measured text rectangles using the same local transforms as production content. The flag is absent from normal acceptance renders. The Venus debug frame is preserved at `artifacts/mf-002r1/frames/venus-safe-areas-debug.png`.
