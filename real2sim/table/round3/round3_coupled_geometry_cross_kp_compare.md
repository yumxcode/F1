# Coupled Geometry Cross-Kp Comparison

- Scope: first 4 touchdowns only
- Purpose: compare whether `coupled_geometry` under high-kp and low-kp settings keeps the same structural signature or changes category.

## Summary Table

| label | group | cross_side_roll_pattern | dominant_mode | dominant_root | mean_sole_roll_abs_rad | mean_ankle_roll_q_abs_rad | mean_roll_to_joint_gain_ratio | side_roll_sign_majority |
|---|---|---|---|---|---:|---:|---:|---|
| 35_0.5_baseline | baseline | bilateral_mirror_stable | parallel_mapping_mismatch | coupled_geometry | 1.7454 | 0.0780 | 27.3721 | {'left': 'positive', 'right': 'negative'} |
| 35_0.5_retest | baseline | bilateral_mirror_stable | parallel_mapping_mismatch | command_not_flat | 1.6704 | 0.0508 | 47.0660 | {'right': 'negative', 'left': 'positive'} |
| 50_0.8_right_roll | high_kp | bilateral_mirror_stable | parallel_mapping_mismatch | command_not_flat | 1.7456 | 0.0795 | 27.3156 | {'left': 'positive', 'right': 'negative'} |
| 40_0.8_right_roll | high_kp | bilateral_mirror_stable | parallel_mapping_mismatch | command_not_flat | 1.6498 | 0.1605 | 17.3421 | {'left': 'positive', 'right': 'negative'} |
| 25_0.5_right_roll | low_kp | bilateral_mirror_stable | parallel_mapping_mismatch | command_not_flat | 1.5549 | 0.0542 | 93.7084 | {'right': 'negative', 'left': 'positive'} |
| 25_0.5_all_ankles | low_kp | bilateral_mirror_stable | parallel_mapping_mismatch | coupled_geometry | 1.6841 | 0.0299 | 372.2790 | {'left': 'positive', 'right': 'negative'} |

## Interpretation

### High-kp set

- `50_0.8_right_roll`: mode=`parallel_mapping_mismatch`, root=`command_not_flat`, `cross_side_roll_pattern=bilateral_mirror_stable`, `mean_roll_to_joint_gain_ratio=27.3156`
- `40_0.8_right_roll`: mode=`parallel_mapping_mismatch`, root=`command_not_flat`, `cross_side_roll_pattern=bilateral_mirror_stable`, `mean_roll_to_joint_gain_ratio=17.3421`

### Low-kp set

- `25_0.5_right_roll`: mode=`parallel_mapping_mismatch`, root=`command_not_flat`, `cross_side_roll_pattern=bilateral_mirror_stable`, `mean_roll_to_joint_gain_ratio=93.7084`
- `25_0.5_all_ankles`: mode=`parallel_mapping_mismatch`, root=`coupled_geometry`, `cross_side_roll_pattern=bilateral_mirror_stable`, `mean_roll_to_joint_gain_ratio=372.2790`

## Current Read

1. If both high-kp and low-kp datasets keep `bilateral_mirror_stable` plus a high `roll_to_joint_gain_ratio`, then `coupled_geometry` is not just a low-kp artifact.
2. If high-kp mainly changes `dominant_root` but keeps the same mirror geometry signature, then gain changes are modulating expression rather than replacing the underlying geometry issue.
3. If low-kp suppresses shaking but retains the same mirror sign pattern, that supports the interpretation that controller gain is not the root source of the mirror roll bias.
