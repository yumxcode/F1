# Windowed Roll Origin Probe

- Source action log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t25_action_20260326_102002.csv`
- Source joint log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t23_joint_20260326_102002.csv`
- Source current log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t3_current_20260326_102002.csv`
- Source gait log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t22_gait_20260326_102002.csv`
- Source pose log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t24_pose_20260326_102002.csv`
- Shared suffix: `20260326_102002`

## Summary

- `swing` source guesses: `{'execution_chain_dominant': 4}`
- `touchdown` source guesses: `{'execution_chain_dominant': 3, 'output_chain_dominant': 1}`

## Per Event

| side | touchdown_time_sec | swing sole mean abs | touchdown sole mean abs | swing source guess | touchdown source guess | swing action->sole lag ms | swing target->sole lag ms | swing current->sole lag ms | swing pos->sole lag ms | touchdown action->sole lag ms | touchdown target->sole lag ms | touchdown current->sole lag ms | touchdown pos->sole lag ms |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| left | 1774491603.481 | 0.3222 | 0.0528 | execution_chain_dominant | execution_chain_dominant | 36.4494 | 36.4494 | 63.7865 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 9.1124 |
| right | 1774491603.881 | 0.2722 | 0.0701 | execution_chain_dominant | output_chain_dominant | 91.1236 | 91.1236 | 100.2359 | 36.4494 | 0.0000 | 0.0000 | 27.3371 | 27.3371 |
| left | 1774491604.171 | 0.2563 | 0.0451 | execution_chain_dominant | execution_chain_dominant | 164.0224 | 164.0224 | 63.7865 | 0.0000 | 18.2247 | 18.2247 | 0.0000 | 9.1124 |
| right | 1774491604.551 | 0.2740 | 0.0603 | execution_chain_dominant | execution_chain_dominant | 0.0000 | 0.0000 | 182.2472 | 72.8989 | 18.2247 | 18.2247 | 36.4494 | 45.5618 |

## Interpretation

- 若 swing 窗口里 `sole_roll` 更接近 `action/target`，说明问题更早出现在输出链或映射链。
- 若 touchdown 窗口里 `sole_roll` 更接近 `current/pos`，说明接触阶段更受执行链/机械响应影响。
- 两个窗口若都保留同样的左右镜像 roll 偏置，则底层几何/映射问题仍然存在，延迟只是在放大表现。
