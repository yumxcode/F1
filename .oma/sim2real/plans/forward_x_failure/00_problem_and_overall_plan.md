# X 轴前进指令无法前进：整体问题与方案

状态：`active`。这是当前 sim2real 主问题的入口文件。

## 当前进度速览（2026-05-06 审计后）

| 分类 | 内容 |
|---|---|
| **当前唯一待执行项** | ⬜ `05D FK Foot-Frame / Contact 现场复核`（Phase 0-4，见 [05_coupled_geometry_probe.md](./05_coupled_geometry_probe.md)） |
| **当前阻塞项** | ⏸ `02_low_speed_walk_validation_candidate`，等待 `05D` 完成后才允许执行 |
| **已完成** | ✅ 01 / 03 / 04 / 05A / 05B / 05C / 06 / 07 / 08 / 09 / 10 / 11 / 12 / 13 / 15-21 审计与 real/sim 对照 |
| **当前主结论** | real 的 touchdown residual 已越过 sim 可接受包络，并叠加 `state -> joint -> sole` 执行链残差与高 `kp` 抖动放大；旧 `8/8 severe_foot_flat_touchdown`、旧 sim `command_not_flat` 和旧 `05C fk_foot_frame_residual_candidate 3/4` 均已被审计降级 |

> 统一进展和边界口径见 [results/00_forward_x_failure_progress_review.md](../../results/forward_x_failure/00_forward_x_failure_progress_review.md)；18/19/20 合并结论见 [21_real_vs_sim_combined_conclusion.md](../../results/forward_x_failure/21_real_vs_sim_combined_conclusion.md)；plan/results 一致性审计见 [22_forward_x_failure_consistency_audit.md](../../results/forward_x_failure/22_forward_x_failure_consistency_audit.md)。

## 问题定义

当给定机器人 x 轴前进指令时，机器人无法稳定前进，表现为：

- 原地踏步
- 偶发或持续后退
- 真机数据仿真回放显示，脚踝落地时脚底板没有调整到位，存在斜着落地
- 新增观察：落地时双脚高度差不够，摆动脚没有形成足够离地高度，导致前向步态更像低幅踏步

当前不把问题简化为“单个踝关节 kp/kd 不合适”。现象发生在 walking swing-to-touchdown 窗口，必须同时检查策略命令、髋/膝摆腿幅度、摆动时机、踝关节实际跟踪、LPF/控制链延迟、步态相位和并联踝几何耦合。

## 当前主假设

