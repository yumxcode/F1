# Walk Data Analysis

本目录汇总 forward-x failure 的行走数据分析方案、对应报告和分析代码。

## 目录结构

```text
sim2real/walk_data_analysis/
├── plans/
│   ├── 总体指标与阻尼分析方案.md
│   ├── 前6步故障事件指标方案.md
│   └── 踝关节阻尼谐振分析方法论.md
├── reports/
│   ├── 前6步故障细粒度分析报告.md
│   ├── 踝关节阻尼分析报告.md
│   ├── 踝关节阻尼诊断报告.md
│   └── FRF残差稳定性分析报告.md
└── scripts/
    ├── forward_x_failure_first6_step_stage_analysis.py
    ├── landing_window_analysis.py
    ├── ankle_damping_analysis.py
    └── claude_stability_metrics_v2.py
```

## 文件来源

| 本目录文件 | 原始路径 | 角色 |
|---|---|---|
| `plans/总体指标与阻尼分析方案.md` | `.oma/sim2real/plans/forward_x_failure/29_integrated_metric_and_damping_plan.md` | 总体方案，定义两个子方案边界、使用流程和统一字段命名 |
| `plans/前6步故障事件指标方案.md` | `.oma/sim2real/plans/forward_x_failure/28_first6_step_metric_test_plan.md` | 前 6 步故障事件指标方案 |
| `plans/踝关节阻尼谐振分析方法论.md` | `real2sim/ankle_damping_analysis/ankle_damping_analysis_methodology.md` | 踝关节阻尼 / 谐振归因方法论 |
| `reports/前6步故障细粒度分析报告.md` | `.oma/sim2real/results/forward_x_failure/28_forward_x_failure_first6_step_detailed_report.md` | 前 6 步细粒度分析报告 |
| `reports/踝关节阻尼分析报告.md` | `real2sim/ankle_damping_analysis/ankle_damping_analysis_report.md` | 踝关节阻尼分析主报告 |
| `reports/踝关节阻尼诊断报告.md` | `real2sim/ankle_damping_analysis/ankle_damping_diagnostic_report.md` | 阻尼诊断补充报告 |
| `reports/FRF残差稳定性分析报告.md` | `real2sim/ankle_damping_analysis/claude_stability_metrics_v2_report.md` | 频域 / residual 分析补充报告 |
| `scripts/forward_x_failure_first6_step_stage_analysis.py` | `.oma/sim2real/plans/forward_x_failure/scripts/28_forward_x_failure_first6_step_stage_analysis.py` | 前 6 步事件指标分析脚本 |
| `scripts/landing_window_analysis.py` | `.oma/sim2real/plans/forward_x_failure/scripts/03a_round3_landing_window_analysis.py` | 前 6 步脚本依赖的 touchdown / FK helper |
| `scripts/ankle_damping_analysis.py` | `real2sim/ankle_damping_analysis/ankle_damping_analysis.py` | 踝关节阻尼主分析脚本 |
| `scripts/claude_stability_metrics_v2.py` | `real2sim/ankle_damping_analysis/claude_stability_metrics_v2.py` | FRF / residual 辅助分析脚本 |

## 使用顺序

1. 先读 `plans/总体指标与阻尼分析方案.md`，明确事件层和阻尼归因层的边界。
2. 用 `plans/前6步故障事件指标方案.md` 和 `scripts/forward_x_failure_first6_step_stage_analysis.py` 定位 forward-x 前 6 步异常。
3. 对 `risk/fail` 对象，再用 `plans/踝关节阻尼谐振分析方法论.md` 和 `scripts/ankle_damping_analysis.py` 做阻尼 / 谐振归因。
4. 如 FRF 或 residual 细节不足，再参考 `scripts/claude_stability_metrics_v2.py` 及其报告。

## 关键边界

- `range_gain_phase > 1` 只能说明该窗口输出幅值大于输入，不能单独确认欠阻尼。
- 欠阻尼结论必须来自可信 FRF、step/sine，或在 FRF 不可信时明确降级为“局部欠阻尼行为”。
- `sole_roll_td_deg`、`joint_lock_flag`、`step_accumulation_score` 属于故障事件证据，不直接给出阻尼比。
- `frf_coherence_swing` 和 `xcorr_coeff` 含义不同，不能混用。
