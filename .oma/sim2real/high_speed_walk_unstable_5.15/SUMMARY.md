# Sim2Real Current Summary — high_speed_walk_unstable

更新日期: `2026-05-15`

## 当前状态

`high_speed_walk_unstable` 已作为新的 standalone `$deploy` 问题启动。

上游 gate 状态:

- `.oma/standalone.json` 存在，按 Standalone Mode 继续。
- `.oma/best.json` 缺失，deploy gate 作为 advisory warning，不阻断。
- 团队已完成前序开发与训练，本轮只处理真机高速行走不稳的 sim2real 问题。

## 问题定义

自研算法在高速行走时不稳定。当前需要在不先改策略的前提下，区分问题来自:

1. 高速命令下关节执行链跟踪能力不足。
2. `cycle_time` / 相位节律与真实机器人响应带宽不匹配。
3. 髋膝高动态摆动导致支撑切换不稳。
4. 上一轮踝关节修复在高速接触工况下仍有残余耦合风险。
5. 机身姿态、接触、速度估计或命令输入链路问题。

## 当前部署基线

来源:

- 部署合同: `.oma/deploy_info.json`
- 控制配置: `src/module/control_module/cfg/rl_x1.yaml`
- 控制器: `src/module/control_module/src/rl_controller.cc`
- 当前策略: `src/module/control_module/policy/rl_walk_leg.onnx`

当前 `rl_walk_leg` 关键参数:

| 项目 | 当前值 |
|---|---:|
| 控制频率 | `1000 Hz` |
| 推理频率 | `100 Hz` (`decimation=10`) |
| `action_scale` | `0.5` |
| 当前启用 `cycle_time` | `0.7 s` |
| 备用高速 `cycle_time` 注释 | `0.55 s` for `1.2 m/s`, `0.45 s` for `1.35 m/s` |
| 当前踝关节 `kp/kd` | `30 / 1.5` |
| 踝关节控制路径 | parallel joints torque command |

## 已有初筛证据

现有新数据:

- `test_logs/data_csv/t23_joint_20260515_104435.csv`
- 初筛报告: `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t23_joint_tracking_summary.md`
- 新增 sim/real 对比数据:
  - sim: `test_logs/data_csv/t23_joint_20260515_1_sim.csv`
  - real: `test_logs/data_csv/t23_joint_20260515_1_real.csv`
  - 报告: `.oma/sim2real/high_speed_walk_unstable_5.15/results/round_00b_t23_sim_real_compare.md`

t23 只包含关节目标、位置、速度，不包含速度命令、IMU、接触、里程计或跌倒事件。因此它只能回答“高速目标下执行链是否紧张”，不能单独解释“为什么不稳”。

当前 t23 初筛结论:

| 观察 | 证据 | 初步含义 |
|---|---|---|
| 最大 RMS 跟踪误差集中在髋/膝 | `left_hip_pitch=0.717 rad`, `right_hip_pitch=0.622 rad`, `right_knee=0.591 rad` | 高速问题不能只沿用上一轮踝关节归因，髋膝摆动与支撑切换需要重点看 |
| 髋 roll 的目标幅值大但实际幅值很小 | `left_hip_roll pos/target=0.143`, `right_hip_roll=0.164` | 可能存在高速横向稳定控制跟不上或目标被限幅/实际响应不足 |
| 多个关节估计延迟在 `80~150 ms` | 髋/膝多项 delay estimate 落在此范围 | 对 `cycle_time=0.55/0.45 s` 的高速步态可能已经吃掉较大相位裕度 |
| 踝关节不是 t23 中最大误差来源 | 踝 pitch/roll RMS 低于髋 pitch/roll 与右膝 | 踝关节仍要监控，但 Round 1 不应预设踝为唯一根因 |

新增 t23 sim/real 对比结论:

| 观察 | 证据 | 初步含义 |
|---|---|---|
| real 平均跟踪误差高于 sim | mean RMS `0.4205 rad` vs `0.2945 rad` (`1.43x`) | real 执行链在该高速工况下明显更紧张 |
| target-position 相关性在 real 中塌陷 | mean corr `0.757 -> 0.231` | real 不是单纯固定延迟，而是多关节跟随质量下降 |
| 最大 real-minus-sim gap 在髋/膝 | `left_hip_pitch +0.4454 rad`, `right_hip_pitch +0.3806 rad`, `right_knee +0.3321 rad` | HS-01、HS-02 优先级上调 |
| sim/real target 不等价 | real hip_pitch target range 约 `2.47x` sim，hip_yaw 约 `2.37x` sim | 下一轮必须 matched-condition 复采，避免把目标幅值差误判为纯 actuator gap |
| hip_roll 在 sim 和 real 都低响应 | pos/target 约 `0.13~0.15` | roll 通道可能是策略/限幅/映射共性问题，不是 real-only gap |

