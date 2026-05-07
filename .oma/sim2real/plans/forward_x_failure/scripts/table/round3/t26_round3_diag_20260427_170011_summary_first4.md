# Round 3 Early Touchdown Summary (First 4)

- Source log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t26_round3_diag_20260427_170011.csv`
- Touchdowns analyzed: `4`
- Note: Use this slice as the primary diagnosis view when later steps are contaminated by unrecovered instability.
- Mean max swing clearance: `0.0870 m`
- Mean touchdown baseline-corrected foot-frame residual: `0.3191 rad`
- Foot attitude is baseline-corrected per side using stable double-support frames from the same log.

| side | touchdown_time_sec | primary_flag | all_flags | max_swing_clearance_m | clearance_at_minus_50ms_m | foot_flat_error_touch_rad |
|---|---:|---|---|---:|---:|---:|
| left | 1777280412.454 | large_foot_frame_residual_touchdown | large_foot_frame_residual_touchdown|foot_clearance_deficit|hip_knee_tracking_lag|tracking_lag | 0.0264 | 0.0694 | 0.4188 |
| right | 1777280413.084 | large_foot_frame_residual_touchdown | large_foot_frame_residual_touchdown|foot_clearance_deficit|hip_knee_tracking_lag|early_knee_extension|tracking_lag | 0.1372 | -0.0317 | 0.2500 |
| right | 1777280413.814 | large_foot_frame_residual_touchdown | large_foot_frame_residual_touchdown|foot_clearance_deficit|hip_knee_tracking_lag|early_knee_extension|tracking_lag | 0.0697 | -0.0985 | 0.2288 |
| right | 1777280414.944 | large_foot_frame_residual_touchdown | large_foot_frame_residual_touchdown|hip_knee_tracking_lag|tracking_lag | 0.1145 | 0.1141 | 0.3788 |
