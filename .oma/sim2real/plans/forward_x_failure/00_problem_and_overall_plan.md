# X 轴前进指令无法前进：整体问题与方案

状态：`active`。这是当前 sim2real 主问题的入口文件。

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
| `severe_foot_flat_touchdown` | touchdown 时脚板姿态严重不平，已成为当前更上游的主导阻塞项 | [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/03_ankle_landing_attitude_resolution.md:1) |
| `command_not_flat` | 策略在触地前给出的踝关节目标本身不能让足底板调平 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `tracking_lag` | 策略目标基本正确，但实际踝角在落地前没有跟到位 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1)，必要时回到 [03_round_02c_contact_degradation_fix.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/sim2real_steps/ankle_kp_kd/03_round_02c_contact_degradation_fix.md:1) |
| `tracking_lag_repair` | 基于 step 试验和 Round 3 日志，专项验证 walk 踝参数与执行链是否不足以支撑 touchdown 小幅调平 | [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/04_tracking_lag_repair.md:1) |
| `filter_delay` | raw 目标提前，但 LPF 后目标晚到，导致调平动作迟到 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `phase_mismatch` | 策略相位/真实 touchdown 不对齐，调平动作发生在触地后 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `coupled_geometry` | 单轴误差不大，但 pitch/roll 耦合后足底板仍斜 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `windowed_roll_origin_probe` | 在腾空窗与 touchdown 窗中，对比 output / target / current / pos 与 `sole_roll` 的对应关系，判断更像输出链还是执行链驱动 | [07_windowed_roll_origin_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/07_windowed_roll_origin_probe.md:1) |
| `windowed_roll_origin_probe_t27` | 基于 t27 单文件诊断日志，在腾空窗与 touchdown 窗中对比 `action / pos_des_raw / pos_des_lpf / pos` 与 `sole_roll` 的对应关系 | [08_windowed_roll_origin_probe_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/08_windowed_roll_origin_probe_t27.md:1) |
| `phase_lag_limit_cycle_compare_t27` | 基于 t27 多组 kp 数据，对比 touchdown 窗内 `lpf -> pos -> sole_roll` 的相位滞后、零交叉和环面积，判断是否存在高 kp 局部相位滞后引发的限环趋势 | [09_phase_lag_limit_cycle_compare_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/09_phase_lag_limit_cycle_compare_t27.md:1) |
| `foot_clearance_deficit` | 摆动脚相对支撑脚高度差不足，落地前已经接近地面，导致前向推进被提前接触截断 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `hip_knee_swing_timing_or_amplitude` | 髋/膝摆动的相位、峰值或伸膝时机不对，导致摆腿清高不足或过早落地 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |

## 方案结构

当前主问题只在 `plans/forward_x_failure/` 下维护：

| 顺序 | 文件 | 作用 | 状态 |
|---|---|---|---|
| 00 | [00_problem_and_overall_plan.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/00_problem_and_overall_plan.md:1) | 当前文件，定义问题、假设、推进顺序 | active |
| 01 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) | 摆腿中期到触地前后窗口诊断，联合判定足高不足、髋/膝时序、踝调平主因 | ready to plan |
| 02 | [02_low_speed_walk_validation_candidate.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/02_low_speed_walk_validation_candidate.md:1) | 低速前进复测候选方案，必须等 01 和 03 的阻塞项关闭后执行 | blocked |
| 03 | [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/03_ankle_landing_attitude_resolution.md:1) | 基于 Round 3 结果，专项解决 touchdown 时脚板严重不平 | ready to execute |
| 04 | [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/04_tracking_lag_repair.md:1) | 基于 step 试验和 Round 3 跟踪滞后样本，专项验证并修复执行链不足 | executed |
| 05 | [05_coupled_geometry_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/05_coupled_geometry_probe.md:1) | 基于前几步有效 touchdown 与参数试验收口结果，专项排查几何/映射导致的 touchdown 偏置 | active |
| 07 | [07_windowed_roll_origin_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/07_windowed_roll_origin_probe.md:1) | 基于延迟链，分腾空窗与 touchdown 窗对比 output / target / current / pos 与 sole_roll 的对应关系 | active |
| 08 | [08_windowed_roll_origin_probe_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/08_windowed_roll_origin_probe_t27.md:1) | 基于 t27 单文件日志，分腾空窗与 touchdown 窗对比 action / pos_des_raw / pos_des_lpf / pos 与 sole_roll 的对应关系 | active |
| 09 | [09_phase_lag_limit_cycle_compare_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/09_phase_lag_limit_cycle_compare_t27.md:1) | 基于 t27 多组 kp 对比 touchdown 窗内相位滞后与环形响应，判断高 kp 是否形成局部限环趋势 | active |
| 10 | [10_execution_chain_disentanglement.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/10_execution_chain_disentanglement.md:1) | 继续拆解执行链复合延迟与几何镜像偏置，补 `/actuator_states` 级别证据 | active |

