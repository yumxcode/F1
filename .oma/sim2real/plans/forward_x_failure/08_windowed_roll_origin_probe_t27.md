# 08_windowed_roll_origin_probe_t27

状态：`active`

## 目标

基于最新 t27 单文件诊断日志，在两个窗口里比较 `sole_roll` 和四层信号的关系：

- `action`
- `pos_des_raw`
- `pos_des_lpf`
- `pos`

窗口定义：

- 腾空窗：`touchdown - 0.35s` 到 `touchdown - 0.02s`
- touchdown 窗：`touchdown - 0.05s` 到 `touchdown + 0.10s`

## 数据源

- [t27_tracking_lag_b1_diag_20260428_164817.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv:1)

## 成功标准

- 能给出腾空窗和 touchdown 窗各自的 source guess
- 能说明 `sole_roll` 更接近 output 链，还是更接近执行链 / 关节响应
- 能判断这份 t27 数据是否延续了 `07` 里的结论

