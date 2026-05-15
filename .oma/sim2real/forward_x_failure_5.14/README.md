# forward_x_failure_5.14

类型：deploy 阶段问题归档

状态：`ended`

结束日期：`2026-05-15`

## 目录内容

| 文件 | 内容 |
|---|---|
| `SUMMARY.md` | 本问题的最终结论、解决方案和数据分析入口 |
| `sim2real_checklist.md` | 本问题的 deploy checklist、阶段状态和过程索引 |

## 最终结论

经数据分析、视频分析和验证分析，问题收敛为：

1. 踝关节机械标零后仍存在 `ankle pitch` 约 `1.3~1.8 deg` 偏差。
2. 踝关节小腿硬件支撑件发生明显弯曲。
3. 踝关节闭环为严重欠阻尼系统。

已执行解决方案：

1. 配置文件 `offset` 标零对齐。
2. 更换踝关节小腿支撑件。
3. 提升 `kd`、降低 `kp`，当前阶段 `kp/kd = 30/1.5`。

## 独立分析过程

| 分析目录 | 内容 |
|---|---|
| `sim2real/walk_data_analysis/` | 整体行走数据、欠阻尼数据指标统计及分析 |
| `sim2real/ankle_step_response/` | 踝关节阶跃响应试验、`Kp/Kd` 辨识方案、脚本和结果 |

## 中间过程

历史方案、探索脚本和过程报告保留在：

- `.oma/sim2real/intermediate_process/forward_x_failure/`
