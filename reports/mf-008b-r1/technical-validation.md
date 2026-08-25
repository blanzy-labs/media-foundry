# Technical Validation

Independent batch validation: **PASS**.

All three candidates passed timeline execution, mechanism exclusivity, unique-event observation, profile loading, campaign identity, cue selection contract, source hash, music offsets, audio mix, media validation, decode, duration, and final artifact hash checks.

| Candidate | Video/audio decode | Duration | Final peak | RMS | Clipped samples |
|---|---|---:|---:|---:|---:|
| Simon — Pursuit | PASS | 27.0s | 0.794769 | -14.369 dBFS | 0 |
| Leo + Zeph — Investigation | PASS | 28.0s | 0.797424 | -13.122 dBFS | 0 |
| Kill-Switch — Revelation | PASS | 29.0s | 0.796783 | -14.322 dBFS | 0 |

See `artifacts/mf-008b-r1/validation/batch-validation.json` and each job's `output.json`, `media.json`, `mix.json`, and `ffprobe.json`.
