# 11C Windowed Execution Chain Lag Analysis

- Source diag csv: `t27_tracking_lag_b1_diag_20260430_101404.csv`
- Scope: first 4 touchdown events only.
- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.

- `joint->sole` quality gate: keep events with `joint_sole_corr >= 0.20` in the filtered summary.

## Window Summary

| window | events | joint->sole valid | mean left state->joint lag (ms) | mean right state->joint lag (ms) | mean state->joint lag (ms) | mean joint->sole lag raw (ms) | mean joint->sole lag filtered (ms) | median joint->sole lag filtered (ms) | mean left cmd->state lag (ms) | mean right cmd->state lag (ms) | mean_abs_sole_roll |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| swing | 4 | 4 | 48.0489 | 41.1848 | 44.6168 | 116.6902 | 116.6902 | 109.8261 | 0.0000 | 0.0000 | 0.1494 |
| touchdown | 4 | 3 | 0.0000 | 25.1685 | 12.5842 | 57.2011 | 27.4565 | 27.4565 | 0.0000 | 0.0000 | 0.0712 |

## Window Delta

| metric | delta touchdown - swing (ms) |
|---|---:|
| state->joint lag delta | -32.0326 |
| joint->sole lag delta | -89.2337 |

## Event Table

| window | side | t_touch(s) | left cmd->state (ms) | right cmd->state (ms) | left state->joint (ms) | right state->joint (ms) | mean state->joint (ms) | joint->sole raw (ms) | joint->sole corr | joint->sole filtered (ms) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| swing | left | 1777515244.419 | 0.0000 | 0.0000 | 0.0000 | 155.5870 | 77.7935 | 45.7609 | 0.6635 | 45.7609 |
| touchdown | left | 1777515244.419 | 0.0000 | 0.0000 | 0.0000 | 27.4565 | 13.7283 | 18.3043 | 0.5994 | 18.3043 |
| swing | right | 1777515244.759 | 0.0000 | 0.0000 | 173.8913 | 0.0000 | 86.9457 | 118.9783 | 0.5281 | 118.9783 |
| touchdown | right | 1777515244.759 | 0.0000 | 0.0000 | 0.0000 | 36.6087 | 18.3043 | 36.6087 | 0.2530 | 36.6087 |
| swing | left | 1777515245.069 | 0.0000 | 0.0000 | 18.3043 | 0.0000 | 9.1522 | 201.3478 | 0.4115 | 201.3478 |
| touchdown | left | 1777515245.069 | 0.0000 | 0.0000 | 0.0000 | 27.4565 | 13.7283 | 27.4565 | 0.6591 | 27.4565 |
| swing | right | 1777515245.429 | 0.0000 | 0.0000 | 0.0000 | 9.1522 | 4.5761 | 100.6739 | 0.6158 | 100.6739 |
| touchdown | right | 1777515245.429 | 0.0000 | 0.0000 | 0.0000 | 9.1522 | 4.5761 | 146.4348 | 0.0000 | nan |

## Interpretation

- If `cmd->state` stays near zero in both windows, the main lag is not in command acceptance.
- If `state->joint` is already large in `swing`, the lag is pre-contact and not only a touchdown effect.
- `joint->sole` is reported in both raw and corr-gated form because short touchdown windows can produce unstable edge-hitting lag estimates when `joint_sole_corr` is weak.
- If `state->joint` grows further in `touchdown`, contact is amplifying the execution-chain lag.
- Left/right asymmetry should be judged from `left/right state->joint lag`, not from `cmd->state`.
