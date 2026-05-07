# Right Ankle Roll Action-to-Joint Lag Summary

- Scope: all local `t27_tracking_lag_b1_diag_*.csv` samples.
- Signal pair: `action_right_ankle_roll_joint -> pos_right_ankle_roll_joint`.
- Event selection: first 4 `right` touchdown events per file.
- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.

## Summary

| case | csv | window | events | mean_abs_action | mean signed action | mean lag (ms) | mean corr |
|---|---|---|---:|---:|---:|---:|---:|
| 35/0.5 retest_copy | t27_tracking_lag_b1_diag_20260428_152240.csv | swing | 4 | 0.079 | 0.045 | 151.083 | 0.615 |
| 35/0.5 retest_copy | t27_tracking_lag_b1_diag_20260428_152240.csv | touchdown | 4 | 0.398 | -0.335 | 81.179 | 0.093 |
| 50/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_161322.csv | swing | 4 | 0.072 | 0.044 | 60.165 | 0.282 |
| 50/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_161322.csv | touchdown | 4 | 0.483 | -0.431 | 30.082 | 0.294 |
| 40/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_162312.csv | swing | 4 | 0.087 | 0.005 | 85.760 | 0.358 |
| 40/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_162312.csv | touchdown | 4 | 0.461 | -0.423 | 37.086 | 0.133 |
| 25/0.5 right_roll | t27_tracking_lag_b1_diag_20260428_163825.csv | swing | 4 | 0.077 | 0.007 | 89.215 | 0.287 |
| 25/0.5 right_roll | t27_tracking_lag_b1_diag_20260428_163825.csv | touchdown | 4 | 0.426 | -0.381 | 59.477 | 0.213 |
| 25/0.5 all_ankles | t27_tracking_lag_b1_diag_20260428_164817.csv | swing | 4 | 0.106 | -0.005 | 73.062 | 0.392 |
| 25/0.5 all_ankles | t27_tracking_lag_b1_diag_20260428_164817.csv | touchdown | 4 | 0.569 | -0.568 | 47.137 | 0.288 |
| 25/0.5 all_ankles actuator | t27_tracking_lag_b1_diag_20260429_161248.csv | swing | 4 | 0.145 | -0.050 | 60.759 | 0.254 |
| 25/0.5 all_ankles actuator | t27_tracking_lag_b1_diag_20260429_161248.csv | touchdown | 4 | 0.454 | -0.393 | 8.680 | 0.286 |
| 25/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100024.csv | swing | 4 | 0.093 | 0.048 | 76.294 | 0.364 |
| 25/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100024.csv | touchdown | 4 | 0.398 | -0.357 | 20.195 | 0.310 |
| 30/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100314.csv | swing | 4 | 0.085 | 0.026 | 99.467 | 0.326 |
| 30/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100314.csv | touchdown | 4 | 0.355 | -0.293 | 23.683 | 0.100 |
| 35/0.5 all_ankles | t27_tracking_lag_b1_diag_20260430_100705.csv | swing | 3 | 0.139 | 0.030 | 61.797 | 0.500 |
| 35/0.5 all_ankles | t27_tracking_lag_b1_diag_20260430_100705.csv | touchdown | 3 | 0.423 | -0.286 | 15.449 | 0.010 |
| 40/0.8 all_ankles | t27_tracking_lag_b1_diag_20260430_101404.csv | swing | 4 | 0.073 | -0.007 | 54.913 | 0.293 |
| 40/0.8 all_ankles | t27_tracking_lag_b1_diag_20260430_101404.csv | touchdown | 4 | 0.546 | -0.522 | 32.033 | 0.281 |

## Skipped

- `t27_tracking_lag_b1_diag_20260428_155015.csv`: no_right_touchdown_events
- `t27_tracking_lag_b1_diag_20260428_155055.csv`: no_right_touchdown_events
