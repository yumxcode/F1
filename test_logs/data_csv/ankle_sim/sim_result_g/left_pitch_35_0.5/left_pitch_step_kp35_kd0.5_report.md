# Ankle Identifier Analysis: left_pitch_step_kp35_kd0.5.csv

## Basic Info

- **samples**: 18000
- **primary_joint**: left_ankle_pitch_joint
- **coupled_joint**: left_ankle_roll_joint
- **iterations**: [1, 2, 3]
- **phases**: {'pre_hold': 9000, 'active': 3000, 'post_hold': 6000}

## Signal Path Check

- **status**: ok
- **target_span**: 0.015000
- **actual_span**: 0.522289

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
| actual_step | -0.005084 | -0.003366 | 0.184370 |
| tracking_ratio | -0.338916 | -0.224413 | 12.291312 |
| peak_tracking_ratio | -0.187839 | 0.128276 | 13.243439 |
| tail_tracking_ratio | -0.194859 | 0.085638 | 12.552027 |
| final_tracking_ratio | -1.006973 | -0.231046 | 11.524287 |
| peak_overshoot | 0.000000 | 0.000000 | 0.183652 |
| overshoot_ratio | 0.000000 | 0.000000 | 12.243439 |
| steady_error | -0.041273 | -0.056595 | 0.073994 |
| rise_time_sec | N/A | N/A | 0.000000 |
| rise_time_status | not_available | not_available | too_fast |
| peak_time_sec | 0.998999 | 0.998999 | 0.372001 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | N/A | N/A | N/A |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | undershoot_soft | undershoot_soft | single_overshoot |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.058640 | 0.108889 |
| tracking_ratio | 3.909328 | 7.259237 |
| peak_tracking_ratio | 4.394625 | 7.664927 |
| tail_actual_step | 0.062214 | 0.109197 |
| tail_tracking_ratio | 4.147602 | 7.279797 |
| post_actual_step | 0.051431 | 0.105325 |
| final_tracking_ratio | 3.428756 | 7.021662 |
| coupled_motion | -0.013064 | 0.023133 |
| peak_overshoot | 0.061217 | 0.106031 |
| overshoot_ratio | 4.081146 | 7.068753 |
| steady_error | -0.007958 | 0.071385 |
| rise_time_sec | 0.000000 | 0.000000 |
| peak_time_sec | 0.790000 | 0.361997 |
| first_target_cross_time_sec | 0.000000 | 0.000000 |
| zero_crossing_count | 0.000000 | 0.000000 |
| decay_ratio | 1.000119 | 0.000000 |
| primary_peak_velocity | 0.171860 | 0.276051 |
| coupled_peak_velocity | 0.137486 | 0.237545 |
| primary_peak_effort | 2.472736 | 0.684203 |
| coupled_peak_effort | 0.480539 | 0.781963 |

- **response_classes**: ['undershoot_soft', 'undershoot_soft', 'single_overshoot']
- **rise_time_statuses**: ['not_available', 'not_available', 'too_fast']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
