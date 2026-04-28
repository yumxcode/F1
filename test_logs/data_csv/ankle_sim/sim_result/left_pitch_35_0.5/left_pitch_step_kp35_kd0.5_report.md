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
- **actual_span**: 0.014956

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
| actual_step | 0.014313 | 0.014315 | 0.014315 |
| tracking_ratio | 0.954200 | 0.954365 | 0.954365 |
| peak_tracking_ratio | 0.995869 | 0.996033 | 0.996033 |
| tail_tracking_ratio | 0.995700 | 0.995865 | 0.995867 |
| final_tracking_ratio | 0.020596 | 0.020761 | 0.020761 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | 0.000276 | 0.000276 | 0.000276 |
| rise_time_sec | 0.092341 | 0.092271 | 0.092269 |
| rise_time_status | too_slow_for_walking | too_slow_for_walking | too_slow_for_walking |
| peak_time_sec | 0.363999 | 0.363999 | 0.364000 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | 0.176009 | 0.175998 | 0.176004 |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | well_damped_tracking | well_damped_tracking | well_damped_tracking |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.014315 | 0.000001 |
| tracking_ratio | 0.954310 | 0.000095 |
| peak_tracking_ratio | 0.995978 | 0.000095 |
| tail_actual_step | 0.014937 | 0.000001 |
| tail_tracking_ratio | 0.995811 | 0.000096 |
| post_actual_step | 0.000311 | 0.000001 |
| final_tracking_ratio | 0.020706 | 0.000095 |
| coupled_motion | 0.000006 | 0.000010 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | 0.000276 | 0.000000 |
| rise_time_sec | 0.092293 | 0.000041 |
| peak_time_sec | 0.363999 | 0.000001 |
| settling_time_sec | 0.176004 | 0.000006 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.319124 | 0.000002 |
| coupled_peak_velocity | 0.067452 | 0.000099 |
| primary_peak_effort | 0.528706 | 0.000003 |
| coupled_peak_effort | 0.035419 | 0.000056 |

- **response_classes**: ['well_damped_tracking', 'well_damped_tracking', 'well_damped_tracking']
- **rise_time_statuses**: ['too_slow_for_walking', 'too_slow_for_walking', 'too_slow_for_walking']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
