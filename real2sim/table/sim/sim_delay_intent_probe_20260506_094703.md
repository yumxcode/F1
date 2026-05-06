# Sim Delay And Intent Probe

- Source joint log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/sim/t23_joint_20260506_094703.csv`
- Source motor-current log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/sim/tm_raw_motor_current_20260506_094703.csv`
- Shared suffix: `20260506_094703`
- Joint sample dt: `9.999 ms`
- Current sample dt: `0.997 ms`
- Delay compensation proxy: `20 ms`
- High tracking error threshold: `0.12 rad`

## Scope And Limits

- This reuses the `06` lag-reading style on sim logs, but only `target / pos / motor current` are available.
- This does **not** reproduce the full `03` touchdown foot-flat analysis, because sim logs here do not contain `base_euler`, contact state, or FK-derived sole attitude.
- The `03` reference used here is only the joint-space `flattening_intent(target, pos)` logic, as a simplified command-sufficiency proxy.

## Per-Joint Summary

| joint | group | target->pos ms | target->current ms | current->pos ms | target-pos rms rad | flatten intent ratio | high-err flatten ratio |
|---|---|---:|---:|---:|---:|---:|---:|
| left_ankle_pitch_joint | ankle | 49.9940 | 19.9976 | 109.9868 | 0.2731 | 0.4108 | 0.4881 |
| left_ankle_roll_joint | ankle | 29.9964 | 19.9976 | 129.9844 | 0.1949 | 0.2886 | 0.1746 |
| left_hip_pitch_joint | hip | 79.9904 | 19.9976 | 69.9916 | 0.1672 | 0.4800 | 0.3444 |
| left_hip_roll_joint | hip | 129.9844 | 19.9976 | 109.9868 | 0.4679 | 0.4689 | 0.4607 |
| left_hip_yaw_joint | hip | 49.9940 | 9.9988 | 49.9940 | 0.1874 | 0.2285 | 0.1780 |
| left_knee_pitch_joint | knee | 49.9940 | 9.9988 | 119.9856 | 0.2835 | 0.6653 | 0.7250 |
| right_ankle_pitch_joint | ankle | 49.9940 | 19.9976 | 29.9964 | 0.2518 | 0.7585 | 0.9342 |
| right_ankle_roll_joint | ankle | 29.9964 | 19.9976 | 9.9988 | 0.1435 | 0.1603 | 0.0029 |
| right_hip_pitch_joint | hip | 39.9952 | 19.9976 | 19.9976 | 0.2790 | 0.6162 | 0.6414 |
| right_hip_roll_joint | hip | 89.9892 | 19.9976 | 59.9928 | 0.5312 | 0.4719 | 0.6910 |
| right_hip_yaw_joint | hip | 49.9940 | 19.9976 | 49.9940 | 0.1695 | 0.1092 | 0.0145 |
| right_knee_pitch_joint | knee | 59.9928 | 9.9988 | 79.9904 | 0.2661 | 0.7244 | 0.7900 |

## Group Summary

| group | joints | mean target->pos ms | mean target->current ms | mean current->pos ms | mean rms err rad | mean flatten intent ratio | mean high-err flatten ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| ankle | 4 | 39.9952 | 19.9976 | 69.9916 | 0.2158 | 0.4046 | 0.4000 |
| hip | 6 | 73.3245 | 18.3311 | 59.9928 | 0.3004 | 0.3958 | 0.3883 |
| knee | 2 | 54.9934 | 9.9988 | 99.9880 | 0.2748 | 0.6949 | 0.7575 |

## Reading Guide

- `target->pos` is the closest sim counterpart to `06`'s total execution lag.
- `target->current` and `current->pos` are only rough proxies here, because the second file is motor current, not actuator position/state.
- `flatten intent ratio` means how often the delayed target is trying to pull the joint back toward zero / the opposite side, following `03`'s `flattening_intent` rule.
- `high-err flatten ratio` restricts that same check to samples whose delayed tracking error is already large, which is the closer proxy to asking whether `command_not_flat` is still happening when error is nontrivial.
