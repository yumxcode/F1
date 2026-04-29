# Left/Right Ankle Sign Chain Check

## Controller Side

来源：

- [src/module/control_module/src/rl_controller.cc](/Users/yumx/code/X1/agibot_x1_infer/src/module/control_module/src/rl_controller.cc:152)
- [src/module/control_module/src/control_module.cc](/Users/yumx/code/X1/agibot_x1_infer/src/module/control_module/src/control_module.cc:139)

当前 walk 并联踝 joint command 路径：

1. `joint_state.position` 先减去 `joint_offset`
2. 并联踝在 controller 层先算：
   - `tau = kp * (pos_des - q) + kd * (0 - dq)`
3. 然后输出：
   - `joint_cmd.position = 0`
   - `joint_cmd.velocity = 0`
   - `joint_cmd.effort = tau_des_lpf`
   - `joint_cmd.stiffness = 0`
   - `joint_cmd.damping = 0`

这说明：

- walk 阶段并联踝在 controller 输出层是 torque-dominant
- 电机侧 MIT 五元组仍会被填充，但非零核心量是 `effort`

## YAML Side

来源：

- [src/module/control_module/cfg/rl_x1.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/module/control_module/cfg/rl_x1.yaml:94)
- [src/module/dcu_driver_module/cfg/dcu_x1.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/module/dcu_driver_module/cfg/dcu_x1.yaml:329)
- [src/module/dcu_driver_module/cfg/dcu_x1.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/module/dcu_driver_module/cfg/dcu_x1.yaml:363)

结论：

- `left/right ankle pitch/roll joint_offset = 0.0`
- `left_ankle_parallel_trans direction_left = 1.0, direction_right = 1.0`
- `right_ankle_parallel_trans direction_left = 1.0, direction_right = 1.0`

所以：

- 配置层没有直接给出左右踝不同的符号设定

## Left Ankle

### actuator -> joint

来源：

- [src/module/dcu_driver_module/src/ankle_transmission.cc](/Users/yumx/code/X1/agibot_x1_infer/src/module/dcu_driver_module/src/ankle_transmission.cc:79)

链路：

1. `qm5 <- actr_right.state.position * direction`
2. `qm6 <- actr_left.state.position * direction`
3. 额外执行：
   - `qm5 *= -1`
   - `qm6 *= -1`
4. 查表得到 `q5, q6`
5. 额外执行：
   - `q6 *= -1`
6. torque state:
   - `taum5 <- actr_right.state.effort * direction`
   - `taum6 <- actr_left.state.effort * direction`

### joint -> actuator

来源：

- [src/module/dcu_driver_module/src/ankle_transmission.cc](/Users/yumx/code/X1/agibot_x1_infer/src/module/dcu_driver_module/src/ankle_transmission.cc:252)

链路：

1. `q5Des <- joint_pitch.cmd.position`
2. `q6Des <- joint_roll.cmd.position`
3. 反解得到：
   - `qm5Des`
   - `qm6Des`
4. actuator cmd:
   - `actr_right.cmd <- (position=qm5Des, velocity=qdm5Des, effort=taum5Des, kp=joint_pitch.kp, kd=joint_pitch.kd)`
   - `actr_left.cmd <- (position=qm6Des, velocity=qdm6Des, effort=taum6Des, kp=joint_roll.kp, kd=joint_roll.kd)`

## Right Ankle

### actuator -> joint

来源：

- [src/module/dcu_driver_module/src/ankle_transmission.cc](/Users/yumx/code/X1/agibot_x1_infer/src/module/dcu_driver_module/src/ankle_transmission.cc:440)

链路：

1. `qm5 <- actr_left.state.position * direction`
2. `qm6 <- actr_right.state.position * direction`
3. 无额外 `qm5/qm6` 翻转
4. 查表得到 `q5, q6`
5. 无额外 `q6` 翻转
6. torque state:
   - `taum5 <- actr_left.state.effort * direction`
   - `taum6 <- actr_right.state.effort * direction`

### joint -> actuator

来源：

- [src/module/dcu_driver_module/src/ankle_transmission.cc](/Users/yumx/code/X1/agibot_x1_infer/src/module/dcu_driver_module/src/ankle_transmission.cc:601)

链路：

1. `q5Des <- joint_pitch.cmd.position`
2. `q6Des <- joint_roll.cmd.position`
3. 反解得到：
   - `qm5Des`
   - `qm6Des`
4. actuator cmd:
   - `actr_left.cmd <- (position=qm5Des, velocity=qdm5Des, effort=taum5Des, kp=joint_pitch.kp, kd=joint_pitch.kd)`
   - `actr_right.cmd <- (position=qm6Des, velocity=qdm6Des, effort=taum6Des, kp=joint_roll.kp, kd=joint_roll.kd)`

## Side-by-Side Summary

| 项 | left ankle | right ankle |
|---|---|---|
| actuator->joint `qm5` source | `actr_right` | `actr_left` |
| actuator->joint `qm6` source | `actr_left` | `actr_right` |
| extra `qm5 *= -1` | yes | no |
| extra `qm6 *= -1` | yes | no |
| extra `q6 *= -1` | yes | no |
| joint->actuator pitch cmd target | `actr_right` | `actr_left` |
| joint->actuator roll cmd target | `actr_left` | `actr_right` |

## Current Reading

1. 左右踝在代码层不是简单镜像复制，而是存在显式的 side-specific 符号和 actuator 绑定约定。
2. 这套约定如果一直存在，而系统以前能正常走，那么它更像“系统固有结构”，不是新问题突然出现的唯一解释。
3. 但这类 side-specific 结构会提高系统对以下问题的敏感性：
   - 单侧 actuator 出力衰减
   - 编码器零位漂移
   - 并联机构机械间隙或磨损
   - foot-space 与 joint-space 几何关系偏移
4. 因此当前更合理的工程结论是：
   - 代码层需要继续做 `parallel mapping / sign-convention verification`
   - 同时必须把“并联踝物理损坏或性能衰减”作为并行主线排查
