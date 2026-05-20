# Round 01d All-Joint Target-Hit And Position-Following Analysis Plan

_Date: 2026-05-18 | Issue: high_speed_walk_unstable_5.15 | Data: `test_logs/data_csv/t27_joint_20260518_1_real.csv`_

## Goal

把最新 t27 日志中的 12 个策略关节统一放到同一张表里，分析:

- `pos_des_raw` 是否频繁打到关节限位。
- 实际 `pos` 对目标的幅值实现比例是否足够。
- RMS error 是来自 target clamp、低幅值实现、均值偏置、低相关性，还是这些因素叠加。
- 哪些关节应作为下一轮参数或控制链排查重点。

## Input

- Full diagnostic log: `test_logs/data_csv/t27_joint_20260518_1_real.csv`
- Existing diagnostic table: `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t27_20260518_1_real_diagnostic/t27_joint_diagnostic_summary.csv`
- Analyzer: `.oma/sim2real/high_speed_walk_unstable_5.15/scripts/analyze_t27_joint_diagnostic.py`

## Method

对每个关节读取以下字段:

- `pos_des_raw_*`
- `pos_des_lpf_*`
- `pos_*`
- `vel_*`
- `effort_*`
- `tau_des_lpf_*`
- `is_parallel_*`

目标选择规则:

- Serial joints: 使用 `pos_des_lpf`，因为这是实际下发的位置目标。
- Parallel ankle joints: 使用 `pos_des_raw` 作为虚拟位置目标，同时参考 `tau_des_lpf` 与 `effort` 的相关性。

核心指标:

| Metric | Meaning |
|---|---|
| lower / upper hit fraction | `pos_des_raw` 打到 YAML joint limit 的比例 |
| hit total | lower + upper hit |
| pos/target range | 实际位置幅值 / 目标幅值 |
| RMS error | 目标与实际位置误差 RMS |
| error mean | 稳态偏置 |
| best corr | target-position 最佳相关性 |
| delay | 相关性最大时的估计延迟 |
| effort p95 | 执行负载强度 |
| tau-effort corr | parallel ankle 的 torque command 到 effort 相关性 |

## Classification Rules

| Condition | Label |
|---|---|
| hit total >= 30% | target clamp high |
| 10% <= hit total < 30% | target clamp medium |
| pos/target < 0.20 | low realization |
| 0.20 <= pos/target < 0.45 | partial realization |
| best corr < 0.20 | weak tracking corr |
| abs(error mean) > 0.15 rad | bias |
| effort p95 > 30 | high effort |

## Expected Output

- Result doc: `.oma/sim2real/high_speed_walk_unstable_5.15/results/round_01d_all_joint_target_hit_pos_following.md`
- Checklist update: add Round 1d as a completed analysis round.

## Decision Use

This analysis does not directly approve a new Kp/Kd change. It ranks failure modes so the next hardware test changes one axis at a time:

- If target clamp dominates: reduce target aggressiveness, adjust cycle/action policy side, or inspect command/phase/contact coupling.
- If low realization dominates without clamp: inspect actuator load, control mode, Kp/Kd, or mechanical/contact constraints.
- If weak correlation dominates: inspect timing/phase, delay, sensor sign, or command-to-joint mapping.
