# Round 3 Ankle Landing Attitude Classification

- Source touchdown summary: `/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/table/round3/t26_round3_diag_20260427_170011_touchdown_summary.csv`
- Source diag csv: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t26_round3_diag_20260427_170011.csv`
- Touchdowns classified: `8`
- Minimum residual for blocker-style root cause: `0.15 rad`
- Attitude dominant axis counts: `{'roll': 2, 'pitch': 6}`
- Touchdown type counts: `{'roll_positive_dominant': 1, 'heel_first_like': 6, 'roll_negative_dominant': 1}`
- Ankle tracking dominant axis counts: `{'ankle_roll': 5, 'ankle_pitch': 3}`
- Three-layer root cause counts: `{'coupled_geometry': 3, 'tracking_lag': 1, 'command_not_flat': 3, 'residual_not_large_enough': 1}`

- Delay sweep counts: `{'10ms': {'coupled_geometry': 3, 'tracking_lag': 1, 'command_not_flat': 4}, '20ms': {'coupled_geometry': 3, 'tracking_lag': 1, 'command_not_flat': 4}, '30ms': {'coupled_geometry': 4, 'tracking_lag': 1, 'command_not_flat': 3}}`
- Delay-sweep stable touch-downs: `7/8`

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
| 1 | left | 1777280412.454 | roll_positive_dominant | 0.4188 | 0.1503 | 0.3910 | left_ankle_roll_joint | coupled_geometry |
| 2 | right | 1777280414.944 | roll_negative_dominant | 0.3788 | 0.2255 | -0.3043 | right_ankle_roll_joint | coupled_geometry |
| 3 | left | 1777280414.954 | heel_first_like | 0.2641 | 0.2625 | 0.0283 | left_ankle_pitch_joint | command_not_flat |
| 4 | right | 1777280413.084 | heel_first_like | 0.2500 | 0.2499 | 0.0072 | right_ankle_pitch_joint | tracking_lag |
| 5 | right | 1777280413.814 | heel_first_like | 0.2288 | 0.2248 | -0.0426 | right_ankle_pitch_joint | command_not_flat |
| 6 | left | 1777280415.464 | heel_first_like | 0.2166 | 0.2123 | 0.0429 | left_ankle_pitch_joint | coupled_geometry |
| 7 | right | 1777280415.204 | heel_first_like | 0.1959 | 0.1912 | -0.0429 | right_ankle_pitch_joint | command_not_flat |
| 8 | right | 1777280415.674 | heel_first_like | 0.0000 | 0.0000 | 0.0000 | right_ankle_pitch_joint | residual_not_large_enough |

## Ranked by Dominant-Joint Tracking Error

| rank | side | touchdown_time_sec | dominant_joint | effective_delay_to_touch_tracking_err_rad | effective_delay_raw_rad | touch_q_rad | effective_delay_tau_lpf_ratio | three_layer_root_cause |
|---:|---|---:|---|---:|---:|---:|---:|---|
| 1 | right | 1777280413.084 | right_ankle_pitch_joint | 0.4603 | -0.4100 | 0.0503 | 1.0038 | tracking_lag |
| 2 | left | 1777280414.954 | left_ankle_pitch_joint | 0.3226 | -0.4100 | -0.0874 | 0.9980 | command_not_flat |
| 3 | right | 1777280415.204 | right_ankle_pitch_joint | 0.1388 | -0.1554 | -0.0166 | 0.8824 | command_not_flat |
| 4 | left | 1777280412.454 | left_ankle_roll_joint | 0.0874 | -0.0083 | 0.0791 | 1.2259 | coupled_geometry |
| 5 | left | 1777280415.464 | left_ankle_pitch_joint | 0.0488 | -0.1336 | -0.1824 | 1.7698 | coupled_geometry |
| 6 | right | 1777280413.814 | right_ankle_pitch_joint | 0.0248 | -0.0817 | -0.0569 | 2.8522 | command_not_flat |
| 7 | right | 1777280415.674 | right_ankle_pitch_joint | 0.0208 | -0.3646 | -0.3438 | 0.2318 | residual_not_large_enough |
| 8 | right | 1777280414.944 | right_ankle_roll_joint | 0.0118 | -0.0239 | -0.0358 | 1.5476 | coupled_geometry |

## Per-Touchdown Three-Layer Diagnosis

| side | touchdown_time_sec | dominant_axis | dominant_joint | effective_delay_raw_flattening_intent | effective_delay_tau_lpf_ratio | effective_delay_to_touch_tracking_err_rad | three_layer_root_cause | rationale |
|---|---:|---|---|---:|---:|---:|---|---|
| left | 1777280412.454 | roll | left_ankle_roll_joint | 1 | 1.2259 | 0.0874 | coupled_geometry | after 20 ms delay compensation, residual touchdown attitude is more consistent with geometry/coupling than single-axis delay |
| right | 1777280413.084 | pitch | right_ankle_pitch_joint | 1 | 1.0038 | 0.4603 | tracking_lag | with 20 ms delay compensation, raw intent and lpf response exist, but touchdown q still lags dominant joint target |
| right | 1777280413.814 | pitch | right_ankle_pitch_joint | 0 | 2.8522 | 0.0248 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move the dominant ankle joint toward reducing the baseline-corrected foot-frame residual |
| right | 1777280414.944 | roll | right_ankle_roll_joint | 1 | 1.5476 | 0.0118 | coupled_geometry | after 20 ms delay compensation, single-axis command chain is still insufficient to explain touchdown attitude |
| left | 1777280414.954 | pitch | left_ankle_pitch_joint | 0 | 0.9980 | 0.3226 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move the dominant ankle joint toward reducing the baseline-corrected foot-frame residual |
| right | 1777280415.204 | pitch | right_ankle_pitch_joint | 0 | 0.8824 | 0.1388 | command_not_flat | with 20 ms actuation delay compensation, raw intent still does not move the dominant ankle joint toward reducing the baseline-corrected foot-frame residual |
| left | 1777280415.464 | pitch | left_ankle_pitch_joint | 1 | 1.7698 | 0.0488 | coupled_geometry | after 20 ms delay compensation, residual touchdown attitude is more consistent with geometry/coupling than single-axis delay |
| right | 1777280415.674 | pitch | right_ankle_pitch_joint | 0 | 0.2318 | 0.0208 | residual_not_large_enough | baseline-corrected foot-frame residual is small, so touchdown-side three-layer cause is not treated as a blocker |

## Delay Sweep

| side | touchdown_time_sec | delay_10ms_root_cause | delay_20ms_root_cause | delay_30ms_root_cause | delay_sweep_is_stable | delay_sweep_root_cause_sequence |
|---|---:|---|---|---|---:|---|
| left | 1777280412.454 | coupled_geometry | coupled_geometry | coupled_geometry | 1 | coupled_geometry -> coupled_geometry -> coupled_geometry |
| right | 1777280413.084 | tracking_lag | tracking_lag | tracking_lag | 1 | tracking_lag -> tracking_lag -> tracking_lag |
| right | 1777280413.814 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |
| right | 1777280414.944 | coupled_geometry | coupled_geometry | coupled_geometry | 1 | coupled_geometry -> coupled_geometry -> coupled_geometry |
| left | 1777280414.954 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |
| right | 1777280415.204 | coupled_geometry | coupled_geometry | coupled_geometry | 1 | coupled_geometry -> coupled_geometry -> coupled_geometry |
| left | 1777280415.464 | command_not_flat | command_not_flat | coupled_geometry | 0 | command_not_flat -> command_not_flat -> coupled_geometry |
| right | 1777280415.674 | command_not_flat | command_not_flat | command_not_flat | 1 | command_not_flat -> command_not_flat -> command_not_flat |

## Notes

- `toe_first_like` / `heel_first_like` come directly from `sole_pitch_touch_rad` sign.
- Roll currently keeps sign-preserving labels (`roll_negative_dominant` / `roll_positive_dominant`).
- Inside/outside edge mapping is intentionally not hard-coded here, because that depends on confirmed foot frame sign convention.
