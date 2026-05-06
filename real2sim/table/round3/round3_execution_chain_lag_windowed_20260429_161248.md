# 11C Windowed Execution Chain Lag Analysis

- Source diag csv: `t27_tracking_lag_b1_diag_20260429_161248.csv`
- Scope: first 4 touchdown events only.
- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.

## Window Summary

| window | events | mean left state->joint lag (ms) | mean right state->joint lag (ms) | mean state->joint lag (ms) | mean joint->sole lag (ms) | mean left cmd->state lag (ms) | mean right cmd->state lag (ms) | mean |sole_roll| |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| swing | 4 | 156.2376 | 6.5099 | 81.3738 | 82.4587 | 0.0000 | 0.0000 | 1.7004 |
| touchdown | 4 | 49.9092 | 8.6799 | 29.2946 | 32.5495 | 0.0000 | 0.0000 | 1.7463 |

## Window Delta

| metric | delta touchdown - swing (ms) |
|---|---:|
| state->joint lag delta | -52.0792 |
| joint->sole lag delta | -49.9092 |

## Event Table

| window | side | t_touch(s) | left cmd->state (ms) | right cmd->state (ms) | left state->joint (ms) | right state->joint (ms) | mean state->joint (ms) | joint->sole (ms) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| swing | left | 1777450368.932 | 0.0000 | 0.0000 | 199.6369 | 0.0000 | 99.8185 | 199.6369 |
| touchdown | left | 1777450368.932 | 0.0000 | 0.0000 | 34.7195 | 0.0000 | 17.3597 | 0.0000 |
| swing | left | 1777450369.162 | 0.0000 | 0.0000 | 182.2772 | 26.0396 | 104.1584 | 0.0000 |
| touchdown | left | 1777450369.162 | 0.0000 | 0.0000 | 0.0000 | 26.0396 | 13.0198 | 0.0000 |
| swing | left | 1777450369.542 | 0.0000 | 0.0000 | 95.4785 | 0.0000 | 47.7393 | 130.1980 |
| touchdown | left | 1777450369.542 | 0.0000 | 0.0000 | 130.1980 | 8.6799 | 69.4389 | 130.1980 |
| swing | right | 1777450369.582 | 0.0000 | 0.0000 | 147.5577 | 0.0000 | 73.7789 | 0.0000 |
| touchdown | right | 1777450369.582 | 0.0000 | 0.0000 | 34.7195 | 0.0000 | 17.3597 | 0.0000 |

## Interpretation

- If `cmd->state` stays near zero in both windows, the main lag is not in command acceptance.
- If `state->joint` is already large in `swing`, the lag is pre-contact and not only a touchdown effect.
- If `state->joint` grows further in `touchdown`, contact is amplifying the execution-chain lag.
- Left/right asymmetry should be judged from `left/right state->joint lag`, not from `cmd->state`.
