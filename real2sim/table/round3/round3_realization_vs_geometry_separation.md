# Realization vs Geometry Separation

## Rule

- `realization_dominant`: `state->joint` already high-risk/unacceptable and dominates `joint->sole`.
- `geometry_residual_dominant`: `state->joint` is low/tight but `joint->sole` remains high, or geometry jump is obvious.
- `mixed_with_geometry_residual`: both segments are risky, or `state->joint` alone still cannot explain the final `sole_roll`.

## Summary

- overall counts: {'mixed_with_geometry_residual': 4, 'geometry_residual_dominant': 3, 'realization_dominant': 1}
- swing counts: {'mixed_with_geometry_residual': 3, 'realization_dominant': 1}
- touchdown counts: {'geometry_residual_dominant': 3, 'mixed_with_geometry_residual': 1}

## Per Case

- `25/0.4 all_ankles / swing` -> `mixed_with_geometry_residual`: state->joint=71.8ms and joint->sole=92.0ms are both risky; abs_sole_roll=1.740; lag_gap=31.9ms; gain_gap=0.807
- `25/0.4 all_ankles / touchdown` -> `geometry_residual_dominant`: joint->sole=71.8ms dominates over state->joint=23.6ms; abs_sole_roll=1.787; shape=mostly_linear,backlash_like
- `30/0.4 all_ankles / swing` -> `realization_dominant`: state->joint=93.5ms already high while joint->sole=26.1ms is smaller; cmd->state small=True; shape=overall_slow,backlash_like,overall_slow,stick_slip_like,backlash_like,low_realization_gain
- `30/0.4 all_ankles / touchdown` -> `mixed_with_geometry_residual`: state->joint=26.1ms is not enough to fully explain abs_sole_roll=1.678; lag_gap=29.2ms; shape=backlash_like,low_realization_gain,backlash_like
- `35/0.5 all_ankles / swing` -> `mixed_with_geometry_residual`: state->joint=66.0ms and joint->sole=76.5ms are both risky; abs_sole_roll=1.645; lag_gap=36.4ms; gain_gap=3.015
- `35/0.5 all_ankles / touchdown` -> `geometry_residual_dominant`: state->joint=4.6ms is low but joint->sole=74.2ms remains high; abs_sole_roll=1.854; shape=backlash_like,stick_slip_like,low_realization_gain
- `40/0.8 all_ankles / swing` -> `mixed_with_geometry_residual`: state->joint=37.8ms is not enough to fully explain abs_sole_roll=1.643; lag_gap=45.5ms; shape=backlash_like,low_realization_gain,backlash_like
- `40/0.8 all_ankles / touchdown` -> `geometry_residual_dominant`: joint->sole=48.0ms dominates over state->joint=20.6ms; abs_sole_roll=1.623; shape=backlash_like,mostly_linear
