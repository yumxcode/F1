# Round 00b t23 Sim-vs-Real Joint Tracking Compare

_Date: 2026-05-15 | Issue: high_speed_walk_unstable_5.15 | Mode: standalone `$deploy`_

## Scope

本轮基于 `.oma/sim2real/high_speed_walk_unstable_5.15/scripts/analyze_t23_joint_tracking.py`，对同一类 `t23_joint` 日志做 sim/real 对比。

输入:

- sim: `test_logs/data_csv/t23_joint_20260515_1_sim.csv`
- real: `test_logs/data_csv/t23_joint_20260515_1_real.csv`

输出:

- sim 单文件表: `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t23_20260515_1_sim_tracking/t23_joint_tracking_summary.md`
- real 单文件表: `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t23_20260515_1_real_tracking/t23_joint_tracking_summary.md`
- sim-vs-real 对比表: `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t23_20260515_1_sim_real_compare/t23_sim_real_joint_tracking_compare.md`
- sim-vs-real CSV: `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t23_20260515_1_sim_real_compare/t23_sim_real_joint_tracking_compare.csv`

## Method

- 沿用脚本的 raw `target_*` vs `pos_*` 跟踪误差口径。
- 对所有关节统一使用 raw target；parallel ankle joint 的 `target_lpf_*` 不作为位置跟踪目标。
- 延迟估计使用 target-position cross-correlation，在约 `+-250 ms` 范围内搜索最佳 lag。
- 当 correlation 很低时，delay 数字只作为弱证据；优先看 RMS、目标幅值、pos/target range ratio 和 correlation drop。

## Data Quality

| Dataset | Rows | Duration | Sample rate | dt range |
|---|---:|---:|---:|---:|
| sim | `4000` | `39.987 s` | `100.006 Hz` | `7.382 .. 12.626 ms` |
| real | `4000` | `39.989 s` | `100.003 Hz` | `8.700 .. 11.251 ms` |

两份日志长度和采样率可比，可以做 per-log 统计对比。但两份日志的 target trajectory 不完全一致，因此不能把所有 RMS 差异直接解释为纯 actuator degradation。

## Aggregate Result

| Metric | Sim | Real | Real / Sim |
|---|---:|---:|---:|
| mean RMS error across 12 joints | `0.2945 rad` | `0.4205 rad` | `1.43x` |
| mean best-delay correlation | `0.757` | `0.231` | `0.31x` |

核心信号不是单纯 RMS 变大，而是 real 中 target-position 的相关性整体塌陷。sim 中多数关节仍像一个延迟系统；real 中多个髋/膝关节已不像稳定跟随。

## Joint-Group Summary

| Group | Sim RMS | Real RMS | Real/Sim RMS | Real/Sim target range | Corr sim -> real | Pos/target sim -> real |
|---|---:|---:|---:|---:|---:|---:|
| hip_pitch | `0.2566` | `0.6695` | `2.61x` | `2.47x` | `0.878 -> 0.178` | `0.320 -> 0.270` |
| knee_pitch | `0.2454` | `0.4959` | `2.02x` | `1.34x` | `0.932 -> 0.241` | `0.393 -> 0.868` |
| hip_yaw | `0.1961` | `0.3607` | `1.84x` | `2.37x` | `0.551 -> 0.370` | `0.459 -> 0.243` |
| hip_roll | `0.5279` | `0.4848` | `0.92x` | `1.02x` | `0.832 -> 0.225` | `0.130 -> 0.154` |
| ankle_roll | `0.2240` | `0.2747` | `1.23x` | `1.42x` | `0.858 -> 0.356` | `0.423 -> 0.502` |
| ankle_pitch | `0.3173` | `0.2373` | `0.75x` | `1.00x` | `0.489 -> 0.018` | `0.377 -> 0.987` |

## Primary Per-Joint Gaps

| Joint | Sim RMS | Real RMS | Delta | Real/Sim RMS | Real/Sim target range | Sim corr | Real corr |
|---|---:|---:|---:|---:|---:|---:|---:|
| left_hip_pitch_joint | `0.2716` | `0.7169` | `+0.4454` | `2.64x` | `2.41x` | `0.946` | `0.336` |
| right_hip_pitch_joint | `0.2416` | `0.6222` | `+0.3806` | `2.58x` | `2.52x` | `0.811` | `0.019` |
| right_knee_pitch_joint | `0.2589` | `0.5910` | `+0.3321` | `2.28x` | `1.64x` | `0.920` | `0.146` |
| left_hip_yaw_joint | `0.1884` | `0.4161` | `+0.2277` | `2.21x` | `2.64x` | `0.661` | `0.472` |
| left_knee_pitch_joint | `0.2319` | `0.4007` | `+0.1688` | `1.73x` | `1.04x` | `0.944` | `0.336` |
| right_hip_yaw_joint | `0.2038` | `0.3054` | `+0.1016` | `1.50x` | `2.10x` | `0.442` | `0.268` |

