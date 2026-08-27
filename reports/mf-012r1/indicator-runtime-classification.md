# Indicator pulse runtime classification

Date: 2026-08-25

Result: **PASS**

## Classification and cause

`godot/indicator_pulse_stage.gd` is a scene-attached runtime component. It extends
`integrated_lower_right_stage.gd`, whose inheritance chain ends at `Node2D`. The
component is therefore valid for scene instantiation and invalid as the target of
Godot's `--script` option, which requires `SceneTree` or `MainLoop`.

The reported alert is consistent with launching the runtime component directly:

```text
godot --path godot --script res://indicator_pulse_stage.gd
```

This is an entry-point error, not a defect in the component's inheritance.
`indicator_pulse_stage.gd` remains a `Node2D`; its inheritance was not changed.

## Complete invocation and reference inventory

Executable paths:

- `godot/mf002.gd` preloads the component, selects it for
  `godot_indicator_pulse_refinement`, calls `IndicatorPulseStageScript.new()`,
  adds it to the scene tree, and configures it.
- `godot/activity_vocabulary_stage.gd` subclasses the component. It is selected
  and instantiated by `godot/mf002.gd` for `godot_activity_vocabulary_v1`.
- `godot/indicator_pulse_stage_headless.gd` is the new standalone `SceneTree`
  test entry point. It loads and instantiates both runtime classes without
  converting either class into a command-line script.
- `scripts/doctor.sh` invokes only that headless harness. No checked-in command
  invokes `indicator_pulse_stage.gd` directly with `--script`.

Configuration-driven runtime selections occur in 19 fixtures:

- `content/fixtures/mf006r9-unknown-process.json`
- all 3 fixtures under `content/fixtures/mf008b-r1/`
- all 3 fixtures under `content/fixtures/mf008c/`
- all 10 fixtures under `content/fixtures/mf011/`
- both fixtures under `content/fixtures/mf012r1/`

Non-invoking references are also present in:

- `config/production-grammars/unknown-process-recovered-record-v1.json`
- `config/production-grammars/unknown-process-recovered-record-v2.json`
- `scripts/package_mf012r1_evidence.py`
- `scripts/preflight_mf008b_creative_batch.py`
- `scripts/run_mf008c_proof.py`
- `scripts/run_mf012_demos.py`
- `scripts/run_mf012r1.py`
- `scripts/validate_indicator_pulse_runtime.py`

Those files hash, package, document, or validate the component; they do not pass
it directly to Godot's `--script` option.

## Validation rerun

The independent runtime evidence is in
`artifacts/mf-012r1/validation/indicator-runtime-harness.json`.

- Headless component harness: PASS, exit 0, marker observed.
- MF-012R1 restrained fixture through `res://mf002.tscn`: layout PASS,
  micro-variation PASS, exit 0.
- MF-012R1 reactive fixture through `res://mf002.tscn`: layout PASS,
  micro-variation PASS, exit 0.
- MF-012R1 configuration validators: 2/2 PASS.
- MF-012R1 isolated failure tests: 6/6 PASS.
- Project doctor, including the new component/harness check: PASS.
- GUI/MainLoop error markers across the harness and both scene runs: none.

There is no MF-013 implementation, fixture, runner, or validation path in this
repository, so an MF-013 validation could not be run. The independent evidence
records this as `NOT_PRESENT`; it is not represented as a pass.

## Files changed for this correction

- `godot/indicator_pulse_stage_headless.gd`
- `scripts/doctor.sh`
- `scripts/validate_indicator_pulse_runtime.py`
- `artifacts/mf-012r1/validation/indicator-runtime-harness.json`
- `reports/mf-012r1/indicator-runtime-classification.md`

Runtime component changes: **0**.
