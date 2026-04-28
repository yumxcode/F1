# Ankle Identifier Analysis: right_roll_step_kp30_kd0.5.csv

## Basic Info

- **samples**: 18000
- **primary_joint**: right_ankle_roll_joint
- **coupled_joint**: right_ankle_pitch_joint
- **iterations**: [1, 2, 3]
- **phases**: {'pre_hold': 9000, 'active': 3000, 'post_hold': 6000}

## Signal Path Check

- **status**: ok
- **target_span**: 0.015000
- **actual_span**: 0.015001

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
| actual_step | 0.014178 | 0.014200 | 0.014200 |
| tracking_ratio | 0.945178 | 0.946639 | 0.946639 |
| peak_tracking_ratio | 0.996042 | 0.997502 | 0.997503 |
| tail_tracking_ratio | 0.993728 | 0.995169 | 0.995191 |
| final_tracking_ratio | 0.022796 | 0.024257 | 0.024257 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | 0.000334 | 0.000334 | 0.000334 |
| rise_time_sec | 0.110199 | 0.110037 | 0.110033 |
| rise_time_status | too_slow_for_walking | too_slow_for_walking | too_slow_for_walking |
| peak_time_sec | 0.467000 | 0.458998 | 0.450999 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | 0.219002 | 0.219001 | 0.218999 |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | well_damped_tracking | well_damped_tracking | well_damped_tracking |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | 0.014192 | 0.000013 |
| tracking_ratio | 0.946152 | 0.000843 |
| peak_tracking_ratio | 0.997016 | 0.000843 |
| tail_actual_step | 0.014920 | 0.000013 |
| tail_tracking_ratio | 0.994696 | 0.000838 |
| post_actual_step | 0.000357 | 0.000013 |
| final_tracking_ratio | 0.023770 | 0.000844 |
| coupled_motion | -0.000000 | 0.000000 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | 0.000334 | 0.000000 |
| rise_time_sec | 0.110090 | 0.000095 |
| peak_time_sec | 0.458999 | 0.008001 |
| settling_time_sec | 0.219001 | 0.000002 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.355837 | 0.000025 |
| coupled_peak_velocity | 0.005436 | 0.000001 |
| primary_peak_effort | 0.416288 | 0.000026 |
| coupled_peak_effort | 0.003337 | 0.000001 |

- **response_classes**: ['well_damped_tracking', 'well_damped_tracking', 'well_damped_tracking']
- **rise_time_statuses**: ['too_slow_for_walking', 'too_slow_for_walking', 'too_slow_for_walking']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
