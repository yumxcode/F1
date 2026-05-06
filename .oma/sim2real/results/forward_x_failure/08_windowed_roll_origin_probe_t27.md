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

## Dead-zone 边界

这里的 `execution_chain_dominant` 同样不能直接读成“机械结构一定是主因”。
在 `swing` 窗，`action / pos_des_raw` 的幅值本身偏小时，死区 / 阈值敏感区会放大局部相位滞后，使 `sole_roll` 看起来更像跟随执行链。

## 指标字典

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `action` | 网络输出层信号 | 判断 output 侧是否直接主导 `sole_roll` |
| `pos_des_raw` | action 缩放、叠加 init、限幅后的 joint-space 原始目标 | `13` 后续用于 swing 小信号死区审视 |
| `pos_des_lpf` | 低通后的 joint-space 目标 | 判断 target 经过滤波后的执行链位置 |
| `pos` | `/joint_states` 映射后的 joint-space 真实位置 | 执行链兑现结果 |
| `swing source` | swing 窗判定的 `sole_roll` 主导来源 | 区分接触前来源 |
| `touchdown source` | touchdown 窗判定的 `sole_roll` 主导来源 | 区分触地瞬间来源 |
| `execution_chain_dominant` | `sole_roll` 更接近 `pos_des_lpf / pos` | 当前主趋势，但包含 dead-zone 影响可能 |
| `output_chain_dominant` | `sole_roll` 更接近 `action / pos_des_raw` | 当前少数样本，不作为全局反例 |
| `mixed_or_uncertain` | 多条链路相近或窗口内证据不足 | 保留不确定样本 |
