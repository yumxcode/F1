# Sim2Real Issue Index

本目录按 sim2real deploy 阶段的问题进行归档。每个独立问题使用一个子目录，目录内保存该问题的状态、总结、checklist 和 OMA 过程索引。

## 当前问题目录

| 问题目录 | 状态 | 内容 |
|---|---|---|
| `forward_x_failure_5.14/` | `ended` | 5.14 forward-x failure deploy 问题总结、checklist、最终结论和数据分析入口 |

## 组织规则

- `.oma/sim2real/<issue_id>/SUMMARY.md`：该问题的最终总结。
- `.oma/sim2real/<issue_id>/sim2real_checklist.md`：该问题的 deploy checklist 和过程索引。
- `.oma/sim2real/<issue_id>/README.md`：该问题目录说明。
- `sim2real/<analysis_name>/`：独立的数据分析过程、方案、脚本和结果，不和某个问题目录强绑定。

当前独立分析过程：

| 分析目录 | 内容 |
|---|---|
| `sim2real/walk_data_analysis/` | 整体行走数据、欠阻尼数据指标统计及分析 |
| `sim2real/ankle_step_response/` | 踝关节阶跃响应试验、`Kp/Kd` 辨识方案、脚本和结果 |

下次出现新的 sim2real 问题时，在 `.oma/sim2real/` 下新建新的问题目录，不复用 `forward_x_failure_5.14/`。
