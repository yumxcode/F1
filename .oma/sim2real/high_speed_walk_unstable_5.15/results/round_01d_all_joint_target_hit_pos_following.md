# Round 01d All-Joint Target-Hit And Position-Following Result

_Analysis date: 2026-05-18 | Data: `test_logs/data_csv/t27_joint_20260518_1_real.csv` | Issue: high_speed_walk_unstable_5.15_

## Scope

本轮是独立分析，不新增实机测试。基于 Round 1c 的 t27 完整诊断表，专门分析所有 12 个策略关节的 target hit 和 `pos` 跟随情况。

关联方案:

- `.oma/sim2real/high_speed_walk_unstable_5.15/plans/round_01d_all_joint_target_hit_pos_following.md`

输入表:

- `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t27_20260518_1_real_diagnostic/t27_joint_diagnostic_summary.csv`

## All-Joint Summary

| Joint | Target | Lower hit | Upper hit | Hit total | Pos/target | RMS | Err mean | Corr | Delay | Effort p95 | Tau-effort | Assessment |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `left_hip_pitch_joint` | pos_des_lpf | 0.3% | 0.0% | 0.3% | 0.177 | 0.3498 | +0.1432 | 0.374 | 130.0 | 14.579 | - | low realization |
| `left_hip_roll_joint` | pos_des_lpf | 2.0% | 59.6% | 61.7% | 0.114 | 0.3958 | -0.0328 | 0.411 | 60.0 | 33.675 | - | target clamp high, low realization, high effort |
| `left_hip_yaw_joint` | pos_des_lpf | 0.0% | 0.0% | 0.0% | 0.278 | 0.2433 | +0.0507 | 0.199 | 40.0 | 10.476 | - | partial realization, weak tracking corr |
| `left_knee_pitch_joint` | pos_des_lpf | 1.4% | 0.0% | 1.4% | 0.442 | 0.3162 | -0.2229 | 0.564 | 110.0 | 29.280 | - | partial realization, bias |
| `left_ankle_pitch_joint` | pos_des_raw | 15.9% | 9.6% | 25.5% | 0.473 | 0.2823 | +0.1203 | -0.083 | 80.0 | 9.220 | 0.473 | target clamp medium, weak tracking corr |
| `left_ankle_roll_joint` | pos_des_raw | 0.0% | 1.4% | 1.4% | 0.357 | 0.1783 | +0.0110 | 0.452 | 60.0 | 10.789 | 0.842 | partial realization |
| `right_hip_pitch_joint` | pos_des_lpf | 0.0% | 0.0% | 0.0% | 0.248 | 0.6408 | +0.4060 | 0.444 | 130.0 | 14.432 | - | partial realization, bias |
| `right_hip_roll_joint` | pos_des_lpf | 7.6% | 0.2% | 7.8% | 0.149 | 0.3894 | +0.1712 | 0.018 | 130.0 | 38.364 | - | low realization, weak tracking corr, bias, high effort |
| `right_hip_yaw_joint` | pos_des_lpf | 0.0% | 0.0% | 0.0% | 0.368 | 0.3299 | -0.1443 | 0.406 | 50.0 | 10.623 | - | partial realization |
| `right_knee_pitch_joint` | pos_des_lpf | 0.7% | 0.0% | 0.7% | 0.846 | 0.3869 | +0.1408 | 0.135 | 120.0 | 32.992 | - | weak tracking corr, high effort |
| `right_ankle_pitch_joint` | pos_des_raw | 14.3% | 51.7% | 66.0% | 0.580 | 0.3307 | +0.1676 | 0.537 | -190.0 | 13.588 | 0.205 | target clamp high, bias |
| `right_ankle_roll_joint` | pos_des_raw | 0.3% | 0.0% | 0.3% | 0.524 | 0.2380 | -0.1338 | 0.398 | 50.0 | 10.930 | 0.652 | acceptable relative |

## Target-Hit Ranking

| Rank | Joint | Hit total | Dominant hit | Interpretation |
|---:|---|---:|---|---|
| 1 | `right_ankle_pitch_joint` | 66.0% | upper 51.7% | Ankle pitch virtual target is frequently saturated; likely policy/contact compensation is pushing against pitch limit. |
| 2 | `left_hip_roll_joint` | 61.7% | upper 59.6% | Left hip roll is persistently asking for upper-limit correction; strong lateral/yaw/contact-coupling signal. |
| 3 | `left_ankle_pitch_joint` | 25.5% | lower 15.9% | Medium ankle pitch saturation with weak target-position correlation. |
| 4 | `right_hip_roll_joint` | 7.8% | lower 7.6% | Hit rate is not the main issue; poor realization and weak corr dominate. |

Other joints have <= 1.4% hit and are not target-limit dominated.

## Position-Following Ranking

Worst pos/target realization:

