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
- **actual_span**: 0.015012

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
| actual_step | 0.014297 | 0.014315 | 0.014315 |
| tracking_ratio | 0.953103 | 0.954353 | 0.954355 |
| peak_tracking_ratio | 0.996979 | 0.998232 | 0.998232 |
| tail_tracking_ratio | 0.994636 | 0.995862 | 0.995862 |
| final_tracking_ratio | 0.019502 | 0.020754 | 0.020755 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | 0.000286 | 0.000286 | 0.000286 |
| rise_time_sec | 0.094606 | 0.093322 | 0.093180 |
| rise_time_status | too_slow_for_walking | too_slow_for_walking | too_slow_for_walking |
| peak_time_sec | 0.410992 | 0.418999 | 0.417016 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | 0.182992 | 0.182999 | 0.182999 |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | well_damped_tracking | well_damped_tracking | well_damped_tracking |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.014309 | 0.000011 |
| tracking_ratio | 0.953937 | 0.000722 |
| peak_tracking_ratio | 0.997814 | 0.000723 |
| tail_actual_step | 0.014932 | 0.000011 |
| tail_tracking_ratio | 0.995453 | 0.000708 |
| post_actual_step | 0.000305 | 0.000011 |
| final_tracking_ratio | 0.020337 | 0.000723 |
| coupled_motion | -0.000000 | 0.000000 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | 0.000286 | 0.000000 |
| rise_time_sec | 0.093703 | 0.000786 |
| peak_time_sec | 0.415669 | 0.004170 |
| settling_time_sec | 0.182997 | 0.000004 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.403195 | 0.000025 |
| coupled_peak_velocity | 0.005459 | 0.000001 |
| primary_peak_effort | 0.491078 | 0.000026 |
| coupled_peak_effort | 0.003362 | 0.000001 |

- **response_classes**: ['well_damped_tracking', 'well_damped_tracking', 'well_damped_tracking']
- **rise_time_statuses**: ['too_slow_for_walking', 'too_slow_for_walking', 'too_slow_for_walking']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
