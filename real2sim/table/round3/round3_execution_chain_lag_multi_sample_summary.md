# 11D Multi-sample Execution Chain Lag Compare

- Scope: 4 actuator-state t27 logs with all-ankle tuning.
- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.
- Focus: `cmd->state`, `state->joint`, `joint->sole`, and left/right asymmetry.

## Window Summary

| case | window | events | mean left state->joint (ms) | mean right state->joint (ms) | mean state->joint (ms) | mean joint->sole (ms) | mean left cmd->state (ms) | mean right cmd->state (ms) | mean |sole_roll| |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 25/0.4 all_ankles | swing | 4 | 96.4893 | 47.1227 | 71.8060 | 92.0014 | 22.4394 | 47.1227 | 1.7400 |
| 25/0.4 all_ankles | touchdown | 4 | 44.8787 | 2.2439 | 23.5613 | 71.8060 | 0.0000 | 0.0000 | 1.7869 |
| 30/0.4 all_ankles | swing | 4 | 99.4674 | 87.6260 | 93.5467 | 26.0510 | 0.0000 | 0.0000 | 1.7014 |
| 30/0.4 all_ankles | touchdown | 4 | 14.2096 | 37.8923 | 26.0510 | 11.8414 | 0.0000 | 0.0000 | 1.6785 |
| 35/0.5 all_ankles | swing | 4 | 34.7605 | 97.3295 | 66.0450 | 76.4732 | 0.0000 | 0.0000 | 1.6450 |
| 35/0.5 all_ankles | touchdown | 4 | 9.2695 | 0.0000 | 4.6347 | 74.1558 | 0.0000 | 0.0000 | 1.8538 |
| 40/0.8 all_ankles | swing | 4 | 25.1685 | 50.3370 | 37.7527 | 16.0163 | 29.7446 | 27.4565 | 1.6435 |
| 40/0.8 all_ankles | touchdown | 4 | 34.3207 | 6.8641 | 20.5924 | 48.0489 | 0.0000 | 0.0000 | 1.6227 |

## Per-case Delta

| case | state->joint delta (touchdown-swing, ms) | joint->sole delta (touchdown-swing, ms) | left-right asymmetry in swing (ms) | left-right asymmetry in touchdown (ms) |
|---|---:|---:|---:|---:|
| 25/0.4 all_ankles | -48.2446 | -20.1954 | 49.3666 | 42.6348 |
| 30/0.4 all_ankles | -67.4957 | -14.2096 | 11.8414 | -23.6827 |
| 35/0.5 all_ankles | -61.4103 | -2.3174 | -62.5690 | 9.2695 |
| 40/0.8 all_ankles | -17.1603 | 32.0326 | -25.1685 | 27.4565 |

## Interpretation

- If `cmd->state` stays near zero across all 4 cases, command acceptance is not the main lag segment.
- If `state->joint` is consistently large already in `swing`, the lag is pre-contact rather than touchdown-induced.
- If left-right asymmetry is stable across cases, hardware/structure asymmetry priority rises.
- Use `round3_execution_chain_lag_multi_sample_detail.csv` for event-level review.
