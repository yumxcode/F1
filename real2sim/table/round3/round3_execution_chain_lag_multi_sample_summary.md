# 11D Multi-sample Execution Chain Lag Compare

- Scope: 4 actuator-state t27 logs with all-ankle tuning.
- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.
- Focus: `cmd->state`, `state->joint`, `joint->sole`, and left/right asymmetry.
- `joint->sole` filtered summary keeps events with `joint_sole_corr >= 0.20`; raw summary is preserved for audit.

## Window Summary

| case | window | events | joint->sole valid | mean left state->joint (ms) | mean right state->joint (ms) | mean state->joint (ms) | mean joint->sole raw (ms) | mean joint->sole filtered (ms) | median joint->sole filtered (ms) | mean left cmd->state (ms) | mean right cmd->state (ms) | mean_abs_sole_roll |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 25/0.4 all_ankles | swing | 4 | 4 | 96.4893 | 47.1227 | 71.8060 | 94.2453 | 94.2453 | 89.7574 | 0.0000 | 0.0000 | 0.2158 |
| 25/0.4 all_ankles | touchdown | 4 | 3 | 51.6105 | 31.4151 | 41.5128 | 35.9030 | 2.9919 | 0.0000 | 0.0000 | 0.0000 | 0.0776 |
| 30/0.4 all_ankles | swing | 4 | 4 | 59.2068 | 92.3626 | 75.7847 | 80.5212 | 80.5212 | 66.3116 | 0.0000 | 0.0000 | 0.1602 |
| 30/0.4 all_ankles | touchdown | 4 | 3 | 4.7365 | 9.4731 | 7.1048 | 49.7337 | 18.9462 | 28.4193 | 0.0000 | 0.0000 | 0.0565 |
| 35/0.5 all_ankles | swing | 4 | 4 | 46.3474 | 53.2995 | 49.8234 | 71.8384 | 71.8384 | 41.7126 | 0.0000 | 0.0000 | 0.2148 |
| 35/0.5 all_ankles | touchdown | 4 | 3 | 0.0000 | 44.0300 | 22.0150 | 13.9042 | 18.5390 | 9.2695 | 0.0000 | 0.0000 | 0.1484 |
| 40/0.8 all_ankles | swing | 4 | 4 | 48.0489 | 41.1848 | 44.6168 | 116.6902 | 116.6902 | 109.8261 | 0.0000 | 0.0000 | 0.1494 |
| 40/0.8 all_ankles | touchdown | 4 | 3 | 0.0000 | 25.1685 | 12.5842 | 57.2011 | 27.4565 | 27.4565 | 0.0000 | 0.0000 | 0.0712 |

## Per-case Delta

| case | state->joint delta (touchdown-swing, ms) | joint->sole delta (touchdown-swing, ms) | left-right asymmetry in swing (ms) | left-right asymmetry in touchdown (ms) |
|---|---:|---:|---:|---:|
| 25/0.4 all_ankles | -30.2931 | -91.2534 | 49.3666 | 20.1954 |
| 30/0.4 all_ankles | -68.6799 | -61.5751 | -33.1558 | -4.7365 |
| 35/0.5 all_ankles | -27.8084 | -53.2995 | -6.9521 | -44.0300 |
| 40/0.8 all_ankles | -32.0326 | -89.2337 | 6.8641 | -25.1685 |

## Interpretation

- If `cmd->state` stays near zero across all 4 cases, command acceptance is not the main lag segment.
- If `state->joint` is consistently large already in `swing`, the lag is pre-contact rather than touchdown-induced.
- If raw `joint->sole` is much larger than filtered `joint->sole`, first suspect short-window correlation instability before reading it as a physical lag increase.
- If left-right asymmetry is stable across cases, hardware/structure asymmetry priority rises.
- Use `round3_execution_chain_lag_multi_sample_detail.csv` for event-level review.
