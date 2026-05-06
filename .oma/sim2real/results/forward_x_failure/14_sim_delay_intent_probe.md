# Sim Delay / Intent Probe

本轮基于仿真目录下两份日志：

- [t23_joint_20260506_094703.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/sim/t23_joint_20260506_094703.csv:1)
- [tm_raw_motor_current_20260506_094703.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/sim/tm_raw_motor_current_20260506_094703.csv:1)

对应分析脚本：

- [14_sim_delay_intent_probe.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/14_sim_delay_intent_probe.py:1)

输出结果：

- [sim_delay_intent_probe_20260506_094703.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_delay_intent_probe_20260506_094703.md:1)
- [sim_delay_intent_probe_20260506_094703.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_delay_intent_probe_20260506_094703.csv:1)
- [sim_delay_intent_probe_20260506_094703_summary.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_delay_intent_probe_20260506_094703_summary.csv:1)

## 这次能回答什么，不能回答什么

这两份仿真日志可以部分参照 `06_delay_chain_probe` 去看 `target -> pos` 的关节级延迟，但**不能**原样复刻 `03_ankle_landing_attitude_resolution`：

- 缺少 `base_euler_x/y/z`
- 缺少 `left/right_contact`
- 缺少 FK 后的 `sole_roll / sole_pitch`
- 缺少 touchdown 事件表

因此：

1. `06` 风格的 joint-space delay 可以看。
2. `03` 里的 `flattening_intent(target, pos)` 逻辑可以做**简化代理**。
3. 但不能把这次仿真结果直接写成 `command_not_flat / tracking_lag / coupled_geometry` 的 touchdown 三层分类。

## 数据采样

- `t23_joint` 采样约 `100 Hz`
- `tm_raw_motor_current` 采样约 `1000 Hz`

## 06 口径下的仿真结论

按 group 汇总，仿真日志中：

| group | mean target->pos ms | mean target->current ms | mean current->pos ms |
|---|---:|---:|---:|
| `ankle` | `39.9952` | `19.9976` | `69.9916` |
| `knee` | `54.9934` | `9.9988` | `99.9880` |
| `hip` | `73.3245` | `18.3311` | `59.9928` |

对踝关节单独看：

| joint | target->pos ms | target-pos rms err rad |
|---|---:|---:|
| `left_ankle_pitch_joint` | `49.9940` | `0.2731` |
| `left_ankle_roll_joint` | `29.9964` | `0.1949` |
| `right_ankle_pitch_joint` | `49.9940` | `0.2518` |
| `right_ankle_roll_joint` | `29.9964` | `0.1435` |

当前更稳的读法是：

1. 仿真里 `target -> pos` 确实也不是 `0 ms`，而是大致 `30 ~ 50 ms` 的踝关节级延迟。
2. 但踝关节**不是唯一最慢**的一组；hip / knee 同样有可比甚至更大的 `target -> pos` lag。
3. 这点和真实 `06` 的方向是一致的：**ankle 不是唯一慢点**。
4. 仅从这份仿真日志看，不支持把 forward x 问题先收口成“仿真里 ankle 单独严重 lag”。

同时要保留边界：

- 这里的 `current` 是 `tm_raw_motor_current`，不是 `/actuator_states.position`
- 所以 `target->current`、`current->pos` 只能当粗代理，不能和真实 `06` 的 `target -> current -> pos` 逐段一一对表

## 03 口径下的简化观察

这次只复用了 `03` 里最小的一段 joint-space 逻辑：

- `flattening_intent(target, pos)`
- 判据是：
  - `target * pos <= 0`
  - 或 `abs(target) + 0.02 < abs(pos)`

它只回答：

> 在这个时刻，目标是否在把该 joint 往零附近 / 反向拉回去。

它**不回答**：

- 这个动作是不是在让脚底更平
- 这个时刻是不是 touchdown
- 这个 joint-space 目标是否足以解释 foot-space 姿态

仿真里 ankle 汇总为：

| joint | flatten intent ratio | high-err flatten ratio |
|---|---:|---:|
| `left_ankle_pitch_joint` | `0.4108` | `0.4881` |
| `left_ankle_roll_joint` | `0.2886` | `0.1746` |
| `right_ankle_pitch_joint` | `0.7585` | `0.9342` |
| `right_ankle_roll_joint` | `0.1603` | `0.0029` |

这里最重要的不是数值本身，而是边界：

1. `right_ankle_roll_joint` 的低 ratio 不能直接解释成真实 `command_not_flat`。  
   因为这里没有 touchdown / sole_roll / foot-flat 参考，只能说明在 full-log 的 joint-space 样本里，它很少表现成“把 joint 往零拉回去”的形态。

2. `right_ankle_pitch_joint` 的高 ratio 也不能直接解释成“仿真里 command 一定正确”。  
   它只说明 delayed target 相对 delayed joint 更常表现为纠偏型指令。

3. 因此，这次仿真数据**不支持**直接沿用真实 `03` 的 `command_not_flat = 4` 这类 touchdown 结论。

## 当前阶段结论

基于这两份仿真日志，当前可以先收成：

1. 仿真里 joint-space 确实存在非零 `target -> pos` 延迟，但 ankle 并不比 hip / knee 特别异常。
2. 这一点和真实 `06` 一致：`forward_x_failure` 不能先收口成“只有 ankle 慢”。
3. 这两份仿真日志不足以复刻真实 `03` 的 touchdown 判因，因此当前不能基于仿真数据得出 `command_not_flat / tracking_lag / coupled_geometry` 的等价结论。
4. 如果要继续做“仿真-真实对齐”的 `03` 级别对比，下一步必须补仿真日志字段：
   - `base_euler_x/y/z`
   - `left/right_contact`
   - `action_*`
   - `pos_des_raw_* / pos_des_lpf_* / tau_des_lpf_*`
   - 或至少补可离线重建 `sole_roll / sole_pitch` 的 base pose + FK 所需量
