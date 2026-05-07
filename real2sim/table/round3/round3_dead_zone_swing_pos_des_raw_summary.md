# Swing Dead-Zone Audit on pos_des_raw

- Scope: all local `t27_tracking_lag_b1_diag_*.csv` samples.
- Signal: `pos_des_raw_right_ankle_roll_joint` only.
- Event selection: first 4 `right` touchdown events per file from current `ROUND3A.detect_touchdowns()`.
- Window: `swing = touchdown-350ms .. touchdown-20ms`.
- Small-signal threshold: `|pos_des_raw| <= 0.10 rad`.

## Summary

| case | csv | events | mean pos_des_raw | mean_abs_pos_des_raw | mean small-signal ratio | min_abs_pos_des_raw | max_abs_pos_des_raw |
|---|---|---:|---:|---:|---:|---:|---:|
| 35/0.5 retest_copy | t27_tracking_lag_b1_diag_20260428_152240.csv | 4 | 0.0226 | 0.0397 | 0.9167 | 0.0001 | 0.1923 |
| 50/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_161322.csv | 4 | 0.0218 | 0.0361 | 0.9626 | 0.0000 | 0.3005 |
| 40/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_162312.csv | 4 | 0.0023 | 0.0436 | 0.9320 | 0.0000 | 0.3608 |
| 25/0.5 right_roll | t27_tracking_lag_b1_diag_20260428_163825.csv | 4 | 0.0034 | 0.0386 | 0.9396 | 0.0005 | 0.3917 |
| 25/0.5 all_ankles | t27_tracking_lag_b1_diag_20260428_164817.csv | 4 | -0.0027 | 0.0529 | 0.9026 | 0.0005 | 0.5990 |
| 25/0.5 all_ankles actuator | t27_tracking_lag_b1_diag_20260429_161248.csv | 4 | -0.0248 | 0.0724 | 0.7749 | 0.0011 | 0.3441 |
| 25/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100024.csv | 4 | 0.0241 | 0.0466 | 0.9394 | 0.0002 | 0.2078 |
| 30/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100314.csv | 4 | 0.0128 | 0.0427 | 0.9240 | 0.0022 | 0.2059 |
| 35/0.5 all_ankles | t27_tracking_lag_b1_diag_20260430_100705.csv | 3 | 0.0149 | 0.0694 | 0.8491 | 0.0001 | 0.4410 |
| 40/0.8 all_ankles | t27_tracking_lag_b1_diag_20260430_101404.csv | 4 | -0.0035 | 0.0365 | 0.9302 | 0.0008 | 0.2717 |

## 0.05 Bin Histogram on |pos_des_raw|

