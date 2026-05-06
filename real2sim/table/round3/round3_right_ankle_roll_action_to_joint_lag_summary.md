# Right Ankle Roll Action-to-Joint Lag Summary

- Scope: all local `t27_tracking_lag_b1_diag_*.csv` samples.
- Signal pair: `action_right_ankle_roll_joint -> pos_right_ankle_roll_joint`.
- Event selection: first 4 `right` touchdown events per file.
- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.

## Summary

| case | csv | window | events | mean |action| | mean signed action | mean lag (ms) | mean corr |
|---|---|---|---:|---:|---:|---:|---:|
| 35/0.5 retest_copy | t27_tracking_lag_b1_diag_20260428_152240.csv | swing | 3 | 0.245 | -0.146 | 36.079 | 0.231 |
| 35/0.5 retest_copy | t27_tracking_lag_b1_diag_20260428_152240.csv | touchdown | 3 | 0.715 | -0.715 | 6.013 | 0.339 |
| 50/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_161322.csv | swing | 4 | 0.202 | -0.132 | 129.586 | 0.377 |
| 50/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_161322.csv | touchdown | 4 | 0.146 | -0.033 | 20.826 | 0.548 |
| 40/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_162312.csv | swing | 4 | 0.206 | -0.153 | 88.078 | 0.445 |
| 40/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_162312.csv | touchdown | 4 | 0.088 | -0.001 | 55.628 | 0.255 |
| 25/0.5 right_roll | t27_tracking_lag_b1_diag_20260428_163825.csv | swing | 4 | 0.192 | -0.129 | 41.176 | 0.305 |
| 25/0.5 right_roll | t27_tracking_lag_b1_diag_20260428_163825.csv | touchdown | 4 | 0.566 | -0.566 | 25.163 | 0.378 |
| 25/0.5 all_ankles | t27_tracking_lag_b1_diag_20260428_164817.csv | swing | 4 | 0.184 | -0.135 | 113.128 | 0.273 |
| 25/0.5 all_ankles | t27_tracking_lag_b1_diag_20260428_164817.csv | touchdown | 4 | 0.287 | -0.258 | 16.498 | 0.445 |
| 25/0.5 all_ankles actuator | t27_tracking_lag_b1_diag_20260429_161248.csv | swing | 4 | 0.275 | -0.193 | 13.020 | 0.289 |
| 25/0.5 all_ankles actuator | t27_tracking_lag_b1_diag_20260429_161248.csv | touchdown | 4 | 0.500 | -0.485 | 23.870 | 0.590 |
| 25/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100024.csv | swing | 4 | 0.221 | -0.067 | 24.683 | 0.287 |
| 25/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100024.csv | touchdown | 4 | 0.483 | -0.412 | 0.000 | 0.484 |
| 30/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100314.csv | swing | 4 | 0.345 | -0.288 | 59.207 | 0.207 |
| 30/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100314.csv | touchdown | 4 | 0.482 | -0.371 | 47.365 | 0.261 |
| 35/0.5 all_ankles | t27_tracking_lag_b1_diag_20260430_100705.csv | swing | 4 | 0.389 | -0.158 | 44.030 | 0.257 |
| 35/0.5 all_ankles | t27_tracking_lag_b1_diag_20260430_100705.csv | touchdown | 4 | 0.340 | -0.319 | 0.000 | 0.065 |
| 40/0.8 all_ankles | t27_tracking_lag_b1_diag_20260430_101404.csv | swing | 4 | 0.187 | -0.141 | 148.723 | 0.468 |
| 40/0.8 all_ankles | t27_tracking_lag_b1_diag_20260430_101404.csv | touchdown | 4 | 0.103 | -0.078 | 27.457 | 0.204 |

## Skipped

- `t27_tracking_lag_b1_diag_20260428_155015.csv`: no_right_touchdown_events
- `t27_tracking_lag_b1_diag_20260428_155055.csv`: no_right_touchdown_events
