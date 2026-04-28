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
| `command_not_flat` | 策略在触地前给出的踝关节目标本身不能让足底板调平 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `tracking_lag` | 策略目标基本正确，但实际踝角在落地前没有跟到位 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1)，必要时回到 [03_round_02c_contact_degradation_fix.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/sim2real_steps/ankle_kp_kd/03_round_02c_contact_degradation_fix.md:1) |
| `filter_delay` | raw 目标提前，但 LPF 后目标晚到，导致调平动作迟到 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `phase_mismatch` | 策略相位/真实 touchdown 不对齐，调平动作发生在触地后 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `coupled_geometry` | 单轴误差不大，但 pitch/roll 耦合后足底板仍斜 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `foot_clearance_deficit` | 摆动脚相对支撑脚高度差不足，落地前已经接近地面，导致前向推进被提前接触截断 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |
| `hip_knee_swing_timing_or_amplitude` | 髋/膝摆动的相位、峰值或伸膝时机不对，导致摆腿清高不足或过早落地 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) |

## 方案结构

当前主问题只在 `plans/forward_x_failure/` 下维护：

| 顺序 | 文件 | 作用 | 状态 |
|---|---|---|---|
| 00 | [00_problem_and_overall_plan.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/00_problem_and_overall_plan.md:1) | 当前文件，定义问题、假设、推进顺序 | active |
| 01 | [01_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/01_landing_window_diagnosis.md:1) | 摆腿中期到触地前后窗口诊断，联合判定足高不足、髋/膝时序、踝调平主因 | ready to plan |
| 02 | [02_low_speed_walk_validation_candidate.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/02_low_speed_walk_validation_candidate.md:1) | 低速前进复测候选方案，必须等 01 关闭后执行 | blocked |

基础 sim2real 辨识步骤单独放在 `plans/sim2real_steps/ankle_kp_kd/`，作为支撑材料，不再和当前主问题子方案混放。

## 结果文件结构

当前主问题结果只放在 `results/forward_x_failure/`：

| 文件 | 内容 |
|---|---|
| [01_field_baseline.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/01_field_baseline.md:1) | Round 1 基础链路、站立、RL 小速度初测结果 |

kp/kd 辨识结果放在 `results/sim2real_steps/ankle_kp_kd/`：

| 文件 | 内容 |
|---|---|
| [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md:1) | Round 2 踝关节 kp/kd 辨识结果 |

## 推进顺序

1. 先执行 `01_landing_window_diagnosis`，用已有真机日志和仿真回放定位双脚高度差不足、斜着落地和无法前进的主因。
2. 若主因为 `tracking_lag`，只回到 kp/kd 子步骤里处理对应踝轴，不盲目全局扫参数。
3. 若主因为 `filter_delay` 或 `phase_mismatch`，新建对应子方案，不继续把问题归因到 kp/kd。
4. 若主因为 `foot_clearance_deficit` 或 `hip_knee_swing_timing_or_amplitude`，优先进入髋/膝摆腿窗口专项：先确认策略输出是否给了足够抬腿命令，再区分是部署侧关节跟踪/延迟问题，还是策略侧步态设计问题。
5. 若主因为 `command_not_flat`，进入策略/观测/奖励设计反馈，不在部署侧硬调。
6. 只有当 01 的阻塞项关闭后，才允许执行 `02_low_speed_walk_validation_candidate`。

## 命名规则

- 当前主问题方案：`plans/forward_x_failure/{序号}_{主题}.md`
- 当前主问题结果：`results/forward_x_failure/{序号}_{主题}.md`
- sim2real 基础步骤方案：`plans/sim2real_steps/{步骤名}/{序号}_{主题}.md`
- sim2real 基础步骤结果：`results/sim2real_steps/{步骤名}/{主题}.md`

不要再把 kp/kd 辨识执行单直接放在 `plans/` 根目录。
