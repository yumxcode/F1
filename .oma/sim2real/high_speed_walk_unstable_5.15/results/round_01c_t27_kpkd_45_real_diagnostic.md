# Round 01c t27 Kp/Kd 45 Real Diagnostic

_Analysis date: 2026-05-18 | Data: `test_logs/data_csv/t27_joint_20260518_1_real.csv` | Issue: high_speed_walk_unstable_5.15_

## Scope

本轮分析新的 t27 完整诊断日志。当前 `rl_walk_leg` 活跃参数为:

```yaml
stiffness: [45.0, 45.0, 45.0, 80.0, 30.0, 30.0,
            45.0, 45.0, 45.0, 80.0, 30.0, 30.0]
damping:   [3.0,  3.0,  4.0,  10.0, 1.5,  1.5,
            3.0,  3.0,  4.0,  10.0, 1.5,  1.5]
cycle_time: 0.55
```

分析脚本:

- `.oma/sim2real/high_speed_walk_unstable_5.15/scripts/analyze_t27_joint_diagnostic.py`

输出:

- `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t27_20260518_1_real_diagnostic/t27_joint_diagnostic_summary.md`
- `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t27_20260518_1_real_diagnostic/t27_joint_diagnostic_summary.csv`

## Data Quality

| Item | Value |
|---|---:|
| rows | `2052` |
| duration | `20.509 s` |
| sample rate | `100.002 Hz` |
| dt range | `9.442 .. 10.284 ms` |
| cmd_linear_x mean / max | `0.399 / 0.400` |
| cmd_linear_y abs max | `0.000` |
| cmd_angular_z abs max | `0.000` |

本轮是 `0.4 m/s` 前进、无横移、无 yaw 命令的真机日志。

## Base / Contact Result

| Metric | Value | Interpretation |
|---|---:|---|
| left_contact fraction | `0.136` | 左脚接触占比异常低，或接触检测强烈不稳定 |
| right_contact fraction | `0.669` | 右脚接触占比明显更高 |
| left_contact transitions | `171` | 20.5 s 内频繁跳变 |
| right_contact transitions | `202` | 20.5 s 内频繁跳变 |
| base roll x abs max | `0.094 rad` | roll/pitch 幅值未到明显翻倒级别 |
| base pitch y abs max | `0.088 rad` | 约 5 deg 量级 |
| base yaw z range | `0.736 rad` | 零 yaw 命令下出现约 42 deg yaw 漂移 |
| gyro z abs p95 | `1.288 rad/s` | yaw 动态较强 |

关键点: 这份日志里 roll/pitch 没有先爆掉，但 yaw drift 和左右接触不对称很强。当前问题不应只看单个关节 RMS。

## Joint Group Summary

| Group | RMS | Corr | Pos/target | Delay | Effort p95 | Lower hit | Upper hit |
|---|---:|---:|---:|---:|---:|---:|---:|
| hip_pitch | `0.4953` | `0.409` | `0.213` | `130 ms` | `14.505` | `0.1%` | `0.0%` |
| hip_roll | `0.3926` | `0.215` | `0.132` | `95 ms` | `36.020` | `4.8%` | `29.9%` |
| hip_yaw | `0.2866` | `0.302` | `0.323` | `45 ms` | `10.549` | `0.0%` | `0.0%` |
| knee_pitch | `0.3515` | `0.350` | `0.644` | `115 ms` | `31.136` | `1.0%` | `0.0%` |
| ankle_pitch | `0.3065` | `0.227` | `0.527` | weak | `11.404` | `15.1%` | `30.6%` |
| ankle_roll | `0.2081` | `0.425` | `0.440` | `55 ms` | `10.859` | `0.2%` | `0.7%` |

## Key Observations

### 1. Right hip_roll 比 E1 好，但仍未真正跟随

`right_hip_roll_joint`:

| Metric | Value |
|---|---:|
| RMS | `0.3894 rad` |
| error mean / std | `+0.1712 / 0.3497 rad` |
| target range | `1.6825 rad` |
| pos range | `0.2514 rad` |
| pos/target | `0.149` |
| best corr | `0.018` |
| delay estimate | `130 ms` but weak due low corr |
| lower / upper hit | `7.6% / 0.2%` |
| effort p95 | `38.364` |

相比 E1 的 `right_hip_roll` 严重正向 target 饱和，本轮右侧 target 分布已经缓和:

```text
right_hip_roll raw target:
min/p10/p50/p90/max = -0.200 / -0.151 / +0.136 / +0.740 / +1.500

right_hip_roll pos:
min/p10/p50/p90/max = -0.112 / -0.036 / +0.087 / +0.087 / +0.139
```

但它仍然不是有效跟随: target p90 已到 `+0.740`，pos p90 只有 `+0.087`，best corr 只有 `0.018`。也就是说右 hip_roll 的 target 饱和问题缓和了，但 roll 通道实际可动幅值仍很小。