| 假设 | 含义 | 对应子方案 |
|---|---|---|
| `touchdown_residual_over_sim_envelope` | real touchdown 几何 / 接触残差已经超出 sim 稳定前走时可接受包络，是当前主线 | [21_real_vs_sim_combined_conclusion.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/21_real_vs_sim_combined_conclusion.md:1) |
| `frame_bias_contamination` | 旧 raw FK foot-frame 直接当真实脚底平面的读法污染了 `03/05/15` 的部分强结论 | [16_real_round3_logic_audit_after_sim_contrast.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/16_real_round3_logic_audit_after_sim_contrast.md:1)，[22_forward_x_failure_consistency_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/22_forward_x_failure_consistency_audit.md:1) |
| `execution_chain_residual` | output 不是主瓶颈；real 更明显的问题在 `state -> joint`，且 swing 期已存在 | [19_real_vs_sim_execution_chain_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/19_real_vs_sim_execution_chain_compare.md:1) |
| `touchdown_jitter_amplification` | 新 kinematic touchdown 口径下，real/sim 周期一致；real 仍表现为更大的 roll/pitch joint 调整幅值、路径和 tracking error，roll touchdown 最明显；`kp` 更像放大器 | [20_real_vs_sim_joint_jitter_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/20_real_vs_sim_joint_jitter_compare.md:1)，[24_touchdown_gait_period_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/24_touchdown_gait_period_compare.md:1) |
| `command_not_flat` | 早期三层判因之一；旧 sim/real 强判断已降级，只能作为候选标签而非当前第一修复入口 | [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/03_ankle_landing_attitude_resolution.md:1) |
| `tracking_lag` | 目标有调平意图但真实关节没到位；后续统一读作执行链响应问题，不再单独作为第一修复入口 | [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/04_tracking_lag_repair.md:1)，[11_execution_chain_lag_analysis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/11_execution_chain_lag_analysis.md:1) |
| `tracking_lag_repair` | 已验证单轴 `right_ankle_roll_joint` 扫参不能关闭主问题，只会改变表现形式 | [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/04_tracking_lag_repair.md:1) |
| `filter_delay` | raw 目标提前，但 LPF 后目标晚到，导致调平动作迟到 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `phase_mismatch` | 策略相位/真实 touchdown 不对齐，调平动作发生在触地后 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `coupled_geometry` | 当前专指 touchdown 窗 `joint_pos -> sole` 仍解释不完的 foot-space / contact residual；必须先经 `05D` 验证真实物理含义 | [05_coupled_geometry_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/05_coupled_geometry_probe.md:1) |
| `windowed_roll_origin_probe` | 在腾空窗与 touchdown 窗中，对比 output / target / current / pos 与 `sole_roll` 的对应关系，判断更像输出链还是执行链驱动 | [07_windowed_roll_origin_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/07_windowed_roll_origin_probe.md:1) |
| `windowed_roll_origin_probe_t27` | 基于 t27 单文件诊断日志，在腾空窗与 touchdown 窗中对比 `action / pos_des_raw / pos_des_lpf / pos` 与 `sole_roll` 的对应关系 | [08_windowed_roll_origin_probe_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/08_windowed_roll_origin_probe_t27.md:1) |
| `phase_lag_limit_cycle_compare_t27` | 基于 t27 多组 kp 数据，对比 touchdown 窗内 `lpf -> pos -> sole_roll` 的相位滞后、零交叉和环面积，判断是否存在高 kp 局部相位滞后引发的限环趋势 | [09_phase_lag_limit_cycle_compare_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/09_phase_lag_limit_cycle_compare_t27.md:1) |
| `foot_clearance_deficit` | 摆动脚相对支撑脚高度差不足，落地前已经接近地面，导致前向推进被提前接触截断 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `hip_knee_swing_timing_or_amplitude` | 髋/膝摆动的相位、峰值或伸膝时机不对，导致摆腿清高不足或过早落地 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |

## 当前统一边界

详细统一口径见 [00_forward_x_failure_progress_review.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/00_forward_x_failure_progress_review.md:1)。当前边界固定为：

- `13` 负责 `swing` 期 `pos_des_raw` 小信号死区 / 阈值敏感区。
- `11/12` 负责执行链，尤其是 `actuator_state -> joint_pos` 兑现不足。
- `05` 负责 touchdown 窗最终剩余的 `joint_pos -> sole_roll` foot-space / contact residual。
- `04` 已证明单轴 ankle `kp/kd` 扫参不是当前第一修复入口。

## 方案结构

当前主问题只在 `plans/forward_x_failure/` 下维护：