| Rank | Joint | Pos/target | RMS | Corr | Interpretation |
|---:|---|---:|---:|---:|---|
| 1 | `left_hip_roll_joint` | 0.114 | 0.3958 | 0.411 | Target is heavily clamped and actual position only realizes a small range. |
| 2 | `right_hip_roll_joint` | 0.149 | 0.3894 | 0.018 | Target not followed in phase or shape; high effort suggests load/control limitation. |
| 3 | `left_hip_pitch_joint` | 0.177 | 0.3498 | 0.374 | Low pitch realization without target hit. |
| 4 | `right_hip_pitch_joint` | 0.248 | 0.6408 | 0.444 | Largest RMS; strong positive bias even without target hit. |
| 5 | `left_hip_yaw_joint` | 0.278 | 0.2433 | 0.199 | Partial realization with weak correlation. |

Best relative realization:

- `right_knee_pitch_joint`: pos/target `0.846`, but corr `0.135` and effort p95 `32.992`; range is large but timing/shape is poor.
- `right_ankle_pitch_joint`: pos/target `0.580`, but target hit `66.0%`; range alone is not a pass.
- `right_ankle_roll_joint`: pos/target `0.524`, low hit `0.3%`, corr `0.398`; this is the cleanest relative ankle channel in this log.

## RMS Ranking

| Rank | Joint | RMS | Hit total | Pos/target | Primary failure mode |
|---:|---|---:|---:|---:|---|
| 1 | `right_hip_pitch_joint` | 0.6408 | 0.0% | 0.248 | Bias + low realization, not target hit |
| 2 | `left_hip_roll_joint` | 0.3958 | 61.7% | 0.114 | Target clamp + low realization |
| 3 | `right_hip_roll_joint` | 0.3894 | 7.8% | 0.149 | Low realization + weak corr + high effort |
| 4 | `right_knee_pitch_joint` | 0.3869 | 0.7% | 0.846 | Weak corr + high effort |
| 5 | `left_hip_pitch_joint` | 0.3498 | 0.3% | 0.177 | Low realization |
| 6 | `right_ankle_pitch_joint` | 0.3307 | 66.0% | 0.580 | Target clamp + bias |

## Interpretation

### 1. Target hit is concentrated, not global

The high target-hit joints are `right_ankle_pitch_joint`, `left_hip_roll_joint`, and `left_ankle_pitch_joint`. Most hip pitch/yaw/knee joints do not hit limits often. Therefore the target-hit problem is not a blanket action-scale saturation issue across all joints; it is concentrated in lateral/roll correction and ankle pitch virtual targets.

### 2. Hip roll remains the clearest roll-channel bottleneck

Both hip roll joints have very low pos/target:

- `left_hip_roll_joint`: `0.114`
- `right_hip_roll_joint`: `0.149`

But their failure modes differ:

- Left hip roll: target is clamped at the upper limit for `59.6%` of the log.
- Right hip roll: target hit is only `7.8%`, but corr is `0.018` and effort p95 is `38.364`.

This supports a roll/yaw/contact-coupling diagnosis more than a simple symmetric Kp-too-low diagnosis.

### 3. Right hip pitch is the largest non-hit execution gap

`right_hip_pitch_joint` has the largest RMS (`0.6408`) with zero target hit. This means its error is not caused by command clipping. The dominant problem is bias and low realization under load or phase timing.

### 4. Ankle pitch target saturation is real, but it should not be read as direct position-control failure

Ankle pitch is on the parallel torque path. Its `pos_des_raw` is a virtual target used to compute torque. Frequent hit means the virtual PD target is being pushed to the limit, not that the controller is directly commanding position saturation.

Important asymmetry:

- `right_ankle_pitch_joint`: hit `66.0%`, tau-effort corr `0.205`
- `left_ankle_pitch_joint`: hit `25.5%`, tau-effort corr `0.473`

Right ankle pitch torque realization is weaker and should be monitored in touchdown windows.

## Decision

This experiment confirms three separate failure classes:

1. **Clamp dominated**: `left_hip_roll_joint`, `right_ankle_pitch_joint`, `left_ankle_pitch_joint`.
2. **Low realization without clamp**: `right_hip_roll_joint`, `left_hip_pitch_joint`, `right_hip_pitch_joint`.
3. **Weak timing/shape correlation**: `right_hip_roll_joint`, `right_knee_pitch_joint`, `left_hip_yaw_joint`, `left_ankle_pitch_joint`.

Do not treat this as “increase all Kp”. The data argues for separating target generation, contact/yaw coupling, and actuator realization.

## Next Action

For the next hardware run, keep this all-joint table as the pass/fail dashboard:

- `left_hip_roll upper hit` should drop from `59.6%`.
- `right_ankle_pitch hit total` should drop from `66.0%`.
- `right_hip_roll corr` should rise meaningfully above `0.2`.
- `right_hip_pitch RMS` should fall from `0.6408`.
- `right_knee_pitch corr` should rise above `0.2` without increasing effort p95.

Recommended next A/B remains: keep Kp/Kd fixed and change only `cycle_time=0.55 -> 0.7` at `cmd_x=0.4`, because this can test whether target clamp and weak following are consequences of phase-period aggressiveness rather than raw stiffness.
