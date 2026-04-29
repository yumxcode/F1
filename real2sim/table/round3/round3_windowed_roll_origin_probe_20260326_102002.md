# Windowed Roll Origin Probe

- Source action log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t25_action_20260326_102002.csv`
- Source joint log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t23_joint_20260326_102002.csv`
- Source current log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t3_current_20260326_102002.csv`
- Source gait log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t22_gait_20260326_102002.csv`
- Source pose log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t24_pose_20260326_102002.csv`
- Shared suffix: `20260326_102002`

## Summary

- `swing` source guesses: `{'execution_chain_dominant': 3}`
- `touchdown` source guesses: `{'mixed_or_uncertain': 1, 'execution_chain_dominant': 2}`

## Per Event

| side | touchdown_time_sec | swing sole mean abs | touchdown sole mean abs | swing source guess | touchdown source guess | swing action->sole lag ms | swing target->sole lag ms | swing current->sole lag ms | swing pos->sole lag ms | touchdown action->sole lag ms | touchdown target->sole lag ms | touchdown current->sole lag ms | touchdown pos->sole lag ms |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| right | 1774491603.921 | 1.8944 | 1.5948 | execution_chain_dominant | mixed_or_uncertain | 63.7865 | 63.7865 | 173.1348 | 54.6741 | 18.2247 | 18.2247 | 136.6854 | 136.6854 |
| right | 1774491607.211 | 1.9436 | 1.6732 | execution_chain_dominant | execution_chain_dominant | 9.1124 | 9.1124 | 109.3483 | 9.1124 | 0.0000 | 0.0000 | 127.5730 | 27.3371 |
| left | 1774491607.741 | 1.9431 | 1.6433 | execution_chain_dominant | execution_chain_dominant | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 18.2247 | 18.2247 | 0.0000 | 0.0000 |

## Interpretation

- 若 swing 窗口里 `sole_roll` 更接近 `action/target`，说明问题更早出现在输出链或映射链。
- 若 touchdown 窗口里 `sole_roll` 更接近 `current/pos`，说明接触阶段更受执行链/机械响应影响。
- 两个窗口若都保留同样的左右镜像 roll 偏置，则底层几何/映射问题仍然存在，延迟只是在放大表现。
