# Swing Dead-Zone Audit on pos_des_raw

- Scope: all local `t27_tracking_lag_b1_diag_*.csv` samples.
- Signal: `pos_des_raw_right_ankle_roll_joint` only.
- Event selection: first 4 `right` touchdown events per file.
- Window: `swing = touchdown-350ms .. touchdown-20ms`.
- Small-signal threshold: `|pos_des_raw| <= 0.10 rad`.

## Summary

| case | csv | events | mean pos_des_raw | mean |pos_des_raw| | mean small-signal ratio | min |pos_des_raw| | max |pos_des_raw| |
|---|---|---:|---:|---:|---:|---:|---:|
| 35/0.5 retest_copy | t27_tracking_lag_b1_diag_20260428_152240.csv | 3 | 0.0878 | 0.0878 | 0.5722 | 0.0247 | 0.1923 |
| 50/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_161322.csv | 3 | -0.1054 | 0.1722 | 0.3619 | 0.0269 | 0.4555 |
| 40/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_162312.csv | 3 | -0.1177 | 0.1742 | 0.4632 | 0.0207 | 0.3991 |
| 25/0.5 right_roll | t27_tracking_lag_b1_diag_20260428_163825.csv | 3 | -0.0850 | 0.1247 | 0.6429 | 0.0011 | 0.4307 |
| 25/0.5 all_ankles | t27_tracking_lag_b1_diag_20260428_164817.csv | 3 | -0.0577 | 0.1193 | 0.5685 | 0.0003 | 0.3813 |
| 25/0.5 all_ankles actuator | t27_tracking_lag_b1_diag_20260429_161248.csv | 3 | -0.0535 | 0.1069 | 0.7016 | 0.0016 | 0.3791 |
| 25/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100024.csv | 3 | -0.0167 | 0.0816 | 0.8119 | 0.0039 | 0.4335 |
| 30/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100314.csv | 3 | -0.0733 | 0.0937 | 0.7951 | 0.0010 | 0.4993 |
| 35/0.5 all_ankles | t27_tracking_lag_b1_diag_20260430_100705.csv | 3 | -0.0018 | 0.0779 | 0.7895 | 0.0006 | 0.4359 |
| 40/0.8 all_ankles | t27_tracking_lag_b1_diag_20260430_101404.csv | 3 | -0.0933 | 0.1434 | 0.5672 | 0.0047 | 0.4392 |

## 0.05 Bin Histogram on |pos_des_raw|

