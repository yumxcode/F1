# Touchdown Contact Residual Classification

## Scope

- This is `05C`: only touchdown-window foot-space / contact residual is classified.
- `13` owns swing dead-zone / small-signal realization.
- `12` owns `actuator_state -> joint_pos` realization residual.
- This report only classifies what remains in `joint_pos -> sole_roll`.

## Summary

- label counts: `{'fk_foot_frame_residual_candidate': 3, 'pitch_roll_coupled_contact_residual': 1}`

## Per Case

- `25/0.4 all_ankles` -> `fk_foot_frame_residual_candidate`: `abs_sole_roll=1.7768`, `abs_sole_pitch=0.0289`, `abs_ankle_roll_q=0.0467`, `roll_gain=74.6846`, `joint->sole=71.8ms`; mirror roll remains stable; ankle roll q is small while sole roll is large; pitch participation is low, but sole_roll is MuJoCo FK-derived, so treat this as a foot-frame/contact residual candidate until real sole contact is validated
- `30/0.4 all_ankles` -> `fk_foot_frame_residual_candidate`: `abs_sole_roll=1.7249`, `abs_sole_pitch=0.0516`, `abs_ankle_roll_q=0.0351`, `roll_gain=170.5229`, `joint->sole=11.8ms`; mirror roll remains stable; ankle roll q is small while sole roll is large; pitch participation is low, but sole_roll is MuJoCo FK-derived, so treat this as a foot-frame/contact residual candidate until real sole contact is validated
- `35/0.5 all_ankles` -> `pitch_roll_coupled_contact_residual`: `abs_sole_roll=1.8361`, `abs_sole_pitch=0.1849`, `abs_ankle_roll_q=0.1182`, `roll_gain=570718.8108`, `joint->sole=74.2ms`; foot-space residual remains, but pitch participation is material; do not reduce this case to pure roll contact edge
- `40/0.8 all_ankles` -> `fk_foot_frame_residual_candidate`: `abs_sole_roll=1.6852`, `abs_sole_pitch=0.1028`, `abs_ankle_roll_q=0.1082`, `roll_gain=23.5217`, `joint->sole=48.0ms`; mirror roll remains stable; ankle roll q is small while sole roll is large; pitch participation is low, but sole_roll is MuJoCo FK-derived, so treat this as a foot-frame/contact residual candidate until real sole contact is validated

## Current 05C Reading

- If `fk_foot_frame_residual_candidate` dominates, next test should first validate FK foot-frame alignment, then check real sole contact edge with synchronized video/contact evidence.
- If `pitch_roll_coupled_contact_residual` appears, that case should not be treated as a pure roll residual.
- If `mapping_workpoint_residual` dominates, next test should focus on mapping table / real mechanism consistency around touchdown operating points.
