# 09_phase_lag_limit_cycle_compare_t27

状态：`active`

## 目标

基于 t27 多组 kp 诊断日志，对比 touchdown 窗内：

- `pos_des_lpf -> pos` 的局部相位滞后
- `pos -> sole_roll` 的局部相位滞后
- `sole_roll` 的零交叉和 dominant period
- `pos_des_lpf` 与 `pos` 的相位环面积

判断高 kp 是否把接触阶段推成了稳定的局部限环，还是仅仅放大了执行链滞后。

## 数据源

优先使用以下 t27 日志：

- [t27_tracking_lag_b1_diag_20260428_152240.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_152240.csv:1)
- [t27_tracking_lag_b1_diag_20260428_161322.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_161322.csv:1)
- [t27_tracking_lag_b1_diag_20260428_162312.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_162312.csv:1)
- [t27_tracking_lag_b1_diag_20260428_163825.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_163825.csv:1)
- [t27_tracking_lag_b1_diag_20260428_164817.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv:1)

## 成功标准

- 能区分高 kp 和低 kp 的 touchdown 窗局部滞后大小
- 能判断是否出现稳定周期震荡
- 能说明 `sole_roll` 更偏执行链响应，还是更像被 output 直接驱动

