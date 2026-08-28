# MF-018B-R1 Control-Panel Cleanup

## Upper reactor ring

The ring now contains two separate physical tracks:

- eighteen small fixed details on an outer ellipse;
- six larger linked activation indicators on an inner upper ellipse.

The large count is reduced from twelve to six. The two tracks use different radii, and deterministic geometry validation confirms that large housings neither overlap each other nor cover any small detail. The linked bulbs use amber activation, visually distinct from the console's blue/green/yellow progression.

Review evidence:

- `artifacts/mf-018b-r1/closeups/upper-ring-dormant.png`
- `artifacts/mf-018b-r1/closeups/upper-ring-linked.png`

## Four-dot device

The lower console panel was redrawn with four centers at x = 70, 116, 162, and 208, y = 921. Each housing has an 11 px radius and 46 px center spacing. All four remain inside the panel; the fourth has 19.13 px measured clearance from the sloped border.

The row progresses through blue, green, and yellow rather than duplicating red warning lamps. Yellow is the explicit linked-ring threshold.

Review evidence:

- `artifacts/mf-018b-r1/closeups/four-dot-blue-clean.png`
- `artifacts/mf-018b-r1/closeups/four-dot-yellow-clean.png`

## Lever cleanup

The passive containment-switch node and exported interaction were removed. The remaining red-knob lever is named `startup_lever`, has a stable node path, and is the only lever exposed by the R1 handoff. Its exported state snapshot contains no legacy passive-control entries.