### 2. 问题转移到 left hip_roll 上限 clamp

`left_hip_roll_joint` 是本轮最重要的新信号:

| Metric | Value |
|---|---:|
| RMS | `0.3958 rad` |
| target range | `1.7930 rad` |
| pos range | `0.2046 rad` |
| pos/target | `0.114` |
| best corr | `0.411` |
| lower / upper hit | `2.0% / 59.6%` |
| effort p95 | `33.675` |

分位数显示 target 长时间被 clamp 在左 hip_roll 上限 `+0.2`:

```text
left_hip_roll raw target:
min/p10/p50/p90/max = -1.500 / -0.563 / +0.200 / +0.200 / +0.200

left_hip_roll pos:
min/p10/p50/p90/max = -0.093 / +0.002 / +0.049 / +0.060 / +0.112
```

这说明策略/控制链持续要求左髋 roll 向上限侧修正，但实机位置只在 `0.05 rad` 附近小范围运动。该现象和零 yaw 命令下 yaw drift、左右 contact 不对称需要放在一起看。

### 3. Hip pitch 仍是执行链主要误差来源

最大 RMS 仍是 `right_hip_pitch_joint = 0.6408 rad`，`hip_pitch` 组平均 RMS `0.4953 rad`，pos/target 只有 `0.213`，delay 约 `130 ms`。

这继续支持 HS-01/HS-02: 高速/较快周期下髋 pitch 执行链有明显幅值和相位压力。

### 4. Ankle pitch 仍有 clamp 和 torque-realization 风险

`right_ankle_pitch_joint`:

- RMS `0.3307 rad`
- upper hit `51.7%`
- lower hit `14.3%`
- `tau_des_lpf_abs_p95 = 14.099`
- `tau_effort_corr = 0.205`

`left_ankle_pitch_joint`:

- RMS `0.2823 rad`
- lower hit `15.9%`
- upper hit `9.6%`
- `tau_des_lpf_abs_p95 = 21.268`
- `tau_effort_corr = 0.473`

由于踝是 parallel torque path，`pos_des_raw` 是虚拟位置目标，不是直接位置命令。本轮证据显示 ankle pitch 的虚拟目标经常打到限位，且右踝 torque command 与 effort 的相关性较弱。它不是唯一主因，但仍是高速接触鲁棒性的风险点。

## Updated Root-Cause Assessment

| Hypothesis | Status | Evidence |
|---|---|---|
| HS-01: 髋/膝执行链幅值/相位不足 | still strong | hip_pitch RMS `0.4953`, delay `130 ms`; right_hip_pitch RMS `0.6408` |
| HS-02: `cycle_time=0.55` 对真实响应带宽偏激进 | still strong | hip_pitch/hip_roll/knee delay `95-130 ms` 量级 |
| HS-03: lateral/roll 通道不足导致 yaw/roll 耦合 | strengthened | hip_roll pos/target `0.132`, left hip_roll upper hit `59.6%`, yaw range `0.736 rad` |
| HS-04: ankle pitch touchdown/torque path 风险 | still medium | ankle_pitch upper/lower clamp 明显，right ankle tau-effort corr `0.205` |
| HS-05: 接触检测或真实接触不对称 | new high priority | left/right contact fraction `0.136 / 0.669`, transitions `171 / 202` |

## Decision

本轮参数比 E1 更合理地降低了 `right_hip_roll` 的正向 target 饱和，但没有解决 roll 通道可执行性问题。当前不建议继续盲目增大 hip_roll Kp。

原因:

- 左 hip_roll 已经 `59.6%` 时间打到上限，继续加 Kp 可能把 lateral 接触冲击和 yaw drift 放大。
- hip_roll effort p95 已经高于 hip_pitch/hip_yaw，说明 roll 通道负载不低。
- 零 yaw 命令下 yaw 漂移 `0.736 rad`，需要优先定位 yaw/roll/contact 耦合。

## Next Test Recommendation

1. 不继续直接加 hip_roll Kp。先做 yaw/roll/contact 诊断:
   - 同样 `cmd_x=0.4`，记录视频同步点。
   - 保留 t27 full log。
   - 对 left/right contact 检测阈值或来源做校验。

2. 做单变量对照:
   - 保持当前 Kp/Kd，只把 `cycle_time` 回到 `0.7` 复测 `cmd_x=0.4`。
   - 目标是判断 yaw drift/contact asymmetry 是否由 `0.55 s` 周期触发。

3. 若必须试参数，优先降低横向/yaw激励，而不是加硬:
   - hip_yaw 从 `45/4` 回到 `35/6` 或 `40/6` 做 A/B。
   - hip_roll 暂保持 `45/3`，不要直接上 `50/4`。

4. 下一轮报告必须同时看:
   - yaw range / gyro z
   - left/right contact fraction
   - left_hip_roll upper hit fraction
   - right_hip_roll corr and pos/target
   - right_hip_pitch RMS/delay
