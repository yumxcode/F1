# 26 Touchdown Detector Reaudit and Plan Update

## Why This Audit Was Needed

Visual review says real first 4 steps can still step normally, and real/sim gait rhythm is close. The old touchdown detector contradicted that fact: early real sequences included repeated same-side events such as `L-L-L-R` and unrealistically short same-side periods.

Root cause: `left_contact/right_contact` in `t27_tracking_lag_b1_diag` are not physical foot-contact sensors. They are ankle-pitch low-velocity proxies from `DetectFootContact()`, so `contact: 0 -> 1` can mark a joint-speed stall rather than true touchdown.

## Detector Change

Current `ROUND3A.detect_touchdowns()` now uses:

1. FK foot relative height / vertical velocity as the primary touchdown evidence.
2. Prior swing clearance as a required condition.
3. Post-touch low-height stability as a required condition.
4. Hip pitch motion as gait-phase sanity check.
5. Old ankle-pitch low-velocity contact and geometry fallback only if the kinematic detector finds no events for that side.

Implementation:

- [.oma/sim2real/plans/forward_x_failure/scripts/03a_round3_landing_window_analysis.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/03a_round3_landing_window_analysis.py:1)
- [.oma/sim2real/plans/forward_x_failure/scripts/25_kinematic_touchdown_detector_audit.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/25_kinematic_touchdown_detector_audit.py:1)

## Detector Validation

The new detector restores real first-4 touchdown order:

| real case | old first-4 | new first-4 | new same-side period |
|---|---|---|---:|
| `25/0.4 all_ankles` | `left-left-left-right` | `left-right-left-right` | `0.6499 s` |
| `30/0.4 all_ankles` | `left-left-left-left` | `left-right-left-right` | `0.6949 s` |
| `35/0.5 all_ankles` | `right-left-left-right` | `left-right-left-right` | `0.6499 s` |
| `40/0.8 all_ankles` | `left-left-left-right` | `left-right-left-right` | `0.6600 s` |

Full-period comparison after the detector change:

| stage | same-side period mean | adjacent touchdown interval mean |
|---|---:|---:|
| real | `0.6821 s` | `0.3386 s` |
| sim | `0.6995 s` | `0.3516 s` |

Conclusion: touchdown timing is now consistent with the visual fact that real/sim have similar gait rhythm. This does not prove physical contact timing exactly, but it is a better analysis window anchor than the old ankle-pitch velocity proxy.

## Recomputed Joint Adjustment/Jitter Result

`20` was regenerated with the new touchdown windows.

| axis/window | joint hp real/sim | joint range real/sim | joint path real/sim | joint dir-rate real/sim |
|---|---:|---:|---:|---:|
| roll `swing` | `3.22x` | `2.94x` | `3.90x` | `1.18x` |
| roll `touchdown` | `1.76x` | `2.08x` | `2.26x` | `0.80x` |
| pitch `swing` | `1.28x` | `1.43x` | `1.50x` | `1.08x` |
| pitch `touchdown` | `0.74x` | `1.69x` | `1.23x` | `0.57x` |

Updated reading:

- The old claim that real `touchdown` roll/pitch high-frequency, amplitude, path, and direction-change rate are all higher than sim is no longer valid.
- The remaining stable finding is that real has larger joint adjustment amplitude/path and larger tracking error, especially roll touchdown.
- Pitch touchdown is no longer a high-frequency jitter finding; it is mainly an amplitude/path/tracking-error finding.

## Plan / Result Impact

| Artifact | Status after detector audit |
|---|---|
| `20_real_vs_sim_joint_jitter_compare.md` | Regenerated with kinematic touchdown windows; conclusions updated. |
| `21_real_vs_sim_combined_conclusion.md` | Updated: touchdown jitter conclusion narrowed to range/path/tracking-error burden; pitch high-frequency claim downgraded. |
| `22_forward_x_failure_consistency_audit.md` | Updated: records old detector pollution and new current interpretation. |
| `23_forward_x_failure_stage_report.md` | Updated Step 6 numbers and detector audit entries. |
| `00_problem_and_overall_plan.md` | Updated current issue map and result index with `24/25`. |
| Older `03/05/18/19` residual/contact conclusions | Need careful reread if they use exact touchdown event timing. Their broad sim-vs-real residual theme remains useful, but numeric touchdown-window conclusions should be treated as pre-kinematic-detector until regenerated. |

## Current Canonical Reading

The current forward_x_failure story is now:

> The real robot's early gait rhythm is not fundamentally different from sim under the corrected touchdown detector. The remaining gap is not explained by a bad gait period estimate. It is better described as larger real joint adjustment amplitude/path and output-to-joint tracking error around swing/touchdown, with roll touchdown still the most important window. Kp/kd remains a behavior amplifier, not the only root cause.

## Next Required Reanalysis

1. Regenerate any residual-envelope tables that directly use `03a.detect_touchdowns()` and were produced before this detector change.
2. Re-check `18/19` quantitative rows before using them as hard thresholds.
3. Keep the qualitative constraints from sim video review: sim walks forward across kp/kd cases, real still fails forward progression, and detector conclusions must not contradict that visual fact.
