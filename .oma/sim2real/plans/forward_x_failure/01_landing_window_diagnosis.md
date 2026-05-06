# Round 3 摆腿清高与落地窗口联合诊断方案

状态：`done`。本轮由真机数据仿真回放的新现象触发：机器人无法前进行走时，脚踝落地瞬间脚底板没有调整到位，表现为斜着落地；后续结果已确认当前第一阻塞项是 `severe_foot_flat_touchdown`。摆腿清高、髋膝时序和执行链问题作为并发问题保留，但不再作为当前第一入口。

统一进展和指标口径见 [00_forward_x_failure_progress_review.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/00_forward_x_failure_progress_review.md:1)。

## 结论先行

现有试验计划需要再次修改。此前 Round 2C 主要验证静态触地阶跃下的踝关节 `kp/kd`、接触阈值与 timing；这能解释“触地后跟踪退化”，但不能直接证明 walking 中“摆动脚是否抬够、是否过早触地、落地前脚底板是否调平”。新现象把诊断重点从单纯 touchdown 前 `100~150 ms` 扩展到完整 swing-to-touchdown 窗口：

- 辨识单轴可能可收敛，但 walking 中摆动脚仍抬不够或落地仍调不平
- 优先怀疑髋/膝 swing 输出幅度不足、髋/膝摆动相位错误、膝关节伸展过早、RL walking torque 路径、LPF 相位滞后、接触时序、策略输出相位或落地前踝关节目标不足
- 不应继续只靠静态 ground 阶跃扫 `kp/kd`

因此低速行走验证前必须插入本轮摆腿清高与落地窗口联合诊断。

## 本轮核心假设

H1：策略在落地前给出的踝关节 `pos_des` 本身没有把脚底板调平。

H2：策略给出了正确 `pos_des`，但 `q` 跟不上，原因是踝关节 torque 路径、`kp/kd`、力矩上限或接触前速度导致响应不足。

H3：`pos_des` 与 `q` 的误差不大，但 LPF 或控制链延迟使调平动作晚于触地发生。

H4：单轴辨识看似可用，但实际脚底板姿态由 pitch/roll 耦合决定，落地时组合姿态仍斜。

H5：接触检测或步态相位与真实触地不对齐，策略预期的 touchdown 时刻晚于真实落地。

H6：摆动脚相对支撑脚高度差不足，`foot_clearance` 在摆腿中期没有形成峰值，导致脚提前接近地面并截断前向推进。

H7：髋关节或膝关节摆动时机不对，例如髋 pitch 前摆峰值太晚、膝 pitch 屈曲峰值太小或伸膝太早，导致落地前双脚高度差不够。

H8：策略给出了足够的髋/膝摆动目标，但实际 `q` 跟不上，主因是髋/膝刚度、阻尼、限幅、速度限制或控制链延迟，而不是策略步态本身。

## 必须记录的信号

以左右脚分别记录，重点截取每次摆腿中期到触地后的窗口。建议窗口为 `[-350 ms, +100 ms]`，其中 touchdown 前 `150 ms` 仍保留为踝调平重点窗口：

| 类别 | 信号 | 用途 |
|---|---|---|
| 命令 | policy action 原始值 | 判断策略是否要求抬腿、摆腿和调平 |
| 命令 | hip/knee/ankle `pos_des`（LPF 前） | 判断策略目标幅度和相位是否足够 |
| 命令 | hip/knee/ankle `pos_des_lpf` 或实际下发目标 | 判断 LPF/控制链延迟和幅值削弱 |
| 状态 | hip/knee/ankle `q` / `dq` | 判断实际跟踪与响应速度 |
| 输出 | hip/knee/ankle `tau_des` / effort cmd | 判断是否打到力矩瓶颈、速度瓶颈或方向错误 |
| 相位 | `phase_sin/cos` 或 phase 标量 | 对齐策略步态相位 |
| 接触 | 左右脚 contact state / 估计接触时刻 | 定义 touchdown |
| 姿态 | base roll/pitch/yaw、角速度 | 判断机体姿态是否提前偏移 |
| 足底 | 足底板 pitch/roll 或由脚部 link 姿态计算的 sole normal | 直接量化斜着落地 |
| 足高 | 左右足底世界系高度 `foot_z_l/r` | 直接量化双脚高度差和摆动脚清高 |
| 运动学 | 髋 pitch、膝 pitch、踝 pitch 对 foot_z 的贡献 | 区分髋/膝幅度不足、伸膝过早和踝补偿不足 |

如果当前日志没有足底板姿态，应在仿真回放侧从足部 link quaternion 计算：

- `sole_pitch_at_touchdown`
- `sole_roll_at_touchdown`
- `sole_normal_z`
- `foot_flat_error = sqrt(sole_pitch^2 + sole_roll^2)`
- `left_foot_z` / `right_foot_z`
- `swing_foot_clearance = swing_foot_z - stance_foot_z`
- `max_swing_clearance`
- `clearance_at_touchdown_minus_50ms`
- `clearance_peak_phase`

## 测试数据来源

优先使用已经发现问题的真机日志进行回放分析，不先上新真机试验。

最低输入：
- 一段“无法前进行走且斜着落地”的真机日志
- 对应的仿真回放输出或可复现脚底姿态的回放脚本
- 控制器下发的 hip/knee/ankle 命令与实际关节状态

如果日志缺少命令链信号，则先补日志，不进入下一轮步态。

## 分析流程

