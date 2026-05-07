# 25 Kinematic Touchdown Detector Audit

- Old detector: `ankle_pitch` low-velocity contact proxy plus FK refine.
- New/current detector: FK foot relative height/vertical velocity first, hip pitch motion as phase sanity check.
- Validation target from visual fact: real first 4 touchdowns should look like normal stepping, with early adjacent intervals near the observed gait rhythm instead of repeated spurious same-side triggers.

## First-4 Comparison

| stage | case | old sides | old adj mean±std | old same-side mean±std | new sides | new adj mean±std | new same-side mean±std | old/new events |
|---|---|---|---:|---:|---|---:|---:|---:|
| real | 25/0.4 all_ankles | left-left-left-right | 0.1900 ± 0.1665 | 0.1551 ± 0.2194 | left-right-left-right | 0.3299 ± 0.0436 | 0.6499 ± 0.0567 | 23/21 |
| real | 30/0.4 all_ankles | left-left-left-left | 0.0633 ± 0.1096 | 0.0633 ± 0.1096 | left-right-left-right | 0.3400 ± 0.0519 | 0.6949 ± 0.0636 | 23/19 |
| real | 35/0.5 all_ankles | right-left-left-right | 0.1266 ± 0.1267 | 0.2048 ± 0.2474 | left-right-left-right | 0.3299 ± 0.0529 | 0.6499 ± 0.0707 | 8/7 |
| real | 40/0.8 all_ankles | left-left-left-right | 0.3301 ± 0.4359 | 0.4800 ± 0.4950 | left-right-left-right | 0.3367 ± 0.0253 | 0.6600 ± 0.0143 | 18/10 |
| sim | 25/0.4 | left-left-left-right | 0.4467 ± 0.2194 | 0.5100 ± 0.2687 | left-left-right-left | 0.4600 ± 0.1997 | 0.6900 ± 0.0000 | 124/40 |
| sim | 35/0.5 | left-left-right-left | 0.2400 ± 0.1480 | 0.3600 ± 0.0283 | left-right-left-right | 0.3233 ± 0.0321 | 0.6650 ± 0.0071 | 99/42 |
| sim | 40/0.5 | left-right-right-left | 0.2433 ± 0.0981 | 0.5150 ± 0.3041 | left-right-left-right | 0.3300 ± 0.0400 | 0.6800 ± 0.0283 | 105/50 |
| sim | 50/0.8 | left-left-right-left | 0.2367 ± 0.1616 | 0.3551 ± 0.0355 | left-right-left-right | 0.3200 ± 0.0458 | 0.6600 ± 0.0424 | 102/52 |

## Reading

- Real old first-4 adjacent mean across cases: `0.1775 s`; new: `0.3341 s`.
- Real old first-4 same-side mean across cases: `0.2258 s`; new: `0.6637 s`.
- If the new detector restores alternating side sequence and period close to visual gait rhythm, downstream jitter/residual windows should be regenerated from this detector.
