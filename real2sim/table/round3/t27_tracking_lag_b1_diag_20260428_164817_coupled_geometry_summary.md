# Coupled Geometry Probe Summary

- Source diag csv: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv`
- Touchdowns analyzed: `4` (first `4` only)
- Dominant axis counts: `{'roll': 4}`
- Touchdown attitude counts: `{'roll_positive_dominant': 2, 'roll_negative_dominant': 2}`
- Three-layer root counts: `{'coupled_geometry': 3, 'command_not_flat': 1}`
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
| left | 1777366098.099 | roll_positive_dominant | -0.0500 | 1.7795 | -0.2573 | 0.0190 | -0.0639 | -0.0981 | 93.6026 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small,sole_roll_large,foot_to_joint_gain_high,joint_tracking_not_extreme |
| right | 1777366098.459 | roll_negative_dominant | 0.0429 | -1.6351 | -0.3466 | 0.0929 | 0.0891 | -0.0934 | 17.5946 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small,sole_roll_large,foot_to_joint_gain_high,joint_tracking_not_extreme |
| right | 1777366098.749 | roll_negative_dominant | -0.0594 | -1.6026 | 0.1419 | -0.0061 | -0.5519 | -0.1703 | 262.2538 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small,sole_roll_large,foot_to_joint_gain_high |
| left | 1777366098.819 | roll_positive_dominant | -0.0626 | 1.7193 | -0.3009 | -0.0015 | -0.1091 | 0.0303 | 1115.6651 | parallel_mapping_mismatch | roll_sign_stable,left_right_roll_mirror_stable,ankle_roll_q_small,sole_roll_large,foot_to_joint_gain_high |

## Side-Level Notes

### left

- Roll sign majority: `positive`
- Mean sole_roll_touch_rad: `1.7494`
- Mean sole_pitch_touch_rad: `-0.0563`
- Mean ankle_roll_q_touch_rad: `0.0087`
- Mean roll_to_joint_gain_ratio: `604.6338`

### right

- Roll sign majority: `negative`
- Mean sole_roll_touch_rad: `-1.6188`
- Mean sole_pitch_touch_rad: `-0.0083`
- Mean ankle_roll_q_touch_rad: `0.0434`
- Mean roll_to_joint_gain_ratio: `139.9242`

