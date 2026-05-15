# Forward X Failure Intermediate Archive

状态：`ended`

结束日期：`2026-05-15`

本目录保存 `forward_x_failure` 单独 `$deploy` 分析过程中的中间方案、脚本、模板和阶段性结果。

最终整理结果已迁移到：

- `sim2real/walk_data_analysis/`
- `sim2real/ankle_step_response/`

最终问题结论：

1. 踝关节机械标零后仍存在 `ankle pitch` 约 `1.3~1.8 deg` 偏差。
2. 踝关节小腿硬件支撑件发生明显弯曲。
3. 踝关节闭环为严重欠阻尼系统。

已执行解决方案：

1. 配置文件 `offset` 标零对齐。
2. 更换踝关节小腿支撑件。
3. 提升 `kd`、降低 `kp`，当前阶段 `kp/kd = 30/1.5`。

## 目录说明

| 路径 | 含义 |
|---|---|
| `plans/` | OMA 过程中形成的中间方案、历史分支方案、脚本和模板 |
| `results/` | OMA 过程中形成的阶段性分析结果和过程报告 |

## 使用边界

- 本目录不是最终交付入口。
- 若最终报告与本目录中间文件存在冲突，以 `sim2real/walk_data_analysis/` 为准。
- 本目录保留历史推理链，便于追溯哪些方向被保留、降级或废弃。
