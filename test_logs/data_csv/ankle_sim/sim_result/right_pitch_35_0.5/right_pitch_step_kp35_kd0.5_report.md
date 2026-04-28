# Ankle Identifier Analysis: right_pitch_step_kp35_kd0.5.csv

## Basic Info

- **samples**: 18000
- **primary_joint**: right_ankle_pitch_joint
- **coupled_joint**: right_ankle_roll_joint
- **iterations**: [1, 2, 3]
- **phases**: {'pre_hold': 9000, 'active': 3000, 'post_hold': 6000}

## Signal Path Check

- **status**: ok
- **target_span**: 0.015000
- **actual_span**: 0.014961

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
| actual_step | 0.014315 | 0.014315 | 0.014315 |
| tracking_ratio | 0.954313 | 0.954359 | 0.954359 |
| peak_tracking_ratio | 0.995987 | 0.996033 | 0.996033 |
| tail_tracking_ratio | 0.995821 | 0.995865 | 0.995865 |
| final_tracking_ratio | 0.020710 | 0.020756 | 0.020756 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | 0.000327 | 0.000327 | 0.000327 |
| rise_time_sec | 0.092289 | 0.092260 | 0.092286 |
| rise_time_status | too_slow_for_walking | too_slow_for_walking | too_slow_for_walking |
| peak_time_sec | 0.361999 | 0.362000 | 0.362001 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | 0.166998 | 0.167002 | 0.167000 |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | well_damped_tracking | well_damped_tracking | well_damped_tracking |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.014315 | 0.000000 |
| tracking_ratio | 0.954343 | 0.000027 |
| peak_tracking_ratio | 0.996018 | 0.000027 |
| tail_actual_step | 0.014938 | 0.000000 |
| tail_tracking_ratio | 0.995850 | 0.000026 |
| post_actual_step | 0.000311 | 0.000000 |
| final_tracking_ratio | 0.020741 | 0.000027 |
| coupled_motion | -0.000006 | 0.000011 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | 0.000327 | 0.000000 |
| rise_time_sec | 0.092278 | 0.000016 |
| peak_time_sec | 0.362000 | 0.000001 |
| settling_time_sec | 0.167000 | 0.000002 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.319694 | 0.000001 |
| coupled_peak_velocity | 0.067986 | 0.000009 |
| primary_peak_effort | 0.527216 | 0.000004 |
| coupled_peak_effort | 0.036088 | 0.000005 |

- **response_classes**: ['well_damped_tracking', 'well_damped_tracking', 'well_damped_tracking']
- **rise_time_statuses**: ['too_slow_for_walking', 'too_slow_for_walking', 'too_slow_for_walking']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
