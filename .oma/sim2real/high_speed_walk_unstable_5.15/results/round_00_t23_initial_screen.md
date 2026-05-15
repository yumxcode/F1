# Round 00 t23 Initial Screen

_Date: 2026-05-15 | Data: `test_logs/data_csv/t23_joint_20260515_104435.csv`_

## Scope

本轮不是实机新测试，而是对已有 `t23_joint` 数据做进入 `$deploy` 后的初筛。

脚本:

- `.oma/sim2real/high_speed_walk_unstable_5.15/scripts/analyze_t23_joint_tracking.py`

输出:

- `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t23_joint_tracking_summary.md`
- `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t23_joint_tracking_summary.csv`

## 数据质量

| 项目 | 值 |
|---|---:|
| rows | `4000` |
| duration | `39.989 s` |
| sample rate | `100.003 Hz` |
| dt range | `8.700 .. 11.251 ms` |

## 关键观察

| Joint | RMS err rad | Target range | Pos range | Pos/target | Delay ms |
|---|---:|---:|---:|---:|---:|
| `left_hip_pitch_joint` | `0.7169` | `2.6217` | `0.5356` | `0.204` | `140.0` |
| `right_hip_pitch_joint` | `0.6222` | `2.8653` | `0.9620` | `0.336` | `140.0` |
| `right_knee_pitch_joint` | `0.5910` | `1.6722` | `1.4113` | `0.844` | `150.0` |
| `left_hip_roll_joint` | `0.5722` | `1.7000` | `0.2431` | `0.143` | `100.0` |
| `right_hip_roll_joint` | `0.3974` | `1.7000` | `0.2794` | `0.164` | `80.0` |

## 初步结论

- 最大执行误差在髋 pitch、髋 roll 和右膝，不是踝关节。
- 如果这份数据对应高速行走不稳现场，则 Round 1 要优先定位髋/膝执行延迟、roll 稳定通道和 `cycle_time` 相位裕度。
- 由于缺少 cmd、IMU、接触、odometry 和跌倒事件时间点，本轮不能给出根因闭环。

## 后续动作

进入 Round 1: `high_speed_boundary_and_logging`。