基础 sim2real 辨识步骤单独放在 `plans/sim2real_steps/ankle_kp_kd/`，作为支撑材料，不再和当前主问题子方案混放。

## 结果文件结构

当前主问题结果只放在 `results/forward_x_failure/`：

| 文件 | 内容 |
|---|---|
| [01_field_baseline.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/01_field_baseline.md:1) | Round 1 基础链路、站立、RL 小速度初测结果 |
| [02_round3_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/02_round3_landing_window_diagnosis.md:1) | Round 3 touchdown 判因结果；新版脚本下为 `8` 次 touchdown，`primary_flag` 主因仍锁定为 `severe_foot_flat_touchdown`，并同步保留并发 flags |
| [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/03_ankle_landing_attitude_resolution.md:1) | Round 3A 踝落地姿态专项结果；新版脚本下 `8/8` 为 roll 主导，三层根因为 `command_not_flat 4 / tracking_lag 2 / coupled_geometry 2` |
| [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/04_tracking_lag_repair.md:1) | Round 3B 执行链修复结果；按前 `4` 步优先口径，单轴 `right roll` 扫参表现出明显 tradeoff，未关闭主问题，停止继续盲调 |
| [05_coupled_geometry_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/05_coupled_geometry_probe.md:1) | Round 3C 几何/映射排查结果；在 `4 ankles = 25 / 0.5` 数据上，refined geometry 判因首轮收敛为 `parallel_mapping_mismatch 4 / 4`，且 `05A` 已初步排除 controller offset / yaml direction，收敛到 C++ 映射符号链；补充 swing 期统计后，左右摆动腿在腾空期已存在稳定镜像 `roll` 偏置 |
| [06_delay_chain_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/06_delay_chain_probe.md:1) | Round 3D 延迟链排查结果；`action -> target` 近似 0 ms，主要延迟出现在 `target/current -> pos` 执行链，且 ankle 不是这份日志里最慢的一组，因此 current 数据更支持“执行链存在延迟，但不足以单独解释 coupled_geometry” |
| [07_windowed_roll_origin_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/07_windowed_roll_origin_probe.md:1) | Round 3E 窗口化 `sole_roll` 来源排查；腾空窗 `3/3`、touchdown 窗 `2/3` 都更偏 `execution_chain_dominant`，说明这份数据里 `sole_roll` 更接近执行链响应，而不是立即的 output 链 |
| [08_windowed_roll_origin_probe_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/08_windowed_roll_origin_probe_t27.md:1) | Round 3F t27 窗口化 `sole_roll` 来源排查；在最新 t27 诊断日志上，腾空窗 `3/4`、touchdown 窗 `3/4` 更偏 `execution_chain_dominant`，`sole_roll` 仍主要跟随执行链而不是即时 output 链 |
| [09_phase_lag_limit_cycle_compare_t27.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/09_phase_lag_limit_cycle_compare_t27.md:1) | Round 3G t27 高 kp 相位滞后/限环对比；高 kp 组存在局部 `lpf -> pos` 滞后增加，但没有形成稳定周期震荡，`sole_roll` 仍主要跟随执行链响应 |
| [10_execution_chain_disentanglement.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/10_execution_chain_disentanglement.md:1) | Round 3H 执行链拆解代理判定；先用 `pos_des_lpf -> pos` 作为执行链代理后，H2 已支持：`lpf -> pos` 迟滞明显，`sole_roll` 仍主要跟随执行链，不直接跟随 output，但真正的 `/actuator_states` 仍需补录以拆分两段延迟 |

