# Ankle Identifier Analysis: left_pitch_step_kp30_kd0.5.csv

## Basic Info

- **samples**: 18000
- **primary_joint**: left_ankle_pitch_joint
- **coupled_joint**: left_ankle_roll_joint
- **iterations**: [1, 2, 3]
- **phases**: {'pre_hold': 9000, 'active': 3000, 'post_hold': 6000}

## Signal Path Check

- **status**: ok
- **target_span**: 0.015000
- **actual_span**: 0.014943

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
| actual_step | 0.014197 | 0.014200 | 0.014200 |
| tracking_ratio | 0.946447 | 0.946638 | 0.946638 |
| peak_tracking_ratio | 0.995142 | 0.995333 | 0.995333 |
| tail_tracking_ratio | 0.994974 | 0.995165 | 0.995165 |
| final_tracking_ratio | 0.024069 | 0.024260 | 0.024260 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | 0.000323 | 0.000323 | 0.000323 |
| rise_time_sec | 0.108330 | 0.108257 | 0.108258 |
| rise_time_status | too_slow_for_walking | too_slow_for_walking | too_slow_for_walking |
| peak_time_sec | 0.561999 | 0.562003 | 0.564004 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | 0.212000 | 0.212013 | 0.212000 |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | well_damped_tracking | well_damped_tracking | well_damped_tracking |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.014199 | 0.000002 |
| tracking_ratio | 0.946575 | 0.000110 |
| peak_tracking_ratio | 0.995270 | 0.000110 |
| tail_actual_step | 0.014927 | 0.000002 |
| tail_tracking_ratio | 0.995101 | 0.000110 |
| post_actual_step | 0.000363 | 0.000002 |
| final_tracking_ratio | 0.024196 | 0.000110 |
| coupled_motion | 0.000007 | 0.000012 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | 0.000323 | 0.000000 |
| rise_time_sec | 0.108282 | 0.000042 |
| peak_time_sec | 0.562669 | 0.001156 |
| settling_time_sec | 0.212004 | 0.000008 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.275896 | 0.000002 |
| coupled_peak_velocity | 0.067368 | 0.000100 |
| primary_peak_effort | 0.453691 | 0.000004 |
| coupled_peak_effort | 0.035207 | 0.000055 |

- **response_classes**: ['well_damped_tracking', 'well_damped_tracking', 'well_damped_tracking']
- **rise_time_statuses**: ['too_slow_for_walking', 'too_slow_for_walking', 'too_slow_for_walking']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