| 顺序 | 文件 | 作用 | 状态 |
|---|---|---|---|
| 00 | [00_problem_and_overall_plan.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/00_problem_and_overall_plan.md:1) | 当前文件，定义问题、假设、推进顺序 | active |
| 01 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) | 摆腿中期到触地前后窗口诊断，联合判定足高不足、髋/膝时序、踝调平主因 | done |
| 02 | [02_low_speed_walk_validation_candidate.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/02_low_speed_walk_validation_candidate.md:1) | 低速前进复测候选方案，必须等 `05D` 先验证 FK foot frame、再把 touchdown residual 拆成可执行修正项后再评估 | blocked |
| 03 | [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/03_ankle_landing_attitude_resolution.md:1) | 基于 Round 3 结果，专项解决 touchdown 时脚板严重不平 | done |
| 04 | [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/04_tracking_lag_repair.md:1) | 基于 step 试验和 Round 3 跟踪滞后样本，专项验证并修复执行链不足 | done |
| 05 | [05_coupled_geometry_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/05_coupled_geometry_probe.md:1) | 基于前几步有效 touchdown 与参数试验收口结果，专项排查 touchdown residual 的几何/映射偏置；当前推进到 `05D` contact / foot-frame 现场复核 | active |
| 06 | [06_delay_chain_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/06_delay_chain_probe.md:1) | 基于历史多日志拆 `action -> target -> current -> pos` 延迟链 | done |
| 07 | [07_windowed_roll_origin_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/07_windowed_roll_origin_probe.md:1) | 基于延迟链，分腾空窗与 touchdown 窗对比 output / target / current / pos 与 sole_roll 的对应关系 | done |
| 08 | [08_windowed_roll_origin_probe_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/08_windowed_roll_origin_probe_t27.md:1) | 基于 t27 单文件日志，分腾空窗与 touchdown 窗对比 action / pos_des_raw / pos_des_lpf / pos 与 sole_roll 的对应关系 | done |
| 09 | [09_phase_lag_limit_cycle_compare_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/09_phase_lag_limit_cycle_compare_t27.md:1) | 基于 t27 多组 kp 对比 touchdown 窗内相位滞后与环形响应，判断高 kp 是否形成局部限环趋势 | done |
| 10 | [10_execution_chain_disentanglement.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/10_execution_chain_disentanglement.md:1) | 拆解执行链复合延迟与几何镜像偏置；已从代理判定推进到 `/actuator_states` 级别实测确认 | done |
| 11 | [11_execution_chain_lag_analysis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/11_execution_chain_lag_analysis.md:1) | 在 `10` 线收口基础上定位 lag 分段、窗口放大位置和左右踝不对称 | done |
| 12 | [12_parallel_actuation_realization_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/12_parallel_actuation_realization_probe.md:1) | 解释 `actuator_state -> joint_pos` 为什么兑现不足，区分整体慢、间隙、stick-slip 与左右链不一致 | done |
| 13 | [13_dead_zone_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/13_dead_zone_audit.md:1) | 审视 `swing` 期 `pos_des_raw` 的小信号死区贡献，并细化到 `0.05 rad` 分箱 | done |

基础 sim2real 辨识步骤单独放在 `plans/sim2real_steps/ankle_kp_kd/`，作为支撑材料，不再和当前主问题子方案混放。

## 结果文件结构

当前主问题结果只放在 `results/forward_x_failure/`：

