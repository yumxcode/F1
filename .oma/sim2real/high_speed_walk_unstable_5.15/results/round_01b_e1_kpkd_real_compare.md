# Round 01b E1 Kp/Kd Real Compare

_Analysis date: 2026-05-18 | Test data date: 2026-05-15 | Issue: high_speed_walk_unstable_5.15_

## Scope

本轮分析用户提供的 E1 参数实机日志:

```yaml
stiffness: [60.0, 40.0, 45.0, 80.0, 20.0, 30.0,
            60.0, 40.0, 45.0, 80.0, 20.0, 30.0]
damping:   [6.0,  3.0,  7.0,  10.0, 1.5,  1.5,
            6.0,  3.0,  7.0,  10.0, 1.5,  1.5]
```

对比对象:

- baseline real: `test_logs/data_csv/t23_joint_20260515_1_real.csv`
- E1 real: `test_logs/data_csv/t23_joint_20260515_2_real.csv`

输出表:

- E1 单文件统计: `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t23_20260515_2_real_tracking/t23_joint_tracking_summary.md`
- baseline-vs-E1 对比: `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t23_20260515_1_vs_2_real_compare/t23_sim_real_joint_tracking_compare.md`

## Method

- 沿用 `scripts/analyze_t23_joint_tracking.py` 的 raw `target_*` vs `pos_*` 口径。
- 由于 t23 不含 `cmd`、IMU、接触、tau 和跌倒事件，本报告只评价关节执行链跟踪变化，不能单独证明整机稳定性根因。
- 两个日志均为 4000 行、39.989 s、100.003 Hz，可做同类统计对比。
- 仍需检查 target range；若目标幅值变化较大，RMS 变化不能直接解释为纯 Kp/Kd 效果。

## Aggregate Result

| Metric | Baseline real | E1 real | Change |
|---|---:|---:|---:|
| mean RMS error across 12 joints | `0.4205 rad` | `0.4799 rad` | `+14.1%` |
| mean best-delay correlation | `0.231` | `0.138` | `-40.3%` |

整体上，E1 没有形成干净改善。虽然 hip_pitch RMS 下降，但全关节平均 RMS 上升，target-position correlation 进一步下降。

## Joint Group Summary

| Group | Baseline RMS | E1 RMS | Change | Target ratio | Pos/target baseline -> E1 | Corr baseline -> E1 |
|---|---:|---:|---:|---:|---:|---:|
| hip_pitch | `0.6695` | `0.6132` | `-8.4%` | `0.92x` | `0.270 -> 0.289` | `0.178 -> 0.119` |
| hip_roll | `0.4848` | `0.7279` | `+50.2%` | `1.00x` | `0.154 -> 0.249` | `0.225 -> -0.067` |
| hip_yaw | `0.3607` | `0.3717` | `+3.1%` | `1.01x` | `0.243 -> 0.383` | `0.370 -> 0.232` |
| knee_pitch | `0.4959` | `0.5042` | `+1.7%` | `1.17x` | `0.868 -> 0.649` | `0.241 -> 0.101` |
| ankle_pitch | `0.2373` | `0.3570` | `+50.5%` | `1.00x` | `0.987 -> 0.807` | `0.018 -> 0.004` |
| ankle_roll | `0.2747` | `0.3052` | `+11.1%` | `1.04x` | `0.502 -> 0.587` | `0.356 -> 0.441` |

## Key Per-Joint Changes

| Joint | Baseline RMS | E1 RMS | Change | Target ratio | Interpretation |
|---|---:|---:|---:|---:|---|
| `left_hip_pitch_joint` | `0.7169` | `0.6397` | `-0.0772` | `1.06x` | 正向信号；目标幅值略增但 RMS 下降 |
| `right_hip_pitch_joint` | `0.6222` | `0.5867` | `-0.0355` | `0.79x` | 改善较弱，且目标幅值下降，不能强判 |
| `right_knee_pitch_joint` | `0.5910` | `0.5434` | `-0.0476` | `0.87x` | 表面改善，但目标幅值下降 |
| `right_hip_roll_joint` | `0.3974` | `0.8732` | `+0.4758` | `1.00x` | 明确恶化；同目标幅值下 RMS 变为 `2.20x` |
| `left_ankle_pitch_joint` | `0.1642` | `0.4113` | `+0.2472` | `1.00x` | 明确恶化；同目标幅值下 RMS 变为 `2.51x` |
| `left_knee_pitch_joint` | `0.4007` | `0.4651` | `+0.0644` | `1.61x` | 混杂较大，目标幅值显著增大 |

