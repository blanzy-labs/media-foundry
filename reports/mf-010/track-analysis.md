# Four-Track Analysis

| Track | Duration | Mean RMS | Range | Proposals | Evidence |
|---|---:|---:|---:|---:|---|
| `abandoned_intake` | 171.886 s | -14.902 dB | -48.388 to -7.947 dB | 5 | `artifacts/mf-010/analysis/abandoned_intake.json` |
| `below_the_iron_floor` | 179.252 s | -13.440 dB | -51.263 to -7.357 dB | 5 | `artifacts/mf-010/analysis/below_the_iron_floor.json` |
| `cold_concrete_anatomy` | 180.898 s | -17.854 dB | -120.000 to -7.521 dB | 5 | `artifacts/mf-010/analysis/cold_concrete_anatomy.json` |
| `concrete_and_chain` | 179.383 s | -15.396 dB | -42.459 to -7.274 dB | 5 | `artifacts/mf-010/analysis/concrete_and_chain.json` |

Analysis uses mono 8 kHz decoding, one-second RMS windows, three-window smoothing, peak amplitude, transient activity, and measured energy change. Labels describe candidates, not asserted song structure. Stable IDs and output ordering are deterministic.

Moderate intentional overlap exists in every track. The overlap report found no pair at or above the highly-overlapping threshold (80% of the smaller region). Detailed pairwise measurements are in each analysis JSON.
