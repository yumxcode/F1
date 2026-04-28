# Ankle Identifier Analysis: right_pitch_step_kp30_kd0.5.csv

## Basic Info

- **samples**: 18000
- **primary_joint**: right_ankle_pitch_joint
- **coupled_joint**: right_ankle_roll_joint
- **iterations**: [1, 2, 3]
- **phases**: {'pre_hold': 9000, 'active': 3000, 'post_hold': 6000}

## Signal Path Check

- **status**: ok
- **target_span**: 0.015000
- **actual_span**: 0.014953

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
| actual_step | 0.014199 | 0.014199 | 0.014199 |
| tracking_ratio | 0.946581 | 0.946624 | 0.946624 |
| peak_tracking_ratio | 0.995257 | 0.995300 | 0.995300 |
| tail_tracking_ratio | 0.995088 | 0.995133 | 0.995132 |
| final_tracking_ratio | 0.024211 | 0.024255 | 0.024255 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | 0.000382 | 0.000382 | 0.000382 |
| rise_time_sec | 0.108280 | 0.108263 | 0.108263 |
| rise_time_status | too_slow_for_walking | too_slow_for_walking | too_slow_for_walking |
| peak_time_sec | 0.521999 | 0.522000 | 0.521999 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | 0.198000 | 0.198000 | 0.197999 |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | well_damped_tracking | well_damped_tracking | well_damped_tracking |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.014199 | 0.000000 |
| tracking_ratio | 0.946610 | 0.000025 |
| peak_tracking_ratio | 0.995286 | 0.000025 |
| tail_actual_step | 0.014927 | 0.000000 |
| tail_tracking_ratio | 0.995118 | 0.000026 |
| post_actual_step | 0.000364 | 0.000000 |
| final_tracking_ratio | 0.024240 | 0.000025 |
| coupled_motion | -0.000007 | 0.000013 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | 0.000382 | 0.000000 |
| rise_time_sec | 0.108269 | 0.000010 |
| peak_time_sec | 0.521999 | 0.000001 |
| settling_time_sec | 0.198000 | 0.000001 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.276401 | 0.000001 |
| coupled_peak_velocity | 0.067902 | 0.000009 |
| primary_peak_effort | 0.452201 | 0.000004 |
| coupled_peak_effort | 0.035874 | 0.000005 |

- **response_classes**: ['well_damped_tracking', 'well_damped_tracking', 'well_damped_tracking']
- **rise_time_statuses**: ['too_slow_for_walking', 'too_slow_for_walking', 'too_slow_for_walking']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
