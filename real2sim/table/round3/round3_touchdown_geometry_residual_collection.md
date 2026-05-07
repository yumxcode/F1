# Touchdown Foot-Space / Contact Residual Collection

## Rule

- Fix `12C` first: use its touchdown-side `state->joint` vs `joint->sole` separation as the upstream boundary.
- Then collect touchdown-only geometry signatures from `05` on the same cases.
- If `12C` says `geometry_residual_dominant` and `05` still shows `bilateral_mirror_stable + parallel_mapping_mismatch`, the remaining residual is treated as foot-space / contact residual rather than upstream realization lag.

## Per Case

- `25/0.4 all_ankles` -> `mixed_residual`: `state->joint=41.5ms`, `joint->sole=35.9ms`, `abs_sole_roll=0.1351`, `roll_gain=6.1447`, `pattern=bilateral_mirror_stable`, `geometry=parallel_mapping_mismatch`
- `30/0.4 all_ankles` -> `geometry_residual_dominant_but_not_mirror_stable`: `state->joint=7.1ms`, `joint->sole=49.7ms`, `abs_sole_roll=0.0914`, `roll_gain=3.8815`, `pattern=bilateral_same_sign`, `geometry=parallel_mapping_mismatch`
- `35/0.5 all_ankles` -> `mixed_residual`: `state->joint=22.0ms`, `joint->sole=13.9ms`, `abs_sole_roll=0.1659`, `roll_gain=76443.3557`, `pattern=bilateral_same_sign`, `geometry=touchdown_contact_geometry_bias`
- `40/0.8 all_ankles` -> `foot_space_or_contact_residual_dominant`: `state->joint=12.6ms`, `joint->sole=57.2ms`, `abs_sole_roll=0.1495`, `roll_gain=5.1959`, `pattern=bilateral_mirror_stable`, `geometry=parallel_mapping_mismatch`

## Current Reading

- residual counts: `{'mixed_residual': 2, 'geometry_residual_dominant_but_not_mirror_stable': 1, 'foot_space_or_contact_residual_dominant': 1}`
