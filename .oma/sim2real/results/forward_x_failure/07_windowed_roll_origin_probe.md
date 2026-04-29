# 07 Windowed Roll Origin Probe

## 数据源

- [t25_action_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t25_action_20260326_102002.csv:1)
- [t23_joint_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t23_joint_20260326_102002.csv:1)
- [t3_current_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t3_current_20260326_102002.csv:1)
- [t22_gait_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t22_gait_20260326_102002.csv:1)
- [t24_pose_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t24_pose_20260326_102002.csv:1)

分析脚本：
- [.oma/sim2real/plans/forward_x_failure/scripts/07_windowed_roll_origin_probe.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/07_windowed_roll_origin_probe.py:1)

生成结果：
- [round3_windowed_roll_origin_probe_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_windowed_roll_origin_probe_20260326_102002.csv:1)
- [round3_windowed_roll_origin_probe_20260326_102002.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_windowed_roll_origin_probe_20260326_102002.md:1)

## 结论

这次把 `sole_roll` 拆成两个窗口看：

- 腾空窗：`touchdown - 0.35s` 到 `touchdown - 0.02s`
- touchdown 窗：`touchdown - 0.05s` 到 `touchdown + 0.10s`

结果显示：

- 腾空窗 `3/3` 都被判成 `execution_chain_dominant`
- touchdown 窗 `2/3` 为 `execution_chain_dominant`，`1/3` 为 `mixed_or_uncertain`

也就是说，在这份日志里，`sole_roll` 不是主要跟着网络 `output` 走，而是更接近 `current / pos` 所代表的执行链响应。

## 具体样本

| side | touchdown_time_sec | swing source | touchdown source |
|---|---:|---|---|
| right | 1774491603.921 | execution_chain_dominant | mixed_or_uncertain |
| right | 1774491607.211 | execution_chain_dominant | execution_chain_dominant |
| left | 1774491607.741 | execution_chain_dominant | execution_chain_dominant |

## 与延迟链的关系

[06_delay_chain_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/06_delay_chain_probe.md:1) 已经给出：

- `action -> target ≈ 0 ms`
- `target -> current ≈ 20~30 ms`
- `current -> pos ≈ 80~145 ms`

结合本次窗口化结果，当前数据更支持：

1. `sole_roll` 的表现层更偏执行链响应，而不是即时 output。
2. output 和 target 在当前采样分辨率下几乎可视为同层。
3. 延迟会放大 touchdown 阶段的表现，但不是 swing/touchdown 镜像 roll 偏置的唯一来源。

## 解释边界

这是一份诊断性结果，不是严格的因果证明。
`current` 仍是执行器侧反馈代理，`pos` 是关节侧结果，不等价于电机内部的完整物理状态。
但就当前数据而言，`sole_roll` 更接近执行链而不是 output 链，这个结论是稳定的。

