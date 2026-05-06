# 12A Parallel Realization Shape Analysis

- Scope: 4 actuator-state t27 logs, 4 first touchdown events, swing/touchdown windows.
- Focus: `actuator_state -> joint_pos` realization shape.

## Side Summary

| case | window | side | events | mean lag (ms) | mean corr | mean gain | mean hysteresis area | mean stiction ratio | dominant shape |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 25/0.4 all_ankles | swing | left | 6 | 68.4192 | 0.5071 | 0.2690 | 0.4408 | 0.2476 | backlash_like |
| 25/0.4 all_ankles | touchdown | left | 6 | 33.2820 | 0.4787 | 0.2949 | 0.2226 | 0.2712 | mostly_linear |
| 25/0.4 all_ankles | swing | right | 2 | 100.3003 | 0.7962 | 1.0758 | 0.1781 | 0.2500 | overall_slow,backlash_like |
| 25/0.4 all_ankles | touchdown | right | 2 | 4.9599 | 0.5041 | 0.2553 | 0.6567 | 0.2538 | backlash_like |
| 30/0.4 all_ankles | swing | left | 4 | 99.1225 | 0.6049 | 0.4779 | 0.2535 | 0.1444 | overall_slow,backlash_like |
| 30/0.4 all_ankles | touchdown | left | 4 | 41.5255 | 0.0675 | -0.0257 | 0.3725 | 0.0333 | backlash_like,low_realization_gain |
| 30/0.4 all_ankles | swing | right | 4 | 77.2117 | 0.7360 | 0.1483 | 1.5687 | 0.2897 | overall_slow,stick_slip_like,backlash_like,low_realization_gain |
| 30/0.4 all_ankles | touchdown | right | 4 | 12.3584 | 0.2085 | -0.5133 | 0.7518 | 0.1229 | backlash_like |
| 35/0.5 all_ankles | swing | right | 4 | 49.0069 | -0.1096 | -2.5057 | 0.1258 | 0.5110 | low_realization_gain |
| 35/0.5 all_ankles | touchdown | right | 4 | 0.0000 | 0.9164 | 0.3569 | 0.0908 | 0.5778 | stick_slip_like,low_realization_gain |
| 35/0.5 all_ankles | swing | left | 4 | 85.3750 | 0.8445 | 0.5094 | 0.3964 | 0.2718 | mostly_linear |
| 35/0.5 all_ankles | touchdown | left | 4 | 9.9465 | 0.9278 | 1.9090 | 0.6014 | 0.0694 | backlash_like |
| 40/0.8 all_ankles | swing | left | 6 | 50.4996 | 0.6683 | 0.2939 | 0.3606 | 0.1283 | backlash_like,low_realization_gain |
| 40/0.8 all_ankles | touchdown | left | 6 | 29.9139 | 0.4913 | 0.3582 | 0.3948 | 0.2533 | backlash_like |
| 40/0.8 all_ankles | swing | right | 2 | 4.9899 | 0.5735 | 0.3614 | 0.2191 | 0.0667 | backlash_like |
| 40/0.8 all_ankles | touchdown | right | 2 | 0.0000 | 0.9916 | 1.0498 | 0.0767 | 0.0417 | mostly_linear |

## Case Summary

| case | window | lag gap left-right (ms) | gain gap | left shape | right shape |
|---|---|---:|---:|---|---|
| 25/0.4 all_ankles | swing | -31.8811 | -0.8068 | backlash_like | overall_slow,backlash_like |
| 25/0.4 all_ankles | touchdown | 28.3221 | 0.0396 | mostly_linear | backlash_like |
| 30/0.4 all_ankles | swing | 21.9108 | 0.3295 | overall_slow,backlash_like | overall_slow,stick_slip_like,backlash_like,low_realization_gain |
| 30/0.4 all_ankles | touchdown | 29.1671 | 0.4877 | backlash_like,low_realization_gain | backlash_like |
| 35/0.5 all_ankles | swing | 36.3680 | 3.0152 | mostly_linear | low_realization_gain |
| 35/0.5 all_ankles | touchdown | 9.9465 | 1.5521 | backlash_like | stick_slip_like,low_realization_gain |
| 40/0.8 all_ankles | swing | 45.5097 | -0.0675 | backlash_like,low_realization_gain | backlash_like |
| 40/0.8 all_ankles | touchdown | 29.9139 | -0.6915 | backlash_like | mostly_linear |

## Interpretation

- `overall_slow` means the lag itself is already large.
- `stick_slip_like` means actuator state moves while joint response stays locally pinned for a noticeable fraction of the window.
- `backlash_like` means the state-joint loop encloses a visible area, consistent with backlash / hysteresis.
- `low_realization_gain` means the joint realizes only a small fraction of the actuator-state variation.
- Use the detail csv for per-event/per-actuator review.
