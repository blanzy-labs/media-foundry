# MF-002 evidence summary

## Assessment

**PASS.** One canonical grammar and one shared renderer produced three independently valid, distinct 15-second videos. On 2026-08-23, the human reviewer confirmed that all three videos passed visual inspection, closing the MF-002 aesthetic acceptance gate.

## Preserved baseline

`./scripts/mf-001-acceptance.sh` passed before MF-002 implementation. The MF-001 reference artifact retained its SHA-256 `3304f3f06ee58736cb53a4efd525da094407c6a5189e850f628f441fb0e69f60`. MF-001 validation was not weakened; the shared validator's new `--slice` argument defaults to `MF-001` for compatibility.

## Environment

- Ubuntu 26.04 LTS, Linux 7.0.0-30-generic, x86_64
- NVIDIA GeForce RTX 5070, display-backed Godot capture
- Godot 4.7.2 Standard
- FFmpeg / FFprobe 8.0.1 with libx264 and AAC
- Python 3.14.4
- Blender 5.2.0 LTS READY in background mode, detected but unused
- Lato Heavy and Regular bundled under SIL Open Font License 1.1

The detailed current inventory is `artifacts/mf-002/doctor.json`.

## Architecture established

- Canonical machine grammar: `config/visual-grammar.json`
- Human grammar guide: `reports/mf-002/visual-grammar.md`
- Shared scene/renderer: `godot/mf002.tscn` and `godot/mf002.gd`
- Structured fixtures: fact, Turd Burglar, and general technology
- Deterministic generated audio vocabulary: intro hit, text pop, transition, emphasis, outro sting
- Independent structural and media validators
- Nine representative frames and a labeled 3×3 contact sheet

The renderer logged the required `INTRO`, `ENTER`, `SETTLE`, `EMPHASIS`, `EXIT`, and `OUTRO` stages for every fixture, plus the workshop, sign, media, paper, tape, and prop layers. Structural validation also proved typography roles, physical surfaces, explicit seeds, safe areas, audio events, font assets, fixture distinction, and canonical documentation.

## Commands executed

```bash
./scripts/mf-001-acceptance.sh
godot --headless --path godot --editor --quit
./scripts/mf-002-acceptance.sh
./scripts/mf-002-failure-tests.sh
```

## Video validation

All videos independently passed file, MP4 container, 1080×1920 resolution, vertical orientation, 15.000-second duration, 30 fps, H.264 video, AAC audio, and complete FFmpeg decode checks.

| Fixture | Bytes | SHA-256 |
|---|---:|---|
| fact | 2,258,011 | `fce59a3804df0be000643655a27f891928eb99ef5b0bc2c5b3591deabc00bf87` |
| turd-burglar | 2,278,789 | `2bea61e1f240749f69daafe1067ff60805dd36dc33bbd7c8cb16b6392533dc42` |
| general | 2,336,286 | `820312e4d780e2ff711e5709f7c03016a7b4a6b183b2c2b04fb58781364f1eab` |

The fact fixture was rendered and finalized a second time. Its second MP4 had the identical SHA-256, proving same-source reproducibility on this workstation.

## Fail-closed result

**PASS: 6, FAIL: 0.** The suite proved rejection of invalid grammar, missing fixture sets, injected renderer failure, missing video, malformed media, and otherwise decodable media that violates the MF-002 technical contract. Faults ran in isolated temporary directories and did not damage accepted artifacts.

## Visual evidence review

The retained frames show a shared workshop environment, crooked wood and paper surfaces, coarse wear, tape, bolts, crates, cable/lamp movement, high-contrast Lato typography, shared intro/outro signs, and three different primitive illustrations. Critical text remains within the declared safe area and is readable in the contact sheet. The fixtures are recognizably related without separate handcrafted scenes.

These observations were followed by human review of all three videos. The reviewer accepted the visual family on 2026-08-23.

## Retained evidence

- `artifacts/mf-002/fact.mp4`
- `artifacts/mf-002/turd-burglar.mp4`
- `artifacts/mf-002/general.mp4`
- `artifacts/mf-002/contact-sheet.png`
- `artifacts/mf-002/frames/{fact,turd-burglar,general}/{intro,main,outro}.png`
- `artifacts/mf-002/render-logs/`
- `artifacts/mf-002/validation/`
- `reports/mf-002/result.json`
- `reports/mf-002/failure-tests.json`

## Limitations and gate

Godot frame capture still requires a display-backed worker; Blender is not part of production rendering. Illustrations are intentionally primitive and the prop vocabulary deliberately small. Fine-grained automatic text-bound analysis is not implemented; contract length limits, deterministic layouts, safe-area geometry, and extracted-frame review provide the current guardrail. No external AI-video system, SaaS, research, publishing, or social-account access was used.

The MF-002 human visual gate is accepted. This acceptance does not authorize publication; publishing remains a separate explicit human decision.
