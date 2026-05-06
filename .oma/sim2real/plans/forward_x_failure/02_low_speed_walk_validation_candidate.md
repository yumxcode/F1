# Round 4 低速步态验证候选方案

状态：`blocked by 05D_fk_foot_frame_contact_review`。本方案原为 Round 3 候选执行稿；在真机数据仿真回放发现“踝关节落地时脚底板没有调整到位、斜着落地”，以及新增发现“落地时双脚高度差不够、摆动脚清高不足”后，本方案降级为 Round 4 候选。

当前 `01/03/04/06-13` 已完成阶段性收口，但 `05C` 只给出 FK 派生的 `fk_foot_frame_residual_candidate`，尚需先完成 `05D FK Foot-Frame / Contact 现场复核`。因此本方案仍保持 blocked。统一进展见 [00_forward_x_failure_progress_review.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/00_forward_x_failure_progress_review.md:1)。

目标：在不改动策略模型与步态时序参数的前提下，仅替换 `rl_walk_leg` 的踝关节 `kp/kd` 为 `Round 2A` 收敛值，验证真机低速行走的连续性、推进性和踝关节抖动是否改善。

## 本轮假设

- `Round 1` 的主要症状中，踝关节轻微抖动和推进不足可能主要来自并联踝关节闭环参数过软，而不是策略输出幅度本身。
- `Round 2A` 已在悬空工况下收敛出各关节 best_air_candidate，`Round 2B` 触地退化测量将决定这组参数能否直接用于步态。
- 如果只改踝关节参数后，连续性或抖动已经明显改善，就没有必要立即引入 `lpf_conf.wc`、`action_scale` 等新变量。
- 新增约束：若 Round 3 证明落地斜脚由 `command_not_flat`、`phase_mismatch` 或 `filter_delay` 主导，则本轮不能直接执行；必须先改策略/相位/LPF 后再重写本方案。
  > 🔍 **Round 3 结论**：`coupled_geometry` 是主导（非 `command_not_flat` 单独主导），`filter_delay` 无稳定主导证据。此约束**部分触发**：问题非策略/相位/LPF，但仍未关闭，本轮继续 blocked。
- 新增约束：若 Round 3 证明双脚高度差不足由 `foot_clearance_deficit`、`hip_knee_command_low`、`hip_knee_tracking_lag` 或 `early_knee_extension` 主导，则本轮不能直接执行；必须先完成髋/膝摆腿专项或策略设计反馈。
  > 🔍 **Round 3 结论**：`foot_clearance_deficit` / `hip_knee_tracking_lag` 作为并发问题保留，但**非主因**，主因是 `severe_foot_flat_touchdown`。此约束**未直接触发**（并发问题，非主导），但主问题仍未关闭，本轮仍 blocked。
- 新增约束：若 Round 3 证明落地斜脚由 `tracking_lag` 主导，本轮使用的踝关节参数必须先替换为 Round 2C 对应关节的 timing 修复结果。
  > 🔍 **Round 3 结论**：`tracking_lag` **不是**稳定的主导因（04 已证明单轴扫参转移表现但不关闭主问题）。此约束**未直接触发**。

**⏸ 当前 block 原因**：`05C` 将残差收口为 `fk_foot_frame_residual_candidate`，需先完成 `05D FK Foot-Frame / Contact 现场复核`，明确 FK foot frame 是否可信并给出可执行修正后，才允许重启本方案。

## 采用参数

`rl_walk_leg`（基于 Round 2A 最终结论，待 Round 2B 确认后正式使用）：
- `left_ankle_pitch_joint: kp=80, kd=0.8`
- `left_ankle_roll_joint: kp=80, kd=1.0`
- `right_ankle_pitch_joint: kp=40, kd=0.8`
- `right_ankle_roll_joint: kp=50, kd=0.8`

说明：
- 上述参数为 `Round 2A` 悬空辨识收口值，已替换旧的触地暂存候选值。
- `Round 2B` 退化测量结果可能导致个别关节参数微调，正式执行前以 `Round 2` 关闭时的最终值为准。
- 只有当 `Round 2` 文档明确关闭（Round 2B 完成且退化可接受）后，才允许执行本轮。
- 若 `Round 2B` 某关节退化显著，该关节参数需等 `Round 2C` 调整后再更新此处。

