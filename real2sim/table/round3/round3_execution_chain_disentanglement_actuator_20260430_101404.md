# 11 Execution Chain Disentanglement with Actuator States

- Source diag csv: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv`
- This analysis uses the newly added `/actuator_cmd` and `/actuator_states` logs.
- Window: first 4 touchdown events, touchdown-350ms to touchdown+100ms.

## Summary

| metric | value |
|---|---:|
| event_count | 4 |
| mean_abs_sole_roll | 0.0712 |
| mean action->sole lag (ms) | 25.1685 |
| mean raw->sole lag (ms) | 25.1685 |
| mean tau_lpf->sole lag (ms) | 6.8641 |
| mean joint_pos->sole lag (ms) | 57.2011 |
| mean left act cmd->state lag (ms) | 0.0000 |
| mean right act cmd->state lag (ms) | 0.0000 |
| mean left act state->joint lag (ms) | 0.0000 |
| mean right act state->joint lag (ms) | 25.1685 |
| dominant sole source | execution_chain_dominant |
| actuator_chain_support_mean | 0.5000 |

## Event table

| side | t_touch(s) | sole_source_guess | best_match_signal | best_match_lag(ms) | best_match_corr | act_left_cmd->state(ms) | act_right_cmd->state(ms) | act_left_state->joint(ms) | act_right_state->joint(ms) |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| left | 1777515244.419 | execution_chain_dominant | actuator_state_pos_left_ankle_left_actuator | 9.1522 | 0.7081 | 0.0000 | 0.0000 | 0.0000 | 27.4565 |
| right | 1777515244.759 | execution_chain_dominant | actuator_state_pos_right_ankle_right_actuator | 9.1522 | 0.7415 | 0.0000 | 0.0000 | 0.0000 | 36.6087 |
| left | 1777515245.069 | output_chain_dominant | tau_des_lpf | 9.1522 | 0.7304 | 0.0000 | 0.0000 | 0.0000 | 27.4565 |
| right | 1777515245.429 | output_chain_dominant | tau_des_lpf | 18.3043 | 0.6373 | 0.0000 | 0.0000 | 0.0000 | 9.1522 |

## Interpretation

- If `sole_source_guess` remains `execution_chain_dominant`, the newly logged actuator path still supports the previous conclusion: `sole_roll` is not directly following the network output chain.
- The new actuator logs let us split the execution chain into `actuator_cmd -> actuator_state` and `actuator_state -> joint_pos`, which was previously only a proxy.
- Use this file as the baseline before changing `kp/kd` again.
