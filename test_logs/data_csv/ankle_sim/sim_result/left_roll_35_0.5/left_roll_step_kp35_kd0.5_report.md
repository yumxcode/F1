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
- **actual_span**: 0.016244

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
| actual_step | 0.014333 | 0.014315 | 0.014315 |
| tracking_ratio | 0.955543 | 0.954346 | 0.954347 |
| peak_tracking_ratio | 0.999363 | 0.998164 | 0.998164 |
| tail_tracking_ratio | 0.997019 | 0.995844 | 0.995828 |
| final_tracking_ratio | 0.021955 | 0.020756 | 0.020756 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | 0.000297 | 0.000297 | 0.000297 |
| rise_time_sec | 0.093754 | 0.093887 | 0.093882 |
| rise_time_status | too_slow_for_walking | too_slow_for_walking | too_slow_for_walking |
| peak_time_sec | 0.423999 | 0.421999 | 0.420001 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | 0.179998 | 0.179999 | 0.180002 |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | well_damped_tracking | well_damped_tracking | well_damped_tracking |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.014321 | 0.000010 |
| tracking_ratio | 0.954745 | 0.000691 |
| peak_tracking_ratio | 0.998563 | 0.000692 |
| tail_actual_step | 0.014943 | 0.000010 |
| tail_tracking_ratio | 0.996230 | 0.000683 |
| post_actual_step | 0.000317 | 0.000010 |
| final_tracking_ratio | 0.021156 | 0.000692 |
| coupled_motion | -0.000001 | 0.000001 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | 0.000297 | 0.000000 |
| rise_time_sec | 0.093841 | 0.000076 |
| peak_time_sec | 0.422000 | 0.001999 |
| settling_time_sec | 0.180000 | 0.000002 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.402157 | 0.000102 |
| coupled_peak_velocity | 0.004848 | 0.000007 |
| primary_peak_effort | 0.560071 | 0.000047 |
| coupled_peak_effort | 0.003762 | 0.000004 |

- **response_classes**: ['well_damped_tracking', 'well_damped_tracking', 'well_damped_tracking']
- **rise_time_statuses**: ['too_slow_for_walking', 'too_slow_for_walking', 'too_slow_for_walking']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
