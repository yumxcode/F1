# Realization vs Geometry Separation

## Rule

- `realization_dominant`: `state->joint` already high-risk/unacceptable and dominates `joint->sole`.
- `geometry_residual_dominant`: `state->joint` is low/tight but `joint->sole` remains high, or geometry jump is obvious.
- `mixed_with_geometry_residual`: both segments are risky, or `state->joint` alone still cannot explain the final `sole_roll`.

## Summary

- overall counts: {'mixed_with_geometry_residual': 6, 'geometry_residual_dominant': 2}
- swing counts: {'mixed_with_geometry_residual': 4}
- touchdown counts: {'mixed_with_geometry_residual': 2, 'geometry_residual_dominant': 2}

## Per Case

- `25/0.4 all_ankles / swing` -> `mixed_with_geometry_residual`: state->joint=71.8ms and joint->sole=94.2ms are both risky; abs_sole_roll=0.216; lag_gap=19.5ms; gain_gap=0.074
- `25/0.4 all_ankles / touchdown` -> `mixed_with_geometry_residual`: state->joint=41.5ms and joint->sole=35.9ms are both risky; abs_sole_roll=0.078; lag_gap=2.8ms; gain_gap=0.298
- `30/0.4 all_ankles / swing` -> `mixed_with_geometry_residual`: state->joint=75.8ms and joint->sole=80.5ms are both risky; abs_sole_roll=0.160; lag_gap=34.7ms; gain_gap=0.001
- `30/0.4 all_ankles / touchdown` -> `geometry_residual_dominant`: state->joint=7.1ms is low but joint->sole=49.7ms remains high; abs_sole_roll=0.056; shape=backlash_like,low_realization_gain,stick_slip_like,backlash_like,low_realization_gain
- `35/0.5 all_ankles / swing` -> `mixed_with_geometry_residual`: state->joint=49.8ms and joint->sole=71.8ms are both risky; abs_sole_roll=0.215; lag_gap=8.1ms; gain_gap=0.023
- `35/0.5 all_ankles / touchdown` -> `mixed_with_geometry_residual`: state->joint=22.0ms is not enough to fully explain abs_sole_roll=0.148; lag_gap=32.4ms; shape=stick_slip_like,stick_slip_like,low_realization_gain
- `40/0.8 all_ankles / swing` -> `mixed_with_geometry_residual`: state->joint=44.6ms and joint->sole=116.7ms are both risky; abs_sole_roll=0.149; lag_gap=2.4ms; gain_gap=0.078
- `40/0.8 all_ankles / touchdown` -> `geometry_residual_dominant`: state->joint=12.6ms is low but joint->sole=57.2ms remains high; abs_sole_roll=0.071; shape=mostly_linear,low_realization_gain
