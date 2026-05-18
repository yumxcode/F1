# t23 Joint Tracking Initial Screen

Source: `test_logs/data_csv/t23_joint_20260515_2_real.csv`
Rows: 4000
Duration: 39.989 s
Sample rate: 100.003 Hz
dt range: 9.047 .. 10.323 ms

## Top Tracking Errors

| Joint | RMS err rad | Max err rad | Target range | Pos/target | Target mean | Pos mean | Error mean | Error std | Delay ms | Best corr | Zero corr | Vel p95 rad/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| right_hip_roll_joint | 0.8732 | 1.6272 | 1.7000 | 0.240 | +0.4780 | -0.0449 | +0.5229 | 0.6993 | 80.0 | 0.031 | -0.019 | 0.911 |
| left_hip_pitch_joint | 0.6397 | 1.3405 | 2.7822 | 0.228 | +0.3254 | +0.2428 | +0.0826 | 0.6343 | 140.0 | 0.148 | 0.057 | 1.703 |
| right_hip_pitch_joint | 0.5867 | 1.2855 | 2.2747 | 0.350 | -0.1740 | -0.4572 | +0.2833 | 0.5138 | 140.0 | 0.089 | -0.120 | 2.489 |
| left_hip_roll_joint | 0.5826 | 1.6428 | 1.7000 | 0.258 | -0.3013 | +0.1269 | -0.4282 | 0.3951 | 120.0 | -0.166 | -0.299 | 0.862 |
| right_knee_pitch_joint | 0.5434 | 1.2217 | 1.4565 | 0.873 | +0.6121 | +0.3130 | +0.2991 | 0.4537 | 150.0 | -0.011 | -0.410 | 4.404 |
| left_knee_pitch_joint | 0.4651 | 1.2633 | 1.7844 | 0.424 | +0.6472 | +0.5280 | +0.1192 | 0.4496 | 140.0 | 0.213 | -0.069 | 3.053 |
| left_ankle_pitch_joint | 0.4113 | 0.7397 | 0.7600 | 0.589 | -0.0405 | -0.2507 | +0.2102 | 0.3536 | 70.0 | -0.111 | -0.169 | 1.891 |
| left_hip_yaw_joint | 0.3965 | 1.2074 | 2.2600 | 0.238 | -0.3098 | -0.0622 | -0.2476 | 0.3097 | 60.0 | 0.025 | -0.175 | 2.427 |
| right_hip_yaw_joint | 0.3470 | 1.2060 | 2.2031 | 0.527 | +0.2757 | +0.0986 | +0.1771 | 0.2984 | 70.0 | 0.439 | 0.207 | 4.342 |
| left_ankle_roll_joint | 0.3190 | 0.7603 | 1.2800 | 0.464 | -0.0652 | +0.0186 | -0.0838 | 0.3078 | 60.0 | 0.527 | 0.449 | 3.941 |
| right_ankle_pitch_joint | 0.3027 | 0.8125 | 0.7600 | 1.025 | -0.0467 | -0.0072 | -0.0395 | 0.3001 | -140.0 | 0.118 | 0.099 | 2.258 |
| right_ankle_roll_joint | 0.2915 | 0.9361 | 1.2800 | 0.710 | -0.2419 | -0.1428 | -0.0991 | 0.2742 | 70.0 | 0.355 | 0.244 | 4.178 |

## Interpretation Boundary

- This log can reveal execution-chain tracking stress at high speed.
- It cannot by itself prove body instability because it lacks velocity command, IMU, odometry, contact, and fall-event annotations.
- For parallel ankle joints, raw target tracking is used; LPF columns are not compared to position in this report.
