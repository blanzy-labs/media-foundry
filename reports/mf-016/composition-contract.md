# MF-016 composition contract

## Scene hierarchy

- Primary: `main_reactor`
- Secondary: `left_control_bank`
- Tertiary: `rear_tower`, `left_wall_pipe`, `floor_plinth`
- Preserved negative space: `negative_space_upper_left`

## Object-purpose table

| Object | Role | Purpose | Zone | Occlusion permission |
| --- | --- | --- | --- | --- |
| room_shell | background_structure | establish location; support perspective | background_full | background only |
| main_reactor | hero | story, state, light, eye guidance, scale | hero_center_right | background only |
| left_control_bank | machine_support | state, scale, depth | support_left | background only |
| rear_tower | depth_element | depth, scale, perspective | background_full | background only |
| left_wall_pipe | depth_element | location, perspective | background_full | background only |
| floor_plinth | foreground_frame | foreground depth, frame hero, perspective | foreground_bottom | background only |

Every object carries `remove_if_no_visual_purpose: true`. No object uses `decorative` or `fill_empty_space`.

## Static gate

Machine validation is `PASS`, human status is `PENDING_HUMAN`, and the resulting authorization state is `BLOCKED_COMPOSITION`. Changing the gate state field alone cannot authorize animation: the integration function recomputes validation and requires an identified human reviewer with `APPROVED` status.
