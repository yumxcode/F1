# Round 1 High-Speed Boundary and Logging Plan

目标: 在不先改策略的前提下，找到当前部署参数的稳定速度边界，并采集足够完整的日志来定位高速不稳的 onset。

## 固定基线

| 项目 | 固定值 |
|---|---|
| Policy | `src/module/control_module/policy/rl_walk_leg.onnx` |
| Config | `src/module/control_module/cfg/rl_x1.yaml` |
| Controller | `rl_walk_leg` |
| Control Hz | `1000` |
| Inference Hz | `100` |
| `action_scale` | `0.5` |
| 当前踝 `kp/kd` | `30 / 1.5` |
| 初始 `cycle_time` | `0.7 s` |

Round 1 不做多参数随机试错。每次只改变一个变量: 速度命令或 `cycle_time`。

## 测试前检查

| 检查项 | 要求 |
|---|---|
| 安全保护 | 吊保护或随时可扶持，操作员明确 e-stop |
| 地面 | 同一平整地面，记录摩擦条件 |
| 电池/温度 | 电量充足，电机温升不过高 |
| 标零 | 沿用上一轮修正后的 ankle pitch offset |
| 配置快照 | 保存 `rl_x1.yaml`、policy hash、commit hash |
| 视频 | 侧面 + 正面或斜前方，视频时间与日志时间尽量对齐 |

## 必需日志

必须至少采集:

| 日志 | 必需字段 |
|---|---|
| `t27` 或等价完整诊断 | timestamp, phase, cmd, action, pos, vel, effort, pos_des_raw, pos_des_lpf, tau_des_raw, tau_des_lpf, is_parallel |
| IMU | roll/pitch/yaw 或 quat, angular velocity |
| cmd | `/cmd_vel_limiter` 实际进入 controller 的 vx/vy/wz |
| joint state | 12 leg joints pos/vel/effort |
| video marker | 每次速度档位开始/结束时间，失稳时间点 |

只采 `t23_joint` 不够。t23 可保留，但不能作为唯一数据。

## 速度阶梯

先在 `cycle_time=0.7 s` 下找当前参数边界:

| Step | `vx` command | Hold | 通过条件 |
|---|---:|---:|---|
| 1 | `0.20 m/s` | `8 s` | 无明显 roll/pitch 发散，无连续打滑 |
| 2 | `0.40 m/s` | `8 s` | 同上 |
| 3 | `0.60 m/s` | `8 s` | 同上 |
| 4 | `0.80 m/s` | `8 s` | 同上 |
| 5 | `1.00 m/s` | `6 s` | 同上；若出现明显不稳，停止 |
| 6 | `1.20 m/s` | `5 s` | 只在 Step 5 稳定后执行 |

若团队定义的“高速”是 `1.35 m/s`，不要直接跳到 `1.35`；先确认 `1.20` 是否稳定。

## `cycle_time` 对比

只有在 `cycle_time=0.7` 下完成边界后，才做 `cycle_time` 对比:

| Case | `cycle_time` | 用途 |
|---|---:|---|
| A | `0.7` | 当前启用基线 |
| B | `0.55` | 配置注释中的 `1.2 m/s` 节律 |
| C | `0.45` | 配置注释中的 `1.35 m/s` 节律，只在 B 稳定后测 |

对比速度只选边界附近的 1 到 2 个速度档，不做全量扫。

## 观察项

| 观察项 | 指标 |
|---|---|
| 髋/膝执行链 | `pos_des_raw -> pos` lag, RMS error, target range, pos/target |
| 横向稳定 | IMU roll 增长率, hip_roll tracking, 左右 stance 差异 |
| touchdown 质量 | touchdown 前后 `-150 ms .. +150 ms` 的 ankle/hip/knee error 和 IMU gyro spike |
| 相位裕度 | instability 是否随 `cycle_time` 缩短明显提前 |
| 限幅 | joint limit clamp 或 target range 长时间贴边 |

## 通过 / 失败标准

| 结果 | 判定 |
|---|---|
| 通过 | 某速度档完整 hold，无明显姿态发散、无 e-stop、无跌倒趋势 |
| 部分通过 | 可短时通过但 roll/pitch 或 joint error 随步数累计 |
| 失败 | 出现持续发散、脚底打滑不可恢复、明显 foot slap 后姿态失控、操作员需要 e-stop |

## 立即停止条件

- 机身 roll 或 pitch 明显超过安全阈值并继续增大。
- 任何关节接近机械限位或出现异常声响。
- 足底连续打滑或落脚后无法恢复。
- 电机过热、异常电流、操作员判断不安全。

## Round 1 结果模板

结果文件写到:

`results/round_01_high_speed_boundary_and_logging.md`

必须包含:

| 字段 | 内容 |
|---|---|
| 每个速度档结果 | pass / partial / fail, 失稳时间点 |
| 参数快照 | policy, yaml, `cycle_time`, `action_scale`, `kp/kd` |
| 日志路径 | t27, imu, cmd, t23, video |
| 首个失稳事件 | 速度、步数、视频时间、日志时间 |
| 初步归因 | phase lag / hip-knee tracking / roll authority / ankle touchdown / command-chain |

## Round 1 后的决策

| 证据 | 下一步 |
|---|---|
| 髋/膝 lag 主导 | 建立 `phase_and_execution_delay_identification` 计划 |
| roll 发散主导 | 建立 `roll_lateral_authority_check` 计划 |
| touchdown 冲击主导 | 复用上一轮 ankle/contact 方法，建立高速 touchdown 分析 |
| `cycle_time=0.55/0.45` 明显更差 | 暂停高速节律，回到设计侧检查训练节律与真实延迟 |
| cmd 或 IMU 链路异常 | HOLD，先修配置/传感器链路 |
