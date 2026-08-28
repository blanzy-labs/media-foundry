# MF-018B-R4 Validation

Result: `TECHNICAL_PASS` — 20/20 checks passed.

Validation covers:

- preserved R3 artifact, scene, script, config, manifest, evidence, and handoff hashes;
- all 17 inherited semantic composition checks;
- valid playable-ready handoff with no interface change;
- standalone scene load with five required nodes and preserved state signals;
- absent legacy partial outline and exactly one closed clean perimeter;
- unchanged panel shape, internal controls, and prop count;
- three matched frame comparisons with zero changed pixels outside the outline region;
- measured reduction of 1,983 doubled teal linework pixels;
- pixel-identical gauges, dials, startup lever, four-dot row, title/CTA display, and reactor;
- byte-identical startup, indicator, and reactor promo driver;
- artifact hashes, complete media decode, evidence counts, and R3/R4 comparisons;
- H.264/AAC delivery at 768×1152, 30 fps, 420 frames, and 14 seconds;
- identical R3/R4 audio at −16.03 LUFS and −2.78 dBTP;
- no gameplay, publication, release-ready, or completed-human-review claim.

Machine-readable checks are in `reports/mf-018b-r4/result.json`. Logs and retained contract results are under `artifacts/mf-018b-r4/logs/` and `artifacts/mf-018b-r4/validation/`.

Technical acceptance is complete. Final ship approval remains subject to human review.
