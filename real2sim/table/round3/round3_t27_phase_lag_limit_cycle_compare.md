# t27 Phase Lag / Limit Cycle Compare

## Summary by case

| case | events | mean |sole_roll| | mean zero crossings | mean dominant period (s) | mean |lpf-pos| loop area | mean |pos-sole| loop area | mean lpf->pos lag (ms) | mean pos->sole lag (ms) | dominant source |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 35/0.5 baseline | 4 | 1.6941 | 0.0000 | nan | nan | 0.0053 | 133.0428 | 0.0000 | execution_chain_dominant |
| 50/0.8 right_roll | 4 | 1.7233 | 0.0000 | nan | nan | 0.0339 | 136.5278 | 18.5122 | execution_chain_dominant |
| 40/0.8 right_roll | 4 | 1.6043 | 0.0000 | nan | nan | 0.0528 | 134.4351 | 71.8532 | output_chain_dominant |
| 25/0.5 right_roll | 4 | 1.5744 | 0.0000 | nan | nan | 0.0006 | 141.8291 | 9.1503 | execution_chain_dominant |
| 25/0.5 all_ankles | 4 | 1.6298 | 0.0000 | nan | nan | 0.0060 | 143.7665 | 16.4978 | execution_chain_dominant |

## Interpretation

- 若高 kp 组的 `lpf->pos` lag、`pos->sole` lag、loop area 和 zero crossings 同时更大，更符合局部相位滞后驱动的限环振荡。
- 若低 kp 组这些指标显著减小，但前进变弱，说明低 kp 是把不稳定压住了，而不是根因消失。
- `sole_roll` 若仍主要判为 `execution_chain_dominant`，说明问题仍主要在执行链/机构响应，不是 output 直接把姿态做坏。
