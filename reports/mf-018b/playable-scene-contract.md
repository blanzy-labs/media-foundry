# Playable Scene Package Contract

Contract: `playable_scene_package_v1`

The package separates three responsibilities:

1. `godot/mf018b_pulp_scene.tscn` and `godot/mf018b_pulp_scene.gd` contain machines, named controls, visual state, setters, signals, and deterministic rendering.
2. `godot/mf018b_promo_driver.gd` applies the 14-second Media Foundry timeline through the public setters.
3. A future Game Foundry consumer may omit the promo driver and call the same setters in response to its own gameplay. No Game Foundry dependency exists.

## External state API

- `set_reactor_energy(value)`
- `set_temperature(value)`
- `set_containment(value)`
- `set_field_strength(value)`
- `set_pressure(value)`
- `set_warning_level(value)`
- `set_machine_state(state)`
- `set_control_value(id, value)`
- `activate_control(id)`
- `state_snapshot()`

Normalized values clamp to `[0.0, 1.0]`. Visual states are `DORMANT`, `STABLE`, `UNSTABLE`, and `CRITICAL`.

## Interaction points

- `coolant_dial` → `Machines/Console/Controls/DialCoolant`
- `field_dial` → `Machines/Console/Controls/DialField`
- `containment_switch` → `Machines/Console/Controls/SwitchContainment`
- `emergency_lever` → `Machines/Console/Controls/LeverEmergency`

Each entry declares type, range, default, animation hook, audio hook, and affected visual signals in the handoff manifest.

## Ownership boundary

Media Foundry owns the visual world, lighting, scene animation, audio presentation, promo driver, and interaction metadata. Input, objectives, rules, scoring, difficulty, progression, win/fail conditions, saves, and platform integrations remain explicitly assigned to Game Foundry. No gameplay was implemented.
