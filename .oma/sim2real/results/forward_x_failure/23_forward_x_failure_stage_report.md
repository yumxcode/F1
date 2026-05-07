# 23 Forward X Failure Stage Report

日期：2026-05-06

本文件是 `forward_x_failure` 问题的阶段性总结汇报，基于当前已完成的 real / sim 数据分析、审计修正和一致性清理。

## 1. 总体问题

真机在给定 x 轴前进指令时无法形成稳定前向推进，主要表现为：

- 原地踏步或前进不足。
- 视觉上 touchdown 附近脚掌存在 roll 方向先触地 / 抖动。
- 降低 ankle `kp` 后，roll 方向抖动减轻，原地踏步更稳定，但仍不能恢复前向推进。

当前不能再把问题简单表述为：

- “roll 外翻就是主因”
- “output 延迟导致不前进”
- “单纯 ankle `kp/kd` 不合适”
- “sim 也复现了同样 failure”

当前统一判断是：

> real 的 touchdown 几何 / 接触残差已经越过 sim 稳定前走时的可接受包络，并与执行链 `state -> joint -> sole` 残差放大叠加；高 `kp` 进一步把这种越界残差表现成 swing / touchdown 阶段更重的真实 joint 抖动，尤其 touchdown 最明显，最终破坏有效支撑和前向推进。

## 2. 已做分析

### 2.1 Real 分析

| 编号 | 分析内容 | 主要产物 | 当前读法 |
|---|---|---|---|
| `01/02` | landing window / 清高 / touchdown 事件诊断 | [02_round3_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/02_round3_landing_window_diagnosis.md:1) | pre-audit raw FK 口径，旧 `8/8 severe` 已降级；窗口化诊断仍有参考价值 |
| `03` | ankle touchdown 姿态与三层判因 | [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/03_ankle_landing_attitude_resolution.md:1) | 旧 `8/8 roll` / `command_not_flat 4` 已降级；校准后 real 为 `pitch 6/8, roll 2/8` |
| `04` | ankle `kp/kd` / tracking lag 修复尝试 | [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/04_tracking_lag_repair.md:1) | 单轴调参不能关闭问题，只会转移表现；停止盲扫 `kp/kd` |
| `05A/05B/05C` | geometry / mapping / contact residual 分类 | [05_coupled_geometry_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/05_coupled_geometry_probe.md:1) | 旧 `fk_foot_frame_residual_candidate 3/4` 强收口已降级；下一步必须先做 `05D` |
| `06` | delay chain | [06_delay_chain_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/06_delay_chain_probe.md:1) | `action -> target` 近似 0，output 不是主瓶颈 |
| `07/08/09` | windowed roll origin / phase lag / limit cycle | [09_phase_lag_limit_cycle_compare_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/09_phase_lag_limit_cycle_compare_t27.md:1) | `sole_roll` 更偏执行链响应；高 `kp` 放大局部相位滞后，但未形成稳定限环 |
| `10/11/12` | execution chain / actuator-state / realization | [19_real_vs_sim_execution_chain_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/19_real_vs_sim_execution_chain_compare.md:1) | 主问题不在 output；real 主滞后更靠近 `state -> joint`，且 swing 期已存在 |
| `13` | swing 小信号 dead-zone audit | [13_dead_zone_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/13_dead_zone_audit.md:1) | 解释一部分 swing lag，不解释 touchdown contact residual |
| `16` | real 旧结论审计 | [16_real_round3_logic_audit_after_sim_contrast.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/16_real_round3_logic_audit_after_sim_contrast.md:1) | 确认旧 `03/05` 受到 raw FK foot-frame 偏置污染 |

### 2.2 Sim 分析