## Interpretation

### 1. Real 的高速问题优先指向髋 pitch、膝和髋 yaw 执行链

real 相比 sim 最大的 RMS gap 集中在 `hip_pitch`、`knee_pitch`、`hip_yaw`。其中 `left_knee_pitch_joint` 的 target range 与 sim 基本接近 (`1.04x`)，但 RMS 仍从 `0.2319 rad` 增到 `0.4007 rad`，correlation 从 `0.944` 降到 `0.336`。这条证据较少受 target 不等价影响，说明 real 执行链本身存在跟随质量下降。

### 2. target 不等价是必须控制的混杂因素

real 的 `hip_pitch` target range 是 sim 的约 `2.47x`，`hip_yaw` 是约 `2.37x`。这说明当前 sim/real 数据不是严格同一输入工况，不能直接用本轮数据判定“真实电机比仿真差 2.6x”。更准确的结论是：real 日志处在更激进的髋部目标驱动下，而该驱动下 target-position correlation 明显失真。

### 3. Hip roll 通道在 sim 和 real 中都异常弱

`hip_roll` 的 RMS 在 sim/real 都很高，pos/target range ratio 都只有约 `0.13~0.15`。这不是单纯 real-only sim2real gap，而是策略目标、关节限幅、控制映射或 roll 通道模型本身就存在低响应问题。高速不稳如果伴随机身 roll 增长，hip roll 应作为独立诊断线处理。

### 4. 踝关节不是本轮最强主因

ankle pitch 的 real 平均 RMS 低于 sim (`0.75x`)，ankle roll 只小幅升高 (`1.23x`)。右踝 pitch 的 correlation 为负需要留意，但由于 ankle 是 parallel torque path，且本报告不使用 `target_lpf_*` 做位置跟踪，不能把该项直接解释成踝位置闭环失败。当前证据不足以支持“高速不稳主要由踝关节造成”。

### 5. 100-150 ms 级别延迟仍然威胁高速步态相位裕度

real 中 `left_hip_pitch`、`right_hip_pitch`、`left_knee_pitch`、`right_knee_pitch` 的 delay 估计集中在 `140-150 ms`。虽然部分 correlation 低导致 delay 可信度下降，但如果高速配置切到 `cycle_time=0.55 s` 或 `0.45 s`，`140-150 ms` 已经占单周期约 `25-33%`，足以破坏摆动落脚和支撑切换时序。

## Current Root-Cause Assessment

| Hypothesis | Status | Evidence |
|---|---|---|
| HS-01: 高速不稳主因是髋/膝执行链相位滞后和幅值跟踪不足 | strengthened | hip_pitch/knee RMS gap 最大，real correlation 大幅下降 |
| HS-02: `cycle_time` 与真实响应带宽不匹配 | strengthened | real 髋/膝 delay 约 `140-150 ms`，对 `0.55/0.45 s` 高速周期相位裕度不利 |
| HS-03: lateral/roll 通道不足导致高速 roll 稳定失败 | still high priority | hip_roll 在 sim/real 都只有约 `0.13-0.15` pos/target，但 t23 缺 IMU roll，不能闭环 |
| HS-04: 踝关节高速接触耦合是主因 | weakened as primary | ankle RMS 不是最大 gap；仍需 touchdown 窗口和 torque/IMU 证据确认 |

## Actionable Next Steps

1. 做 matched-condition 复采：同一 `cmd_vel`、同一 `cycle_time`、同一 `action_scale` 下各采 sim/real t23，避免 target range 不等价。
2. 在 `cycle_time=0.7/0.55/0.45` 三个条件下只改一个变量，记录 hip_pitch/knee delay、RMS、correlation 和稳定边界。
3. 追加 t27 或完整日志：`cmd`、`phase`、`action`、`pos_des_raw`、`pos`、`tau/effort`、IMU roll/pitch/gyro、contact/touchdown 或视频同步点。
4. 针对 hip_roll 单独检查 joint limit、action-to-command mapping、符号和目标限幅，因为该通道在 sim 中也明显低响应。
5. 在没有 touchdown torque/IMU 证据前，不优先调踝 `kp/kd`；先定位髋/膝执行链和步态周期。

## Decision

当前不建议直接进入高速参数反复试跑。下一轮应转为 matched-condition 的 sim/real 对照与 `cycle_time` 单变量边界测试，目标是判断高速目标是否超过真实髋/膝执行带宽，以及 hip_roll 低响应是否与机身 roll 失稳同步。
