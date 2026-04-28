# Ankle Identifier Analysis: right_roll_step_kp35_kd0.5.csv

## Basic Info

- **samples**: 18000
- **primary_joint**: right_ankle_roll_joint
- **coupled_joint**: right_ankle_pitch_joint
- **iterations**: [1, 2, 3]
- **phases**: {'pre_hold': 9000, 'active': 3000, 'post_hold': 6000}

## Signal Path Check

- **status**: ok
- **target_span**: 0.015000
- **actual_span**: 0.003709

## Timing Context

- **control_hz**: 1000
- **cycle_time_sec**: 0.700000
- **stance_time_sec**: 0.420000
- **rise_time_bounds**: [0.005000, 0.084000]
- **peak_time_bounds**: [0.015000, 0.147000]

## Per-Iteration Results

| Field | Iter 1 | Iter 2 | Iter 3 |
|---| --- | --- | --- |
| command_step | 0.015000 | 0.015000 | 0.015000 |
| actual_step | 0.000781 | 0.000675 | 0.000805 |
| tracking_ratio | 0.052045 | 0.044998 | 0.053658 |
| peak_tracking_ratio | 0.084029 | 0.076535 | 0.084865 |
| tail_tracking_ratio | 0.062437 | 0.057229 | 0.067048 |
| final_tracking_ratio | -0.031975 | -0.027801 | -0.014601 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | -0.000644 | -0.001520 | -0.002094 |
| rise_time_sec | N/A | N/A | N/A |
| rise_time_status | not_available | not_available | not_available |
| peak_time_sec | 0.349999 | 0.350000 | 0.351014 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | N/A | N/A | N/A |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | undershoot_soft | undershoot_soft | undershoot_soft |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.000754 | 0.000069 |
| tracking_ratio | 0.050234 | 0.004606 |
| peak_tracking_ratio | 0.081809 | 0.004587 |
| tail_actual_step | 0.000934 | 0.000074 |
| tail_tracking_ratio | 0.062238 | 0.004913 |
| post_actual_step | -0.000372 | 0.000136 |
| final_tracking_ratio | -0.024792 | 0.009069 |
| coupled_motion | -0.004689 | 0.002821 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | -0.001419 | 0.000730 |
| peak_time_sec | 0.350338 | 0.000586 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.019169 | 0.000143 |
| coupled_peak_velocity | 0.004160 | 0.005493 |
| primary_peak_effort | 0.569518 | 0.029833 |
| coupled_peak_effort | 1.780456 | 0.478661 |

- **response_classes**: ['undershoot_soft', 'undershoot_soft', 'undershoot_soft']
- **rise_time_statuses**: ['not_available', 'not_available', 'not_available']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
