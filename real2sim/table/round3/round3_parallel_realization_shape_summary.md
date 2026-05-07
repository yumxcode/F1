# 12A Parallel Realization Shape Analysis

- Scope: 4 actuator-state t27 logs, 4 first touchdown events, swing/touchdown windows.
- Focus: `actuator_state -> joint_pos` realization shape.

## Side Summary

| case | window | side | events | mean lag (ms) | mean corr | mean gain | mean hysteresis area | mean stiction ratio | dominant shape |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 25/0.4 all_ankles | swing | left | 4 | 67.9017 | 0.4716 | 0.3076 | 0.4094 | 0.2906 | backlash_like,low_realization_gain |
| 25/0.4 all_ankles | touchdown | left | 4 | 47.7109 | 0.3843 | -0.1706 | 0.5994 | 0.2434 | backlash_like |
| 25/0.4 all_ankles | swing | right | 4 | 87.4001 | 0.5792 | 0.3813 | 0.3552 | 0.1706 | overall_slow,backlash_like |
| 25/0.4 all_ankles | touchdown | right | 4 | 44.9477 | 0.6348 | 0.1276 | 0.6843 | 0.0476 | backlash_like,low_realization_gain |
| 30/0.4 all_ankles | swing | left | 4 | 59.6421 | 0.1976 | 0.2353 | 0.3496 | 0.0457 | mostly_linear |
| 30/0.4 all_ankles | touchdown | left | 4 | 9.9821 | 0.6342 | 0.1688 | 0.4023 | 0.1580 | backlash_like,low_realization_gain |
| 30/0.4 all_ankles | swing | right | 4 | 94.2951 | 0.7405 | 0.2345 | 0.4665 | 0.1635 | backlash_like |
| 30/0.4 all_ankles | touchdown | right | 4 | 4.9514 | 0.1295 | 0.0235 | 0.3100 | 0.2143 | stick_slip_like,backlash_like,low_realization_gain |
| 35/0.5 all_ankles | swing | left | 4 | 54.8515 | 0.4322 | 0.2552 | 0.2173 | 0.0922 | backlash_like,low_realization_gain |
| 35/0.5 all_ankles | touchdown | left | 4 | 7.3945 | 0.1512 | -0.4688 | 0.1915 | 0.3760 | stick_slip_like |
| 35/0.5 all_ankles | swing | right | 4 | 46.7559 | 0.4887 | 0.2782 | 0.2786 | 0.2809 | overall_slow |
| 35/0.5 all_ankles | touchdown | right | 4 | 39.7873 | 0.5855 | 0.0295 | 0.0512 | 0.7619 | stick_slip_like,low_realization_gain |
| 40/0.8 all_ankles | swing | left | 4 | 47.5842 | 0.7390 | 0.5616 | 0.2024 | 0.2541 | mostly_linear |
| 40/0.8 all_ankles | touchdown | left | 4 | 15.0880 | 0.2219 | -0.0653 | 0.3519 | 0.3491 | mostly_linear |
| 40/0.8 all_ankles | swing | right | 4 | 49.9610 | 0.8223 | 0.4838 | 0.3222 | 0.2012 | overall_slow,backlash_like |
| 40/0.8 all_ankles | touchdown | right | 4 | 12.5207 | 0.2302 | 0.1085 | 0.0729 | 0.1624 | low_realization_gain |

## Case Summary

| case | window | lag gap left-right (ms) | gain gap | left shape | right shape |
|---|---|---:|---:|---|---|
| 25/0.4 all_ankles | swing | -19.4984 | -0.0737 | backlash_like,low_realization_gain | overall_slow,backlash_like |
| 25/0.4 all_ankles | touchdown | 2.7632 | -0.2982 | backlash_like | backlash_like,low_realization_gain |
| 30/0.4 all_ankles | swing | -34.6531 | 0.0008 | mostly_linear | backlash_like |
| 30/0.4 all_ankles | touchdown | 5.0308 | 0.1453 | backlash_like,low_realization_gain | stick_slip_like,backlash_like,low_realization_gain |
| 35/0.5 all_ankles | swing | 8.0956 | -0.0229 | backlash_like,low_realization_gain | overall_slow |
| 35/0.5 all_ankles | touchdown | -32.3928 | -0.4983 | stick_slip_like | stick_slip_like,low_realization_gain |
| 40/0.8 all_ankles | swing | -2.3768 | 0.0779 | mostly_linear | overall_slow,backlash_like |
| 40/0.8 all_ankles | touchdown | 2.5672 | -0.1738 | mostly_linear | low_realization_gain |

## Interpretation

- `overall_slow` means the lag itself is already large.
- `stick_slip_like` means actuator state moves while joint response stays locally pinned for a noticeable fraction of the window.
- `backlash_like` means the state-joint loop encloses a visible area, consistent with backlash / hysteresis.
- `low_realization_gain` means the joint realizes only a small fraction of the actuator-state variation.
- Use the detail csv for per-event/per-actuator review.
