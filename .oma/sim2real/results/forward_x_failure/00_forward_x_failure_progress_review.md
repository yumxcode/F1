# Forward X Failure Progress Review

本文件是 `forward_x_failure` 系列结果的统一入口，用于避免后续文档之间出现口径冲突。

## 当前总判断

### 阶段性结论快照（2026-05-05）

截至 2026-05-05，`forward_x_failure` 的阶段性结论是：

**当前问题不是单一的“前向指令没发出”、也不是单纯 ankle `kp/kd` 偏低；最直接阻塞项是 touchdown 窗口内 roll 主导的严重斜脚触地，导致脚底接触 / 支撑方向异常，前向支撑与推进被破坏。**

中间测验的收口如下：

| 子线 | 核心结果 | 阶段判断 |
|---|---|---|
| `01/02` landing window | `8/8` touchdown 命中 `severe_foot_flat_touchdown`，mean foot-flat error 约 `1.6766 rad` | 直接阻塞项明确：严重斜脚触地 |
| `03` ankle landing attitude | `8/8` 为 roll 主导；三层原因分布为 `command_not_flat 4 / tracking_lag 2 / coupled_geometry 2` | 主方向是 roll，不是 pitch |
| `04` tracking lag repair | 多组 ankle `kp/kd` 不能关闭问题，只让标签在 `tracking_lag / filter_delay / coupled_geometry / command_not_flat` 间迁移 | 停止盲目扫 `kp/kd` |
| `05A/05B` geometry / code check | controller offset、YAML direction、简单 actuator ownership / sign bug 基本排除 | 不是显式配置方向错误 |
| `05C` contact residual classification | `fk_foot_frame_residual_candidate 3/4`，`pitch_roll_coupled_contact_residual 1/4` | 当前最强候选是 foot-frame / contact 残差 |
| `06` delay chain | `action -> target` 近似 `0 ms`，主要延迟在执行链 | policy output 不是主瓶颈 |
| `07/08` windowed roll origin | `sole_roll` 更贴近执行链 / 关节响应，而非直接 output | 执行链是表现层和放大器，但不能替代几何残差解释 |
| `09` phase lag / limit cycle | 高 `kp` 会放大局部 lag，但无稳定限环证据 | 不是稳定振荡主因 |
| `10/11` execution chain | 主滞后更接近 `actuator_state -> joint_pos` / `state -> joint`，且 swing 期已存在 | 执行实现不健康，但不是完整解释 |
| `12` realization probe | 存在 backlash / hysteresis-like、低实现增益、模式相关不对称 | 可解释 swing 异常的一部分 |
| `13` dead-zone audit | swing `pos_des_raw` 小信号特征稳定存在 | swing lag 不能默认先归因于机械结构；不解释 touchdown contact residual |

因此，当前原因链为：

1. 直接现象：落脚时脚底没有以可接受姿态接触地面，且 roll 方向主导。
2. 结果影响：脚底接触边 / 接触面异常，支撑相位无法稳定形成前向推进，表现为 forward x 不走或原地踏。
3. 已排除或降权：纯 output delay、简单配置方向错误、单侧固定硬件故障、单纯低 `kp/kd`、稳定极限环。
4. 仍成立的伴随因素：执行链 lag、小信号 / 死区、`state -> joint` 实现不健康。
5. 当前主候选：`joint_pos -> fk_sole_roll` 的 foot-frame / contact residual。但 `fk_sole_roll` 来自 MuJoCo FK 的 `link_*_ankle_roll` body frame，不能直接等同真实脚底接触平面；必须通过 `05D` 验证 FK frame 与真实 sole plane / contact edge 的对应关系后，才能最终定性。

当前主问题仍是：

**x 方向前进不足 / 原地踏步，直接阻塞项是 touchdown 时脚底姿态严重不平；最新收口认为 touchdown 剩余残差更偏 foot-space / contact frame，而不是单纯 output 错误或单纯执行链 lag。**

统一边界如下：

| 子线 | 负责解释 | 不负责解释 |
|---|---|---|
| `05_coupled_geometry_probe` | touchdown 窗里 `joint_pos -> sole_roll` 的 foot-space / contact residual | swing 小信号死区、`actuator_state -> joint_pos` 兑现不足 |
| `11_execution_chain_lag_analysis` | 执行链 lag 落在哪一段、是否左右不对称、是否接触前已存在 | policy output 是否错、最终 contact geometry 残差 |
| `12_parallel_actuation_realization_probe` | `actuator_state -> joint_pos` 的兑现形态：lag、backlash、hysteresis、low gain、左右链不一致 | touchdown 最终 `sole_roll` 残差的完整解释 |
| `13_dead_zone_audit` | swing 窗 `pos_des_raw` 小信号 / 死区 / 阈值敏感区 | touchdown contact residual |

