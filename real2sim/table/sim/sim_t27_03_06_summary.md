# Sim T27 03/06 Analysis Summary

- Source directory: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/sim`
- Cases analyzed: `4`
- Touchdown slice per case: first `4` touchdown events
- Case code rule: filename suffix last 4 digits, e.g. `3505 -> kp=35, kd=0.5`.

## Metric Table

| metric | meaning |
|---|---|
| `mean_flat_error_rad` | `03` touchdown baseline-corrected foot-frame residual mean over first 4 touchdown events |
| `dominant_axis_counts` | touchdown dominant axis count from `sole_pitch/sole_roll` |
| `root_cause_counts` | `03b` three-layer root cause count |
| `mean_action_to_raw_lag_ms` | sim `06` proxy: policy action to raw joint target lag |
| `mean_raw_to_lpf_lag_ms` | sim `06` proxy: raw joint target to lpf joint target lag |
| `mean_tau_raw_to_tau_lpf_lag_ms` | sim `06` proxy: raw torque to filtered torque lag |
| `mean_raw_to_pos_lag_ms` | sim `06` proxy: raw joint target to actual joint position lag |

## Per-Case Summary

| case | kp/kd | touchdowns | mean_flat_error_rad | large_residual_count | dominant_axis_counts | root_cause_counts | ankle action->raw ms | ankle raw->lpf ms | ankle tau_raw->tau_lpf ms | ankle raw->pos ms |
|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|
| 2504 | 25/0.4 | 4 | 0.1498 | 1 | {'roll': 4} | {'command_not_flat': 2, 'residual_not_large_enough': 1, 'filter_delay': 1} | 0.0000 | 0.0000 | 10.7126 | 144.6204 |
| 3505 | 35/0.5 | 4 | 0.1331 | 2 | {'roll': 3, 'pitch': 1} | {'command_not_flat': 1, 'residual_not_large_enough': 2, 'coupled_geometry': 1} | 0.0000 | 0.0000 | 11.7464 | 30.8343 |
| 4005 | 40/0.5 | 4 | 0.1395 | 2 | {'roll': 3, 'pitch': 1} | {'command_not_flat': 2, 'residual_not_large_enough': 2} | 0.0000 | 0.0000 | 16.4022 | 32.8045 |
| 5008 | 50/0.8 | 4 | 0.1329 | 1 | {'roll': 3, 'pitch': 1} | {'command_not_flat': 2, 'residual_not_large_enough': 2} | 0.0000 | 0.0000 | 11.4632 | 30.0908 |

## 03 Readout

- `03` here fully reuses touchdown detection + baseline-corrected FK foot-frame residual + three-layer classification logic on sim `t27`.
- Interpretation still follows real-data rules: `command_not_flat`, `filter_delay`, `tracking_lag`, `coupled_geometry`.

## 06 Readout

- Sim `t27` does not contain actuator cmd/state, so this is a degraded `06`.
- The usable chain is `action -> pos_des_raw -> pos_des_lpf / tau_des_lpf -> pos`.
- Therefore `raw->pos` should be read as the sim-side total execution lag proxy, not the full hardware execution chain.
