# MF-005 Narration Contract

Narration is optional and belongs to a beat. `null` or `{ "enabled": false }` preserves the existing silent behavior. A narrated beat selects exactly one mode: `source` for supplied audio, or `generate: true` with `text`, `provider`, and `voice`. `narration_required_beats` may make selected beat narration mandatory.

Pre-generated WAV, MP3, FLAC, M4A, AAC, and OGG inputs are accepted when FFprobe finds a valid audio stream. Deterministic acceptance uses local FFmpeg-Flite WAV fixtures. The optional generated boundary currently exposes `local_ffmpeg_flite` with voices `slt`, `kal`, `kal16`, `awb`, and `rms`; no live SaaS or credentials are required.

Every segment defaults to 150 ms lead-in and tail-out. Normalized duration must fit between those boundaries. Audio is normalized by FFmpeg to 48 kHz mono PCM16 using EBU R128 `loudnorm` with targets of -18 LUFS integrated, -2 dB true peak, and LRA 7. Overflow, truncation, implicit speed changes, and overlap are forbidden.

The deterministic mixer gives narration priority over content cues and the background bed. Existing cue/bed audio is reduced by 6 dB during narration with 30 ms linear attack/release; cues are retained. The mixer fails on clipping.

Generated requests are cached by SHA-256 of provider, provider version, voice, text, and speech settings. Both cached audio and metadata are hash-checked; incomplete or stale/corrupt entries fail closed. Manifests record beat linkage, paths, duration, format, text, provenance, hashes, provider, voice, cache state, and exact timing.

Example:

```json
{
  "id": "setup",
  "type": "statement",
  "duration": 2.5,
  "text": "WE'RE MAKING A GAME...",
  "narration": {
    "source": "media/audio/setup.wav",
    "text": "We are making a game.",
    "lead_in": 0.15,
    "tail_out": 0.15
  }
}
```
