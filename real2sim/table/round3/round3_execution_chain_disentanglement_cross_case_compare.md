# 11B Execution Chain Disentanglement Cross-Case Compare

- Proxy source: `round3_t27_execution_chain_disentanglement_h2.csv`
- Actuator-state source: `round3_execution_chain_disentanglement_actuator_20260429_161248.csv`
- Scope: current repo only has one t27 log with `/actuator_cmd` + `/actuator_states`; cross-case compare therefore uses `5` proxy cases + `1` actuator-state case.

## Case Summary

| case | mode | events | mean |sole_roll| | mean output->sole lag (ms) | mean exec->sole lag (ms) | mean exec-internal lag (ms) | exec support | dominant source |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 25/0.5 all_ankles | proxy | 4 | 1.6298 | 14.1410 | 16.4978 | 143.7665 | 1.0000 | execution_chain_dominant |
| 25/0.5 right_roll | proxy | 4 | 1.5744 | 29.7384 | 9.1503 | 141.8291 | 1.0000 | execution_chain_dominant |
| 35/0.5 baseline | proxy | 4 | 1.6941 | 42.8443 | 0.0000 | 133.0428 | 0.7500 | execution_chain_dominant |
| 40/0.8 right_roll | proxy | 4 | 1.6043 | 4.6357 | 71.8532 | 134.4351 | 0.5000 | output_chain_dominant |
| 50/0.8 right_roll | proxy | 4 | 1.7233 | 30.0824 | 18.5122 | 136.5278 | 0.7500 | execution_chain_dominant |
| 25/0.5 all_ankles (actuator-state) | actuator_state | 4 | 1.7463 | 8.6799 | 32.5495 | 29.2946 | 1.0000 | execution_chain_dominant |

## Consistency Check: 25/0.5 all_ankles

| metric | proxy | actuator-state |
|---|---:|---:|
| mean |sole_roll| | 1.6298 | 1.7463 |
| mean output->sole lag (ms) | 14.1410 | 8.6799 |
| mean exec->sole lag (ms) | 16.4978 | 32.5495 |
| mean exec-internal lag (ms) | 143.7665 | 29.2946 |
| dominant source | execution_chain_dominant | execution_chain_dominant |

## Interpretation

- Across proxy cases, `sole_roll` is execution-chain-dominant in `4/5` parameter groups; only `40/0.8 right_roll` shifts toward `output_chain_dominant` under the proxy criterion.
- The only currently available actuator-state case (`4 ankles = 25/0.5`) still lands on `execution_chain_dominant`, so the new actuator evidence is directionally consistent with the broader proxy dataset.
- Current evidence supports: `output` is not the primary bottleneck; the execution chain remains the main source shaping `sole_roll`, while `coupled_geometry` stays as a concurrent underlying bias.
- Limitation: there is only one actuator-state case. To close Phase B, actuator-state logs still need to be repeated for at least one higher-kp condition.
