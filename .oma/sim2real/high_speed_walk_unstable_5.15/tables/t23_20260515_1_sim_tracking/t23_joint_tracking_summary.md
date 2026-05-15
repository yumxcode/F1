# t23 Joint Tracking Initial Screen

Source: `test_logs/data_csv/t23_joint_20260515_1_sim.csv`
Rows: 4000
Duration: 39.987 s
Sample rate: 100.006 Hz
dt range: 7.382 .. 12.626 ms

## Top Tracking Errors

| Joint | RMS err rad | Max err rad | Target range | Pos range | Pos/target | Delay ms | Corr | Vel p95 rad/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| left_hip_roll_joint | 0.5515 | 1.4998 | 1.6480 | 0.2371 | 0.144 | 190.0 | 0.847 | 1.052 |
| right_hip_roll_joint | 0.5043 | 1.4839 | 1.6757 | 0.1952 | 0.117 | 200.0 | 0.816 | 0.718 |
| left_ankle_pitch_joint | 0.3505 | 0.7815 | 0.7600 | 0.2761 | 0.363 | -140.0 | 0.666 | 2.684 |
| right_ankle_pitch_joint | 0.2841 | 0.7843 | 0.7600 | 0.2971 | 0.391 | -220.0 | 0.311 | 2.258 |
| right_ankle_roll_joint | 0.2791 | 0.5756 | 0.7469 | 0.4017 | 0.538 | 90.0 | 0.941 | 2.822 |
| left_hip_pitch_joint | 0.2716 | 0.8032 | 1.0872 | 0.3732 | 0.343 | 130.0 | 0.946 | 2.274 |
| right_knee_pitch_joint | 0.2589 | 0.5993 | 1.0226 | 0.4311 | 0.422 | 70.0 | 0.920 | 2.736 |
| right_hip_pitch_joint | 0.2416 | 0.7258 | 1.1363 | 0.3366 | 0.296 | 150.0 | 0.811 | 1.411 |
| left_knee_pitch_joint | 0.2319 | 0.5657 | 1.0618 | 0.3870 | 0.364 | 80.0 | 0.944 | 2.176 |
| right_hip_yaw_joint | 0.2038 | 0.5800 | 0.8743 | 0.4875 | 0.558 | -200.0 | 0.442 | 1.212 |
| left_hip_yaw_joint | 0.1884 | 0.5575 | 0.9733 | 0.3513 | 0.361 | 60.0 | 0.661 | 1.835 |
| left_ankle_roll_joint | 0.1690 | 0.6024 | 1.0472 | 0.3220 | 0.308 | 40.0 | 0.775 | 1.619 |

## Interpretation Boundary

- This log can reveal execution-chain tracking stress at high speed.
- It cannot by itself prove body instability because it lacks velocity command, IMU, odometry, contact, and fall-event annotations.
- For parallel ankle joints, raw target tracking is used; LPF columns are not compared to position in this report.