## 文档编号口径

`forward_x_failure` 系列目前存在一个历史编号偏移：计划文档从当前主问题的 `01_landing_window_diagnosis` 开始，而结果目录保留了更早的 `01_field_baseline` 作为 Round 1 基线结果。因此：

| 结果编号 | 对应计划 | 当前含义 | 状态 |
|---|---|---|---|
| `00_forward_x_failure_progress_review` | `00_problem_and_overall_plan` | 全局进展、边界和指标字典入口 | active |
| `01_field_baseline` | 无同编号计划；历史基线 | Round 1 现场基线链路结果 | done |
| `02_round3_landing_window_diagnosis` | `01_landing_window_diagnosis` | Round 3 landing window / clearance / hip-knee / touchdown 事件诊断 | done |
| `03_ankle_landing_attitude_resolution` | `03_ankle_landing_attitude_resolution` | touchdown 踝姿态分型与三层根因分类 | done |
| `04_tracking_lag_repair` | `04_tracking_lag_repair` | right ankle roll 单轴扫参与 tracking lag 修复尝试 | done |
| `05_coupled_geometry_probe` | `05_coupled_geometry_probe` | touchdown foot-space / contact residual 主线；当前推进到 `05D` 现场复核 | active |
| `06` - `13` | 同编号计划 | delay / window / execution-chain / realization / dead-zone 分线收口 | done |

后续新增文档优先保持 plan/result 同编号；如需保留历史基线，仍放在 `01_field_baseline`，不要复用 `01` 表示新的主线结果。

## 进展总表

| 阶段 | 当前状态 | 核心结论 | 对下一步的影响 |
|---|---|---|---|
| `01` landing window diagnosis | done | 主旗标锁定 `severe_foot_flat_touchdown`，并发存在 clearance / hip-knee / tracking 风险 | 不直接进入低速复测 |
| `02` low speed validation | blocked | touchdown 姿态问题未关闭 | 暂停执行 |
| `03` ankle landing attitude | done | `8/8` roll 主导；三层根因 `command_not_flat 4 / tracking_lag 2 / coupled_geometry 2` | 进入 `04/05/06` 分线 |
| `04` tracking lag repair | done | 单轴 right-roll 扫参不能关闭问题，只在多个标签间转移表现 | 不继续盲扫 ankle `kp/kd` |
| `05A/05B` geometry/code check | done | controller offset、YAML direction、简单 actuator ownership/sign bug 基本排除 | 残差转向 foot-space / contact |
| `05C` contact residual classification | done | `fk_foot_frame_residual_candidate 3/4`，`pitch_roll_coupled_contact_residual 1/4` | 下一步做 `05D`，先验证 FK foot frame，再验证真实接触边缘 |
| `06` delay chain | done | `action -> target` 近似 0，主要延迟在执行链 | output 不是主瓶颈 |
| `07/08` windowed roll origin | done | `sole_roll` 更偏执行链响应，不直接跟随 output | 保留执行链放大器，同时不替代几何残差 |
| `09` phase lag / limit cycle | done | 高 kp 有局部相位滞后放大，但未形成稳定限环 | 高 kp 是放大器，不是唯一根因 |
| `10` execution chain disentanglement | done | actuator-state 实测继续支持执行链主导，主滞后更偏 `actuator_state -> joint_pos` | 进入 `11/12` |
| `11` execution chain lag | done | `state -> joint` 大 lag 在 swing 期已存在，慢侧不固定 | 不能收口为单侧固定硬件故障 |
| `12` realization probe | done | `state -> joint` 存在不健康兑现，但只能解释一部分现象 | touchdown 主残差仍交给 `05` |
| `13` dead-zone audit | done | swing `pos_des_raw` 小信号特征稳定存在 | swing lag 不能默认先归机械结构 |

## 当前下一步

当前唯一第一优先级是：

**`05D FK Foot-Frame / Contact 现场复核`**

目的：

- 先确认 MuJoCo FK 的 foot body frame 是否能代表真实脚底接触平面；
- 再判断 touchdown 大 FK `sole_roll` 是否对应真实脚底固定边缘先接触；
- 最后区分静态 frame mismatch、真实接触边缘偏置、动态变形 / 回差释放。

不建议继续做：

