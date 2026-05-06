# Touchdown Foot-Space / Contact Residual Collection

## Rule

- Fix `12C` first: use its touchdown-side `state->joint` vs `joint->sole` separation as the upstream boundary.
- Then collect touchdown-only geometry signatures from `05` on the same cases.
- If `12C` says `geometry_residual_dominant` and `05` still shows `bilateral_mirror_stable + parallel_mapping_mismatch`, the remaining residual is treated as foot-space / contact residual rather than upstream realization lag.

## Per Case

- `25/0.4 all_ankles` -> `foot_space_or_contact_residual_dominant`: `state->joint=23.6ms`, `joint->sole=71.8ms`, `abs_sole_roll=1.7768`, `roll_gain=74.6846`, `pattern=bilateral_mirror_stable`, `geometry=parallel_mapping_mismatch`
- `30/0.4 all_ankles` -> `mixed_with_strong_foot_space_residual`: `state->joint=26.1ms`, `joint->sole=11.8ms`, `abs_sole_roll=1.7249`, `roll_gain=170.5229`, `pattern=bilateral_mirror_stable`, `geometry=parallel_mapping_mismatch`
- `35/0.5 all_ankles` -> `foot_space_or_contact_residual_dominant`: `state->joint=4.6ms`, `joint->sole=74.2ms`, `abs_sole_roll=1.8361`, `roll_gain=570718.8108`, `pattern=bilateral_mirror_stable`, `geometry=parallel_mapping_mismatch`
- `40/0.8 all_ankles` -> `foot_space_or_contact_residual_dominant`: `state->joint=20.6ms`, `joint->sole=48.0ms`, `abs_sole_roll=1.6852`, `roll_gain=23.5217`, `pattern=bilateral_mirror_stable`, `geometry=parallel_mapping_mismatch`

## Current Reading

- residual counts: `{'foot_space_or_contact_residual_dominant': 3, 'mixed_with_strong_foot_space_residual': 1}`
