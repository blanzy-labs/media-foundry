# MF-002 — Scrappy visual grammar v1

## Goal

Prove that one source-controlled visual grammar and one Godot renderer can produce three different 15-second subjects that clearly belong to one scrappy indie-game family.

## Architecture

```text
three JSON fixtures ─┐
visual-grammar.json ─┼─> mf002.gd shared renderer ─> PNG frames
Lato OFL fonts ──────┘                              + generated WAV
                                                        |
                                                        v
                                            FFmpeg H.264/AAC MP4
                                                        |
                                                        v
                                           FFprobe + complete decode
```

MF-001's doctor, finalizer settings, independent validator, evidence layout, and fail-closed philosophy remain intact. `validate_media.py` gained an optional slice identifier while preserving MF-001 as its default.

## Fixtures

- `fact`: a strange octopus fact with a radial creature illustration.
- `turd-burglar`: the stealth dung-beetle game premise with a beetle and suspicious ball.
- `general`: a self-referential JSON robot topic with a battered terminal illustration.

All differences enter through structured content, palette data, an explicit seed, and a primitive illustration kind. There is one scene and one renderer.

## Validation

`./scripts/mf-002-acceptance.sh` validates the workstation, grammar schema, typography, surfaces, safe area, motion and audio vocabularies, all fixture contracts, required runtime layers/stages, every MP4, nine evidence frames, the contact sheet, and an identical-hash repeat render of the fact fixture.

`./scripts/mf-002-failure-tests.sh` exercises invalid grammar, missing fixtures, render failure, missing video, malformed media, and valid media that violates the format contract.

## Scope boundary

MF-002 adds no browser renderer, SaaS, AI video, social integration, voice system, Blender production pipeline, research, or autonomous publishing. The human visual gate remains pending after technical acceptance.