| case | bin start (rad) | bin end (rad) | count | ratio |
|---|---:|---:|---:|---:|
| 35/0.5 retest_copy | 0.00 | 0.05 | 33 | 0.4177 |
| 35/0.5 retest_copy | 0.05 | 0.10 | 14 | 0.1772 |
| 35/0.5 retest_copy | 0.10 | 0.15 | 20 | 0.2532 |
| 35/0.5 retest_copy | 0.15 | 0.20 | 12 | 0.1519 |
| 50/0.8 right_roll | 0.00 | 0.05 | 7 | 0.0959 |
| 50/0.8 right_roll | 0.05 | 0.10 | 18 | 0.2466 |
| 50/0.8 right_roll | 0.10 | 0.15 | 18 | 0.2466 |
| 50/0.8 right_roll | 0.15 | 0.20 | 5 | 0.0685 |
| 50/0.8 right_roll | 0.20 | 0.25 | 2 | 0.0274 |
| 50/0.8 right_roll | 0.25 | 0.30 | 5 | 0.0685 |
| 50/0.8 right_roll | 0.30 | 0.35 | 9 | 0.1233 |
| 50/0.8 right_roll | 0.35 | 0.40 | 2 | 0.0274 |
| 50/0.8 right_roll | 0.40 | 0.45 | 5 | 0.0685 |
| 50/0.8 right_roll | 0.45 | 0.50 | 2 | 0.0274 |
| 40/0.8 right_roll | 0.00 | 0.05 | 12 | 0.1791 |
| 40/0.8 right_roll | 0.05 | 0.10 | 18 | 0.2687 |
| 40/0.8 right_roll | 0.10 | 0.15 | 4 | 0.0597 |
| 40/0.8 right_roll | 0.15 | 0.20 | 6 | 0.0896 |
| 40/0.8 right_roll | 0.20 | 0.25 | 5 | 0.0746 |
| 40/0.8 right_roll | 0.25 | 0.30 | 5 | 0.0746 |
| 40/0.8 right_roll | 0.30 | 0.35 | 6 | 0.0896 |
| 40/0.8 right_roll | 0.35 | 0.40 | 11 | 0.1642 |
| 25/0.5 right_roll | 0.00 | 0.05 | 35 | 0.4430 |
| 25/0.5 right_roll | 0.05 | 0.10 | 17 | 0.2152 |
| 25/0.5 right_roll | 0.10 | 0.15 | 6 | 0.0759 |
| 25/0.5 right_roll | 0.15 | 0.20 | 4 | 0.0506 |
| 25/0.5 right_roll | 0.20 | 0.25 | 4 | 0.0506 |
| 25/0.5 right_roll | 0.25 | 0.30 | 2 | 0.0253 |
| 25/0.5 right_roll | 0.30 | 0.35 | 2 | 0.0253 |
| 25/0.5 right_roll | 0.35 | 0.40 | 5 | 0.0633 |
| 25/0.5 right_roll | 0.40 | 0.45 | 4 | 0.0506 |
| 25/0.5 all_ankles | 0.00 | 0.05 | 31 | 0.4247 |
| 25/0.5 all_ankles | 0.05 | 0.10 | 14 | 0.1918 |
| 25/0.5 all_ankles | 0.10 | 0.15 | 11 | 0.1507 |
| 25/0.5 all_ankles | 0.15 | 0.20 | 2 | 0.0274 |
| 25/0.5 all_ankles | 0.20 | 0.25 | 4 | 0.0548 |
| 25/0.5 all_ankles | 0.25 | 0.30 | 4 | 0.0548 |
| 25/0.5 all_ankles | 0.30 | 0.35 | 3 | 0.0411 |
| 25/0.5 all_ankles | 0.35 | 0.40 | 4 | 0.0548 |
| 25/0.5 all_ankles actuator | 0.00 | 0.05 | 47 | 0.4700 |
| 25/0.5 all_ankles actuator | 0.05 | 0.10 | 23 | 0.2300 |
| 25/0.5 all_ankles actuator | 0.10 | 0.15 | 6 | 0.0600 |
| 25/0.5 all_ankles actuator | 0.15 | 0.20 | 3 | 0.0300 |
| 25/0.5 all_ankles actuator | 0.20 | 0.25 | 1 | 0.0100 |
| 25/0.5 all_ankles actuator | 0.25 | 0.30 | 7 | 0.0700 |
| 25/0.5 all_ankles actuator | 0.30 | 0.35 | 10 | 0.1000 |
| 25/0.5 all_ankles actuator | 0.35 | 0.40 | 3 | 0.0300 |
| 25/0.4 all_ankles | 0.00 | 0.05 | 33 | 0.4024 |
| 25/0.4 all_ankles | 0.05 | 0.10 | 33 | 0.4024 |
| 25/0.4 all_ankles | 0.10 | 0.15 | 6 | 0.0732 |
| 25/0.4 all_ankles | 0.15 | 0.20 | 2 | 0.0244 |
| 25/0.4 all_ankles | 0.25 | 0.30 | 1 | 0.0122 |
| 25/0.4 all_ankles | 0.30 | 0.35 | 4 | 0.0488 |
| 25/0.4 all_ankles | 0.35 | 0.40 | 1 | 0.0122 |
| 25/0.4 all_ankles | 0.40 | 0.45 | 2 | 0.0244 |
| 30/0.4 all_ankles | 0.00 | 0.05 | 48 | 0.6400 |
| 30/0.4 all_ankles | 0.05 | 0.10 | 9 | 0.1200 |
| 30/0.4 all_ankles | 0.10 | 0.15 | 2 | 0.0267 |
| 30/0.4 all_ankles | 0.25 | 0.30 | 2 | 0.0267 |
| 30/0.4 all_ankles | 0.30 | 0.35 | 1 | 0.0133 |
| 30/0.4 all_ankles | 0.35 | 0.40 | 5 | 0.0667 |
| 30/0.4 all_ankles | 0.40 | 0.45 | 6 | 0.0800 |
| 30/0.4 all_ankles | 0.45 | 0.50 | 2 | 0.0267 |
| 35/0.5 all_ankles | 0.00 | 0.05 | 43 | 0.4943 |
| 35/0.5 all_ankles | 0.05 | 0.10 | 24 | 0.2759 |
| 35/0.5 all_ankles | 0.10 | 0.15 | 8 | 0.0920 |
| 35/0.5 all_ankles | 0.15 | 0.20 | 5 | 0.0575 |
| 35/0.5 all_ankles | 0.20 | 0.25 | 1 | 0.0115 |
| 35/0.5 all_ankles | 0.25 | 0.30 | 2 | 0.0230 |
| 35/0.5 all_ankles | 0.35 | 0.40 | 1 | 0.0115 |
| 35/0.5 all_ankles | 0.40 | 0.45 | 3 | 0.0345 |
| 40/0.8 all_ankles | 0.00 | 0.05 | 32 | 0.4000 |
| 40/0.8 all_ankles | 0.05 | 0.10 | 15 | 0.1875 |
| 40/0.8 all_ankles | 0.10 | 0.15 | 6 | 0.0750 |
| 40/0.8 all_ankles | 0.15 | 0.20 | 3 | 0.0375 |
| 40/0.8 all_ankles | 0.20 | 0.25 | 6 | 0.0750 |
| 40/0.8 all_ankles | 0.25 | 0.30 | 6 | 0.0750 |
| 40/0.8 all_ankles | 0.30 | 0.35 | 2 | 0.0250 |
| 40/0.8 all_ankles | 0.35 | 0.40 | 6 | 0.0750 |
| 40/0.8 all_ankles | 0.40 | 0.45 | 4 | 0.0500 |

## Skipped

- `t27_tracking_lag_b1_diag_20260428_155015.csv`: no_valid_swing_rows
- `t27_tracking_lag_b1_diag_20260428_155055.csv`: no_valid_swing_rows