- 单独扩大 `right_ankle_roll_joint kp/kd`
- 只用 `tracking_lag` 解释所有现象
- 只用 `dead-zone` 解释 touchdown contact residual

## 全局指标字典

| 指标 / 标签 | 含义 | 所属子线 | 当前口径 |
|---|---|---|---|
| `primary_flag` | touchdown 事件的主旗标，按优先级只保留一个主因 | `01/02` | 用于找上游阻塞，不代表并发问题不存在 |
| `all_flags` | 同一次 touchdown 命中的全部并发 flags | `01/02` | 必须与 `primary_flag` 同时看 |
| `severe_foot_flat_touchdown` | touchdown 时脚底姿态严重不平 | `01/03` | 当前主阻塞项 |
| `foot_clearance_deficit` | 摆动脚相对支撑脚高度不足 | `01` | 并发问题，当前不是第一修复入口 |
| `hip_knee_tracking_lag` | 髋/膝摆腿目标或实际响应不足 / 延迟 | `01` | 并发问题，待踝 touchdown 主因收敛后复判 |
| `command_not_flat` | touchdown 前目标本身不足以把脚底调平 | `03/04` | 早期三层判因之一，后续不能单独解释全部 residual |
| `tracking_lag` | 目标有调平意图但真实关节没到位 | `03/04/06` | 更准确应读作执行链响应问题，不是 output 慢 |
| `filter_delay` | raw 目标较早，LPF 后目标迟到 | `03/04/09` | 当前无稳定主导证据 |
| `coupled_geometry` | 单轴 joint 解释不完 foot-space 姿态，存在几何/接触残差 | `05` | 现在只保留 touchdown residual 解释权 |
| `pos_des_raw` | 网络 action 缩放、叠加 init、限幅后的 joint-space 原始目标 | `03/08/13` | `13` 只统计 swing 期小信号分布 |
| `pos_des_lpf` | 经过低通后的 joint-space 目标 | `03/08/09` | 并联 ankle 部分 case 可能为 NaN，要看日志版本 |
| `pos_<joint>` | `/joint_states` 经 controller 映射后的真实 joint-space 位置 | `03/05/11/12` | ankle roll 来自 actuator 反馈经 transmission 映射 |
| `actuator_cmd_pos` | 写给 actuator 的命令位置 | `10/11/12` | 用于拆 `cmd -> state` |
| `actuator_state_pos` | actuator 真实反馈位置 | `10/11/12` | 用于拆 `state -> joint` |
| `actuator_cmd -> actuator_state` | 通信 / 驱动接受段 lag | `10/11` | 当前不是主瓶颈 |
| `actuator_state -> joint_pos` | actuator 反馈到 joint-space 兑现段 lag | `11/12` | 当前执行链主滞后段 |
| `joint_pos -> sole_roll` | joint-space 到 foot-space 姿态残差 | `05/12C` | 当前 touchdown 主 residual |
| `sole_roll` | MuJoCo FK 中 foot body 的 roll 姿态 | `03/05/07-12` | 依赖 MJCF foot body frame，不是真机直接传感器 |
| `mean_abs_sole_roll` | 前若干 touchdown / 窗口中 `abs(sole_roll)` 的均值 | `05/11/12` | 用于量化脚底 roll 不平程度 |
| `mean_abs_ankle_roll_q` | touchdown 时 `abs(pos_<side>_ankle_roll_joint)` 的均值 | `05` | 用于判断 joint-space 角是否足以解释 foot-space roll |
| `roll_to_joint_gain_ratio` | `abs(sole_roll) / max(abs(ankle_roll_q), 1e-6)` | `05` | 高值表示 foot-space 相对 joint-space 异常放大；分母很小时只作启发式 |
| `fk_foot_frame_residual_candidate` | joint 角不大但 FK `sole_roll` 大，pitch 参与低 | `05C` | 降级后的候选标签；必须先验证 FK foot frame，再判断真实接触边缘 |
| `pitch_roll_coupled_contact_residual` | touchdown 残差中 pitch 也明显参与 | `05C` | 不能按纯 roll 边缘问题处理 |
| `dead_zone_dominant` | swing 期目标幅值长期落在小信号区，lag 优先按死区理解 | `13` | 不解释 touchdown contact residual |
| `mixed_dead_zone_and_realization` | swing lag 同时有小信号和执行兑现不足成分 | `13` | 后续需继续分离 |
| `realization_dominant` | 输出幅值不小但兑现仍差 | `12/13` | 再考虑结构性迟滞、摩擦、回差 |
