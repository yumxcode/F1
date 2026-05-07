# 12B Left-Right Asymmetry Analysis

- Source case summary: `round3_parallel_realization_shape_case_summary.csv`
- Scope: 4 all-ankle actuator-state cases, swing/touchdown windows.
- Asymmetry is judged along 3 axes: lag gap, gain gap, and shape severity gap.

## Window-level Summary

| window | cases | mean_abs_lag_gap_ms | mean_abs_gain_gap | dominant lag side | dominant gain side | dominant shape side |
|---|---:|---:|---:|---|---|---|
| swing | 4 | 16.1560 | 0.0438 | right_worse | right_worse | right_worse |
| touchdown | 4 | 10.6885 | 0.2789 | left_worse | right_worse | right_worse |

## Per-case View

| case | window | lag gap (ms) | lag worse side | gain gap | gain worse side | shape gap | shape worse side |
|---|---|---:|---|---:|---|---:|---|
| 25/0.4 all_ankles | swing | -19.4984 | right_worse | -0.0737 | right_worse | -1.0000 | right_worse |
| 25/0.4 all_ankles | touchdown | 2.7632 | left_worse | -0.2982 | right_worse | -2.0000 | right_worse |
| 30/0.4 all_ankles | swing | -34.6531 | right_worse | 0.0008 | left_worse | -2.0000 | right_worse |
| 30/0.4 all_ankles | touchdown | 5.0308 | left_worse | 0.1453 | left_worse | -3.0000 | right_worse |
| 35/0.5 all_ankles | swing | 8.0956 | left_worse | -0.0229 | right_worse | 1.0000 | left_worse |
| 35/0.5 all_ankles | touchdown | -32.3928 | right_worse | -0.4983 | right_worse | -2.0000 | right_worse |
| 40/0.8 all_ankles | swing | -2.3768 | right_worse | 0.0779 | left_worse | -5.0000 | right_worse |
| 40/0.8 all_ankles | touchdown | 2.5672 | left_worse | -0.1738 | right_worse | -2.0000 | right_worse |

## Interpretation

- If dominant worse side flips across windows or metrics, asymmetry exists but is not a fixed single-side failure.
- If one side were consistently worse in lag, gain, and shape severity, that would support a fixed unilateral fault hypothesis.
- Current output is intended to answer exactly whether `left/right asymmetry` should be interpreted as fixed-side or mode-dependent.
