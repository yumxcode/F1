# Round 3 Early Touchdown Summary (First 4)

- Source log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv`
- Touchdowns analyzed: `4`
- Note: Use this slice as the primary diagnosis view when later steps are contaminated by unrecovered instability.
- Mean max swing clearance: `0.0728 m`
- Mean touchdown baseline-corrected foot-frame residual: `0.1626 rad`
- Foot attitude is baseline-corrected per side using stable double-support frames from the same log.

| side | touchdown_time_sec | primary_flag | all_flags | max_swing_clearance_m | clearance_at_minus_50ms_m | foot_flat_error_touch_rad |
|---|---:|---|---|---:|---:|---:|
| left | 1777515244.419 | hip_knee_tracking_lag | hip_knee_tracking_lag | 0.0502 | 0.0288 | 0.0908 |
| right | 1777515244.759 | foot_clearance_deficit | foot_clearance_deficit|hip_knee_tracking_lag|tracking_lag | 0.0860 | 0.0088 | 0.1183 |
| left | 1777515245.069 | large_foot_frame_residual_touchdown | large_foot_frame_residual_touchdown|hip_knee_tracking_lag|tracking_lag | 0.0937 | 0.0461 | 0.2624 |
| right | 1777515245.429 | hip_knee_tracking_lag | hip_knee_tracking_lag|tracking_lag | 0.0614 | 0.0273 | 0.1789 |
