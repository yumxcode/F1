# Coupled Geometry Probe Summary

- Source diag csv: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv`
- Touchdowns analyzed: `4` (first `4` only)
- Dominant axis counts: `{'roll': 4}`
- Touchdown attitude counts: `{'roll_positive_dominant': 3, 'roll_negative_dominant': 1}`
- Three-layer root counts: `{'command_not_flat': 2, 'coupled_geometry': 2}`
- Suspected geometry mode counts: `{'parallel_mapping_mismatch': 4}`
- Side roll sign majority: `{'left': 'positive', 'right': 'negative'}`
- Cross-side roll pattern: `bilateral_mirror_stable`

## Interpretation

- `roll_axis_sign_or_zero_bias`: touchdown roll sign on one side is stable, ankle roll joint angle itself is not large, but sole roll remains large.
- `pitch_roll_coupling_mismatch`: pitch and roll both materially participate in touchdown tilt.
- `parallel_mapping_mismatch`: left/right roll sign shows mirror-stable behavior or foot-space tilt is strongly amplified relative to joint-space motion, and tracking cannot explain it away.
- `touchdown_contact_geometry_bias`: joint-space values are not extreme, but touchdown foot attitude remains biased and is more consistent with contact geometry or foot reference mismatch.

## Per-Touchdown Table

| side | touchdown_time_sec | attitude_type | sole_pitch_touch_rad | sole_roll_touch_rad | ankle_pitch_q_touch_rad | ankle_roll_q_touch_rad | ankle_pitch_err_touch_rad | ankle_roll_err_touch_rad | roll_to_joint_gain_ratio | suspected_geometry_mode | rationale |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| left | 1777515244.339 | roll_positive_dominant | -0.0060 | 1.7539 | -0.2923 | -0.0470 | -0.1177 | 0.0019 | 37.3053 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small,sole_roll_large,foot_to_joint_gain_high |
| left | 1777515245.299 | roll_positive_dominant | -0.2265 | 1.5426 | -0.0385 | 0.1395 | -0.3715 | 0.1905 | 11.0600 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,sole_roll_large,foot_to_joint_gain_high |
| right | 1777515245.329 | roll_negative_dominant | 0.1497 | -1.8140 | -0.3426 | 0.2018 | 0.0476 | -0.1952 | 8.9905 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,sole_roll_large,foot_to_joint_gain_high |
| left | 1777515245.699 | roll_positive_dominant | -0.0288 | 1.6303 | -0.4263 | -0.0444 | 0.0163 | 0.1165 | 36.7310 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small,sole_roll_large,foot_to_joint_gain_high |

## Side-Level Notes

### left

- Roll sign majority: `positive`
- Mean sole_roll_touch_rad: `1.6423`
- Mean sole_pitch_touch_rad: `-0.0871`
- Mean ankle_roll_q_touch_rad: `0.0160`
- Mean roll_to_joint_gain_ratio: `28.3654`

### right

- Roll sign majority: `negative`
- Mean sole_roll_touch_rad: `-1.8140`
- Mean sole_pitch_touch_rad: `0.1497`
- Mean ankle_roll_q_touch_rad: `0.2018`
- Mean roll_to_joint_gain_ratio: `8.9905`

