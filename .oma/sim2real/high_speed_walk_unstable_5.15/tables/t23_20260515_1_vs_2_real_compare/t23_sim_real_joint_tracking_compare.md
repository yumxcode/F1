# t23 Sim-vs-Real Joint Tracking Compare

Sim source: `test_logs/data_csv/t23_joint_20260515_1_real.csv`
Real source: `test_logs/data_csv/t23_joint_20260515_2_real.csv`

## Data Quality

| Dataset | Rows | Duration s | Sample Hz | dt min ms | dt max ms |
|---|---:|---:|---:|---:|---:|
| sim | 4000 | 39.989 | 100.003 | 8.700 | 11.251 |
| real | 4000 | 39.989 | 100.003 | 9.047 | 10.323 |

## Aggregate Tracking

| Metric | Sim | Real | Real / Sim |
|---|---:|---:|---:|
| mean RMS error across joints | 0.4205 rad | 0.4799 rad | 1.14x |
| mean best-delay correlation | 0.231 | 0.138 | 0.60x |

## Largest Real-minus-Sim RMS Gaps

| Joint | Sim RMS | Real RMS | Δ RMS | Real/Sim RMS | Target range Real/Sim | Sim pos/target | Real pos/target | Sim delay ms | Real delay ms | Sim corr | Real corr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| right_hip_roll_joint | 0.3974 | 0.8732 | +0.4758 | 2.20x | 1.00x | 0.164 | 0.240 | 80.0 | 80.0 | 0.253 | 0.031 |
| left_ankle_pitch_joint | 0.1642 | 0.4113 | +0.2472 | 2.51x | 1.00x | 0.817 | 0.589 | 60.0 | 70.0 | 0.349 | -0.111 |
| left_ankle_roll_joint | 0.2274 | 0.3190 | +0.0915 | 1.40x | 1.08x | 0.561 | 0.464 | 60.0 | 60.0 | 0.474 | 0.527 |
| left_knee_pitch_joint | 0.4007 | 0.4651 | +0.0644 | 1.16x | 1.61x | 0.891 | 0.424 | 140.0 | 140.0 | 0.336 | 0.213 |
| right_hip_yaw_joint | 0.3054 | 0.3470 | +0.0416 | 1.14x | 1.20x | 0.284 | 0.527 | 80.0 | 70.0 | 0.268 | 0.439 |
| left_hip_roll_joint | 0.5722 | 0.5826 | +0.0104 | 1.02x | 1.00x | 0.143 | 0.258 | 100.0 | 120.0 | 0.197 | -0.166 |
| right_ankle_pitch_joint | 0.3104 | 0.3027 | -0.0077 | 0.98x | 1.00x | 1.157 | 1.025 | -130.0 | -140.0 | -0.313 | 0.118 |
| left_hip_yaw_joint | 0.4161 | 0.3965 | -0.0195 | 0.95x | 0.88x | 0.202 | 0.238 | 60.0 | 60.0 | 0.472 | 0.025 |
| right_ankle_roll_joint | 0.3219 | 0.2915 | -0.0304 | 0.91x | 1.00x | 0.442 | 0.710 | 60.0 | 70.0 | 0.238 | 0.355 |
| right_hip_pitch_joint | 0.6222 | 0.5867 | -0.0355 | 0.94x | 0.79x | 0.336 | 0.350 | 140.0 | 140.0 | 0.019 | 0.089 |
| right_knee_pitch_joint | 0.5910 | 0.5434 | -0.0476 | 0.92x | 0.87x | 0.844 | 0.873 | 150.0 | 150.0 | 0.146 | -0.011 |
| left_hip_pitch_joint | 0.7169 | 0.6397 | -0.0772 | 0.89x | 1.06x | 0.204 | 0.228 | 140.0 | 140.0 | 0.336 | 0.148 |

## Largest Real Target-Range Increases

| Joint | Sim RMS | Real RMS | Δ RMS | Real/Sim RMS | Target range Real/Sim | Sim pos/target | Real pos/target | Sim delay ms | Real delay ms | Sim corr | Real corr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| left_knee_pitch_joint | 0.4007 | 0.4651 | +0.0644 | 1.16x | 1.61x | 0.891 | 0.424 | 140.0 | 140.0 | 0.336 | 0.213 |
| right_hip_yaw_joint | 0.3054 | 0.3470 | +0.0416 | 1.14x | 1.20x | 0.284 | 0.527 | 80.0 | 70.0 | 0.268 | 0.439 |
| left_ankle_roll_joint | 0.2274 | 0.3190 | +0.0915 | 1.40x | 1.08x | 0.561 | 0.464 | 60.0 | 60.0 | 0.474 | 0.527 |
| left_hip_pitch_joint | 0.7169 | 0.6397 | -0.0772 | 0.89x | 1.06x | 0.204 | 0.228 | 140.0 | 140.0 | 0.336 | 0.148 |
| left_ankle_pitch_joint | 0.1642 | 0.4113 | +0.2472 | 2.51x | 1.00x | 0.817 | 0.589 | 60.0 | 70.0 | 0.349 | -0.111 |
| left_hip_roll_joint | 0.5722 | 0.5826 | +0.0104 | 1.02x | 1.00x | 0.143 | 0.258 | 100.0 | 120.0 | 0.197 | -0.166 |