kp/kd 辨识结果放在 `results/sim2real_steps/ankle_kp_kd/`：

| 文件 | 内容 |
|---|---|
| [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md:1) | Round 2 踝关节 kp/kd 辨识结果 |

## 推进顺序

1. 先执行 `01_landing_window_diagnosis`，用已有真机日志和仿真回放定位双脚高度差不足、斜着落地和无法前进的主因。
2. 当前 `01` 的结果已经表明主导阻塞为 `severe_foot_flat_touchdown`，因此先执行 `03_ankle_landing_attitude_resolution`。
3. `03` 已经把根因拆成 `command_not_flat / tracking_lag / coupled_geometry`，`04` 已按“前 `4` 步优先”口径执行完一轮 right-roll 单轴扫参。
4. `04` 的结论是否定性的：单轴 `right_ankle_roll_joint` 调参会在 `tracking_lag / filter_delay / coupled_geometry / command_not_flat` 之间转移表现，但未关闭主问题。
5. 因此后续不再继续盲目扩大 `right_ankle_roll_joint` 参数，优先转向 `command_not_flat / coupled_geometry / filter_delay` 的联合排查；当前更一致的综合结论是“调软 4 个 ankle 能提升平稳性，但推进不足，主问题仍未关闭”。
6. 当前正式进入 `05_coupled_geometry_probe` 阶段，优先解释“为什么抖动压住后，脚底仍以错误几何姿态 touchdown”；`05A zero bias check` 已完成首轮收口，当前主线已进一步收窄到 `parallel_mapping / sign-convention verification`。
7. `07_windowed_roll_origin_probe` 进一步验证了：在腾空窗和 touchdown 窗里，`sole_roll` 更偏执行链响应而不是立即 output 链；这不推翻 `05` 的几何/映射结论，只是说明执行链延迟在表现层上是并发放大器。
8. `08_windowed_roll_origin_probe_t27` 在最新 t27 诊断日志上再次得到同方向结果：腾空窗 `3/4`、touchdown 窗 `3/4` 仍更偏 `execution_chain_dominant`，说明低 kp 之后 `sole_roll` 仍主要跟随执行链而不是即时 output 链。
9. `09_phase_lag_limit_cycle_compare_t27` 进一步表明：高 kp 组确实存在局部 `lpf -> pos` 滞后增加，但没有出现稳定的零交叉/周期震荡，因此当前更像接触阶段的相位滞后与响应迟滞，而不是一个已成型的限环。
10. 若后续仍保留明显 `tracking_lag`，只作为并发问题复核，不再单独作为当前第一修复入口。
11. `foot_clearance_deficit` 与 `hip_knee_swing_timing_or_amplitude` 保留为二级问题，在踝落地姿态主因收敛后复判。
12. 只有当 `01`、`03`、`04`、`05`、`07`、`08`、`09`、`10` 的阻塞项关闭后，才允许执行 `02_low_speed_walk_validation_candidate`。

## 命名规则

- 当前主问题方案：`plans/forward_x_failure/{序号}_{主题}.md`
- 当前主问题结果：`results/forward_x_failure/{序号}_{主题}.md`
- sim2real 基础步骤方案：`plans/sim2real_steps/{步骤名}/{序号}_{主题}.md`
- sim2real 基础步骤结果：`results/sim2real_steps/{步骤名}/{主题}.md`

不要再把 kp/kd 辨识执行单直接放在 `plans/` 根目录。
