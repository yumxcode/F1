# Coupled Geometry Cross-Kp Comparison

- Scope: first 4 touchdowns only
- Purpose: compare whether `coupled_geometry` under high-kp and low-kp settings keeps the same structural signature or changes category.

## Summary Table

| label | group | cross_side_roll_pattern | dominant_mode | dominant_root | mean_sole_roll_abs_rad | mean_ankle_roll_q_abs_rad | mean_roll_to_joint_gain_ratio | side_roll_sign_majority |
|---|---|---|---|---|---:|---:|---:|---|
| 35_0.5_baseline | baseline | bilateral_mirror_stable | touchdown_contact_geometry_bias | command_not_flat | 0.0934 | 0.0986 | 1.2110 | {'left': 'positive', 'right': 'negative'} |
| 35_0.5_retest | baseline | bilateral_mirror_stable | touchdown_contact_geometry_bias | residual_not_large_enough | 0.1189 | 0.0896 | 9.2990 | {'right': 'positive', 'left': 'negative'} |
| 50_0.8_right_roll | high_kp | bilateral_same_sign | touchdown_contact_geometry_bias | residual_not_large_enough | 0.0846 | 0.0797 | 2.8735 | {'right': 'positive', 'left': 'positive'} |
| 40_0.8_right_roll | high_kp | bilateral_mirror_stable | parallel_mapping_mismatch | command_not_flat | 0.1238 | 0.1337 | 2.6214 | {'right': 'positive', 'left': 'negative'} |
| 25_0.5_right_roll | low_kp | bilateral_mirror_stable | touchdown_contact_geometry_bias | residual_not_large_enough | 0.1070 | 0.0668 | 8.3749 | {'right': 'positive', 'left': 'negative'} |
| 25_0.5_all_ankles | low_kp | bilateral_same_sign | parallel_mapping_mismatch | residual_not_large_enough | 0.1182 | 0.0390 | 5.2093 | {'right': 'negative', 'left': 'negative'} |

## Interpretation

### High-kp set

- `50_0.8_right_roll`: mode=`touchdown_contact_geometry_bias`, root=`residual_not_large_enough`, `cross_side_roll_pattern=bilateral_same_sign`, `mean_roll_to_joint_gain_ratio=2.8735`
- `40_0.8_right_roll`: mode=`parallel_mapping_mismatch`, root=`command_not_flat`, `cross_side_roll_pattern=bilateral_mirror_stable`, `mean_roll_to_joint_gain_ratio=2.6214`

### Low-kp set

- `25_0.5_right_roll`: mode=`touchdown_contact_geometry_bias`, root=`residual_not_large_enough`, `cross_side_roll_pattern=bilateral_mirror_stable`, `mean_roll_to_joint_gain_ratio=8.3749`
- `25_0.5_all_ankles`: mode=`parallel_mapping_mismatch`, root=`residual_not_large_enough`, `cross_side_roll_pattern=bilateral_same_sign`, `mean_roll_to_joint_gain_ratio=5.2093`

## Current Read

1. If both high-kp and low-kp datasets keep `bilateral_mirror_stable` plus a high `roll_to_joint_gain_ratio`, then `coupled_geometry` is not just a low-kp artifact.
2. If high-kp mainly changes `dominant_root` but keeps the same mirror geometry signature, then gain changes are modulating expression rather than replacing the underlying geometry issue.
3. If low-kp suppresses shaking but retains the same mirror sign pattern, that supports the interpretation that controller gain is not the root source of the mirror roll bias.
