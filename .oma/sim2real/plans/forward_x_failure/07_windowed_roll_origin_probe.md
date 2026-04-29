# 07_windowed_roll_origin_probe

状态：`active`

## 目标

基于已确认的延迟链，分两个窗口观察 `sole_roll` 的来源倾向：

- 腾空窗：摆动腿还未触地时
- touchdown 窗：触地前后短窗口

重点对比四条链：

- `action`，网络输出
- `target`，关节目标
- `current`，执行器反馈代理
- `pos`，关节实际位置

判断 `sole_roll` 更接近哪一层：

- output 链主导
- 执行链/电机响应主导
- 混合或不确定

## 数据源

- [t25_action_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t25_action_20260326_102002.csv:1)
- [t23_joint_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t23_joint_20260326_102002.csv:1)
- [t3_current_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t3_current_20260326_102002.csv:1)
- [t22_gait_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t22_gait_20260326_102002.csv:1)
- [t24_pose_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t24_pose_20260326_102002.csv:1)

## 方法

- 先用 `03a` 的 FK 和 touchdown 检测链路复用出事件序列
- 对每个 touchdown，取：
  - 腾空窗：`touchdown - 0.35s` 到 `touchdown - 0.02s`
  - touchdown 窗：`touchdown - 0.05s` 到 `touchdown + 0.10s`
- 对两个窗口分别计算：
  - `action / target / current / pos / sole_roll` 的均值、绝对均值、方差
  - `sole_roll` 与四条链的滞后相关
  - `sole_source_guess`

## 成功标准

- 能明确给出：
  - 腾空窗更偏 output 还是执行链
  - touchdown 窗更偏 output 还是执行链
- 能说明这份数据里 `sole_roll` 的主导来源是否被延迟链解释

