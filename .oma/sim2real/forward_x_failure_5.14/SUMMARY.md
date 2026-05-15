# Sim2Real Current Summary

更新日期：`2026-05-15`

## 当前状态

`forward_x_failure` standalone `$deploy` 已结束。

结束标记：

- `.oma/standalone.json`: `status = ended`, `completedSubject = forward_x_failure`
- `.oma/sim2real/intermediate_process/forward_x_failure/STATUS.md`: `状态：ended`

## 最终问题结论

经数据分析、视频分析和验证分析，当前问题收敛为三个因素叠加：

1. 踝关节机械标零后，仍存在 `ankle pitch` 约 `1.3~1.8 deg` 的偏差。
2. 踝关节小腿硬件支撑件发生明显弯曲。
3. 踝关节闭环表现为严重欠阻尼系统。

## 已执行解决方案

1. 通过配置文件 `offset` 做标零对齐。
2. 更换踝关节小腿支撑件。
3. 提升踝关节 `kd`，降低 `kp`。

当前阶段踝关节参数：

```text
kp / kd = 30 / 1.5
```

## 数据分析归档

当前数据分析过程拆分为两个独立入口：

| 入口 | 内容 |
|---|---|
| `sim2real/walk_data_analysis/` | 整体行走数据、欠阻尼数据指标统计及分析 |
| `sim2real/ankle_step_response/` | 踝关节阶跃响应试验、`Kp/Kd` 辨识方案、脚本和结果 |

## OMA 中间过程

`.oma/sim2real/` 仍保留 OMA 执行过程材料。本问题的 issue archive 为：

- `.oma/sim2real/forward_x_failure_5.14/`

| 路径 | 用途 |
|---|---|
| `.oma/sim2real/forward_x_failure_5.14/` | 本次 deploy 问题的总结、checklist 和问题目录 |
| `.oma/sim2real/intermediate_process/forward_x_failure/` | `forward_x_failure` 中间方案、历史分支和过程报告 |
| `.oma/sim2real/plans/` | 原始 deploy / sim2real 方案草稿 |
| `.oma/sim2real/results/` | 原始轮次结果和阶段性记录 |

后续查阅最终结论时，优先读取 `sim2real/walk_data_analysis/` 和 `sim2real/ankle_step_response/`；只有需要追溯历史推理链时，再读取 `.oma/sim2real/intermediate_process/`。
