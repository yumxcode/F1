# Coupled Geometry Probe Summary

- Source diag csv: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv`
- Touchdowns analyzed: `4` (first `4` only)
- `sole_pitch_touch_rad / sole_roll_touch_rad` below are baseline-corrected foot-frame residuals, not raw ankle-roll-link orientation.
- Dominant axis counts: `{'roll': 3, 'coupled': 1}`
- Touchdown attitude counts: `{'roll_negative_dominant': 2, 'roll_positive_dominant': 1, 'pitch_roll_coupled': 1}`
- Three-layer root counts: `{'residual_not_large_enough': 2, 'coupled_geometry': 2}`
- Suspected geometry mode counts: `{'parallel_mapping_mismatch': 3, 'touchdown_contact_geometry_bias': 1}`
- Side roll sign majority: `{'left': 'negative', 'right': 'positive'}`
- Cross-side roll pattern: `bilateral_mirror_stable`

## Interpretation

- `roll_axis_sign_or_zero_bias`: touchdown roll sign on one side is stable, ankle roll joint angle itself is not large, but baseline-corrected foot-frame roll residual remains material.
- `pitch_roll_coupling_mismatch`: pitch and roll both materially participate in the corrected touchdown residual.
- `parallel_mapping_mismatch`: left/right roll sign shows mirror-stable behavior or corrected foot-frame tilt is strongly amplified relative to joint-space motion, and tracking cannot explain it away.
- `touchdown_contact_geometry_bias`: joint-space values are not extreme, but corrected touchdown foot-frame residual remains biased and is more consistent with contact geometry or foot reference mismatch.

## Per-Touchdown Table

| side | touchdown_time_sec | attitude_type | sole_pitch_touch_rad | sole_roll_touch_rad | ankle_pitch_q_touch_rad | ankle_roll_q_touch_rad | ankle_pitch_err_touch_rad | ankle_roll_err_touch_rad | roll_to_joint_gain_ratio | suspected_geometry_mode | rationale |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| left | 1777515244.419 | roll_negative_dominant | -0.0338 | -0.0843 | -0.2137 | 0.0253 | -0.1963 | 0.3886 | 3.3338 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small,foot_to_joint_gain_high |
| right | 1777515244.759 | roll_positive_dominant | -0.0043 | 0.1182 | -0.0876 | -0.0145 | -0.0160 | -0.3249 | 8.1437 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small,foot_to_joint_gain_high |
| left | 1777515245.069 | roll_negative_dominant | -0.0236 | -0.2614 | -0.1887 | 0.0348 | -0.2213 | 0.1360 | 7.5113 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small,sole_roll_large,foot_to_joint_gain_high |
| right | 1777515245.429 | pitch_roll_coupled | -0.1186 | 0.1339 | -0.2422 | -0.0746 | -0.1678 | -0.1672 | 1.7948 | touchdown_contact_geometry_bias | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small |

## Side-Level Notes

### left

- Roll sign majority: `negative`
- Mean sole_roll_touch_rad: `-0.1728`
- Mean sole_pitch_touch_rad: `-0.0287`
- Mean ankle_roll_q_touch_rad: `0.0300`
- Mean roll_to_joint_gain_ratio: `5.4226`

### right

- Roll sign majority: `positive`
- Mean sole_roll_touch_rad: `0.1261`
- Mean sole_pitch_touch_rad: `-0.0615`
- Mean ankle_roll_q_touch_rad: `-0.0446`
- Mean roll_to_joint_gain_ratio: `4.9692`