| 文件 | 内容 |
|---|---|
| [00_forward_x_failure_progress_review.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/00_forward_x_failure_progress_review.md:1) | 当前主问题统一进展、边界和全局指标字典；后续文档若有歧义，以此文件的边界为准 |
| [01_field_baseline.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/01_field_baseline.md:1) | Round 1 基础链路、站立、RL 小速度初测结果 |
| [02_round3_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/02_round3_landing_window_diagnosis.md:1) | Round 3 touchdown 历史判因结果；旧 `8/8 severe_foot_flat_touchdown` 已被 frame 偏置审计降级，仅作 pre-audit 过程记录 |
| [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/03_ankle_landing_attitude_resolution.md:1) | Round 3A 踝落地姿态历史结果；旧 `8/8 roll dominant` 和 `command_not_flat 4` 不再作为当前修复入口 |
| [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/04_tracking_lag_repair.md:1) | Round 3B 执行链修复历史结果；单轴 `right roll` 扫参表现出 tradeoff，未关闭问题；审计后保留为“不要盲扫 kp/kd”的证据 |
| [05_coupled_geometry_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/05_coupled_geometry_probe.md:1) | Round 3C 几何/映射历史结果；旧 `parallel_mapping_mismatch` / `fk_foot_frame_residual_candidate 3/4` 已降级，当前只保留为 `05D FK Foot-Frame / Contact` 待验证假设 |
| [06_delay_chain_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/06_delay_chain_probe.md:1) | Round 3D 延迟链排查结果；`action -> target` 近似 0 ms，主要延迟出现在 `target/current -> pos` 执行链，且 ankle 不是这份日志里最慢的一组，因此 current 数据更支持“执行链存在延迟，但不足以单独解释 coupled_geometry” |
| [07_windowed_roll_origin_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/07_windowed_roll_origin_probe.md:1) | Round 3E 窗口化 `sole_roll` 来源排查；腾空窗 `3/3`、touchdown 窗 `2/3` 都更偏 `execution_chain_dominant`，说明这份数据里 `sole_roll` 更接近执行链响应，而不是立即的 output 链 |
| [08_windowed_roll_origin_probe_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/08_windowed_roll_origin_probe_t27.md:1) | Round 3F t27 窗口化 `sole_roll` 来源排查；在最新 t27 诊断日志上，腾空窗 `3/4`、touchdown 窗 `3/4` 更偏 `execution_chain_dominant`，`sole_roll` 仍主要跟随执行链而不是即时 output 链 |
| [09_phase_lag_limit_cycle_compare_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/09_phase_lag_limit_cycle_compare_t27.md:1) | Round 3G t27 高 kp 相位滞后/限环对比；高 kp 组存在局部 `lpf -> pos` 滞后增加，但没有形成稳定周期震荡，`sole_roll` 仍主要跟随执行链响应 |
| [10_execution_chain_disentanglement.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/10_execution_chain_disentanglement.md:1) | Round 3H 执行链拆解结果；先用 `pos_des_lpf -> pos` 做 H2 代理判定，随后在补上 `/actuator_cmd` 与 `/actuator_states` 后完成 actuator-state 级别确认；现有 `5` 组 proxy case 与 `1` 组 actuator-state case 的 cross-case 对比继续支持：`sole_roll` 仍主要跟随执行链，不直接跟随 output，`40/0.8` 暂按 proxy 判据不稳处理，且更明显的滞后落在 `actuator_state -> joint_pos` 段 |
| [11_execution_chain_lag_analysis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/11_execution_chain_lag_analysis.md:1) | Round 3I 执行链 lag 分析；`4` 组 actuator-state 多样本复核后，主滞后段仍更像 `actuator_state -> joint_pos`，且 lag 普遍在 `swing` 期已明显存在；`left/right asymmetry` 明显但慢侧不稳定，现阶段不能收口为单侧固定故障 |
| [12_parallel_actuation_realization_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/12_parallel_actuation_realization_probe.md:1) | Round 3J 并联执行兑现分析；当前 `12A + 12B + 12C` 已表明 `state -> joint` 更像 `backlash / hysteresis` 主导，并发 `low_realization_gain` 与 `mode-dependent asymmetry`；它能解释一部分 `swing` 异常，但不能替代 `05` 去解释 touchdown 期的主要 `sole_roll` 残差 |
| [13_dead_zone_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/13_dead_zone_audit.md:1) | Round 3K 死区审视结果；当前主证据已收缩到 `swing` 期 `pos_des_raw`，并显示一部分 `swing` lag 应优先按小信号死区 / 阈值敏感区理解，而不应默认先归到机械结构 |
| [15_sim_t27_03_06_analysis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/15_sim_t27_03_06_analysis.md:1) | sim `03/06` 历史分析；已被 `17` 审计降级，不能作为 sim failure 证据 |
| [16_real_round3_logic_audit_after_sim_contrast.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/16_real_round3_logic_audit_after_sim_contrast.md:1) | real `03/05/06` 审计；确认旧 raw FK foot-frame 结论受 frame 偏置污染 |
| [17_sim_round3_reaudit_with_video_fact.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/17_sim_round3_reaudit_with_video_fact.md:1) | sim 视频事实复审；确认 sim 能前走，仅左脚轻微外翻 |
| [18_real_vs_sim_residual_acceptance_comparison.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/18_real_vs_sim_residual_acceptance_comparison.md:1) | 定义 sim 可接受 residual 包络，并指出 real 超限项 |
| [19_real_vs_sim_execution_chain_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/19_real_vs_sim_execution_chain_compare.md:1) | 对比 real/sim 执行链，确认 output 不是主瓶颈 |
| [20_real_vs_sim_joint_jitter_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/20_real_vs_sim_joint_jitter_compare.md:1) | 基于新 kinematic touchdown 窗口，对比 swing/touchdown roll/pitch joint 调整/抖动；确认 real 的 range/path/track err 仍更重，pitch touchdown 高频结论降级 |
| [24_touchdown_gait_period_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/24_touchdown_gait_period_compare.md:1) | 验证新 touchdown detector 下 real/sim 步态周期一致，修正旧 contact proxy 导致的早期同侧误触发 |
| [25_kinematic_touchdown_detector_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/25_kinematic_touchdown_detector_audit.md:1) | 对比旧 ankle-pitch 低速 contact proxy 与新 FK+hip kinematic detector，确认 real 前 4 次 touchdown 恢复正常交替 |
| [26_touchdown_detector_reaudit_and_plan_update.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/26_touchdown_detector_reaudit_and_plan_update.md:1) | 汇总触地检测修正、重新计算结果和 plan/results 受影响范围 |
| [21_real_vs_sim_combined_conclusion.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/21_real_vs_sim_combined_conclusion.md:1) | 合并 `18/19/20` 的 canonical 结论 |
| [22_forward_x_failure_consistency_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/22_forward_x_failure_consistency_audit.md:1) | 本轮 plan/results 一致性审计和下一步工作 |

