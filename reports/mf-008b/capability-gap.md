# MF-008B Capability Gap

The preflight found six blockers:

1. The recovered-record stage cannot select one investigation mechanism. `_record_index()` advances through all three branches, and `_draw_record_content()` hardcodes tracking, Leo/Zeph linkage, and biometrics.
2. The timeline exposes generic record typing/refresh events, not the required per-brief unique events.
3. Accent colors, projection treatment, camera magnitude, colored cells, and CTA colors are not fixture-configurable.
4. Indicator pulse periods, offsets, and durations are constants.
5. The approved cue map has one section, `baseline_full`; no pursuit, investigation, or revelation cue sections are approved.
6. Runtime is pinned at 28 seconds, so natural per-story runtime variation is not configurable within this frozen grammar.

The smallest future engineering slice would add schema-validated, bounded configuration for mechanism choice, event sequences, cosmetic profiles, and timing while retaining the same visual grammar and validators. That work is deliberately not part of MF-008B. Cue selection remains a separate content approval task.
