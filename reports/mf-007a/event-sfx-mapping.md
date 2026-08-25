# MF-007A Event-SFX Mapping

| Event | Visible trigger | Time | Sound family |
|---|---|---:|---|
| `circuit_trace` | `path_draw_start` | 0.05s | `conductive_trace` |
| `energy_flow_out` | `energy_flow` | 0.75s | `moving_energy` |
| `node_charge` | `central_node_charge` | 1.45s | `power_build` |
| `node_overload` | `spark_burst` | 2.70s | `electrical_physical_impact` |
| `projection_start` | `screen_initialize` | 2.90s | `projection_ignition` |
| `simon_search` | `record_query_1` | 6.20s | `searching_trace` |
| `simon_lock` | `record_lock_1` | 8.65s | `restrained_confirmation` |
| `refresh_1` | `record_reset_1` | 9.70s | `record_refresh` |
| `bridge_search` | `record_query_2` | 10.00s | `dual_node_bridge` |
| `bridge_lock` | `record_lock_2` | 13.00s | `restrained_confirmation` |
| `refresh_2` | `record_reset_2` | 13.95s | `record_refresh` |
| `biometric_scan` | `record_query_3` | 14.25s | `active_scan` |
| `hidden_reveal` | `record_lock_3` | 17.30s | `low_confirmation` |
| `projection_collapse` | `screen_collapse` | 19.10s | `field_deconstruction` |
| `return_energy` | `return_energy` | 20.70s | `reverse_energy` |
| `cta_transmission` | `cta_energy` | 22.40s | `signal_reroute` |
| `cta_lock` | `cta_lock` | 23.65s | `final_signal_lock` |
| `machine_power_down` | `cta_settle` | 26.30s | `environmental_decay` |

The four orange indicators and powered wall cells have no dedicated sound event.
