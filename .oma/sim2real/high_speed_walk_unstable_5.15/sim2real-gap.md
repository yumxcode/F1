# Sim2Real Gap Analysis — high_speed_walk_unstable

_Date: 2026-05-15 | Policy: rl_walk_leg | Hardware: X1_

## Algorithm Profile

- Policy file: `src/module/control_module/policy/rl_walk_leg.onnx`
- Obs space: phase sin/cos, velocity command, joint position/velocity, last action, base angular velocity, base euler.
- Action space: 12 leg joint position targets before postprocess.
- Parallel ankle path: ankle pitch/roll use torque command derived from `kp * (pos_des - q) + kd * (0 - dq)`.
- Control frequency: `1000 Hz`
- Inference frequency: `100 Hz`
- History buffer: `66 x 47 = 3102`
- Current enabled gait period: `cycle_time=0.7 s`
- High-speed candidate periods in config comments: `0.55 s`, `0.45 s`

## Gap Assessment Table

| Category | Sim / Config Setting | Real-World Risk | Gap Risk | Priority |
|---|---|---|---|---|
| Phase timing | `cycle_time=0.7`, candidates `0.55/0.45` | Real joint delay may consume too much phase margin at shorter period | HIGH | 1 |
| Hip/knee bandwidth | High target range in t23, max RMS errors at hip/knee | Swing placement and stance transition can miss timing at high speed | HIGH | 1 |
| Lateral/roll authority | Hip roll pos/target ratio low in t23 | Roll stabilization may be insufficient before touchdown | HIGH | 1 |
| Ankle contact response | Previous issue fixed low-speed ankle bias/support/underdamping | High-speed touchdown can reintroduce impact amplification | MEDIUM | 2 |
| Velocity command chain | t23 lacks cmd and odom | Unknown whether commanded high speed reaches policy cleanly | MEDIUM | 2 |
| State estimation | t23 lacks IMU/contact | Cannot separate body instability from joint tracking using t23 alone | HIGH | 1 |
| Action scaling | `action_scale=0.5` | At high speed, larger actions may hit joint limits or produce excessive swing | MEDIUM | 2 |
| Joint limits | Position targets clamped by `rl_x1.yaml` | High-speed policy may spend time near clamp, causing tracking mismatch | MEDIUM | 2 |

## Predicted Failure Modes

| Failure mode | Expected evidence | First diagnostic |
|---|---|---|
| Phase lag instability | `pos_des_raw -> pos` lag grows above `80~120 ms`; instability appears earlier with `cycle_time=0.55/0.45` | Compare same command under different cycle_time, same controller |
| Swing foot placement miss | Hip/knee target large, actual delayed; touchdown occurs with high residual joint error | t27 event windows: touchdown-350 ms to touchdown+100 ms |
| Roll channel collapse | Hip roll command does not realize; IMU roll grows before fall | IMU roll + hip_roll tracking + left/right stance split |
| Touchdown impact amplification | Ankle tau/effort spike, IMU gyro spike, foot slap at instability onset | touchdown window ankle pitch/roll and effort |
| Command-chain issue | cmd jumps, residual joystick noise, or command not matching intended ramp | Log `/cmd_vel_limiter` with timestamps |

## Stage Priority

1. `high_speed_boundary_and_logging`: find stable boundary and capture full evidence.
2. `phase_and_execution_delay_identification`: quantify lag by joint group and speed.
3. `roll_lateral_authority_check`: verify hip roll / body roll pathway.
4. `touchdown_contact_check`: only if evidence points to ankle/contact.
5. `parameter_ablation`: one variable at a time after the above is quantified.
