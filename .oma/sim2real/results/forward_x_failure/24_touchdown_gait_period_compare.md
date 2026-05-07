# 24 Touchdown-based Gait Period Compare

- Touchdown source: current `ROUND3A.detect_touchdowns()` logic.
- Current detector: FK foot relative height / vertical velocity first, with hip-pitch motion as phase sanity check; `left_contact/right_contact` are fallback only.
- Full gait period: same-side touchdown-to-touchdown interval.
- Adjacent step interval: consecutive left/right touchdown interval, approximately half gait period when gait alternates cleanly.

## Case Summary

| stage | case | events L/R | same-side period mean±std (s) | gait freq (Hz) | adjacent step mean±std (s) | step freq (Hz) |
|---|---|---:|---:|---:|---:|---:|
| real | 25/0.4 all_ankles | 11/10 | 0.6968 ± 0.0650 | 1.4351 | 0.3455 ± 0.0723 | 2.8945 |
| real | 30/0.4 all_ankles | 10/9 | 0.7018 ± 0.0494 | 1.4250 | 0.3489 ± 0.0522 | 2.8662 |
| real | 35/0.5 all_ankles | 4/3 | 0.6460 ± 0.0560 | 1.5480 | 0.3167 ± 0.0388 | 3.1580 |
| real | 40/0.8 all_ankles | 5/5 | 0.6837 ± 0.0421 | 1.4626 | 0.3433 ± 0.0651 | 2.9128 |
| sim | 25/0.4 | 21/19 | 0.6992 ± 0.0170 | 1.4302 | 0.3585 ± 0.0591 | 2.7897 |
| sim | 35/0.5 | 21/21 | 0.6995 ± 0.0147 | 1.4296 | 0.3488 ± 0.0365 | 2.8671 |
| sim | 40/0.5 | 25/25 | 0.6998 ± 0.0114 | 1.4290 | 0.3496 ± 0.0194 | 2.8605 |
| sim | 50/0.8 | 26/26 | 0.6996 ± 0.0195 | 1.4294 | 0.3496 ± 0.0235 | 2.8604 |

## Side Summary

| stage | case | side | touchdowns | same-side periods | period mean±std (s) |
|---|---|---|---:|---:|---:|
| real | 25/0.4 all_ankles | left | 11 | 10 | 0.6910 ± 0.0565 |
| real | 25/0.4 all_ankles | right | 10 | 9 | 0.7033 ± 0.0763 |
| real | 30/0.4 all_ankles | left | 10 | 9 | 0.6978 ± 0.0581 |
| real | 30/0.4 all_ankles | right | 9 | 8 | 0.7062 ± 0.0410 |
| real | 35/0.5 all_ankles | left | 4 | 3 | 0.6333 ± 0.0666 |
| real | 35/0.5 all_ankles | right | 3 | 2 | 0.6650 ± 0.0493 |
| real | 40/0.8 all_ankles | left | 5 | 4 | 0.6800 ± 0.0217 |
| real | 40/0.8 all_ankles | right | 5 | 4 | 0.6875 ± 0.0602 |
| sim | 25/0.4 | left | 21 | 20 | 0.6990 ± 0.0171 |
| sim | 25/0.4 | right | 19 | 18 | 0.6994 ± 0.0173 |
| sim | 35/0.5 | left | 21 | 20 | 0.6995 ± 0.0119 |
| sim | 35/0.5 | right | 21 | 20 | 0.6995 ± 0.0173 |
| sim | 40/0.5 | left | 25 | 24 | 0.6996 ± 0.0096 |
| sim | 40/0.5 | right | 25 | 24 | 0.7000 ± 0.0132 |
| sim | 50/0.8 | left | 26 | 25 | 0.6992 ± 0.0152 |
| sim | 50/0.8 | right | 26 | 25 | 0.7000 ± 0.0233 |

## Reading

- Real same-side gait period mean across cases: `0.6821 s`; sim: `0.6995 s`.
- Real adjacent step interval mean across cases: `0.3386 s`; sim: `0.3516 s`.
- Interpret this as FK-kinematic touchdown-detector period, not force-plate ground-truth contact period.