## Largest Correlation Drops

| Joint | Sim RMS | Real RMS | Δ RMS | Real/Sim RMS | Target range Real/Sim | Sim pos/target | Real pos/target | Sim delay ms | Real delay ms | Sim corr | Real corr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| left_ankle_pitch_joint | 0.1642 | 0.4113 | +0.2472 | 2.51x | 1.00x | 0.817 | 0.589 | 60.0 | 70.0 | 0.349 | -0.111 |
| left_hip_yaw_joint | 0.4161 | 0.3965 | -0.0195 | 0.95x | 0.88x | 0.202 | 0.238 | 60.0 | 60.0 | 0.472 | 0.025 |
| left_hip_roll_joint | 0.5722 | 0.5826 | +0.0104 | 1.02x | 1.00x | 0.143 | 0.258 | 100.0 | 120.0 | 0.197 | -0.166 |
| right_hip_roll_joint | 0.3974 | 0.8732 | +0.4758 | 2.20x | 1.00x | 0.164 | 0.240 | 80.0 | 80.0 | 0.253 | 0.031 |
| left_hip_pitch_joint | 0.7169 | 0.6397 | -0.0772 | 0.89x | 1.06x | 0.204 | 0.228 | 140.0 | 140.0 | 0.336 | 0.148 |
| right_knee_pitch_joint | 0.5910 | 0.5434 | -0.0476 | 0.92x | 0.87x | 0.844 | 0.873 | 150.0 | 150.0 | 0.146 | -0.011 |

## Mean/Bias Diagnostics

| Joint | Sim target mean | Real target mean | Sim pos mean | Real pos mean | Sim error mean | Real error mean | Sim error std | Real error std | Sim zero corr | Real zero corr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| right_hip_roll_joint | +0.1899 | +0.4780 | -0.0415 | -0.0449 | +0.2314 | +0.5229 | 0.3230 | 0.6993 | 0.114 | -0.019 |
| left_ankle_pitch_joint | -0.3268 | -0.0405 | -0.3138 | -0.2507 | -0.0130 | +0.2102 | 0.1637 | 0.3536 | 0.264 | -0.169 |
| left_ankle_roll_joint | +0.2775 | -0.0652 | +0.1900 | +0.0186 | +0.0876 | -0.0838 | 0.2099 | 0.3078 | 0.392 | 0.449 |
| left_knee_pitch_joint | +0.3431 | +0.6472 | +0.5344 | +0.5280 | -0.1913 | +0.1192 | 0.3521 | 0.4496 | 0.033 | -0.069 |
| right_hip_yaw_joint | +0.2100 | +0.2757 | +0.0120 | +0.0986 | +0.1980 | +0.1771 | 0.2325 | 0.2984 | -0.029 | 0.207 |
| left_hip_roll_joint | -0.2779 | -0.3013 | +0.0596 | +0.1269 | -0.3375 | -0.4282 | 0.4620 | 0.3951 | -0.055 | -0.299 |
| right_ankle_pitch_joint | -0.2380 | -0.0467 | -0.0904 | -0.0072 | -0.1477 | -0.0395 | 0.2731 | 0.3001 | -0.382 | 0.099 |
| left_hip_yaw_joint | -0.4829 | -0.3098 | -0.1754 | -0.0622 | -0.3075 | -0.2476 | 0.2802 | 0.3097 | 0.294 | -0.175 |
| right_ankle_roll_joint | +0.0906 | -0.2419 | -0.0864 | -0.1428 | +0.1770 | -0.0991 | 0.2689 | 0.2742 | 0.146 | 0.244 |
| right_hip_pitch_joint | -0.7333 | -0.1740 | -0.3256 | -0.4572 | -0.4077 | +0.2833 | 0.4700 | 0.5138 | -0.286 | -0.120 |
| right_knee_pitch_joint | +0.5300 | +0.6121 | +0.3746 | +0.3130 | +0.1554 | +0.2991 | 0.5702 | 0.4537 | -0.124 | -0.410 |
| left_hip_pitch_joint | +0.8012 | +0.3254 | +0.3815 | +0.2428 | +0.4197 | +0.0826 | 0.5812 | 0.6343 | 0.166 | 0.057 |

## Interpretation Boundary

- The two logs have nearly identical duration and sample rate, so per-log statistics are comparable.
- Target trajectories are not identical; Real/Sim target-range ratios must be checked before interpreting RMS deltas as pure actuator degradation.
- Delay estimates with low correlation are weak evidence; in those rows, RMS, range ratio, and correlation drop carry more weight than the delay number.