## Interpretation

### 1. E1 对 hip_pitch 有一定帮助，但不足以作为通过条件

hip_pitch 平均 RMS 从 `0.6695` 降到 `0.6132`，pos/target 从 `0.270` 小幅升到 `0.289`。这符合提高 hip_pitch `50/5 -> 60/6` 后响应略有改善的预期。

但 correlation 从 `0.178` 继续降到 `0.119`，说明它并没有恢复成稳定的延迟跟随系统。高速相位问题仍在。

### 2. E1 引入了新的 lateral/roll 风险

hip_roll 的 target range 完全相同，RMS 却从 `0.4848` 升到 `0.7279`，其中 `right_hip_roll_joint` 从 `0.3974` 升到 `0.8732`。这是本轮最强的负面证据。

由于本轮没有提高 hip_roll Kp/Kd，hip_roll 变差更可能来自全身耦合: hip_pitch/yaw 更硬后，接触/摆动相位或躯干横向动态被改变，roll 通道跟不上。

### 3. ankle_pitch 也出现同目标幅值下恶化

ankle_pitch target range 保持 `0.7600 rad`，但 RMS 从 `0.2373` 升到 `0.3570`。尤其 `left_ankle_pitch_joint` 从 `0.1642` 升到 `0.4113`。

这不支持继续只沿 hip_pitch/yaw 加硬。高速落脚或支撑切换可能把更多误差传递到踝部并放大 touchdown 影响。

### 4. hip_yaw 没有兑现预期收益

hip_yaw Kp/Kd 提高后，平均 RMS 基本持平略差 (`+3.1%`)，target range 基本相同 (`1.01x`)，但 correlation 从 `0.370` 降到 `0.232`。如果视频或 IMU 同步显示 yaw/roll 摆动，hip_yaw `45/7` 可能偏激进。

## Decision

E1 判定为 **fail / hold**，不建议继续在该方向上直接增加 Kp。

具体原因:

- 全关节 mean RMS `+14.1%`，mean correlation `-40.3%`。
- 同 target range 下 `right_hip_roll_joint` 明确恶化到 `2.20x` RMS。
- 同 target range 下 `left_ankle_pitch_joint` 明确恶化到 `2.51x` RMS。
- hip_pitch 只获得小幅 RMS 改善，未恢复 target-position correlation。

## Next Test Recommendation

优先执行回退/半步验证，而不是继续加硬:

1. 回到 baseline 或执行 E3 半步:

```yaml
stiffness: [55.0, 40.0, 40.0, 80.0, 20.0, 30.0,
            55.0, 40.0, 40.0, 80.0, 20.0, 30.0]
damping:   [6.0,  3.0,  7.0,  10.0, 1.5,  1.5,
            6.0,  3.0,  7.0,  10.0, 1.5,  1.5]
```

2. 若继续定位 hip_pitch，请只改 hip_pitch，先不要同时提高 hip_yaw:

```yaml
stiffness: [60.0, 40.0, 35.0, 80.0, 20.0, 30.0,
            60.0, 40.0, 35.0, 80.0, 20.0, 30.0]
damping:   [6.0,  3.0,  6.0,  10.0, 1.5,  1.5,
            6.0,  3.0,  6.0,  10.0, 1.5,  1.5]
```

3. 下一轮必须补充 IMU roll/pitch、gyro、tau/effort、cmd 和接触/视频同步点。当前 t23 证据已经足够说明 E1 不是稳定推进方向，但还不足以区分 roll 发散、touchdown 冲击和 yaw-roll 耦合的先后因果。
