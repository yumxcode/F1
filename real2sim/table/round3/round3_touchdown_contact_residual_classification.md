# Touchdown Contact Residual Classification

## Scope

- This is `05C`: only touchdown-window foot-space / contact residual is classified.
- `13` owns swing dead-zone / small-signal realization.
- `12` owns `actuator_state -> joint_pos` realization residual.
- This report only classifies what remains in `joint_pos -> baseline-corrected foot-frame residual`.

## Summary

- label counts: `{'mixed_or_uncertain_contact_residual': 2, 'contact_geometry_residual': 1, 'mapping_workpoint_residual': 1}`

## Per Case

- `25/0.4 all_ankles` -> `mixed_or_uncertain_contact_residual`: `abs_sole_roll=0.1351`, `abs_sole_pitch=0.0264`, `abs_ankle_roll_q=0.0358`, `roll_gain=6.1447`, `joint->sole=35.9ms`; corrected foot-frame residual exists but current aggregates are not decisive
- `30/0.4 all_ankles` -> `contact_geometry_residual`: `abs_sole_roll=0.0914`, `abs_sole_pitch=0.0895`, `abs_ankle_roll_q=0.0984`, `roll_gain=3.8815`, `joint->sole=49.7ms`; joint->sole lag dominates state->joint lag, but the corrected residual pattern is not clean enough for a narrower label
- `35/0.5 all_ankles` -> `mixed_or_uncertain_contact_residual`: `abs_sole_roll=0.1659`, `abs_sole_pitch=0.0909`, `abs_ankle_roll_q=0.0895`, `roll_gain=76443.3557`, `joint->sole=13.9ms`; corrected foot-frame residual exists but current aggregates are not decisive
- `40/0.8 all_ankles` -> `mapping_workpoint_residual`: `abs_sole_roll=0.1495`, `abs_sole_pitch=0.0451`, `abs_ankle_roll_q=0.0373`, `roll_gain=5.1959`, `joint->sole=57.2ms`; mirror pattern and parallel_mapping_mismatch remain, but amplification is less extreme; focus on mapping table / real-mechanism workpoint consistency

## Current 05C Reading

- If `fk_foot_frame_residual_candidate` dominates, next test should first validate FK foot-frame alignment, then check real sole contact edge with synchronized video/contact evidence.
- If `pitch_roll_coupled_contact_residual` appears, that case should not be treated as a pure roll residual.
- If `mapping_workpoint_residual` dominates, next test should focus on mapping table / real mechanism consistency around touchdown operating points.
