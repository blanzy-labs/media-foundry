# MF-002R1 Evidence Summary

## Result

Technical acceptance: **PASS**. Human visual review remains required before publication or use as an approved production artifact.

Acceptance command: `./scripts/mf-002r1-acceptance.sh`

## Observed defect and root cause

The unchanged production Venus fixture was rendered before the change and preserved at `artifacts/mf-002r1/before/venus-problem.png`. The old `_center_text` helper wrapped to a fixed width, but never measured the resulting block height or checked it against a panel. The headline was centered on a fixed baseline at local y=-63, so a three-line block extended above the paper note into the dark media region. There was no minimum-size policy, layout rejection, or machine-readable geometry result.

## Renderer hardening

The shared renderer now preflights all fixture-driven intro, headline, body, emphasis, primary label, outro, outro-label, note-label, and counter text before rendering frame zero. It uses Godot font metrics, wraps at the safe-area width, decreases font size through a bounded sequence, then tries the configured minimum line spacing. It accepts only when the measured rectangle is contained by its assigned safe rectangle. No content is hidden or truncated.

The template grammar is authoritative for typography constraints, fixed safe areas, panel bounds, derived decoration safe-area rules, collision pairs, and the maximum fitting iterations. There is no Venus ID or content-specific renderer branch.

## Safe-area and readability policy

- Every role defines preferred/minimum font size, maximum lines, preferred/minimum line spacing, wrapping, fit mode, and alignment.
- Headline minimum is 27 internal pixels (54 pixels at output scale), greater than the body preferred size of 23, preserving `HEADLINE > BODY`.
- Fixed safe areas must fit inside their declared panels. Prop text uses declared inset rules and must fit inside the corresponding note/counter container.
- Headline/body and body/emphasis stage regions are checked for collision using configured stage origins.
- Fitting is capped at 32 attempts per element.
- Exhaustion returns an actionable `*_LAYOUT_FAILED` result before any production render is accepted.

## Fixtures and results

| Fixture | Headline size | Lines | Result |
|---|---:|---:|---|
| stress-short | 39 | 1 | PASS |
| stress-normal | 39 | 2 | PASS |
| stress-long | 29 | 3 | PASS |
| stress-overflow | minimum exhausted | — | EXPECTED FAIL |
| fact | 39 | 2 | PASS |
| turd-burglar | 39 | 2 | PASS |
| general | 39 | 2 | PASS |
| books | 39 | 2 | PASS |
| mythadis | 37 | 2 | PASS |
| venus | 35 | 2 | PASS |

All six regression fixtures produced 1080×1920, 30fps, 15-second H.264/AAC MP4 files and passed full-decode validation. The original MF-002 structural contract validator also passes with the hardened grammar.

## Failure tests

The oversized headline, malformed font bounds, missing headline safe area, and forced minimum-size exhaustion all returned non-zero and emitted machine-readable FAIL reports with fixture, role, safe area, minimum size where relevant, and rejection reason. See `reports/mf-002r1/failure-tests.json`.

## Venus before/after

- Before: `artifacts/mf-002r1/before/venus-problem.png`
- After: `artifacts/mf-002r1/after/venus-corrected.png`
- Comparison: `artifacts/mf-002r1/frames/venus-before-after.png`
- Debug geometry: `artifacts/mf-002r1/frames/venus-safe-areas-debug.png`

The corrected Venus headline uses two lines at size 35. Its measured local rectangle is x=-192.5, y=-95.9, width=385, height=80.8, contained by `HEADLINE_SAFE_AREA` x=-194, y=-106, width=388, height=101. It no longer intrudes into the media region, does not clip, and remains larger than body text at size 23.

## Known limitations

- The fitter wraps at whitespace and deliberately rejects a single word wider than its safe area; it does not hyphenate or rewrite content.
- Geometry validation uses font metrics and declared layout regions, not semantic or pixel-level visual scoring.
- Debug outlines are opt-in via `--debug-layout`; the acceptance renders do not enable them.
- Human review is still required to judge taste, phone readability, and preservation of the scrappy visual character.

## Recommendation

**Technical PASS; proceed to the MF-002R1 human review gate.** Do not treat the artifacts as publication-approved until that review passes.
