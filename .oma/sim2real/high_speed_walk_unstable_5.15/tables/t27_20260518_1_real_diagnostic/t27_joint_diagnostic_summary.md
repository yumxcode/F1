# t27 Joint Diagnostic Summary

Source: `test_logs/data_csv/t27_joint_20260518_1_real.csv`
Rows: 2052
Duration: 20.509 s
Sample rate: 100.002 Hz
dt range: 9.442 .. 10.284 ms

## Command / Contact / Base Motion

| Metric | Value |
|---|---:|
| cmd_linear_x mean / max | 0.399 / 0.400 |
| cmd_linear_y abs max | 0.000 |
| cmd_angular_z abs max | 0.000 |
| left_contact fraction / transitions | 0.136 / 171 |
| right_contact fraction / transitions | 0.669 / 202 |
| base roll x std / abs p95 / max | 0.0225 / 0.0617 / 0.0944 |
| base pitch y std / abs p95 / max | 0.0227 / 0.0669 / 0.0876 |
| base yaw z range | 0.7363 |
| gyro x/y/z abs p95 | 0.7576 / 0.6822 / 1.2882 |

## Top Tracking Errors

| Joint | Target used | RMS | Err mean | Err std | Target range | Pos range | Pos/target | Delay ms | Corr | Lower hit | Upper hit | Effort p95 | Tau cmd p95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| right_hip_pitch_joint | pos_des_lpf | 0.6408 | +0.4060 | 0.4958 | 2.2262 | 0.5530 | 0.248 | 130.0 | 0.444 | 0.0% | 0.0% | 14.432 | nan |
| left_hip_roll_joint | pos_des_lpf | 0.3958 | -0.0328 | 0.3944 | 1.7930 | 0.2046 | 0.114 | 60.0 | 0.411 | 2.0% | 59.6% | 33.675 | nan |
| right_hip_roll_joint | pos_des_lpf | 0.3894 | +0.1712 | 0.3497 | 1.6825 | 0.2514 | 0.149 | 130.0 | 0.018 | 7.6% | 0.2% | 38.364 | nan |
| right_knee_pitch_joint | pos_des_lpf | 0.3869 | +0.1408 | 0.3603 | 1.0795 | 0.9135 | 0.846 | 120.0 | 0.135 | 0.7% | 0.0% | 32.992 | nan |
| left_hip_pitch_joint | pos_des_lpf | 0.3498 | +0.1432 | 0.3191 | 2.1498 | 0.3816 | 0.177 | 130.0 | 0.374 | 0.3% | 0.0% | 14.579 | nan |
| right_ankle_pitch_joint | pos_des_raw | 0.3307 | +0.1676 | 0.2851 | 0.7600 | 0.4408 | 0.580 | -190.0 | 0.537 | 14.3% | 51.7% | 13.588 | 14.099 |
| right_hip_yaw_joint | pos_des_lpf | 0.3299 | -0.1443 | 0.2967 | 1.7125 | 0.6309 | 0.368 | 50.0 | 0.406 | 0.0% | 0.0% | 10.623 | nan |
| left_knee_pitch_joint | pos_des_lpf | 0.3162 | -0.2229 | 0.2243 | 1.2543 | 0.5540 | 0.442 | 110.0 | 0.564 | 1.4% | 0.0% | 29.280 | nan |
| left_ankle_pitch_joint | pos_des_raw | 0.2823 | +0.1203 | 0.2554 | 0.7600 | 0.3598 | 0.473 | 80.0 | -0.083 | 15.9% | 9.6% | 9.220 | 21.268 |
| left_hip_yaw_joint | pos_des_lpf | 0.2433 | +0.0507 | 0.2380 | 1.6201 | 0.4497 | 0.278 | 40.0 | 0.199 | 0.0% | 0.0% | 10.476 | nan |
| right_ankle_roll_joint | pos_des_raw | 0.2380 | -0.1338 | 0.1969 | 1.0493 | 0.5493 | 0.524 | 50.0 | 0.398 | 0.3% | 0.0% | 10.930 | 12.685 |
| left_ankle_roll_joint | pos_des_raw | 0.1783 | +0.0110 | 0.1779 | 1.2800 | 0.4571 | 0.357 | 60.0 | 0.452 | 0.0% | 1.4% | 10.789 | 11.185 |

