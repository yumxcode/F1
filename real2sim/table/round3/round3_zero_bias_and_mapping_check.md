# Round 3C Zero Bias and Mapping Check

## Config-Level Facts

### RL joint_offset

- `left_ankle_pitch_joint`: `0.0`
- `left_ankle_roll_joint`: `0.0`
- `right_ankle_pitch_joint`: `0.0`
- `right_ankle_roll_joint`: `0.0`

### DCU ankle transmission directions

- `left_ankle_parallel_trans`: `joint_pitch=left_ankle_pitch_joint`, `joint_roll=left_ankle_roll_joint`, `actuator_left=left_ankle_left_actuator`, `actuator_right=left_ankle_right_actuator`, `direction_left=1.0`, `direction_right=1.0`
- `right_ankle_parallel_trans`: `joint_pitch=right_ankle_pitch_joint`, `joint_roll=right_ankle_roll_joint`, `actuator_left=right_ankle_left_actuator`, `actuator_right=right_ankle_right_actuator`, `direction_left=1.0`, `direction_right=1.0`

## Code-Level Sign Facts

- `Left TransformActuatorToJoint`: extra `qm5 *= -1`: `True`
- `Left TransformActuatorToJoint`: extra `qm6 *= -1`: `True`
- `Left TransformActuatorToJoint`: extra `q6 *= -1`: `True`
- `Right TransformActuatorToJoint`: extra `qm5 *= -1`: `False`
- `Right TransformActuatorToJoint`: extra `qm6 *= -1`: `False`
- `Right TransformActuatorToJoint`: extra `q6 *= -1`: `False`
- `Left actuator state source`: `qm5 = actr_right_.handle->state.position`
- `Right actuator state source`: `qm5 = actr_left_.handle->state.position`
- `Left joint->actuator kp path consistent`: `True`
- `Right joint->actuator kp path consistent`: `True`

## Mapping Table Zero-Neighborhood

- Nearest grid entry to `(q5=0, q6=0)`: `(i=202, j=144)`, `q5=0.001402`, `q6=0.000769`, `qm5=0.003245`, `qm6=-0.001672`
- Local derivative along `qm5` axis: `dq5/dqm5=0.2854`, `dq6/dqm5=0.4658`
- Local derivative along `qm6` axis: `dq5/dqm6=-0.2855`, `dq6/dqm6=0.4667`

## Engineering Interpretation

- `joint_offset` for all 4 ankle joints is zero: `True`
- Both left/right ankle transmission blocks use `direction_left = 1.0`, `direction_right = 1.0`.
- Left ankle actuator->joint path contains extra sign flips (`qm5`, `qm6`, `q6`), while right ankle actuator->joint path does not.
- Therefore left/right symmetry is not established only by YAML directions; part of the sign convention is hard-coded inside `ankle_transmission.cc`.
- If touchdown results show stable left/right mirror roll bias, these hard-coded asymmetries are higher-priority suspects than controller-side `joint_offset`.

## Current Conclusion

1. `controller joint_offset` does not currently explain the touchdown roll bias, because all ankle offsets are configured to `0.0`.
2. `transmission direction` also does not explain it at YAML level, because both ankle transmissions are configured as `1.0 / 1.0`.
3. The stronger zero-bias risk is inside `ankle_transmission.cc` itself, where left/right sign handling is not symmetric in actuator->joint reconstruction.
4. This supports advancing `05` from generic `coupled_geometry` into a narrower `parallel_mapping / sign-convention verification` line.
