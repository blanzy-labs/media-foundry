# MF-012 compatibility report

Result: **PASS**.

MF-011 remains the golden production baseline. Its grammar, style configuration, campaign manifest, renderer baseline, activity controls, and representative outputs are recorded in `config/production-baselines/mf011-golden.json`.

All three representative legacy fixtures rendered through their pre-existing strategies. The selected output PNGs are byte-identical to their archived references:

| Baseline | Fixture | Frame | Actual/expected SHA-256 | Result |
|---|---|---:|---|---|
| MF-011 | `content/fixtures/mf011/01-simon-target-acquired.json` | 461 | `bb8d0d615befab967914f8e7bd531dd4e07fc68fe880988493226edeabd81abf` | PASS |
| MF-008B-R1 | `content/fixtures/mf008b-r1/leo-zeph-investigation.json` | 481 | `565c3ebab7f7a936361ad4d9090095ea41069e4890cc1b62d50276ad92b90d8f` | PASS |
| MF-006R9 | `content/fixtures/mf006r9-unknown-process.json` | 349 | `3d4a5e0b40aa721a7fc08aadae28d231b0a6bd658425189251ad2dfe435efa8e` | PASS |

The MF-012 renderer selection is opt-in via `godot_activity_vocabulary_v1`. Fixtures without that preference retain the legacy/default path. Existing creative profiles such as pursuit, mystery, and revelation remain usable and are not replaced by the new activity layer.