| 编号 | 分析内容 | 主要产物 | 当前读法 |
|---|---|---|---|
| `15` | sim `03/06` 初版分析 | [15_sim_t27_03_06_analysis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/15_sim_t27_03_06_analysis.md:1) | 已被 `17` supersede；旧 sim `severe / command_not_flat` 读法失效 |
| `17` | sim 视频事实复审 | [17_sim_round3_reaudit_with_video_fact.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/17_sim_round3_reaudit_with_video_fact.md:1) | sim 多 `kp/kd` 均能正常前走，仅左脚轻微 roll 外翻，无明显抖动 |
| `18` | real vs sim residual 包络 | [18_real_vs_sim_residual_acceptance_comparison.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/18_real_vs_sim_residual_acceptance_comparison.md:1) | sim 定义“可接受 residual 包络”；real 明显越界 |
| `19` | real vs sim execution chain | [19_real_vs_sim_execution_chain_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/19_real_vs_sim_execution_chain_compare.md:1) | sim 也有 imperfect realization，但仍可前走；real residual 已进入 failure 区 |
| `20` | real vs sim joint adjustment/jitter | [20_real_vs_sim_joint_jitter_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/20_real_vs_sim_joint_jitter_compare.md:1) | 新 kinematic touchdown 窗口下，real 的 joint range/path/track err 仍更大，roll touchdown 最明显；pitch touchdown 高频结论降级 |
| `24/25` | touchdown detector audit / gait period | [24_touchdown_gait_period_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/24_touchdown_gait_period_compare.md:1), [25_kinematic_touchdown_detector_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/25_kinematic_touchdown_detector_audit.md:1) | 旧 ankle-pitch 低速 contact proxy 会误触发；新 FK+hip detector 恢复 real 前 4 次正常交替，并使 real/sim 周期一致 |
| `21/22` | 合并结论与一致性审计 | [21_real_vs_sim_combined_conclusion.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/21_real_vs_sim_combined_conclusion.md:1), [22_forward_x_failure_consistency_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/22_forward_x_failure_consistency_audit.md:1) | 当前 canonical 口径 |

## 3. 推理链条与阶段结论

### Step 1: 初始现象锁定

真机低速前进时不形成有效 x 方向推进，同时 touchdown 附近出现脚掌 roll 方向异常和抖动。早期通过 landing window / ankle attitude 分析，把问题指向 touchdown 脚底姿态异常、执行链跟踪不足和几何 / 接触 residual。

阶段结论：

- 真机 failure 现象成立。
- 问题集中在 swing-to-touchdown 到支撑建立阶段。
- 不适合直接进入低速复测。

### Step 2: `kp/kd` 修复尝试

对 ankle `kp/kd` 做过多组尝试后发现：

- 降低 `kp` 可以明显减轻 roll 方向抖动。
- 但即使抖动减轻，机器人仍不能恢复前向推进。
- 单轴 right-roll 扫参会让旧标签在 `tracking_lag / filter_delay / coupled_geometry / command_not_flat` 之间迁移，而不是关闭问题。

阶段结论：

- `kp` 更像抖动放大器，不是根因。
- 不应继续把大范围 `kp/kd` 扫参作为第一入口。

### Step 3: 执行链分析

`06/10/11/12/19` 逐步把执行链拆开：

- `action -> target` 近似 0，output 发布链不是主瓶颈。
- real 更明显的滞后靠近 `state -> joint`。
- `state -> joint` lag 在 swing 期已经存在，不是 touchdown 才突然出现。
- 左右不对称明显，但慢侧不固定，不能简单定性为固定单侧硬件故障。

阶段结论：

- real 的执行链兑现不健康，是重要并发放大因素。
- 但执行链 lag 单独解释不了 touchdown residual 和 forward failure。

### Step 4: Sim 数据复审推翻旧强结论

今天对 sim 多 `kp/kd` 工况重新审查后确认：

- sim 多个 `kp/kd` 工况均能正常往前走。
- sim 视觉上只有左脚轻微 roll 外翻。
- sim swing / touchdown 无明显抖动。
- 旧版 sim `03/06` 将多个 case 判成 `severe_foot_flat_touchdown / command_not_flat`，与视频事实冲突。

进一步审计发现：

