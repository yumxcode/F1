# t27 Phase Lag / Limit Cycle Compare

## Summary by case

| case | events | mean_abs_sole_roll | mean zero crossings | mean dominant period (s) | mean_abs_lpf_pos_loop_area | mean_abs_pos_sole_loop_area | mean lpf->pos lag (ms) | mean pos->sole lag (ms) | dominant source |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 35/0.5 baseline | 4 | 0.0622 | 1.7500 | nan | nan | 0.0100 | 135.2978 | 15.7847 | execution_chain_dominant |
| 50/0.8 right_roll | 4 | 0.0624 | 2.0000 | nan | nan | 0.0176 | 138.8419 | 46.2806 | execution_chain_dominant |
| 40/0.8 right_roll | 4 | 0.0738 | 1.0000 | nan | nan | 0.0198 | 141.3886 | 50.9926 | execution_chain_dominant |
| 25/0.5 right_roll | 4 | 0.0588 | 1.0000 | nan | nan | 0.0106 | 134.9664 | 9.1503 | execution_chain_dominant |
| 25/0.5 all_ankles | 4 | 0.0599 | 1.5000 | nan | nan | 0.0033 | 141.4096 | 9.4273 | execution_chain_dominant |

## Interpretation

- 若高 kp 组的 `lpf->pos` lag、`pos->sole` lag、loop area 和 zero crossings 同时更大，更符合局部相位滞后驱动的限环振荡。
- 若低 kp 组这些指标显著减小，但前进变弱，说明低 kp 是把不稳定压住了，而不是根因消失。
- `sole_roll` 若仍主要判为 `execution_chain_dominant`，说明问题仍主要在执行链/机构响应，不是 output 直接把姿态做坏。