## Focus: Roll And Ankle Channels

| Joint | Target used | RMS | Err mean | Err std | Target range | Pos range | Pos/target | Delay ms | Corr | Lower hit | Upper hit | Effort p95 | Tau cmd p95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| left_hip_roll_joint | pos_des_lpf | 0.3958 | -0.0328 | 0.3944 | 1.7930 | 0.2046 | 0.114 | 60.0 | 0.411 | 2.0% | 59.6% | 33.675 | nan |
| left_ankle_pitch_joint | pos_des_raw | 0.2823 | +0.1203 | 0.2554 | 0.7600 | 0.3598 | 0.473 | 80.0 | -0.083 | 15.9% | 9.6% | 9.220 | 21.268 |
| left_ankle_roll_joint | pos_des_raw | 0.1783 | +0.0110 | 0.1779 | 1.2800 | 0.4571 | 0.357 | 60.0 | 0.452 | 0.0% | 1.4% | 10.789 | 11.185 |
| right_hip_roll_joint | pos_des_lpf | 0.3894 | +0.1712 | 0.3497 | 1.6825 | 0.2514 | 0.149 | 130.0 | 0.018 | 7.6% | 0.2% | 38.364 | nan |
| right_ankle_pitch_joint | pos_des_raw | 0.3307 | +0.1676 | 0.2851 | 0.7600 | 0.4408 | 0.580 | -190.0 | 0.537 | 14.3% | 51.7% | 13.588 | 14.099 |
| right_ankle_roll_joint | pos_des_raw | 0.2380 | -0.1338 | 0.1969 | 1.0493 | 0.5493 | 0.524 | 50.0 | 0.398 | 0.3% | 0.0% | 10.930 | 12.685 |

## Lowest Correlations

| Joint | Target used | RMS | Err mean | Err std | Target range | Pos range | Pos/target | Delay ms | Corr | Lower hit | Upper hit | Effort p95 | Tau cmd p95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| left_ankle_pitch_joint | pos_des_raw | 0.2823 | +0.1203 | 0.2554 | 0.7600 | 0.3598 | 0.473 | 80.0 | -0.083 | 15.9% | 9.6% | 9.220 | 21.268 |
| right_hip_roll_joint | pos_des_lpf | 0.3894 | +0.1712 | 0.3497 | 1.6825 | 0.2514 | 0.149 | 130.0 | 0.018 | 7.6% | 0.2% | 38.364 | nan |
| right_knee_pitch_joint | pos_des_lpf | 0.3869 | +0.1408 | 0.3603 | 1.0795 | 0.9135 | 0.846 | 120.0 | 0.135 | 0.7% | 0.0% | 32.992 | nan |
| left_hip_yaw_joint | pos_des_lpf | 0.2433 | +0.0507 | 0.2380 | 1.6201 | 0.4497 | 0.278 | 40.0 | 0.199 | 0.0% | 0.0% | 10.476 | nan |
| left_hip_pitch_joint | pos_des_lpf | 0.3498 | +0.1432 | 0.3191 | 2.1498 | 0.3816 | 0.177 | 130.0 | 0.374 | 0.3% | 0.0% | 14.579 | nan |
| right_ankle_roll_joint | pos_des_raw | 0.2380 | -0.1338 | 0.1969 | 1.0493 | 0.5493 | 0.524 | 50.0 | 0.398 | 0.3% | 0.0% | 10.930 | 12.685 |

## Interpretation Boundary

- Serial joints are evaluated against `pos_des_lpf`, the position command actually sent by the controller.
- Parallel ankle joints are evaluated against `pos_des_raw` as a virtual position target; their actual command path is `tau_des_lpf`.
- Contact fields are controller-detected contact flags; they are useful for phase segmentation but are not force-plate ground truth.