- 旧版 `03` 直接把 raw FK foot-frame 姿态当真实脚底平面。
- 固定 frame 偏置污染了旧 `8/8 severe`、`8/8 roll dominant`、`mean 1.6~1.9 rad` 等强结论。
- 校准后 real `03` 变为 `pitch 6/8, roll 2/8`，root counts 为 `coupled_geometry 3 / command_not_flat 3 / tracking_lag 1 / residual_not_large_enough 1`。

阶段结论：

- sim 没有 `forward_x_failure`。
- sim 的轻微左脚外翻是“可接受 residual”，不是 failure 证据。
- real 的问题必须解释为“为什么 residual 越过 sim 可接受包络”，而不是“为什么有 roll 外翻”。

### Step 5: Real vs Sim residual 对照

`18` 用 sim 稳定前走状态定义了可接受 residual 包络，再与 real 对比：

- sim 左脚允许轻中度 roll residual，仍能前走。
- sim 右脚大多接近水平。
- real 相比 sim 的明确超限项包括：
  - 双侧 `pitch residual` 系统性偏大。
  - 右脚不再接近水平。
  - 左脚 roll 峰值偏大。
  - `joint -> sole` residual 放大链过重。

阶段结论：

- real 不是“比 sim 多一点 roll 外翻”。
- real 是 touchdown residual 整体越过了 sim 可接受包络。

### Step 6: Real vs Sim joint jitter 对照

`20` 对比 ankle `roll/pitch` 的 `pos_des_raw` 和 `pos`。本节已基于 `24/25` 的新 kinematic touchdown detector 重跑；判定不只看高频 `hp_rms`，还看调整幅值 `range`、总调整量 `path_length` 和方向变化频率：

| axis/window | joint hp real/sim | joint range real/sim | joint path real/sim | joint dir-rate real/sim |
|---|---:|---:|---:|---:|
| roll `swing` | `3.22x` | `2.94x` | `3.90x` | `1.18x` |
| roll `touchdown` | `1.76x` | `2.08x` | `2.26x` | `0.80x` |
| pitch `swing` | `1.28x` | `1.43x` | `1.50x` | `1.08x` |
| pitch `touchdown` | `0.74x` | `1.69x` | `1.23x` | `0.57x` |

阶段结论：

- real swing 和 touchdown 的共同点是 `range/path/track err` 更大，说明 real joint 调整负担和兑现误差仍高于 sim。
- roll touchdown 仍是最重异常点，但数值从旧 contact proxy 口径下的 `4.56x/4.93x/5.33x` 降为新 kinematic 口径下的 `1.76x/2.08x/2.26x`。
- pitch touchdown 高频结论降级：`joint hp` 和方向变化频率不高于 sim，但 `range/path/track err` 仍高于 sim。
- 因此“抖动”后续应拆成高频抖动、调整幅值、调整频率三个维度，不再用单一 `hp_rms` 代表全部现象。
- real touchdown 期不仅 residual 更大，真实 joint 高频抖动也更重。
- 这支持“高 `kp` 是放大器，主因仍是 residual 越界 + 执行链兑现残差”的判断。

## 4. 当前统一结论

当前最稳妥的阶段性结论是：

1. sim 不存在 `forward_x_failure`。sim 多 `kp/kd` 工况能正常前走，仅左脚轻微外翻，无明显抖动。
2. real 确实存在 `forward_x_failure`。降低 `kp` 能减轻抖动，但不能恢复前向推进。
3. 旧 raw FK foot-frame 直接判定脚底平面的做法已经失效。
4. real 的关键异常不是“看到 roll 触地”，而是 touchdown residual 已经越过 sim 可接受包络。
5. output 链不是第一主因。
6. `kp/kd` 不是第一修复入口。
7. 当前问题应定位为：

> real touchdown residual 越界 + `state -> joint -> sole` 执行链兑现残差 + 高 `kp` 抖动放大，三者叠加后破坏支撑相位和前向推进。

## 5. 接下来应该做什么测试

当前唯一第一优先级是：

**`05D FK Foot-Frame / Contact` 现场复核**

目标：确认 `joint -> sole residual` 的真实物理含义，避免继续优化受 frame 偏置污染的日志指标。

### Test 1: 静态 FK foot-frame 校验