## 当前假设

| ID | 假设 | 优先级 | 需要的下一步证据 |
|---|---|---|---|
| HS-01 | 高速不稳主因是髋/膝执行链相位滞后和幅值跟踪不足 | HIGH | t27 完整日志中 `pos_des_raw -> pos` delay、目标幅值、支撑/摆动窗口统计 |
| HS-02 | `cycle_time` 降到 `0.55/0.45 s` 后，真实执行延迟导致相位裕度不足 | HIGH | 同一速度命令下比较 `cycle_time=0.7/0.55/0.45` 的稳定边界 |
| HS-03 | 高速下 lateral/roll 通道不足导致机身 roll 增长并触发失稳 | HIGH | IMU roll/pitch、hip_roll 目标/实际、左右支撑期对比 |
| HS-04 | 踝关节 `30/1.5` 对低速已改善，但高速 touchdown 仍可能产生接触冲击放大 | MEDIUM | touchdown 前后 150 ms 的 ankle pitch/roll、effort/tau、IMU gyro |

## 当前不建议

- 不建议直接切到注释中的 `1.2 m/s` 或 `1.35 m/s` 参数并反复试跑。
- 不建议先调踝 `kp/kd`，除非 Round 1 完整日志显示 touchdown 冲击或踝 torque saturation 是首要触发点。
- 不建议只用 t23 关节日志下结论；高速不稳必须同时看命令、机身姿态和接触事件。

## 最新 t27 结果

数据:

- `test_logs/data_csv/t27_joint_20260518_1_real.csv`
- 报告: `.oma/sim2real/high_speed_walk_unstable_5.15/results/round_01c_t27_kpkd_45_real_diagnostic.md`
- 表格: `.oma/sim2real/high_speed_walk_unstable_5.15/tables/t27_20260518_1_real_diagnostic/t27_joint_diagnostic_summary.md`

当前配置:

- stiffness: `[45,45,45,80,30,30] x2`
- damping: `[3,3,4,10,1.5,1.5] x2`
- `cycle_time=0.55`

关键结论:

- `right_hip_roll` 相比 E1 的正向 target 饱和已经缓解，但仍几乎不跟随: RMS `0.3894`, pos/target `0.149`, corr `0.018`。
- `left_hip_roll` 成为更强信号: upper hit `59.6%`, pos/target `0.114`, effort p95 `33.675`。
- 零 yaw 命令下 yaw range `0.736 rad`，gyro z p95 `1.288 rad/s`。
- left/right contact fraction `0.136/0.669`，接触检测或真实接触明显不对称。
- hip_pitch 仍有较大执行压力: group RMS `0.4953`, delay 约 `130 ms`。

## 最新 target-hit / pos-following 结论

资料:

- 方案: `.oma/sim2real/high_speed_walk_unstable_5.15/plans/round_01d_all_joint_target_hit_pos_following.md`
- 结果: `.oma/sim2real/high_speed_walk_unstable_5.15/results/round_01d_all_joint_target_hit_pos_following.md`

分类:

- clamp dominated: `right_ankle_pitch_joint` hit `66.0%`, `left_hip_roll_joint` hit `61.7%`, `left_ankle_pitch_joint` hit `25.5%`。
- low realization without clamp: `right_hip_roll_joint` pos/target `0.149`, `left_hip_pitch_joint` `0.177`, `right_hip_pitch_joint` `0.248`。
- weak timing/shape correlation: `right_hip_roll_joint` corr `0.018`, `right_knee_pitch_joint` `0.135`, `left_hip_yaw_joint` `0.199`, `left_ankle_pitch_joint` `-0.083`。

该结果强化了“不要直接整体加 Kp”的判断。下一轮需要分开验证 target 生成、接触/yaw 耦合和执行链 realization。

## 下一步

- 不建议继续直接增大 hip_roll Kp。
- 优先复测 `cycle_time=0.7`、同样 `cmd_x=0.4`，判断 `0.55 s` 周期是否触发 yaw/contact 不对称。
- 下一轮必须同时看 yaw range、left/right contact fraction、left_hip_roll upper-hit、right_hip_roll corr、right_hip_pitch RMS/delay。
