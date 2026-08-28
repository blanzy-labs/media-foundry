# MF-018B-R4 Outline Cleanup Notes

## Cause

The R3 panel contained two perimeter treatments: an older partial teal outline from the parent scene and the newer continuous sloped outline. Where both remained visible, especially along the left and upper edges, the linework read as doubled and slightly misaligned.

## Cleanup

R4 preserves the parent panel-face fill but suppresses its legacy partial stroke. The single R3 perimeter remains unchanged:

`M51 613 L228 575 L245 625 L240 946 L52 982 Z`

It is a closed path with one consistent three-pixel teal stroke and rounded joins. The gold outer structure and restrained gold upper highlight remain part of the established industrial visual language.

## Preserved scope

No panel geometry, internal control, prop, layout, animation, display copy, reactor behavior, camera behavior, or audio logic changed. The R1 promo driver is reused byte-for-byte. Image comparison confirms that all changed pixels are confined to the control-panel perimeter region.
