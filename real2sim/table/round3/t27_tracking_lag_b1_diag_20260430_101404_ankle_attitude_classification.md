# Round 3 Ankle Landing Attitude Classification

- Source touchdown summary: `/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t27_tracking_lag_b1_diag_20260430_101404_touchdown_summary.csv`
- Source diag csv: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv`
- Touchdowns classified: `10`
- Minimum residual for blocker-style root cause: `0.15 rad`
- Attitude dominant axis counts: `{'roll': 5, 'coupled': 1, 'pitch': 4}`
- Touchdown type counts: `{'roll_negative_dominant': 4, 'roll_positive_dominant': 1, 'pitch_roll_coupled': 1, 'heel_first_like': 3, 'toe_first_like': 1}`
- Ankle tracking dominant axis counts: `{'ankle_roll': 6, 'ankle_pitch': 3, 'coupled': 1}`
- Three-layer root cause counts: `{'residual_not_large_enough': 4, 'coupled_geometry': 3, 'command_not_flat': 3}`

- Delay sweep counts: `{'10ms': {'tracking_lag': 1, 'command_not_flat': 6, 'filter_delay': 2, 'coupled_geometry': 1}, '20ms': {'coupled_geometry': 5, 'filter_delay': 1, 'command_not_flat': 3, 'tracking_lag': 1}, '30ms': {'coupled_geometry': 5, 'filter_delay': 1, 'command_not_flat': 3, 'tracking_lag': 1}}`
- Delay-sweep stable touch-downs: `4/10`

## Interpretation Rules

- `foot_flat_error_touch_rad` / `sole_pitch_touch_rad` / `sole_roll_touch_rad` are baseline-corrected foot-frame residuals, not raw link orientation.
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
| 1 | right | 1777515246.159 | heel_first_like | 0.4298 | 0.3698 | 0.2191 | right_ankle_pitch_joint | command_not_flat |
| 2 | right | 1777515247.509 | toe_first_like | 0.3127 | -0.3013 | 0.0837 | right_ankle_pitch_joint | coupled_geometry |
| 3 | left | 1777515247.139 | heel_first_like | 0.2900 | 0.2794 | 0.0775 | left_ankle_pitch_joint | command_not_flat |
| 4 | left | 1777515245.069 | roll_negative_dominant | 0.2624 | -0.0236 | -0.2614 | left_ankle_roll_joint | coupled_geometry |
| 5 | right | 1777515246.899 | heel_first_like | 0.2126 | 0.1765 | 0.1184 | right_ankle_pitch_joint | command_not_flat |
| 6 | right | 1777515245.429 | pitch_roll_coupled | 0.1789 | -0.1186 | 0.1339 | right_ankle_roll_joint | coupled_geometry |
| 7 | left | 1777515245.759 | roll_negative_dominant | 0.1446 | -0.0504 | -0.1355 | left_ankle_roll_joint | residual_not_large_enough |
| 8 | left | 1777515246.439 | roll_negative_dominant | 0.1354 | -0.0656 | -0.1185 | left_ankle_roll_joint | residual_not_large_enough |
| 9 | right | 1777515244.759 | roll_positive_dominant | 0.1183 | -0.0043 | 0.1182 | right_ankle_roll_joint | residual_not_large_enough |
| 10 | left | 1777515244.419 | roll_negative_dominant | 0.0908 | -0.0338 | -0.0843 | left_ankle_roll_joint | residual_not_large_enough |

## Ranked by Dominant-Joint Tracking Error

| rank | side | touchdown_time_sec | dominant_joint | effective_delay_to_touch_tracking_err_rad | effective_delay_raw_rad | touch_q_rad | effective_delay_tau_lpf_ratio | three_layer_root_cause |
|---:|---|---:|---|---:|---:|---:|---:|---|
| 1 | right | 1777515246.899 | right_ankle_pitch_joint | 0.2116 | -0.3486 | -0.1369 | 1.1453 | command_not_flat |
| 2 | right | 1777515244.759 | right_ankle_roll_joint | 0.1731 | 0.1586 | -0.0145 | 0.4230 | residual_not_large_enough |
| 3 | right | 1777515246.159 | right_ankle_pitch_joint | 0.1451 | -0.4100 | -0.2649 | 3.2255 | command_not_flat |
| 4 | left | 1777515247.139 | left_ankle_pitch_joint | 0.1175 | -0.4100 | -0.2925 | 2.3782 | command_not_flat |
| 5 | left | 1777515244.419 | left_ankle_roll_joint | 0.1101 | 0.1354 | 0.0253 | 1.2305 | residual_not_large_enough |
| 6 | left | 1777515245.759 | left_ankle_roll_joint | 0.0999 | 0.1695 | 0.0696 | nan | residual_not_large_enough |
| 7 | left | 1777515246.439 | left_ankle_roll_joint | 0.0709 | 0.0550 | 0.1259 | 0.5329 | residual_not_large_enough |
| 8 | right | 1777515247.509 | right_ankle_pitch_joint | 0.0464 | -0.1070 | -0.0606 | 1.7683 | coupled_geometry |
| 9 | left | 1777515245.069 | left_ankle_roll_joint | 0.0362 | -0.0014 | 0.0348 | 1.9064 | coupled_geometry |
| 10 | right | 1777515245.429 | right_ankle_roll_joint | 0.0174 | -0.0572 | -0.0746 | 0.9247 | coupled_geometry |

## Per-Touchdown Three-Layer Diagnosis

| side | touchdown_time_sec | dominant_axis | dominant_joint | effective_delay_raw_flattening_intent | effective_delay_tau_lpf_ratio | effective_delay_to_touch_tracking_err_rad | three_layer_root_cause | rationale |
|---|---:|---|---|---:|---:|---:|---|---|
| left | 1777515244.419 | roll | left_ankle_roll_joint | 1 | 1.2305 | 0.1101 | residual_not_large_enough | baseline-corrected foot-frame residual is small, so touchdown-side three-layer cause is not treated as a blocker |
| right | 1777515244.759 | roll | right_ankle_roll_joint | 1 | 0.4230 | 0.1731 | residual_not_large_enough | baseline-corrected foot-frame residual is small, so touchdown-side three-layer cause is not treated as a blocker |
| left | 1777515245.069 | roll | left_ankle_roll_joint | 1 | 1.9064 | 0.0362 | coupled_geometry | after 20 ms delay compensation, residual touchdown attitude is more consistent with geometry/coupling than single-axis delay |
| right | 1777515245.429 | coupled | right_ankle_roll_joint | 1 | 0.9247 | 0.0174 | coupled_geometry | after 20 ms delay compensation, residual touchdown attitude is more consistent with geometry/coupling than single-axis delay |
| left | 1777515245.759 | roll | left_ankle_roll_joint | 0 | nan | 0.0999 | residual_not_large_enough | baseline-corrected foot-frame residual is small, so touchdown-side three-layer cause is not treated as a blocker |
| right | 1777515246.159 | pitch | right_ankle_pitch_joint | 0 | 3.2255 | 0.1451 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move the dominant ankle joint toward reducing the baseline-corrected foot-frame residual |
| left | 1777515246.439 | roll | left_ankle_roll_joint | 1 | 0.5329 | 0.0709 | residual_not_large_enough | baseline-corrected foot-frame residual is small, so touchdown-side three-layer cause is not treated as a blocker |
| right | 1777515246.899 | pitch | right_ankle_pitch_joint | 0 | 1.1453 | 0.2116 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move the dominant ankle joint toward reducing the baseline-corrected foot-frame residual |
| left | 1777515247.139 | pitch | left_ankle_pitch_joint | 0 | 2.3782 | 0.1175 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move the dominant ankle joint toward reducing the baseline-corrected foot-frame residual |
| right | 1777515247.509 | pitch | right_ankle_pitch_joint | 1 | 1.7683 | 0.0464 | coupled_geometry | after 20 ms delay compensation, residual touchdown attitude is more consistent with geometry/coupling than single-axis delay |

## Delay Sweep

| side | touchdown_time_sec | delay_10ms_root_cause | delay_20ms_root_cause | delay_30ms_root_cause | delay_sweep_is_stable | delay_sweep_root_cause_sequence |
|---|---:|---|---|---|---:|---|
| left | 1777515244.419 | tracking_lag | coupled_geometry | coupled_geometry | 0 | tracking_lag -> coupled_geometry -> coupled_geometry |
| right | 1777515244.759 | command_not_flat | filter_delay | filter_delay | 0 | command_not_flat -> filter_delay -> filter_delay |
| left | 1777515245.069 | filter_delay | coupled_geometry | coupled_geometry | 0 | filter_delay -> coupled_geometry -> coupled_geometry |
| right | 1777515245.429 | command_not_flat | coupled_geometry | coupled_geometry | 0 | command_not_flat -> coupled_geometry -> coupled_geometry |
| left | 1777515245.759 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |
| right | 1777515246.159 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |
| left | 1777515246.439 | coupled_geometry | coupled_geometry | coupled_geometry | 1 | coupled_geometry -> coupled_geometry -> coupled_geometry |
| right | 1777515246.899 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |
| left | 1777515247.139 | filter_delay | tracking_lag | tracking_lag | 0 | filter_delay -> tracking_lag -> tracking_lag |
| right | 1777515247.509 | command_not_flat | coupled_geometry | coupled_geometry | 0 | command_not_flat -> coupled_geometry -> coupled_geometry |

## Notes

- `toe_first_like` / `heel_first_like` come directly from `sole_pitch_touch_rad` sign.
- Roll currently keeps sign-preserving labels (`roll_negative_dominant` / `roll_positive_dominant`).
- Inside/outside edge mapping is intentionally not hard-coded here, because that depends on confirmed foot frame sign convention.
