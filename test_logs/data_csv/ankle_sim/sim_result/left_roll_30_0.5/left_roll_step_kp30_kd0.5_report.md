# Ankle Identifier Analysis: left_roll_step_kp30_kd0.5.csv

## Basic Info

- **samples**: 18000
- **primary_joint**: left_ankle_roll_joint
- **coupled_joint**: left_ankle_pitch_joint
- **iterations**: [1, 2, 3]
- **phases**: {'pre_hold': 9000, 'active': 3000, 'post_hold': 6000}

## Signal Path Check

- **status**: ok
- **target_span**: 0.015000
- **actual_span**: 0.016234

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
| actual_step | 0.014220 | 0.014199 | 0.014200 |
| tracking_ratio | 0.948029 | 0.946632 | 0.946637 |
| peak_tracking_ratio | 0.998842 | 0.997379 | 0.997385 |
| tail_tracking_ratio | 0.996548 | 0.995163 | 0.995146 |
| final_tracking_ratio | 0.025655 | 0.024256 | 0.024260 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | 0.000347 | 0.000347 | 0.000347 |
| rise_time_sec | 0.109285 | 0.109393 | 0.109396 |
| rise_time_status | too_slow_for_walking | too_slow_for_walking | too_slow_for_walking |
| peak_time_sec | 0.462000 | 0.444002 | 0.444018 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | 0.214000 | 0.213996 | 0.213999 |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | well_damped_tracking | well_damped_tracking | well_damped_tracking |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.014206 | 0.000012 |
| tracking_ratio | 0.947099 | 0.000805 |
| peak_tracking_ratio | 0.997869 | 0.000843 |
| tail_actual_step | 0.014934 | 0.000012 |
| tail_tracking_ratio | 0.995619 | 0.000805 |
| post_actual_step | 0.000371 | 0.000012 |
| final_tracking_ratio | 0.024724 | 0.000807 |
| coupled_motion | -0.000001 | 0.000002 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | 0.000347 | 0.000000 |
| rise_time_sec | 0.109358 | 0.000063 |
| peak_time_sec | 0.450007 | 0.010387 |
| settling_time_sec | 0.213998 | 0.000002 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.355777 | 0.000102 |
| coupled_peak_velocity | 0.004837 | 0.000007 |
| primary_peak_effort | 0.484862 | 0.000047 |
| coupled_peak_effort | 0.003738 | 0.000003 |

- **response_classes**: ['well_damped_tracking', 'well_damped_tracking', 'well_damped_tracking']
- **rise_time_statuses**: ['too_slow_for_walking', 'too_slow_for_walking', 'too_slow_for_walking']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
