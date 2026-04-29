# Mapping Consistency Notes

- Source diag csv: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv`

## Current Code-Path Facts

1. `src/module/control_module/src/rl_controller.cc`
   - Parallel ankle joints first compute joint-space torque intent with `tau = kp * (pos_des - q) + kd * (0 - dq)`.
   - For parallel joints, `joint_cmd.effort = tau_des_lpf`, while `joint_cmd.stiffness = 0` and `joint_cmd.damping = 0`.
   - This means walk-stage parallel ankles are effectively torque-dominant at joint command output.

2. `src/module/dcu_driver_module/src/ankle_transmission.cc`
   - The transmission maps joint-space `position / velocity / effort / kp / kd` into actuator-space MIT command fields.
   - Actuator `kp / kd` are copied from joint command, so current walk path keeps actuator MIT package shape but with zero stiffness/damping for parallel joints.

3. `src/module/dcu_driver_module/src/dcu_driver_module.cc`
   - The mapped actuator command is sent through `SetMitCmd(position, velocity, effort, kp, kd)`.

4. `src/module/dcu_driver_module/xyber_controller/xyber_api/src/power_flow.cpp`
   - Motor-side command interface is standard MIT five-tuple packaging.

## Current Risk Focus

- If all 4 ankles are softened and extra roll-direction shaking drops, but touchdown still stays in `coupled_geometry`, force magnitude alone is not sufficient to explain the residual issue.
- Priority checks should therefore move to:
  - joint/actuator direction sign consistency
  - zero bias between joint-space and foot-space
  - pitch/roll coupling inside parallel mapping
  - touchdown contact reference mismatch between FK body and real sole contact edge
