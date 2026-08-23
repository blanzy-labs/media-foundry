# MF-005R1 Audio Mix Contract

Fixtures may supply optional ambient music. The shared golden bed is a project-owned deterministic four-second lo-fi pluck loop. It is normalized to 48 kHz mono PCM, looped without gaps to production duration, played at -22 dB, faded in over 350 ms, and faded out over 600 ms.

Priority is narration, important content cues, then ambient music. Content cues remain beat-derived and duck by 3 dB under narration. Music ducks by 8 dB with 60 ms attack and 180 ms release for every exact narration window. Narration remains normalized to -18 LUFS/-2 dBTP. The mixer fails on clipping or duration disagreement.

Silence is not inherently invalid. `pause_after` marks editorial silence; configured music continues beneath it, making the pause intentional rather than dead air. Music is optional for legacy/no-music fixtures. Missing required music, unreadable audio, invalid loop duration, and unsafe duck/fade values fail before rendering.
