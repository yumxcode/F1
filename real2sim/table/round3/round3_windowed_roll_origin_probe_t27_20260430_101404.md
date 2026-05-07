# Windowed Roll Origin Probe on t27

- Source log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv`
- Shared suffix: `20260430_101404`

## Summary

- `swing` source guesses: `{'mixed_or_uncertain': 2, 'execution_chain_dominant': 2}`
- `touchdown` source guesses: `{'execution_chain_dominant': 2, 'mixed_or_uncertain': 1, 'output_chain_dominant': 1}`

## Per Event

| side | touchdown_time_sec | swing sole mean abs | touchdown sole mean abs | swing source guess | touchdown source guess | swing action->sole lag ms | swing raw->sole lag ms | swing lpf->sole lag ms | swing pos->sole lag ms | touchdown action->sole lag ms | touchdown raw->sole lag ms | touchdown lpf->sole lag ms | touchdown pos->sole lag ms |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| left | 1777515244.419 | 0.1419 | 0.0298 | mixed_or_uncertain | execution_chain_dominant | nan | nan | nan | nan | 9.1522 | 9.1522 | 137.2826 | 18.3043 |
| right | 1777515244.759 | 0.2517 | 0.0721 | execution_chain_dominant | mixed_or_uncertain | 64.0652 | 64.0652 | 164.7391 | 64.0652 | 36.6087 | 36.6087 | 137.2826 | 36.6087 |
| left | 1777515245.069 | 0.2098 | 0.1167 | execution_chain_dominant | execution_chain_dominant | 100.6739 | 100.6739 | 0.0000 | 0.0000 | 18.3043 | 18.3043 | 137.2826 | 27.4565 |
| right | 1777515245.429 | 0.1958 | 0.0663 | mixed_or_uncertain | output_chain_dominant | nan | nan | nan | nan | 36.6087 | 36.6087 | 146.4348 | 146.4348 |

## Interpretation

- 若 swing 窗口里 `sole_roll` 更接近 `action/target`，说明问题更早出现在输出链或映射链。
- 若 touchdown 窗口里 `sole_roll` 更接近 `current/pos`，说明接触阶段更受执行链/机械响应影响。
- 两个窗口若都保留同样的左右镜像 roll 偏置，则底层几何/映射问题仍然存在，延迟只是在放大表现。
