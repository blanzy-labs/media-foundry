# MF-018B-R2 Cleanup Notes

## Right-side machine

The parent visual contained a heavy horizontal/vertical pipe assembly, a thin highlighted pipe, a round valve/lever handle, and steam emitted from the same attachment. R2 removes those elements and the `SteamVent` scene node. It adds no replacement geometry. The main reactor silhouette and its vertical structural support remain intact.

## Lower control panel

R2 keeps the existing dark teal panel-face fill and removes its teal inner stroke plus the redundant gold top-border segment. Gauges, dials, the red-knob startup lever, and the four-dot device remain in their R1 positions and retain their R1 behavior.

## Preserved behavior and scope

R2 inherits the R1 scene API and playable-ready handoff because no interaction or state interface changed. The R1 promo driver is reused byte-for-byte, preserving startup timing, gauge response, blue/green/yellow stages, yellow-to-ring linkage, reactor escalation, camera behavior, and audio timing.

Deterministic frame comparisons at the blue, yellow, linked-ring, and final-active states found no pixel changes outside the two cleanup regions. No new props, borders, gameplay, publication action, or unrelated redesign were introduced.