目的：确认 MuJoCo FK foot body frame 是否能代表真实脚底接触平面。

执行：

1. 机器人站立或安全悬空。
2. 左右脚分别做小幅 ankle roll / pitch 扫描。
3. 同步记录：
   - `pos_des_raw`
   - `pos`
   - actuator state
   - FK `sole_roll / sole_pitch`
   - 人工测量或视频估计的真实 sole plane roll / pitch
4. 对比 FK 方向、符号、零位偏置和真实脚底平面是否一致。

判据：

- 如果 FK 与真实脚底平面方向一致，进入动态 touchdown 复核。
- 如果 FK 与真实脚底平面存在固定偏置或符号不一致，先修 frame / contact reference，再重跑 residual 分析。

### Test 2: 动态低速 touchdown 复核

目的：确认 real touchdown residual 和 joint adjustment/jitter 是否在真实接触中同步出现。

执行：

1. 使用当前低风险、抖动较低的参数。
2. 只跑短窗口低速行走。
3. 采前 `4~8` 个 touchdown。
4. 同步记录日志和正视 / 侧视视频。
5. 重点窗口：
   - swing: `touchdown - 350ms .. touchdown - 20ms`
   - touchdown: `touchdown - 50ms .. touchdown + 100ms`

必看信号：

- `pos_des_raw`
- `pos`
- actuator state
- `sole_roll / sole_pitch`
- contact state
- phase
- base attitude
- 视频中的真实触地边缘

判据：

- 如果视频真实脚底也 pitch/roll 不平，且方向与 FK 一致，说明 residual 是物理接触问题。
- 如果 FK residual 大但视频脚底不对应，说明 FK / contact frame 定义仍不可信。
- 如果 touchdown 一接触真实 joint 抖动明显放大，优先查接触负载下 actuator / transmission 兑现。

### Test 3: 同轨迹 sim replay

目的：判断 residual 来自策略目标，还是 real 执行 / 接触 / frame。

执行：

1. 尽量把 real 的 command、phase、target 或 touchdown 轨迹回灌到 sim。
2. 在 sim 中复现同样窗口。
3. 对比 sim 是否产生同方向、同量级 `sole_pitch / sole_roll`。

判据：

- sim 也产生同方向 residual：策略 touchdown 姿态目标或模型内几何目标可能有问题。
- sim 不产生，同样轨迹在 real 越界：优先查 real 执行链、contact、frame 或机械兑现。

### Test 4: `05D` 后的修复入口选择

`05D` 完成后再决定修复路径：

| `05D` 结果 | 下一步 |
|---|---|
| FK foot frame 与真实 sole plane 不一致 | 修 MJCF / FK frame / contact reference，再重跑 `03/05/18/20` |
| 真实接触边缘与模型不一致 | 修 foot/contact geometry、接触边缘或 sole reference |
| 接触负载下 joint 抖动 / 回差释放明显 | 进入执行链兑现修复，重点 `state -> joint`、transmission、摩擦 / 回差 |
| sim replay 也复现 residual | 回到策略侧，检查 touchdown 姿态目标、reward、观测和相位 |

## 6. 当前不建议做

1. 不继续盲扫 ankle `kp/kd`。
2. 不把“看到 roll 触地”直接当主因。
3. 不把旧 sim `03/06` 的 `command_not_flat` 当 failure 证据。
4. 不直接用 raw FK foot body 姿态当真实脚底接触平面。
5. 不在 `05D` 前直接改 policy 或大改 action scale / cycle time。

## 7. 汇报结论

当前阶段已经从“真机为什么 roll 触地”推进到更明确的问题：

> sim 允许轻微左脚外翻且能稳定前走；real 的 touchdown residual、执行链兑现残差和高 `kp` 抖动放大共同越界，导致支撑相位无法形成有效前向推进。

因此，下一阶段不应继续调参试错，而应先用 `05D` 钉死 `joint -> sole residual` 的物理含义。只有明确它是真实接触问题、frame 问题、执行链兑现问题，还是策略目标问题后，才进入修复。
