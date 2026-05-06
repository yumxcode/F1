# 12B Left-Right Asymmetry Analysis

- Source case summary: `round3_parallel_realization_shape_case_summary.csv`
- Scope: 4 all-ankle actuator-state cases, swing/touchdown windows.
- Asymmetry is judged along 3 axes: lag gap, gain gap, and shape severity gap.

## Window-level Summary

| window | cases | mean |lag gap| (ms) | mean |gain gap| | dominant lag side | dominant gain side | dominant shape side |
|---|---:|---:|---:|---|---|---|
| swing | 4 | 33.9174 | 1.0547 | left_worse | right_worse | right_worse |
| touchdown | 4 | 24.3374 | 0.6927 | left_worse | left_worse | right_worse |

## Per-case View

| case | window | lag gap (ms) | lag worse side | gain gap | gain worse side | shape gap | shape worse side |
|---|---|---:|---|---:|---|---:|---|
| 25/0.4 all_ankles | swing | -31.8811 | right_worse | -0.8068 | right_worse | -3.0000 | right_worse |
| 25/0.4 all_ankles | touchdown | 28.3221 | left_worse | 0.0396 | left_worse | -2.0000 | right_worse |
| 30/0.4 all_ankles | swing | 21.9108 | left_worse | 0.3295 | left_worse | -5.0000 | right_worse |
| 30/0.4 all_ankles | touchdown | 29.1671 | left_worse | 0.4877 | left_worse | 2.0000 | left_worse |
| 35/0.5 all_ankles | swing | 36.3680 | left_worse | 3.0152 | left_worse | -2.0000 | right_worse |
| 35/0.5 all_ankles | touchdown | 9.9465 | left_worse | 1.5521 | left_worse | -3.0000 | right_worse |
| 40/0.8 all_ankles | swing | 45.5097 | left_worse | -0.0675 | right_worse | 2.0000 | left_worse |
| 40/0.8 all_ankles | touchdown | 29.9139 | left_worse | -0.6915 | right_worse | 2.0000 | left_worse |

## Interpretation

- If dominant worse side flips across windows or metrics, asymmetry exists but is not a fixed single-side failure.
- If one side were consistently worse in lag, gain, and shape severity, that would support a fixed unilateral fault hypothesis.
- Current output is intended to answer exactly whether `left/right asymmetry` should be interpreted as fixed-side or mode-dependent.
