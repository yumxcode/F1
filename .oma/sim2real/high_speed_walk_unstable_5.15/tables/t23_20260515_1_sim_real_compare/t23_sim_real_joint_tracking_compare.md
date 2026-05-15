# t23 Sim-vs-Real Joint Tracking Compare

Sim source: `test_logs/data_csv/t23_joint_20260515_1_sim.csv`
Real source: `test_logs/data_csv/t23_joint_20260515_1_real.csv`

## Data Quality

| Dataset | Rows | Duration s | Sample Hz | dt min ms | dt max ms |
|---|---:|---:|---:|---:|---:|
| sim | 4000 | 39.987 | 100.006 | 7.382 | 12.626 |
| real | 4000 | 39.989 | 100.003 | 8.700 | 11.251 |

## Aggregate Tracking

| Metric | Sim | Real | Real / Sim |
|---|---:|---:|---:|
| mean RMS error across joints | 0.2945 rad | 0.4205 rad | 1.43x |
| mean best-delay correlation | 0.757 | 0.231 | 0.31x |

## Largest Real-minus-Sim RMS Gaps

| Joint | Sim RMS | Real RMS | Δ RMS | Real/Sim RMS | Target range Real/Sim | Sim pos/target | Real pos/target | Sim delay ms | Real delay ms | Sim corr | Real corr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| left_hip_pitch_joint | 0.2716 | 0.7169 | +0.4454 | 2.64x | 2.41x | 0.343 | 0.204 | 130.0 | 140.0 | 0.946 | 0.336 |
| right_hip_pitch_joint | 0.2416 | 0.6222 | +0.3806 | 2.58x | 2.52x | 0.296 | 0.336 | 150.0 | 140.0 | 0.811 | 0.019 |
| right_knee_pitch_joint | 0.2589 | 0.5910 | +0.3321 | 2.28x | 1.64x | 0.422 | 0.844 | 70.0 | 150.0 | 0.920 | 0.146 |
| left_hip_yaw_joint | 0.1884 | 0.4161 | +0.2277 | 2.21x | 2.64x | 0.361 | 0.202 | 60.0 | 60.0 | 0.661 | 0.472 |
| left_knee_pitch_joint | 0.2319 | 0.4007 | +0.1688 | 1.73x | 1.04x | 0.364 | 0.891 | 80.0 | 140.0 | 0.944 | 0.336 |
| right_hip_yaw_joint | 0.2038 | 0.3054 | +0.1016 | 1.50x | 2.10x | 0.558 | 0.284 | -200.0 | 80.0 | 0.442 | 0.268 |
| left_ankle_roll_joint | 0.1690 | 0.2274 | +0.0585 | 1.35x | 1.13x | 0.308 | 0.561 | 40.0 | 60.0 | 0.775 | 0.474 |
| right_ankle_roll_joint | 0.2791 | 0.3219 | +0.0429 | 1.15x | 1.71x | 0.538 | 0.442 | 90.0 | 60.0 | 0.941 | 0.238 |
| right_ankle_pitch_joint | 0.2841 | 0.3104 | +0.0264 | 1.09x | 1.00x | 0.391 | 1.157 | -220.0 | -130.0 | 0.311 | -0.313 |
| left_hip_roll_joint | 0.5515 | 0.5722 | +0.0206 | 1.04x | 1.03x | 0.144 | 0.143 | 190.0 | 100.0 | 0.847 | 0.197 |
| right_hip_roll_joint | 0.5043 | 0.3974 | -0.1070 | 0.79x | 1.01x | 0.117 | 0.164 | 200.0 | 80.0 | 0.816 | 0.253 |
| left_ankle_pitch_joint | 0.3505 | 0.1642 | -0.1863 | 0.47x | 1.00x | 0.363 | 0.817 | -140.0 | 60.0 | 0.666 | 0.349 |

## Largest Real Target-Range Increases

| Joint | Sim RMS | Real RMS | Δ RMS | Real/Sim RMS | Target range Real/Sim | Sim pos/target | Real pos/target | Sim delay ms | Real delay ms | Sim corr | Real corr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| left_hip_yaw_joint | 0.1884 | 0.4161 | +0.2277 | 2.21x | 2.64x | 0.361 | 0.202 | 60.0 | 60.0 | 0.661 | 0.472 |
| right_hip_pitch_joint | 0.2416 | 0.6222 | +0.3806 | 2.58x | 2.52x | 0.296 | 0.336 | 150.0 | 140.0 | 0.811 | 0.019 |
| left_hip_pitch_joint | 0.2716 | 0.7169 | +0.4454 | 2.64x | 2.41x | 0.343 | 0.204 | 130.0 | 140.0 | 0.946 | 0.336 |
| right_hip_yaw_joint | 0.2038 | 0.3054 | +0.1016 | 1.50x | 2.10x | 0.558 | 0.284 | -200.0 | 80.0 | 0.442 | 0.268 |
| right_ankle_roll_joint | 0.2791 | 0.3219 | +0.0429 | 1.15x | 1.71x | 0.538 | 0.442 | 90.0 | 60.0 | 0.941 | 0.238 |
| right_knee_pitch_joint | 0.2589 | 0.5910 | +0.3321 | 2.28x | 1.64x | 0.422 | 0.844 | 70.0 | 150.0 | 0.920 | 0.146 |

## Largest Correlation Drops

| Joint | Sim RMS | Real RMS | Δ RMS | Real/Sim RMS | Target range Real/Sim | Sim pos/target | Real pos/target | Sim delay ms | Real delay ms | Sim corr | Real corr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| right_hip_pitch_joint | 0.2416 | 0.6222 | +0.3806 | 2.58x | 2.52x | 0.296 | 0.336 | 150.0 | 140.0 | 0.811 | 0.019 |
| right_knee_pitch_joint | 0.2589 | 0.5910 | +0.3321 | 2.28x | 1.64x | 0.422 | 0.844 | 70.0 | 150.0 | 0.920 | 0.146 |
| right_ankle_roll_joint | 0.2791 | 0.3219 | +0.0429 | 1.15x | 1.71x | 0.538 | 0.442 | 90.0 | 60.0 | 0.941 | 0.238 |
| left_hip_roll_joint | 0.5515 | 0.5722 | +0.0206 | 1.04x | 1.03x | 0.144 | 0.143 | 190.0 | 100.0 | 0.847 | 0.197 |
| right_ankle_pitch_joint | 0.2841 | 0.3104 | +0.0264 | 1.09x | 1.00x | 0.391 | 1.157 | -220.0 | -130.0 | 0.311 | -0.313 |
| left_hip_pitch_joint | 0.2716 | 0.7169 | +0.4454 | 2.64x | 2.41x | 0.343 | 0.204 | 130.0 | 140.0 | 0.946 | 0.336 |

## Interpretation Boundary

- The two logs have nearly identical duration and sample rate, so per-log statistics are comparable.
- Target trajectories are not identical; Real/Sim target-range ratios must be checked before interpreting RMS deltas as pure actuator degradation.
- Delay estimates with low correlation are weak evidence; in those rows, RMS, range ratio, and correlation drop carry more weight than the delay number.
