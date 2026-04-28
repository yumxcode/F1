# Round 3 Ankle Landing Attitude Classification

- Source touchdown summary: `/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_touchdown_summary.csv`
- Source diag csv: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t26_round3_diag_20260427_170011.csv`
- Touchdowns classified: `8`
- Attitude dominant axis counts: `{'roll': 8}`
- Touchdown type counts: `{'roll_positive_dominant': 4, 'roll_negative_dominant': 4}`
- Ankle tracking dominant axis counts: `{'ankle_roll': 4, 'ankle_pitch': 4}`
- Three-layer root cause counts: `{'coupled_geometry': 2, 'command_not_flat': 4, 'tracking_lag': 2}`

- Delay sweep counts: `{'10ms': {'coupled_geometry': 2, 'command_not_flat': 4, 'tracking_lag': 2}, '20ms': {'coupled_geometry': 2, 'command_not_flat': 4, 'tracking_lag': 2}, '30ms': {'coupled_geometry': 2, 'command_not_flat': 4, 'tracking_lag': 2}}`
- Delay-sweep stable touch-downs: `8/8`

## Interpretation Rules

- `raw` = `pos_des_raw_*`, interpreted as ankle touchdown correction intent.
- `lpf` = `tau_des_lpf_*`, because current ankle joints are parallel joints and the filtered execution path is torque-domain.
- `q` = actual joint position `pos_*`.
- Default delay compensation: uses measured actuator response delay `Δt = 20 ms`.
- Delay sweep: evaluates `Δt = 10 / 20 / 30 ms`, each with a `+/- 10 ms` window.
- Window choice: actuator response onset is about `20 ms`, and small-step completion is about `10 ms`; the sweep therefore uses windowed evidence rather than a single sample.
- `command_not_flat`: raw intent at `touchdown - Δt` still does not keep moving the dominant ankle axis toward flatter touchdown.
- `filter_delay`: raw intent exists at `touchdown - Δt`, but lpf torque response is still notably attenuated.
- `tracking_lag`: raw intent and lpf response both exist at `touchdown - Δt`, but touchdown q still lags target.
- `coupled_geometry`: single-axis chain cannot fully explain foot attitude; pitch/roll coupling or geometry mismatch remains.

## Ranked by Foot-Flat Error

| rank | side | touchdown_time_sec | touchdown_attitude_type | foot_flat_error_touch_rad | sole_pitch_touch_rad | sole_roll_touch_rad | dominant_joint | three_layer_root_cause |
|---:|---|---:|---|---:|---:|---:|---|---|
| 1 | left | 1777280412.454 | roll_positive_dominant | 1.9376 | -0.1601 | 1.9310 | left_ankle_roll_joint | coupled_geometry |
| 2 | right | 1777280414.944 | roll_negative_dominant | 1.8971 | -0.1019 | -1.8943 | right_ankle_roll_joint | coupled_geometry |
| 3 | right | 1777280415.204 | roll_negative_dominant | 1.6386 | -0.1363 | -1.6329 | right_ankle_roll_joint | tracking_lag |
| 4 | right | 1777280415.674 | roll_negative_dominant | 1.6234 | -0.3274 | -1.5900 | right_ankle_roll_joint | tracking_lag |
| 5 | left | 1777280415.464 | roll_positive_dominant | 1.5859 | -0.0980 | 1.5829 | left_ankle_roll_joint | command_not_flat |
| 6 | right | 1777280413.084 | roll_negative_dominant | 1.5847 | -0.0775 | -1.5828 | right_ankle_roll_joint | command_not_flat |
| 7 | left | 1777280414.804 | roll_positive_dominant | 1.5762 | -0.0966 | 1.5733 | left_ankle_roll_joint | command_not_flat |
| 8 | left | 1777280414.954 | roll_positive_dominant | 1.5691 | -0.0478 | 1.5683 | left_ankle_roll_joint | command_not_flat |

## Ranked by Dominant-Joint Tracking Error

| rank | side | touchdown_time_sec | dominant_joint | effective_delay_to_touch_tracking_err_rad | effective_delay_raw_rad | touch_q_rad | effective_delay_tau_lpf_ratio | three_layer_root_cause |
|---:|---|---:|---|---:|---:|---:|---:|---|
| 1 | left | 1777280415.464 | left_ankle_roll_joint | 0.6021 | 0.6400 | 0.0379 | 0.8707 | command_not_flat |
| 2 | left | 1777280414.804 | left_ankle_roll_joint | 0.4002 | 0.5036 | 0.1033 | 0.7890 | command_not_flat |
| 3 | right | 1777280415.204 | right_ankle_roll_joint | 0.3514 | -0.3263 | 0.0251 | 1.0177 | tracking_lag |
| 4 | right | 1777280415.674 | right_ankle_roll_joint | 0.3064 | 0.0701 | -0.2363 | 1.4247 | tracking_lag |
| 5 | left | 1777280414.954 | left_ankle_roll_joint | 0.2118 | 0.2829 | 0.0711 | 0.8500 | command_not_flat |
| 6 | right | 1777280413.084 | right_ankle_roll_joint | 0.1325 | -0.2263 | -0.0939 | 1.8391 | command_not_flat |
| 7 | left | 1777280412.454 | left_ankle_roll_joint | 0.0874 | -0.0083 | 0.0791 | 1.2259 | coupled_geometry |
| 8 | right | 1777280414.944 | right_ankle_roll_joint | 0.0118 | -0.0239 | -0.0358 | 1.5476 | coupled_geometry |

## Per-Touchdown Three-Layer Diagnosis

| side | touchdown_time_sec | dominant_axis | dominant_joint | effective_delay_raw_flattening_intent | effective_delay_tau_lpf_ratio | effective_delay_to_touch_tracking_err_rad | three_layer_root_cause | rationale |
|---|---:|---|---|---:|---:|---:|---|---|
| left | 1777280412.454 | roll | left_ankle_roll_joint | 1 | 1.2259 | 0.0874 | coupled_geometry | after 20 ms delay compensation, residual touchdown attitude is more consistent with geometry/coupling than single-axis delay |
| right | 1777280413.084 | roll | right_ankle_roll_joint | 0 | 1.8391 | 0.1325 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move ankle toward flatter touchdown |
| left | 1777280414.804 | roll | left_ankle_roll_joint | 0 | 0.7890 | 0.4002 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move ankle toward flatter touchdown |
| right | 1777280414.944 | roll | right_ankle_roll_joint | 1 | 1.5476 | 0.0118 | coupled_geometry | after 20 ms delay compensation, residual touchdown attitude is more consistent with geometry/coupling than single-axis delay |
| left | 1777280414.954 | roll | left_ankle_roll_joint | 0 | 0.8500 | 0.2118 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move ankle toward flatter touchdown |
| right | 1777280415.204 | roll | right_ankle_roll_joint | 1 | 1.0177 | 0.3514 | tracking_lag | with 20 ms delay compensation, raw intent and lpf response exist, but touchdown q still lags dominant joint target |
| left | 1777280415.464 | roll | left_ankle_roll_joint | 0 | 0.8707 | 0.6021 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move ankle toward flatter touchdown |
| right | 1777280415.674 | roll | right_ankle_roll_joint | 1 | 1.4247 | 0.3064 | tracking_lag | with 20 ms delay compensation, raw intent and lpf response exist, but touchdown q still lags dominant joint target |

## Delay Sweep

| side | touchdown_time_sec | delay_10ms_root_cause | delay_20ms_root_cause | delay_30ms_root_cause | delay_sweep_is_stable | delay_sweep_root_cause_sequence |
|---|---:|---|---|---|---:|---|
| left | 1777280412.454 | coupled_geometry | coupled_geometry | coupled_geometry | 1 | coupled_geometry -> coupled_geometry -> coupled_geometry |
| right | 1777280413.084 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |
| left | 1777280414.804 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |
| right | 1777280414.944 | coupled_geometry | coupled_geometry | coupled_geometry | 1 | coupled_geometry -> coupled_geometry -> coupled_geometry |
| left | 1777280414.954 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |
| right | 1777280415.204 | tracking_lag | tracking_lag | tracking_lag | 1 | tracking_lag -> tracking_lag -> tracking_lag |
| left | 1777280415.464 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |
| right | 1777280415.674 | tracking_lag | tracking_lag | tracking_lag | 1 | tracking_lag -> tracking_lag -> tracking_lag |

## Notes

- `toe_first_like` / `heel_first_like` come directly from `sole_pitch_touch_rad` sign.
- Roll currently keeps sign-preserving labels (`roll_negative_dominant` / `roll_positive_dominant`).
- Inside/outside edge mapping is intentionally not hard-coded here, because that depends on confirmed foot frame sign convention.