保持不变：
- `action_scale = 0.5`
- `cycle_time = 0.7`
- `cmd_threshold = 0.05`
- `lpf_conf.wc = 100`

## 执行前检查

- 确认 [rl_x1.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/module/control_module/cfg/rl_x1.yaml:326) 的 `rl_walk_leg` 参数已更新到本轮目标值。
- 确认 [deploy_info.json](/Users/yumx/code/X1/agibot_x1_infer/.oma/deploy_info.json:1) 与源码配置一致。
- 确认 [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md) 已完成，并且结论允许进入低速步态复测。
- 确认摆腿窗口中 `max_swing_clearance`、触地前 `50 ms` 双脚高度差、hip/knee `pos_des-q` 和膝关节伸展时序没有未关闭的阻塞项。
- 确认落地窗口中 `foot_flat_error`、ankle `pos_des-q`、LPF 延迟和 touchdown 相位没有未关闭的阻塞项。
- 确认没有其他节点同时发布 `/joint_cmd`。
- 确认保护吊具、急停和扶持人员到位。

## 实验顺序

1. `zero -> stand -> hold`
2. `walk_leg` 零速命令，持续 `5 s`
3. `walk_leg` 前向 `x = 0.2 m/s`，持续 `10 s`
4. `walk_leg` 前向 `x = 0.3 m/s`，持续 `10 s`
5. 若第 4 步稳定，再执行 `x = 0.4 m/s`，持续 `10 s`

约束：
- 不在本轮同时测试横移、转向或 `walk_leg_arm`
- 任一步出现明显踝关节高频抖动、足端连续拍地或姿态失稳，立即退出并记录停止条件

## 重点观测项

- 连续行走时间是否从 `~10 s` 提升
- 步态是否仍然偏“踏步前进”
- 摆动脚是否仍然抬不够，落地前双脚高度差是否仍不足
- 髋 pitch 前摆、膝 pitch 屈曲和伸膝时机是否与 Round 3 结论一致
- 落地瞬间足底板是否仍斜着落地
- 触地前 `100~150 ms` 内 ankle pitch/roll 是否按 Round 3 结论完成调平
- 踝关节轻微抖动是否减弱、消失或转移到特定单侧/单轴
- 前进命令下是否出现新的左右不对称
- 身体俯仰、横摆是否因为分轴参数导致明显偏置

## 记录要求

- 至少记录每个速度档位的开始/结束时间和人工观察结论
- 若系统已有 gait/contact 日志，保留原始日志文件路径
- 结果文件需明确写出：
  - 是否通过 `low_speed_walk`
  - 最稳定速度档位
  - 最先暴露的问题类型
  - 落地斜脚是否复现
  - 双脚高度差不足是否复现
  - 若复现，是否由髋/膝摆动幅度不足、时机错误或跟踪滞后导致
  - 若复现，是否与 Round 3 判因一致
  - 是否需要进入 `lpf_conf.wc` 调整

## 决策规则

- 若 `x = 0.3 m/s` 可稳定维持，且踝抖明显减轻：
  - 将 `low_speed_walk` 标记为通过
  - 下一轮进入 `lateral_and_yaw`
- 若连续性改善但仍有可重复的踝高频抖动：
  - 保持当前 `kp/kd`
  - 下一轮优先测试 `lpf_conf.wc`
- 若比 `Round 1` 更差，或出现新的明显不对称：
  - 回查 `right roll = 60/0.8` 与左右脚分轴差异
  - 必要时回退到 `right roll = 70/0.8` 做对照轮
- 若无法前进且复现斜着落地：
  - 停止继续加速度档位
  - 回到 Round 3 落地窗口诊断结果，对照 `command_not_flat / tracking_lag / filter_delay / phase_mismatch / coupled_geometry` 分类处理
- 若无法前进且复现双脚高度差不足：
  - 停止继续加速度档位
  - 回到 Round 3 摆腿清高诊断结果，对照 `foot_clearance_deficit / hip_knee_command_low / hip_knee_tracking_lag / early_knee_extension` 分类处理
