# Forward X Failure Deploy Closure

状态：`ended`

结束日期：`2026-05-15`

本次 standalone `$deploy` 的 `forward_x_failure` 专项分析已收尾。

## 最终问题结论

经数据分析、视频分析和验证分析，问题收敛为三个因素叠加：

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

## 最终归档

最终整理后的分析方案、脚本、报告和表格位于：

- `sim2real/walk_data_analysis/`
- `sim2real/ankle_step_response/`

其中：

- `sim2real/walk_data_analysis/` 保存整体行走数据、欠阻尼数据指标统计及分析。
- `sim2real/ankle_step_response/` 保存踝关节阶跃响应试验、`Kp/Kd` 辨识方案、脚本和结果。

## 中间过程归档

OMA 过程中产生的历史方案、探索脚本、过程报告和被废弃/降级的分析分支已归档到：

- `.oma/sim2real/intermediate_process/forward_x_failure/`

后续查阅结论时优先读取 `sim2real/walk_data_analysis/` 和 `sim2real/ankle_step_response/`；只有需要追溯历史判断或复查过程脚本时，才读取本目录。
