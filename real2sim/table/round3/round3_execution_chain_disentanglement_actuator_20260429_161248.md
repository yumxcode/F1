# 11 Execution Chain Disentanglement with Actuator States

- Source diag csv: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260429_161248.csv`
- This analysis uses the newly added `/actuator_cmd` and `/actuator_states` logs.
- Window: first 4 touchdown events, touchdown-350ms to touchdown+100ms.

## Summary

| metric | value |
|---|---:|
| event_count | 4 |
| mean |sole_roll| | 1.7463 |
| mean action->sole lag (ms) | 8.6799 |
| mean raw->sole lag (ms) | 8.6799 |
| mean tau_lpf->sole lag (ms) | 41.2294 |
| mean joint_pos->sole lag (ms) | 32.5495 |
| mean left act cmd->state lag (ms) | 0.0000 |
| mean right act cmd->state lag (ms) | 0.0000 |
| mean left act state->joint lag (ms) | 49.9092 |
| mean right act state->joint lag (ms) | 8.6799 |
| dominant sole source | execution_chain_dominant |
| actuator_chain_support_mean | 1.0000 |

## Event table

| side | t_touch(s) | sole_source_guess | best_match_signal | best_match_lag(ms) | best_match_corr | act_left_cmd->state(ms) | act_right_cmd->state(ms) | act_left_state->joint(ms) | act_right_state->joint(ms) |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| left | 1777450368.932 | execution_chain_dominant | actuator_state_pos_left_ankle_right_actuator | 0.0000 | 0.8504 | 0.0000 | 0.0000 | 34.7195 | 0.0000 |
| left | 1777450369.162 | execution_chain_dominant | actuator_state_pos_left_ankle_left_actuator | 0.0000 | 0.8872 | 0.0000 | 0.0000 | 0.0000 | 26.0396 |
| left | 1777450369.542 | execution_chain_dominant | actuator_state_pos_left_ankle_left_actuator | 34.7195 | 1.0048 | 0.0000 | 0.0000 | 130.1980 | 8.6799 |
| right | 1777450369.582 | execution_chain_dominant | actuator_state_pos_right_ankle_right_actuator | 0.0000 | 0.7809 | 0.0000 | 0.0000 | 34.7195 | 0.0000 |

## Interpretation

- If `sole_source_guess` remains `execution_chain_dominant`, the newly logged actuator path still supports the previous conclusion: `sole_roll` is not directly following the network output chain.
- The new actuator logs let us split the execution chain into `actuator_cmd -> actuator_state` and `actuator_state -> joint_pos`, which was previously only a proxy.
- Use this file as the baseline before changing `kp/kd` again.
