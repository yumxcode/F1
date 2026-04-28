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
- **actual_span**: 0.064371

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
| actual_step | -0.003537 | -0.002135 | 0.000464 |
| tracking_ratio | -0.235832 | -0.142359 | 0.030956 |
| peak_tracking_ratio | -0.064068 | 0.237795 | 0.408883 |
| tail_tracking_ratio | -0.072778 | 0.192672 | 0.362445 |
| final_tracking_ratio | -0.857533 | -0.092994 | 0.168890 |
| peak_overshoot | 0.000000 | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 | 0.000000 |
| steady_error | -0.037703 | -0.049230 | -0.055118 |
| rise_time_sec | N/A | N/A | N/A |
| rise_time_status | not_available | not_available | not_available |
| peak_time_sec | 0.999000 | 0.999001 | 0.999000 |
| peak_time_status | unusable_for_walking | unusable_for_walking | unusable_for_walking |
| settling_time_sec | N/A | N/A | N/A |
| zero_crossing_count | 0 | 0 | 0 |
| response_class | undershoot_soft | undershoot_soft | undershoot_soft |

## Aggregate (mean ± std)

| Field | Mean | Std |
|---|---|---|
| command_step | 0.015000 | 0.000000 |
| actual_step | -0.001736 | 0.002031 |
| tracking_ratio | -0.115745 | 0.135371 |
| peak_tracking_ratio | 0.194203 | 0.239470 |
| tail_actual_step | 0.002412 | 0.003290 |
| tail_tracking_ratio | 0.160780 | 0.219357 |
| post_actual_step | -0.003908 | 0.008000 |
| final_tracking_ratio | -0.260546 | 0.533330 |
| coupled_motion | -0.000159 | 0.000069 |
| peak_overshoot | 0.000000 | 0.000000 |
| overshoot_ratio | 0.000000 | 0.000000 |
| steady_error | -0.047350 | 0.008858 |
| peak_time_sec | 0.999000 | 0.000001 |
| zero_crossing_count | 0.000000 | 0.000000 |
| primary_peak_velocity | 0.013553 | 0.000663 |
| coupled_peak_velocity | 0.000428 | 0.000220 |
| primary_peak_effort | 2.228601 | 0.523757 |
| coupled_peak_effort | 0.043541 | 0.028926 |

- **response_classes**: ['undershoot_soft', 'undershoot_soft', 'undershoot_soft']
- **rise_time_statuses**: ['not_available', 'not_available', 'not_available']
- **peak_time_statuses**: ['unusable_for_walking', 'unusable_for_walking', 'unusable_for_walking']