kp/kd 辨识结果放在 `results/sim2real_steps/ankle_kp_kd/`：

| 文件 | 内容 |
|---|---|
| [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md:1) | Round 2 踝关节 kp/kd 辨识结果 |

## 推进顺序

### 审计后推进顺序（当前有效）

1. `01/03/05` 的 pre-audit 结果保留为历史诊断过程，但其中 `8/8 severe_foot_flat_touchdown`、`8/8 roll dominant`、`mean 1.6~1.9 rad` 和旧 `05C fk_foot_frame_residual_candidate 3/4` 不再作为当前结论。
2. 今天的 sim 多 `kp/kd` 结果已经确认：sim 能稳定前走，仅左脚轻微外翻且无明显抖动；因此旧 sim `03/06` 的 `severe / command_not_flat` 读法失效。
3. 当前采用 `16/17/18/19/20/21/22` 的审计后口径：real 的关键问题是 residual 越过 sim 可接受包络，并叠加执行链兑现残差与 touchdown 抖动放大。
4. `03` 的 `command_not_flat / tracking_lag / coupled_geometry` 仍可作为历史分类标签，但不再直接决定下一轮修复入口；下一轮入口由 `05D` 的 foot/contact frame 复核结果决定。
5. 当前第一优先级是 `05D FK Foot-Frame / Contact`：确认 `joint -> sole residual` 的真实物理含义，再决定修 foot/contact 建模、执行链兑现，还是策略 touchdown 姿态目标。
6. `02_low_speed_walk_validation_candidate` 继续 blocked，直到 `05D` 给出明确修复入口。

### 历史推进顺序（pre-audit，仅保留过程记录）

1. `01_landing_window_diagnosis` 已用已有真机日志和仿真回放定位双脚高度差不足、斜着落地和无法前进的主因。
2. 当前 `01` 的结果已经表明主导阻塞为 `severe_foot_flat_touchdown`，因此先执行 `03_ankle_landing_attitude_resolution`。
3. `03` 已经把根因拆成 `command_not_flat / tracking_lag / coupled_geometry`，`04` 已按“前 `4` 步优先”口径执行完一轮 right-roll 单轴扫参。
4. `04` 的结论是否定性的：单轴 `right_ankle_roll_joint` 调参会在 `tracking_lag / filter_delay / coupled_geometry / command_not_flat` 之间转移表现，但未关闭主问题。
5. 因此后续不再继续盲目扩大 `right_ankle_roll_joint` 参数，优先转向 `command_not_flat / coupled_geometry / filter_delay` 的联合排查；当前更一致的综合结论是“调软 4 个 ankle 能提升平稳性，但推进不足，主问题仍未关闭”。
6. 当前正式进入 `05_coupled_geometry_probe` 阶段，优先解释“为什么抖动压住后，脚底仍以错误几何姿态 touchdown”；在进入 `05` 之前，`13_dead_zone_audit` 已把 `swing` 期的小信号兑现不足前置筛查掉，所以 `05` 只接管 touchdown residual；`05A zero bias check` 已排除 controller offset / YAML direction，`05B parallel mapping verification` 又排除了简单 actuator ownership / sign bug；再结合 `05C` touchdown contact residual classification，`05 / 12 / 13` 的边界现已固定为：
   - `12` 负责 `actuator_state -> joint_pos` realization residual
   - `13` 负责 `swing` 期 `pos_des_raw` 小信号死区 / 阈值响应
   - `05` 负责 `joint_pos -> sole_roll` 的 foot-space / contact residual
   当前 `05` 主线进一步收窄到：
   - foot-space / contact frame 与真实足底接触几何失配
   - 接触边缘、接触线或滚动中心偏置
   - pitch-roll coupled contact residual 作为少数 case 保留
   - 硬件侧 realization asymmetry 作为并发放大器保留
