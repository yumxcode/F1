# 08 Windowed Roll Origin Probe on t27

## 数据源

- [t27_tracking_lag_b1_diag_20260428_164817.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv:1)

分析脚本：
- [.oma/sim2real/plans/forward_x_failure/scripts/08_windowed_roll_origin_probe_t27.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/08_windowed_roll_origin_probe_t27.py:1)

生成结果：
- [round3_windowed_roll_origin_probe_t27_20260428_164817.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_windowed_roll_origin_probe_t27_20260428_164817.csv:1)
- [round3_windowed_roll_origin_probe_t27_20260428_164817.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_windowed_roll_origin_probe_t27_20260428_164817.md:1)

## 结论

这次按 t27 单文件日志，分腾空窗和 touchdown 窗看 `sole_roll` 与四层信号的关系：

- `action`
- `pos_des_raw`
- `pos_des_lpf`
- `pos`

结果显示：

- 腾空窗 `3/4` 更偏 `execution_chain_dominant`
- touchdown 窗 `3/4` 更偏 `execution_chain_dominant`

也就是说，在最新 t27 这份数据里，`sole_roll` 仍然主要跟随执行链或关节响应，而不是即时 output 链。

## 细节

| side | touchdown_time_sec | swing source | touchdown source |
|---|---:|---|---|
| left | 1777366098.099 | execution_chain_dominant | execution_chain_dominant |
| right | 1777366098.459 | execution_chain_dominant | execution_chain_dominant |
| right | 1777366098.749 | mixed_or_uncertain | execution_chain_dominant |
| left | 1777366098.819 | execution_chain_dominant | output_chain_dominant |

## 解释

这和前面的 `06_delay_chain_probe`、`07_windowed_roll_origin_probe` 是同方向的：

- output 链不是唯一主导
- `pos_des_raw / pos_des_lpf / pos` 这条执行链更能解释 `sole_roll`
- 但几何/映射层的镜像偏置没有因此消失，只是被执行链表现放大或收敛到不同样式

## 边界

这里的 `pos_des_raw` 和 `pos_des_lpf` 是 t27 日志里可直接观测的 target 代理，不等同于 `t23_joint / t3_current` 那种拆分日志里的完整链路。
因此这份结果更适合回答“`sole_roll` 更像跟哪层走”，不适合当成最终因果证明。

## 与总结论的关系

这份 t27 数据支持的不是“output 直接把脚做歪”，而是：

1. `output` 侧已经在发出调平意图。
2. `sole_roll` 更接近 `pos_des_lpf / pos` 这条执行链。
3. 所以问题更像是“意图有了，但执行链没有在 touchdown 前稳定兑现”，而不是纯 output 错误。
4. 这也解释了为什么低 kp 能减轻抖动，但不能关闭镜像偏置和触地不平。
