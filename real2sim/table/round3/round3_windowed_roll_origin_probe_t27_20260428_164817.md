# Windowed Roll Origin Probe on t27

- Source log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv`
- Shared suffix: `20260428_164817`

## Summary

- `swing` source guesses: `{'execution_chain_dominant': 3, 'mixed_or_uncertain': 1}`
- `touchdown` source guesses: `{'execution_chain_dominant': 3, 'output_chain_dominant': 1}`

## Per Event

| side | touchdown_time_sec | swing sole mean abs | touchdown sole mean abs | swing source guess | touchdown source guess | swing action->sole lag ms | swing raw->sole lag ms | swing lpf->sole lag ms | swing pos->sole lag ms | touchdown action->sole lag ms | touchdown raw->sole lag ms | touchdown lpf->sole lag ms | touchdown pos->sole lag ms |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| left | 1777366098.099 | 2.0377 | 1.7111 | execution_chain_dominant | execution_chain_dominant | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 28.2819 | 28.2819 | 141.4096 | 0.0000 |
| right | 1777366098.459 | 1.9480 | 1.5705 | execution_chain_dominant | execution_chain_dominant | 65.9912 | 65.9912 | 169.6916 | 0.0000 | 9.4273 | 9.4273 | 141.4096 | 37.7092 |
| right | 1777366098.749 | 1.7491 | 1.5913 | mixed_or_uncertain | execution_chain_dominant | nan | nan | nan | nan | 0.0000 | 0.0000 | 150.8369 | 28.2819 |
| left | 1777366098.819 | 1.8983 | 1.6464 | execution_chain_dominant | output_chain_dominant | 131.9823 | 131.9823 | 131.9823 | 0.0000 | 18.8546 | 18.8546 | 141.4096 | 0.0000 |

## Interpretation

- 若 swing 窗口里 `sole_roll` 更接近 `action/target`，说明问题更早出现在输出链或映射链。
- 若 touchdown 窗口里 `sole_roll` 更接近 `current/pos`，说明接触阶段更受执行链/机械响应影响。
- 两个窗口若都保留同样的左右镜像 roll 偏置，则底层几何/映射问题仍然存在，延迟只是在放大表现。