1. 找出每只脚连续 `5~10` 次 touchdown，并标注前一脚离地或摆腿开始时刻。
2. 对每次 touchdown 截取 `[-350 ms, +100 ms]` 窗口；其中 `[-350 ms, -80 ms]` 用于摆腿清高，`[-150 ms, 0 ms]` 用于落地调平。
3. 计算摆腿窗口内的：
   - `max_swing_clearance`
   - `clearance_peak_phase`
   - hip pitch / knee pitch 的 `pos_des` 峰值、`q` 峰值、峰值时间
   - knee flexion peak 到 touchdown 的时间差
   - swing foot 前向位移与 `cmd_x` 的对应关系
4. 计算触地前 `100 ms / 50 ms / 20 ms / 0 ms` 的：
   - `foot_flat_error`
   - `swing_foot_clearance`
   - hip/knee/ankle `pos_des - q`
   - ankle pitch/roll `pos_des - q`
   - `pos_des_lpf - pos_des_raw`
   - `tau_des` 峰值与方向
5. 将每次 touchdown 分成：
   - `foot_clearance_deficit`：摆动脚高度差不足或峰值过低
   - `hip_knee_command_low`：策略给出的髋/膝目标本身幅度不足
   - `hip_knee_tracking_lag`：髋/膝目标足够但实际关节跟不上
   - `early_knee_extension`：膝关节过早伸展导致脚提前接近地面
   - `command_not_flat`：`pos_des` 已经对应斜脚
   - `tracking_lag`：`pos_des` 基本正确，但 `q` 未到位
   - `filter_delay`：raw 命令正确，但 LPF 后目标明显滞后
   - `phase_mismatch`：调平动作发生在触地后
   - `coupled_geometry`：单轴误差小，但足底组合姿态仍斜
6. 输出左右脚、髋/膝/踝分轴统计，并给出每个 touchdown 的主导阻塞项。

## 判据

| 判因 | 判据 | 下一步 |
|---|---|---|
| `command_not_flat` | 触地前 `50 ms` 的 `pos_des` 已不能让足底接近平 | 回到策略/观测/奖励设计，不再部署侧硬调 |
| `tracking_lag` | `pos_des` 足够但 `q` 落后，且 effort 未明显饱和 | 优先回到 Round 2C 的对应关节 `kp/kd` 与 timing 修复 |
| `effort_limited` | `pos_des` 足够但 effort 长时间顶住或受限 | 查驱动限幅、力矩模式、接触前速度，不能只加 `kp` |
| `filter_delay` | raw 目标提前，但 LPF 后目标晚到 | 建立 `lpf_conf.wc` 小步试验，优先测踝轴 |
| `phase_mismatch` | 调平动作系统性晚于真实 touchdown | 查 phase/contact 估计与策略步态周期，必要时调 `cycle_time` 或进入设计反馈 |
| `coupled_geometry` | ankle 单轴误差小但 foot_flat_error 大 | 查并联踝几何映射、左右足底/杆长/零位标定 |
| `foot_clearance_deficit` | 摆腿中期 `max_swing_clearance` 不足，或触地前 `50 ms` 摆动脚与支撑脚高度差已经接近 0 | 暂停低速复测，进入髋/膝摆腿专项，先判定命令不足还是跟踪不足 |
| `hip_knee_command_low` | hip/knee `pos_des` 没有形成足够抬腿组合，实际 `q` 基本跟随 | 回策略/奖励/观测设计反馈，重点检查足高奖励、摆腿轨迹、相位条件 |
| `hip_knee_tracking_lag` | hip/knee `pos_des` 足够，但 `q` 峰值不足或峰值晚于命令，effort 未长期饱和 | 做髋/膝 `kp/kd`、速度限制、控制延迟专项，不直接改 `action_scale` |
| `early_knee_extension` | 膝 pitch 在 touchdown 前过早回伸，导致足高提前下降 | 查策略相位、cycle_time 和膝关节目标时序，必要时进入设计反馈 |

建议暂定可接受阈值：
- 摆腿中期：`max_swing_clearance >= 0.04 m`，或至少明显高于支撑脚足底高度；实际阈值需用正常步态回放校准
- 触地前 `50 ms`：摆动脚仍应保留可观察的正清高，不能已与支撑脚等高后拖向地面
- 触地前 `20 ms`：`foot_flat_error <= 0.05 rad`
- 触地瞬间：`abs(pos_des - q) <= 0.03 rad`
- 调平动作峰值不得系统性晚于 touchdown

上述阈值只是本轮诊断阈值，不作为最终硬件通过标准。

## 对现有计划的修改

- Round 2C 保留，但只解决已经明确的单轴触地 timing / 振荡 / 阈值问题。
- Round 3 改为本文件的摆腿清高与落地窗口联合诊断，不再直接低速行走验证。
- 原 [02_low_speed_walk_validation_candidate.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/02_low_speed_walk_validation_candidate.md) 降级为下一阶段候选；后续 `05/12/13` 已把进入门槛进一步收紧为先完成 `05D FK Foot-Frame / Contact` 现场复核。

## 本轮结束条件（已全部达成 ✅）

- ✅ 已分析左右脚各 7/8 次 touchdown（Round 3 日志，`7/7` → 后续 `8/8`）
- ✅ 已输出每次 touchdown 的 `max_swing_clearance`、触地前指标和 `foot_flat_error`（见 [results/02_round3_landing_window_diagnosis.md](../../results/forward_x_failure/02_round3_landing_window_diagnosis.md)）
- ✅ 主导判因已确定：`severe_foot_flat_touchdown` 为主因（`8/8`），`foot_clearance_deficit` 和 `hip_knee_tracking_lag` 作为并发问题保留
- ✅ 下一步已明确为：新建踝落地姿态专项（即 `03_ankle_landing_attitude_resolution`），不直接进入低速行走复测

> 本轮执行结果详见 [results/02_round3_landing_window_diagnosis.md](../../results/forward_x_failure/02_round3_landing_window_diagnosis.md)
