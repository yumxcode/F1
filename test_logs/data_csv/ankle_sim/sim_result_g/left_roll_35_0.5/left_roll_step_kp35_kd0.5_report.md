# Ankle Identifier Analysis: left_roll_step_kp35_kd0.5.csv

## Basic Info

- **samples**: 18000
- **primary_joint**: left_ankle_roll_joint
- **coupled_joint**: left_ankle_pitch_joint
- **iterations**: [1, 2, 3]
- **phases**: {'pre_hold': 9000, 'active': 3000, 'post_hold': 6000}

## Signal Path Check

- **status**: ok
- **target_span**: 0.015000
- **actual_span**: 0.137036

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
| actual_step | 0.001323 | 0.001642 | -0.014193 |
| tracking_ratio | 0.088218 | 0.109495 | -0.946211 |
| peak_tracking_ratio | 0.116386 | 0.140762 | 2.931615 |
| tail_tracking_ratio | 0.109571 | 0.132342 | -2.148836 |
| final_tracking_ratio | 0.058852 | 0.084660 | -2.699900 |
| peak_overshoot | 0.000000 | 0.000000 | 0.028974 |
| overshoot_ratio | 0.000000 | 0.000000 | 1.931615 |
| steady_error | 0.000802 | 0.002615 | -0.020667 |
| rise_time_sec | N/A | N/A | 0.000000 |
| rise_time_status | not_available | not_available | too_fast |
| peak_time_sec | 0.349999 | 0.999001 | 0.000000 |
| peak_time_status | unusable_for_walking | unusable_for_walking | too_fast |
| settling_time_sec | N/A | N/A | N/A |
| zero_crossing_count | 0 | 0 | 1 |
| response_class | undershoot_soft | undershoot_soft | undershoot_soft |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | -0.003742 | 0.009052 |
| tracking_ratio | -0.249499 | 0.603464 |
| peak_tracking_ratio | 1.062921 | 1.618382 |
| tail_actual_step | -0.009535 | 0.019658 |
| tail_tracking_ratio | -0.635641 | 1.310515 |
| post_actual_step | -0.012782 | 0.024004 |
| final_tracking_ratio | -0.852129 | 1.600268 |
| coupled_motion | 0.055809 | 0.110394 |
| peak_overshoot | 0.009658 | 0.016728 |
| overshoot_ratio | 0.643872 | 1.115218 |
| steady_error | -0.005750 | 0.012950 |
| rise_time_sec | 0.000000 | 0.000000 |
| peak_time_sec | 0.449667 | 0.506903 |
| first_target_cross_time_sec | 0.000000 | 0.000000 |
| zero_crossing_count | 0.333333 | 0.577350 |
| decay_ratio | 1.002890 | 0.000000 |
| primary_peak_velocity | 0.918199 | 1.556557 |
| coupled_peak_velocity | 1.696125 | 2.924207 |
| primary_peak_effort | 0.928571 | 0.757942 |
| coupled_peak_effort | 4.800550 | 5.200091 |

- **response_classes**: ['undershoot_soft', 'undershoot_soft', 'undershoot_soft']
- **rise_time_statuses**: ['not_available', 'not_available', 'too_fast']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'too_fast']
