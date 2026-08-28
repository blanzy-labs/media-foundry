# MF-019 A/B Integrity

Result: `PASS`

| Controlled field | Candidate A and B |
| --- | --- |
| Runtime | 14.0 s |
| Frame rate | 30 fps |
| Resolution | 768×1152 |
| Frame count | 420 |
| Title | `UNKNOWN PROCESS` |
| CTA | `TRY A WEB GAME` |
| URL | `rcblanzy.com/books/unknown-process` |
| Track | `unknown-process:cold_concrete_anatomy` |
| Cue | `revelation_a`, source 5.0–19.0 s |
| Gain / fades | −1.3 dB; 0.8 s in; 1.4 s out |
| Encoded audio stream MD5 | `f7b5cbdc40dc8096de8738c04ba2491f` |
| Final hold | 3.65 s |

The shared event markers—lever, gauge wake, blue/green/yellow stages, upper-ring activation, reactor escalation, title, CTA, URL, and critical tease—have a maximum measured difference of 0 frames. The tolerance was ±2 frames. Semantic order is identical; pixel identity is intentionally not required.

Candidate A remains byte-identical to the approved MF-018B-R4 artifact. Both final candidates are H.264/AAC, 768×1152, 30 fps, 420 frames, 14 seconds, and 48 kHz; both fully decode.

Evidence: `artifacts/mf-019/validation/backend-timing.json`, `artifacts/mf-019/validation/audio-selection.json`, and `artifacts/mf-019/render-manifest.json`.
