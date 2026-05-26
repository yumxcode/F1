# Round 2: cycle_time 0.7 vs 0.55 单变量对照

_Date: 2026-05-26 | Issue: high_speed_walk_unstable_5.15 | Phase: parameter_identification → fix_validation_

## Goal

在 Kp/Kd 不变的前提下，只改变 `cycle_time`，回答：

> 当前 `cycle_time=0.55` 下的 yaw drift、contact asymmetry、left_hip_roll clamp、right_hip_roll 低 corr 是否由过短步态周期触发？

如果回到 `cycle_time=0.7` 可以显著改善多项指标，则 HS-02（`cycle_time=0.55` 对真实响应带宽偏激进）得到确认，后续方向是**调整步态周期而非加硬**。如果 `cycle_time=0.7` 下问题同样严重，则需聚焦 yaw/roll/contact 耦合的独立诊断。

## Fixed Baseline

| Item | Value |
|---|---|
| Policy | `src/module/control_module/policy/rl_walk_leg.onnx` |
| `action_scale` | `0.5` |
| `decimation` | `10` |
| stiffness (leg joints) | `[45, 45, 45, 80, 30, 30] ×2` |
| damping (leg joints) | `[3, 3, 4, 10, 1.5, 1.5] ×2` |
| `cmd_x` | `0.4 m/s`（匀速直行，零 yaw/零 lateral） |
| 踝 Kp/Kd | `30 / 1.5`（parallel torque path） |

**本轮完全不动 Kp/Kd 和 action_scale**。唯一变量是 `cycle_time`。

## Experiment Design

### Case A: cycle_time=0.7（baseline 回归）

```yaml
walk_step_conf:
  cycle_time: 0.7
```

目的：验证 Round 1c 中观察到的 yaw drift/contact asymmetry/target clamp 是否消失或大幅缓解。

### Case B: cycle_time=0.55（当前配置复测）

```yaml
walk_step_conf:
  cycle_time: 0.55
```

目的：在同日、同地面、同电量、同操作下确认 Round 1c 的结果可复现。这为 A/B 对比提供匹配基准。

### Case C（可选扩展）: cycle_time=0.50

仅在 Case A 明确改善但 Case B 仍复现问题时执行。用于判断"改善来自 0.7 本身"还是"来自逃离 0.55 的特定临界点"。

## Test Protocol

每组参数严格相同流程：

1. **原地 RL idle** 5-10 s：确认无髋部抖动、异常电流、左右 contact 不频繁跳变。
2. **低速短走** 3-5 s：`cmd_x=0.2`，确认左右对称、无明显 foot slap。
3. **目标速度** `cmd_x=0.4`：使用同一 command ramp（不做手动阶跃），持续 ≥ 15 s。
4. 每组间让机器人回到 stand 或 idle 至少 5 s，避免 phase 连续。
5. 若出现 roll 快速增大（>0.15 rad）、髋部振荡、脚尖拖地、过热、电流异常 → 立即停止。

## Required Logging

必须采集 t27 完整诊断日志，至少包含：

| Field | Required | Purpose |
|---|---|---|
| timestamp | ✅ | 对齐分析 |
| `cmd_linear_x`, `cmd_linear_y`, `cmd_angular_z` | ✅ | 确认命令一致 |
| `phase_sin`, `phase_cos` | ✅ | cycle_time 对比核心字段 |
| `pos_des_raw_*` (12 joints) | ✅ | target clamp 判断 |
| `pos_des_lpf_*` (12 joints) | ✅ | serial joint 跟踪判断 |
| `pos_*` (12 joints) | ✅ | 实际位置 |
| `vel_*` (12 joints) | ✅ | 速度/振荡判断 |
| `effort_*` (12 joints) | ✅ | 负载/冲击 |
| `is_parallel_*` (4 ankle) | ✅ | 控制路径标识 |
| IMU: `base_roll`, `base_pitch`, `base_yaw` 或 quat | ✅ | yaw drift 量化 |
| IMU: `gyro_x`, `gyro_y`, `gyro_z` | ✅ | 角速度动态 |
| contact: `left_contact`, `right_contact` | ✅ | 接触对称性 |
| 视频时间点 | 推荐 | 失稳时间对齐 |

每 Case 至少 20 s 有效数据（约 2000 行 @100 Hz）。

## Pass/Fail Dashboard

以下是从 Round 1c/1d 提取的关键指标，作为本轮对比 dashboard：

| Metric | Round 1c (0.55) 参考值 | Case A pass 条件 | Case B 期望 |
|---|---|---|---|
| yaw range | 0.736 rad | ≤ 0.40 rad | ≈ 0.7 rad（复现） |
| gyro z p95 | 1.288 rad/s | ≤ 0.80 rad/s | ≈ 1.3 rad/s |
| left/right contact fraction | 0.136 / 0.669 | 两者 > 0.30 且差距 < 0.25 | ≈ 0.14/0.67 |
| left_hip_roll upper hit | 59.6% | ≤ 25% | ≈ 60% |
| right_hip_roll corr | 0.018 | ≥ 0.20 | ≈ 0.02 |
| right_hip_pitch RMS | 0.641 rad | ≤ 0.45 rad | ≈ 0.64 rad |
| right_knee corr | 0.135 | ≥ 0.25 | ≈ 0.14 |
| hip_pitch mean delay | 130 ms | ≤ 110 ms | ≈ 130 ms |

**A passes**：至少 6/8 指标满足 pass 条件。

**A ambiguous**：3-5 指标改善但未全达标。

**A fails**：≤ 2 指标改善（说明 cycle_time 不是主导因子，需要深入 yaw/roll/contact 耦合诊断）。

## Decision Tree

```
Case A passes (cycle_time=0.7 显著改善)
  → HS-02 确认：0.55 s 对当前硬件带宽偏激进
  → 下一轮：在 cycle_time=0.7 下找 stable speed ceiling
  → 若 ceiling 明显低于目标速度，再单独调 action_scale 或 obs_scales

Case A ambiguous
  → 继续执行 Case C (cycle_time=0.50)
  → 判断是 0.55 特定问题还是随周期单调恶化

Case A fails (cycle_time 不是主因)
  → 进入 yaw/roll/contact 独立诊断
  → Step 1: 零 yaw 命令下用 IMU-only 日志检查 gyro z 积分 vs base yaw
  → Step 2: 检查 left/right_contact 检测阈值或硬件传感器
  → Step 3: 检查 hip_roll joint limit 不对称（left upper=0.2 远小于 right upper=1.5）是否为 target clamp 根源
```

## Safety

| Stop Condition | Action |
|---|---|
| roll > 0.15 rad 且继续增大 | 立即 e-stop 或扶住 |
| 持续 foot slap / 脚尖拖地 | 停止该 Case，切换到下一 Case |
| 电机过热或异常电流 | 停止全部实验 |
| 异响 | 停止，记录来源 |

## Data Output

每 Case 完成后生成：
- `t27_joint_{date}_{case}.csv`
- 分析报告到 `results/round_02_cycle_time_ab.md`
- 更新 dashboard 对比表
