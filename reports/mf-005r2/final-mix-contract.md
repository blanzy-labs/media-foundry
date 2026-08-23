# MF-005R2 Final Mix Contract

Audio priority remains narration, important beat-derived SFX, then music. The approved `Clockwork_Heist.mp3` source is preserved verbatim. The deterministic preparation selects offset 0.0 seconds without looping, normalizes the selection to -24 LUFS, applies -3 dB gain, and spans the full 15-second production with 0.45-second fade-in and 1.0-second fade-out.

Music ducking is derived one-for-one from normalized narration manifest windows: -8 dB, 80 ms attack, and 220 ms release. Existing content cues duck by 3 dB during speech. The final mono PCM mix uses FFmpeg loudness normalization targeting -16 LUFS, -1.5 dBTP, and LRA 7 before AAC finalization. Independent validation allows ±1 LU around the integrated target and no more than 0.5 dB above the true-peak target.

Machine validation covers source readability and hash, continuous activity, fade configuration, exact narration/ducking correspondence, cue activity, full decode, output streams, loudness, and peak. Subjective clarity, musical fit, comedy, and polish remain human-review judgments.
