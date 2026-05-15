# t23 Joint Tracking Initial Screen

Source: `test_logs/data_csv/t23_joint_20260515_104435.csv`
Rows: 4000
Duration: 39.989 s
Sample rate: 100.003 Hz
dt range: 8.700 .. 11.251 ms

## Top Tracking Errors

| Joint | RMS err rad | Max err rad | Target range | Pos range | Pos/target | Delay ms | Corr | Vel p95 rad/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| left_hip_pitch_joint | 0.7169 | 1.6028 | 2.6217 | 0.5356 | 0.204 | 140.0 | 0.336 | 1.654 |
| right_hip_pitch_joint | 0.6222 | 1.5225 | 2.8653 | 0.9620 | 0.336 | 140.0 | 0.019 | 2.433 |
| right_knee_pitch_joint | 0.5910 | 1.3941 | 1.6722 | 1.4113 | 0.844 | 150.0 | 0.146 | 4.704 |
| left_hip_roll_joint | 0.5722 | 1.6265 | 1.7000 | 0.2431 | 0.143 | 100.0 | 0.197 | 0.789 |
| left_hip_yaw_joint | 0.4161 | 1.3958 | 2.5651 | 0.5173 | 0.202 | 60.0 | 0.472 | 1.531 |
| left_knee_pitch_joint | 0.4007 | 0.9422 | 1.1059 | 0.9856 | 0.891 | 140.0 | 0.336 | 2.618 |
| right_hip_roll_joint | 0.3974 | 1.6180 | 1.7000 | 0.2794 | 0.164 | 80.0 | 0.253 | 0.783 |
| right_ankle_roll_joint | 0.3219 | 0.7281 | 1.2800 | 0.5662 | 0.442 | 60.0 | 0.238 | 3.724 |
| right_ankle_pitch_joint | 0.3104 | 0.8388 | 0.7600 | 0.8795 | 1.157 | -130.0 | -0.313 | 2.186 |
| right_hip_yaw_joint | 0.3054 | 1.2219 | 1.8394 | 0.5229 | 0.284 | 80.0 | 0.268 | 1.795 |
| left_ankle_roll_joint | 0.2274 | 0.6951 | 1.1805 | 0.6623 | 0.561 | 60.0 | 0.474 | 3.164 |
| left_ankle_pitch_joint | 0.1642 | 0.8152 | 0.7600 | 0.6211 | 0.817 | 60.0 | 0.349 | 1.702 |

## Interpretation Boundary

- This log can reveal execution-chain tracking stress at high speed.
- It cannot by itself prove body instability because it lacks velocity command, IMU, odometry, contact, and fall-event annotations.
- For parallel ankle joints, raw target tracking is used; LPF columns are not compared to position in this report.
