# MF-018B-R3 Panel Display Notes

## Approved copy

The display reuses repository-approved metadata from `content/fixtures/mf006r4-unknown-process.json`:

- title: `UNKNOWN PROCESS`
- CTA: `TRY A WEB GAME`
- destination: `rcblanzy.com/books/unknown-process`
- canonical destination: `https://rcblanzy.com/books/unknown-process`

## Sequence

The title begins its reveal at 7.10 seconds, followed by the CTA at 8.35 seconds and the URL at 9.55 seconds. All three remain visible through the final frame, providing a 3.65-second complete-copy hold.

## Integration and rendering

The display is a named scene node at `Machines/InformationDisplay`. Its housing occupies the existing dark upper-left machine surface and uses the scene's teal, aged gold, cream, and yellow palette. A small status lamp, inset frame, scan lines, and restrained dividers make it read as machine equipment rather than an overlay.

Copy is rendered with a deterministic 5×7 vector-pixel alphabet. This avoids host-font dependence and works with Godot's SVG rasterizer while preserving a game-like display character. The title receives the strongest size and color treatment, the CTA is secondary, and the two-line URL remains legible within the existing panel width.