| case | bin start (rad) | bin end (rad) | count | ratio |
|---|---:|---:|---:|---:|
| 35/0.5 retest_copy | 0.00 | 0.05 | 102 | 0.7727 |
| 35/0.5 retest_copy | 0.05 | 0.10 | 19 | 0.1439 |
| 35/0.5 retest_copy | 0.10 | 0.15 | 8 | 0.0606 |
| 35/0.5 retest_copy | 0.15 | 0.20 | 3 | 0.0227 |
| 50/0.8 right_roll | 0.00 | 0.05 | 110 | 0.8271 |
| 50/0.8 right_roll | 0.05 | 0.10 | 18 | 0.1353 |
| 50/0.8 right_roll | 0.10 | 0.15 | 2 | 0.0150 |
| 50/0.8 right_roll | 0.15 | 0.20 | 1 | 0.0075 |
| 50/0.8 right_roll | 0.20 | 0.25 | 1 | 0.0075 |
| 50/0.8 right_roll | 0.30 | 0.35 | 1 | 0.0075 |
| 40/0.8 right_roll | 0.00 | 0.05 | 100 | 0.7576 |
| 40/0.8 right_roll | 0.05 | 0.10 | 23 | 0.1742 |
| 40/0.8 right_roll | 0.10 | 0.15 | 5 | 0.0379 |
| 40/0.8 right_roll | 0.20 | 0.25 | 1 | 0.0076 |
| 40/0.8 right_roll | 0.25 | 0.30 | 2 | 0.0152 |
| 40/0.8 right_roll | 0.35 | 0.40 | 1 | 0.0076 |
| 25/0.5 right_roll | 0.00 | 0.05 | 113 | 0.8561 |
| 25/0.5 right_roll | 0.05 | 0.10 | 11 | 0.0833 |
| 25/0.5 right_roll | 0.10 | 0.15 | 2 | 0.0152 |
| 25/0.5 right_roll | 0.15 | 0.20 | 2 | 0.0152 |
| 25/0.5 right_roll | 0.20 | 0.25 | 2 | 0.0152 |
| 25/0.5 right_roll | 0.30 | 0.35 | 1 | 0.0076 |
| 25/0.5 right_roll | 0.35 | 0.40 | 1 | 0.0076 |
| 25/0.5 all_ankles | 0.00 | 0.05 | 94 | 0.7068 |
| 25/0.5 all_ankles | 0.05 | 0.10 | 26 | 0.1955 |
| 25/0.5 all_ankles | 0.10 | 0.15 | 5 | 0.0376 |
| 25/0.5 all_ankles | 0.15 | 0.20 | 4 | 0.0301 |
| 25/0.5 all_ankles | 0.25 | 0.30 | 1 | 0.0075 |
| 25/0.5 all_ankles | 0.30 | 0.35 | 1 | 0.0075 |
| 25/0.5 all_ankles | 0.45 | 0.50 | 1 | 0.0075 |
| 25/0.5 all_ankles | 0.55 | 0.60 | 1 | 0.0075 |
| 25/0.5 all_ankles actuator | 0.00 | 0.05 | 72 | 0.5538 |
| 25/0.5 all_ankles actuator | 0.05 | 0.10 | 29 | 0.2231 |
| 25/0.5 all_ankles actuator | 0.10 | 0.15 | 10 | 0.0769 |
| 25/0.5 all_ankles actuator | 0.15 | 0.20 | 7 | 0.0538 |
| 25/0.5 all_ankles actuator | 0.20 | 0.25 | 7 | 0.0538 |
| 25/0.5 all_ankles actuator | 0.25 | 0.30 | 1 | 0.0077 |
| 25/0.5 all_ankles actuator | 0.30 | 0.35 | 4 | 0.0308 |
| 25/0.4 all_ankles | 0.00 | 0.05 | 84 | 0.6412 |
| 25/0.4 all_ankles | 0.05 | 0.10 | 39 | 0.2977 |
| 25/0.4 all_ankles | 0.10 | 0.15 | 3 | 0.0229 |
| 25/0.4 all_ankles | 0.15 | 0.20 | 2 | 0.0153 |
| 25/0.4 all_ankles | 0.20 | 0.25 | 3 | 0.0229 |
| 30/0.4 all_ankles | 0.00 | 0.05 | 101 | 0.7769 |
| 30/0.4 all_ankles | 0.05 | 0.10 | 19 | 0.1462 |
| 30/0.4 all_ankles | 0.10 | 0.15 | 6 | 0.0462 |
| 30/0.4 all_ankles | 0.15 | 0.20 | 2 | 0.0154 |
| 30/0.4 all_ankles | 0.20 | 0.25 | 2 | 0.0154 |
| 35/0.5 all_ankles | 0.00 | 0.05 | 56 | 0.5600 |
| 35/0.5 all_ankles | 0.05 | 0.10 | 29 | 0.2900 |
| 35/0.5 all_ankles | 0.10 | 0.15 | 2 | 0.0200 |
| 35/0.5 all_ankles | 0.15 | 0.20 | 4 | 0.0400 |
| 35/0.5 all_ankles | 0.20 | 0.25 | 2 | 0.0200 |
| 35/0.5 all_ankles | 0.25 | 0.30 | 2 | 0.0200 |
| 35/0.5 all_ankles | 0.30 | 0.35 | 3 | 0.0300 |
| 35/0.5 all_ankles | 0.35 | 0.40 | 1 | 0.0100 |
| 35/0.5 all_ankles | 0.40 | 0.45 | 1 | 0.0100 |
| 40/0.8 all_ankles | 0.00 | 0.05 | 106 | 0.8154 |
| 40/0.8 all_ankles | 0.05 | 0.10 | 15 | 0.1154 |
| 40/0.8 all_ankles | 0.10 | 0.15 | 6 | 0.0462 |
| 40/0.8 all_ankles | 0.15 | 0.20 | 2 | 0.0154 |
| 40/0.8 all_ankles | 0.25 | 0.30 | 1 | 0.0077 |

## Skipped

- `t27_tracking_lag_b1_diag_20260428_155015.csv`: no_right_touchdown_events
- `t27_tracking_lag_b1_diag_20260428_155055.csv`: no_right_touchdown_events