7. `07_windowed_roll_origin_probe` 进一步验证了：在腾空窗和 touchdown 窗里，`sole_roll` 更偏执行链响应而不是立即 output 链；这不推翻 `05` 的几何/映射结论，只是说明执行链延迟在表现层上是并发放大器。
8. `08_windowed_roll_origin_probe_t27` 在最新 t27 诊断日志上再次得到同方向结果：腾空窗 `3/4`、touchdown 窗 `3/4` 仍更偏 `execution_chain_dominant`，说明低 kp 之后 `sole_roll` 仍主要跟随执行链而不是即时 output 链。
9. `09_phase_lag_limit_cycle_compare_t27` 进一步表明：高 kp 组确实存在局部 `lpf -> pos` 滞后增加，但没有出现稳定的零交叉/周期震荡，因此当前更像接触阶段的相位滞后与响应迟滞，而不是一个已成型的限环。
10. 若后续仍保留明显 `tracking_lag`，只作为并发问题复核，不再单独作为当前第一修复入口。
11. `foot_clearance_deficit` 与 `hip_knee_swing_timing_or_amplitude` 保留为二级问题，在踝落地姿态主因收敛后复判。
12. `10` 线当前已从代理判定推进到 actuator-state 实测确认：新增日志没有推翻旧结论，现有 `5` 组 proxy + `1` 组 actuator-state 的 cross-case 对比也继续支持“`sole_roll` 主要跟随执行链，主要问题不在 output 侧”；`40/0.8` 当前降级为 proxy 判据不稳，不再单独作为 output 主导反例。
13. 基于 `10` 的收口结论，当前正式进入 `11_execution_chain_lag_analysis`：后续不再争论来源归因，而是只分析执行链 lag 的分段位置、窗口放大位置和左右踝不对称；现有 `4` 组 actuator-state 复核继续支持“主滞后段更像 `actuator_state -> joint_pos`，且 lag 在 `swing` 期已存在”。
14. 基于 `11` 的收口结论，当前正式进入 `12_parallel_actuation_realization_probe`：后续重点从“lag 在哪”转向“为什么 `state -> joint` 兑现不足”，并与 `05 coupled_geometry` 做边界划分；当前 `12A + 12B + 12C` 已将其收口为 `backlash / hysteresis like realization` 主导，并发 `low_realization_gain` 与 `mode-dependent left/right asymmetry`，且进一步确认它只能解释一部分 `swing` 异常，不能替代 `05` 去解释 touchdown 期的主要 `sole_roll` 残差。
15. 基于 `11/12/05` 的收口结论，新增 `13_dead_zone_audit`：后续分析 `swing` 期的局部 lag 时，先审视 `pos_des_raw` 是否已落入小信号死区 / 阈值响应；这一部分不再默认归到 `05`，而是由 `13` 前置收口。
16. 当前下一步为 `05D FK Foot-Frame / Contact 现场复核`。只有当 `05D` 先验证 FK foot frame 是否可信，再把 `fk_foot_frame_residual_candidate` 拆成可执行的 `real_contact_edge_bias / foot_frame_reference_mismatch / dynamic_contact_deformation_or_release` 之一，并给出修正动作后，才允许重新评估 `02_low_speed_walk_validation_candidate`。

## 命名规则

- 当前主问题方案：`plans/forward_x_failure/{序号}_{主题}.md`
- 当前主问题结果：`results/forward_x_failure/{序号}_{主题}.md`
- sim2real 基础步骤方案：`plans/sim2real_steps/{步骤名}/{序号}_{主题}.md`
- sim2real 基础步骤结果：`results/sim2real_steps/{步骤名}/{主题}.md`

不要再把 kp/kd 辨识执行单直接放在 `plans/` 根目录。
