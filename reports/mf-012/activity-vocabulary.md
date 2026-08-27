# MF-012 activity vocabulary v1

Status: engineering demonstration; production approval is pending human review.

The vocabulary contains 18 bounded, subject-agnostic primitives. Each event requires a declared target, start, duration, and intensity. Optional repeat is limited to 1–4. A sequence is limited to 10 entries and to one dominant plus at most two supporting activity families.

| Primitive | Family | Purpose | Required | Optional | Dependencies | Expected visual behavior |
|---|---|---|---|---|---|---|
| `target_acquire` | pursuit | Resolve a target and establish a trackable location. | `target`, `start`, `duration` | `intensity`, `origin` | — | Target marker resolves from an uncertain trace. |
| `target_move` | pursuit | Move an acquired target through bounded scene anchors. | `target`, `start`, `duration` | `intensity`, `origin`, `destination` | `target_acquire` | Target travels laterally while trackers adjust. |
| `target_escape` | pursuit | Break the current trace and overshoot trackers. | `target`, `start`, `duration` | `intensity` | `target_move` | Target exits the trace field and tracking lines miss. |
| `target_reacquire` | pursuit | Resolve the escaped target at a new bounded location. | `target`, `start`, `duration` | `intensity`, `destination` | `target_escape` | Target reappears away from its prior position. |
| `tracker_converge` | pursuit | Converge multiple tracking traces on a resolved target. | `target`, `start`, `duration` | `intensity` | `target_reacquire` | Independent trackers correct course toward one point. |
| `target_lock` | pursuit | Commit a stable target lock after acquisition. | `target`, `start`, `duration` | `intensity` | `target_acquire`, `target_reacquire` | Lock brackets close around the target. |
| `fragment_spawn` | reconstruction | Create deterministic corrupt record fragments. | `target`, `start`, `duration` | `intensity`, `repeat` | — | Separated data pieces appear across the chamber. |
| `fragment_drift` | reconstruction | Move fragments through deterministic spatial drift. | `target`, `start`, `duration` | `intensity` | `fragment_spawn` | Fragments drift inward without random choreography. |
| `fragment_align` | reconstruction | Align fragments into a coherent record grid. | `target`, `start`, `duration` | `intensity` | `fragment_drift` | Pieces settle into bounded rows and columns. |
| `record_reconstruct` | reconstruction | Resolve aligned fragments into one recovered record. | `target`, `start`, `duration` | `intensity` | `fragment_align` | The fragmented field consolidates into a coherent screen. |
| `connection_attempt` | connection | Attempt a link between isolated nodes. | `target`, `start`, `duration` | `intensity`, `repeat` | — | An incomplete segmented link searches between nodes. |
| `signal_travel` | connection | Move visible packets through an attempted connection. | `target`, `start`, `duration` | `intensity`, `repeat` | `connection_attempt` | Packets visibly cross the scene rather than flashing. |
| `bridge_form` | connection | Convert an attempted link into a continuous bridge. | `target`, `start`, `duration` | `intensity` | `connection_attempt`, `signal_travel` | Broken segments join into one continuous path. |
| `bridge_stabilize` | connection | Stabilize a formed bridge and propagate downstream response. | `target`, `start`, `duration` | `intensity` | `bridge_form` | Bridge thickens and wall cells respond in sequence. |
| `path_override` | override | Inject a foreign control signal into an existing route. | `target`, `start`, `duration` | `intensity`, `origin` | — | A warm intrusion travels into the normal circuit system. |
| `network_reroute` | override | Move additional paths onto the overridden route. | `target`, `start`, `duration` | `intensity` | `path_override` | Independent paths change color and flow toward new control. |
| `anomaly_seed` | cascade_failure | Introduce one bounded failure origin. | `target`, `start`, `duration` | `intensity` | — | One node enters a visible warning state. |
| `cascade_failure` | cascade_failure | Propagate ordered failures while preserving one survivor path. | `target`, `start`, `duration` | `intensity` | `anomaly_seed` | Nodes fail progressively and one route remains active. |

## Opening choreography

- `cold_open_active_record` — Begin on an already live coherent record.
- `signal_intrusion` — Begin with a foreign signal entering from a scene edge.
- `slow_system_wake` — Wake sparse wall cells and circuits before projection.
- `target_already_moving` — Begin with the primary target in motion.
- `corrupt_record_resolve` — Begin on separated fragments moving toward order.
- `warning_state_open` — Begin with one bounded warning state already active.
- `single_cell_propagation` — Begin at one wall cell and propagate outward.
- `follow_energy_packet` — Begin close on one packet and follow it to the hub.
- `network_overload_open` — Begin on loaded paths before controlled failure.
- `projection_from_darkness` — Materialize the record from a dark chamber.

## Camera choreography

- `static` — Stable established view.
- `slow_push` — Bounded gradual push toward the primary action.
- `pull_back` — Bounded reveal from close framing to the full system.
- `lateral_track` — Track activity laterally within safe bounds.
- `follow_packet` — Follow a moving signal between bounded anchors.
- `orbit_subtle` — Small deterministic orbital drift around the system.
- `close_to_wide` — Reveal system context from a close detail.
- `wide_to_close` — Resolve from system scale into one record detail.
- `reveal_from_detail` — Begin enlarged and settle into readable full composition.
