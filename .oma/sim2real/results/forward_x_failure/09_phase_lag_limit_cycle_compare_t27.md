# 09 Phase Lag / Limit Cycle Compare on t27

## 数据源

- [t27_tracking_lag_b1_diag_20260428_152240.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_152240.csv:1)
- [t27_tracking_lag_b1_diag_20260428_161322.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_161322.csv:1)
- [t27_tracking_lag_b1_diag_20260428_162312.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_162312.csv:1)
- [t27_tracking_lag_b1_diag_20260428_163825.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_163825.csv:1)
- [t27_tracking_lag_b1_diag_20260428_164817.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv:1)

分析脚本：
- [.oma/sim2real/plans/forward_x_failure/scripts/09_phase_lag_limit_cycle_compare_t27.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/09_phase_lag_limit_cycle_compare_t27.py:1)

生成结果：
- [round3_t27_phase_lag_limit_cycle_compare.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_t27_phase_lag_limit_cycle_compare.csv:1)
- [round3_t27_phase_lag_limit_cycle_compare.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_t27_phase_lag_limit_cycle_compare.md:1)

## 结论

这次把 t27 几组 kp 的 touchdown 窗拿来横向比较，关注三类指标：

- `lpf -> pos` 的局部相位滞后
- `pos -> sole_roll` 的局部相位滞后
- `sole_roll` 的零交叉 / dominant period

结果显示：

- 高 kp 组确实存在更明显的局部 `lpf -> pos` 滞后，尤其在 `40/0.8 right_roll` 这组里最明显。
- 但所有组的 `sole_roll` 零交叉都为 `0`，dominant period 也没有形成稳定可识别周期。
- 因此当前更像是“接触窗口里有相位滞后和响应迟滞”，而不是一个已经闭合成型的稳定限环。

## 横向摘要

| case | mean lpf->pos lag (ms) | mean pos->sole lag (ms) | mean_abs_sole_roll | mean zero crossings | dominant source |
|---|---:|---:|---:|---:|---|
| 35/0.5 baseline | 0.0053 | 133.0428 | 1.6941 | 0.0000 | execution_chain_dominant |
| 50/0.8 right_roll | 18.5122 | 136.5278 | 1.7233 | 0.0000 | execution_chain_dominant |
| 40/0.8 right_roll | 71.8532 | 134.4351 | 1.6043 | 0.0000 | output_chain_dominant |
| 25/0.5 right_roll | 9.1503 | 141.8291 | 1.5744 | 0.0000 | execution_chain_dominant |
| 25/0.5 all_ankles | 16.4978 | 143.7665 | 1.6298 | 0.0000 | execution_chain_dominant |

## 解释

1. `sole_roll` 仍然主要跟随执行链/关节响应，不是即时 output 直接决定。
2. 高 kp 的主要变化是局部相位滞后变大，而不是形成稳定周期震荡。
3. `40/0.8` 的 lag 最大，但它没有把系统推成一个清晰的 limit cycle；更像是把接触响应拉得更迟、更不稳。
4. 低 kp 能压住这种相位滞后表现，但推进会变弱。

## Dead-zone 边界

这份结果里的“高 kp 放大局部相位滞后”仍然成立，但现在应和死区一起读：

- `swing` 期的较小输出更容易把系统推到小信号敏感区
- 这会让局部 `lpf -> pos` 滞后显得更大
- 所以 lag 变大不必然等于机械结构退化，至少一部分可能是 dead-zone / threshold response 在放大相位偏移

## 边界

`zero crossings = 0` 和 `dominant period = nan` 说明：这批数据里没有观测到一个稳定的、可重复的周期震荡信号。
所以不能把当前现象简单写成“高 kp 引发稳定限环”；更准确的说法是：

**高 kp 在接触窗口里放大了执行链迟滞和相位偏移，但没有形成一个清晰稳定的周期限环。**

## 与总结论的关系

这份结果把“高 kp 抖动厉害”收紧为：

1. 高 kp 会放大接触窗里的局部相位滞后。
2. 但目前没有证据表明它已经形成稳定的周期震荡闭环。
3. 因此高 kp 更像是把底层执行链迟滞和几何偏置放大出来，而不是单独创造出一个新的动力学故障。
4. 低 kp 只是把这类滞后表现压低，不能消除根因。

## 指标字典

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `mean_lpf_to_pos_lag_ms` | `pos_des_lpf -> pos` 的平均局部相位滞后 | 量化执行链代理滞后 |
| `mean_pos_to_sole_lag_ms` | `pos -> sole_roll` 的平均局部相位滞后 | 量化 joint-space 到 foot-space 表现延迟 |
| `mean_abs_sole_roll` | touchdown 窗 `abs(sole_roll)` 均值 | 量化脚底 roll 不平程度 |
| `mean_zero_crossings` | `sole_roll` 在窗口内的平均零交叉数 | 判断是否存在周期振荡迹象 |
| `dominant_period_s` | `sole_roll` 的估计主周期 | 当前未形成稳定可识别周期 |
| `execution_chain_dominant` | `sole_roll` 更接近执行链响应 | 当前主趋势 |
| `output_chain_dominant` | `sole_roll` 更接近 output 链 | `40/0.8` 仅按 proxy 不稳处理，不推翻全局结论 |
| `limit_cycle_evidence` | 由零交叉和主周期综合判断的限环证据 | 当前为不足，不写成稳定限环 |
