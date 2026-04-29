# 10 Execution Chain Disentanglement

## 数据源

本轮先基于 t27 诊断日志做 H2 代理判定：

- [t27_tracking_lag_b1_diag_20260428_152240.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_152240.csv:1)
- [t27_tracking_lag_b1_diag_20260428_161322.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_161322.csv:1)
- [t27_tracking_lag_b1_diag_20260428_162312.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_162312.csv:1)
- [t27_tracking_lag_b1_diag_20260428_163825.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_163825.csv:1)
- [t27_tracking_lag_b1_diag_20260428_164817.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv:1)

分析脚本：
- [.oma/sim2real/plans/forward_x_failure/scripts/10a_execution_chain_disentanglement_h2_t27.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/10a_execution_chain_disentanglement_h2_t27.py:1)

生成结果：
- [round3_t27_execution_chain_disentanglement_h2.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_t27_execution_chain_disentanglement_h2.csv:1)
- [round3_t27_execution_chain_disentanglement_h2.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_t27_execution_chain_disentanglement_h2.md:1)

## 结论

先用 `pos_des_lpf -> pos` 作为执行链代理后，H2 的代理判定成立。

更准确地说：

- `lpf -> pos` 代理滞后在多数 t27 样本里明显存在
- `sole_roll` 仍主要跟随执行链，不直接跟随 output
- 高 kp 组更容易把这类迟滞放大，但没有形成稳定周期限环

## 结果摘要

| case | events | mean |sole_roll| | mean lpf->pos lag (ms) | mean pos->sole lag (ms) | H2 proxy support | dominant source |
|---|---:|---:|---:|---:|---:|---|
| 35/0.5 baseline | 4 | 1.6941 | 133.0428 | 0.0000 | 0.7500 | execution_chain_dominant |
| 50/0.8 right_roll | 4 | 1.7233 | 136.5278 | 18.5122 | 0.7500 | execution_chain_dominant |
| 40/0.8 right_roll | 4 | 1.6043 | 134.4351 | 71.8532 | 0.5000 | output_chain_dominant |
| 25/0.5 right_roll | 4 | 1.5744 | 141.8291 | 9.1503 | 1.0000 | execution_chain_dominant |
| 25/0.5 all_ankles | 4 | 1.6298 | 143.7665 | 16.4978 | 1.0000 | execution_chain_dominant |

## 解释

1. 这不是严格的 actuator-state 分解。
2. 但在现有日志下，`pos_des_lpf -> pos` 已经足够作为执行链代理，支持“执行链迟滞明显”的判断。
3. `sole_roll` 仍然主要跟随执行链，不支持“output 直接把脚做坏”作为主解释。

## 后续

- 补录 `/actuator_states`
- 真正拆出 `lpf -> actuator` 与 `actuator -> pos`
- 在同一批 kp 下重复前 4 步 touchdown，对比高 kp / 低 kp 的迟滞来源

