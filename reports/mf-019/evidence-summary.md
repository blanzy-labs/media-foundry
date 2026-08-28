# MF-019 Evidence Summary

## Result

`TECHNICAL_PASS` — 32 of 32 independent checks passed. Human backend preference remains `PENDING_HUMAN`; neither candidate is release-ready and nothing was published.

## Proof artifacts

- Godot Candidate A: `artifacts/mf-019/godot/candidate-a.mp4`
- Blender Candidate B: `artifacts/mf-019/blender/candidate-b.mp4`
- Synchronized comparison: `artifacts/mf-019/comparison/side-by-side.mp4`
- Contact sheet: `artifacts/mf-019/comparison/contact-sheet.png`
- Matched frames: `artifacts/mf-019/comparison/matched-frames/`
- Independent result: `reports/mf-019/result.json`

Candidate A is a byte-identical preservation of the approved MF-018B-R4 artifact (`930b0f8bcf264a1ec3af5778e92cdb1958a10de826a6b7c9d670fb88ffed7d2a`). Candidate B is the headless Blender interpretation (`14d2898e8ded37533d9fe47d0e81d75ecab48597f9aaee9e0aa896cdd9aeede8`).

## What was proved

- `GODOT`, `BLENDER`, and `COMPARE` are bounded, declarative backend values; an undeclared backend resolves to `GODOT`.
- Blender 5.2.0 LTS runs headlessly with embedded Python 3.13.13 and `BLENDER_EEVEE`.
- The reusable template and procedural builder produce a 420-frame PNG sequence at 768×1152 and 30 fps.
- Existing valid frames are resumable: the recovery test reused all 420 and rendered zero replacements.
- Separate static and full-render invocations produced pixel-identical pixels at all four composition-gate frames.
- The candidates use identical runtime, resolution, frame rate, approved text, CTA, URL, audio stream, cue, gain, fades, event ordering, and final-hold intent.
- All semantic timing markers match exactly (maximum delta: 0 frames; allowed tolerance: 2).
- Both candidate MP4s and the comparison MP4 decode fully.
- All 13 injected backend-contract failures fail closed with the expected actionable result.

## Boundary

MF-019 adds an optional cinematic render backend; it does not replace Godot, make Blender interactive, export Blender assets to Godot, select a creative winner, or publish media.
