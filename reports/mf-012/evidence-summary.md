# MF-012 evidence summary

Technical result: **TECHNICAL_PASS**. Human creative review: **PENDING_HUMAN**. Publication count: **0**.

MF-012 adds an opt-in vocabulary of 18 reusable activity primitives, 10 opening choreographies, and 9 bounded camera choreographies while retaining the MF-011 recovered-record world and legacy rendering paths.

| Demo | Dominant | Supporting | Opening | Camera | Runtime/frames | SHA-256 |
|---|---|---|---|---|---|---|
| 01-moving-target-pursuit | pursuit | none | `target_already_moving` | `lateral_track` | 11s / 330 | `71376bc91f727d5f8732c5076f2f62d2247ba13701f7576929863c1f5e2984da` |
| 02-record-reconstruction | reconstruction | none | `corrupt_record_resolve` | `reveal_from_detail` | 12s / 360 | `98bfa50d8452bc121ca484cdaaf5e4dc2c50c5267f7fd75e6787246331ac5782` |
| 03-signal-bridge | connection | none | `follow_energy_packet` | `follow_packet` | 12s / 360 | `a3bddb24e87bfa151ec65877c07986e0abd8b672d75149d74cd9c6cffba9b4b0` |
| 04-override-reroute | override | none | `signal_intrusion` | `wide_to_close` | 11s / 330 | `bd9f2936b88548a331fd2adff35fc91e39ecac3f37a24e0b6209c7b182373d7e` |
| 05-cascade-failure | cascade_failure | none | `warning_state_open` | `pull_back` | 13s / 390 | `ff61d1accd96f9d4d1441ee04dbe47aac4dae4f4cc4e33636cb45c02bf771d3c` |

All five demonstrations passed config validation, timeline preflight, full rendering, encoding, media validation, and independent output validation. Motion strips and four representative frames are packaged per demo. Pursuit reproduced byte-identically on a second full run. Six isolated failure cases passed. MF-011, MF-008B-R1, and MF-006R9 representative frames reproduced byte-for-byte.

## Production status and next recommendation

No activity is production-approved yet because human review is pending. Engineering-demonstrated candidates are pursuit, reconstruction, connection, override, and cascade failure.

The bounded v1 intentionally leaves classification, scan/reveal, corruption, network-growth, and decryption families for a later evidence-led extension. Add them only if campaign briefs reveal a concrete gap; do not expand the vocabulary speculatively.

Do not run the post-MF-012 five-video campaign test yet. After at least four demos receive human approval, use one approved dominant choreography per video, avoid adjacent repeated openings, keep one dominant plus no more than two supporting families, and preserve the existing music-only campaign policy.

## Evidence locations

- Demo videos: `artifacts/mf-012/demos/`
- Representative frames: `artifacts/mf-012/representative-frames/`
- Motion evidence: `artifacts/mf-012/motion-evidence/`
- Machine validation: `artifacts/mf-012/validation/`
- Contract and review documents: `reports/mf-012/`

The initial failed preflight archive remains outside the repository at `/home/blanzy/media-foundry-output/mf012/activity-vocabulary-v1/run-000-preflight-failure`. It failed because the first scaled demo fixture produced a sub-one-second intro beat; the fixture builder was corrected before the canonical run. No failed output was treated as acceptance evidence.
