# Forward X Failure Progress Review

本文件是 `forward_x_failure` 系列结果的统一入口，用于避免后续文档之间出现口径冲突。

## 当前总判断

### 审计更新（2026-05-06）

基于仿真对比后的逻辑复核，`03/05` 的旧主结论已经被部分推翻，详见：

- [16_real_round3_logic_audit_after_sim_contrast.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/16_real_round3_logic_audit_after_sim_contrast.md:1)

当前必须采用的新口径是：

1. 真机确实存在 `forward_x_failure`，仿真稳定前走这一事实不应和真机混用。
2. 旧版 `03` 把 MuJoCo FK 的 `link_*_ankle_roll` raw body 姿态直接当成脚底平面姿态，导致：
   - `8/8 severe_foot_flat_touchdown`
   - `8/8 roll dominant`
   - `mean foot-flat error ≈ 1.6766 rad`
   
   这些结论被固定 frame 偏置显著污染，现已失效。
3. 校准后，真机 `t26` 的前 `8` 个 touchdown 平均 residual 约为 `0.2441 rad`，不再是旧版 `1.6766 rad`。
4. 真机 `03` 校准后变为：
   - dominant axis: `pitch 6/8`, `roll 2/8`
   - three-layer root cause: `coupled_geometry 3 / command_not_flat 3 / tracking_lag 1 / residual_not_large_enough 1`
5. 真机 `05C` 不再支持旧版的强收口。校准后 `05C` 的四个 actuator-state case 分别落在：
   - `mapping_workpoint_residual`
   - `mixed_or_uncertain_contact_residual`
   - `pitch_roll_coupled_contact_residual`
   - `contact_geometry_residual`
6. `06` 延迟链本身仍有效，但只能保留为执行链并发问题，不能再和旧版 raw foot-frame 结论绑定。

### 当前收口（基于 real/sim 对照与视频事实，2026-05-06）

18/19/20 的统一结论已经单独落到：

- [21_real_vs_sim_combined_conclusion.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/21_real_vs_sim_combined_conclusion.md:1)
- [22_forward_x_failure_consistency_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/22_forward_x_failure_consistency_audit.md:1)
- [23_forward_x_failure_stage_report.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/23_forward_x_failure_stage_report.md:1)

当前 canonical 收口是：

> `real forward_x_failure` 不是单一的 roll 外翻、单一 output 延迟或单一 `kp/kd` 问题，而是 touchdown 几何 / 接触残差已经越过 sim 稳定前走时的可接受包络，并与执行链 `state -> joint -> sole` 残差放大叠加；高 `kp` 进一步把这种越界残差表现成 swing / touchdown 阶段更重的真实 joint 抖动，尤其 touchdown 最明显，最终破坏有效支撑和前向推进。

当前必须统一采用下面这套收口：

1. **real 确实存在 `forward_x_failure`**  
   试验现象是：
   - x 前进不足
   - 视觉上脚掌会以 roll 方向先触地，并伴随 roll 方向抖动
   - 降低 `kp` 后，roll 抖动减轻，可以稳定原地踏步，但仍然不前进

2. **sim 不存在 `forward_x_failure`**  
   试验现象是：
   - 四组 `kp/kd` 都能正常前进
   - 左脚存在轻微 roll 外翻触地，但不抖动
   - 右脚基本正常，整体仍能稳定形成前向推进

3. **因此，real 的错误不能再表述成“只要看到 roll 触地就是主因”**  
   因为 sim 也有左脚轻微 roll 外翻，但仍能正常前进。  
   真正需要解释的是：**为什么 real 的 touchdown residual 已经越过了 sim 可接受包络，并进一步破坏了前向推进。**

4. **当前最可信的 real 主问题不是单一 `command_not_flat`，也不是单一执行链 lag**  
   经过校准后，real 真正超出 sim 可接受范围的项是：
   - 双侧 `pitch residual` 系统性偏大
   - 右脚不再接近水平
   - 左脚 roll 峰值偏大
   - `joint -> sole` residual 放大链过重

5. **`kp` 降低后能减轻抖动、但仍不能前进，说明 `kp` 更像放大器，不是根因**  
   这说明：
   - 高 `kp` 会放大 roll 方向抖动
   - 但即使抖动减轻，touchdown 几何 / 接触残差仍然超限，支撑相位仍无法形成有效前向推进

6. **当前最稳妥的 real 阶段错误定位**  
   `forward_x_failure` 现在更应定位为：

   > real 阶段的 touchdown 几何 / 接触残差已经整体超出 sim 中“仍可稳定前走”的可接受范围；  
   > 其中以双侧 `pitch residual` 系统性超限最明显，并叠加执行链 `joint -> sole` 残差放大与高 `kp` 诱发的 roll 抖动，最终导致机器人只能原地踏步或前进不足。

7. **`20/24/25` 触地检测修正后，real 仍有更重 joint 调整负担**  
   旧 `left/right_contact` 是 ankle-pitch 低速 proxy，会污染早期 touchdown 序列；已改为 FK 足端高度/速度为主、hip pitch 相位校验的 kinematic detector。新检测器下 real/sim 步态周期一致，且 real 前 4 次 touchdown 恢复正常交替。
   - roll `swing`: real/sim joint `hp_rms = 3.22x`，`range = 2.94x`，`path_length = 3.90x`，方向变化频率 `1.18x`
   - roll `touchdown`: real/sim joint `hp_rms = 1.76x`，`range = 2.08x`，`path_length = 2.26x`，方向变化频率 `0.80x`
   - pitch `swing`: real/sim joint `hp_rms = 1.28x`，`range = 1.43x`，`path_length = 1.50x`
   - pitch `touchdown`: real/sim joint `hp_rms = 0.74x`，但 `range = 1.69x`、`path_length = 1.23x`

   这说明：
   - sim 确实存在轻微左脚外翻，但 swing / touchdown 阶段的实际 joint 调整幅值、路径和兑现误差整体更轻
   - real 的 touchdown 结论需要从“roll/pitch 高频都更重”修正为：**roll touchdown 的幅值/路径/高频仍更重；pitch touchdown 主要是幅值、路径和兑现误差更重，高频不再高于 sim**
   - 因此“降低 `kp` 后抖动减轻但仍不前进”的现象，与“`kp` 是放大器、主因仍是 residual 越界”这一判断一致

### 阶段性结论快照（2026-05-05）

以下内容是 **2026-05-05 的历史快照**，已被 2026-05-06 审计更新部分 supersede，仅保留作过程记录。

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
| `01` landing window diagnosis | done / superseded-by-audit | 旧主旗标 `severe_foot_flat_touchdown` 被 frame 偏置审计降级；窗口化诊断信号仍有参考价值 | 不直接进入低速复测，先做 `05D` |
| `02` low speed validation | blocked | touchdown 姿态问题未关闭 | 暂停执行 |
| `03` ankle landing attitude | done / superseded-by-audit | 旧 `8/8 roll` 和 `command_not_flat 4` 降级；校准后 real 为 `pitch 6/8, roll 2/8` | 不再作为当前修复入口 |
| `04` tracking lag repair | done / reinterpreted | 单轴 right-roll 扫参不能关闭问题，只在多个标签间转移表现 | 不继续盲扫 ankle `kp/kd` |
| `05A/05B` geometry/code check | done | controller offset、YAML direction、简单 actuator ownership/sign bug 基本排除 | 残差转向 foot-space / contact |
| `05C` contact residual classification | done / superseded-by-audit | 旧 `fk_foot_frame_residual_candidate 3/4` 强收口降级；校准后标签分散 | 下一步做 `05D`，先验证 FK foot frame，再验证真实接触边缘 |
| `06` delay chain | done | `action -> target` 近似 0，主要延迟在执行链 | output 不是主瓶颈 |
| `07/08` windowed roll origin | done | `sole_roll` 更偏执行链响应，不直接跟随 output | 保留执行链放大器，同时不替代几何残差 |
| `09` phase lag / limit cycle | done | 高 kp 有局部相位滞后放大，但未形成稳定限环 | 高 kp 是放大器，不是唯一根因 |
| `10` execution chain disentanglement | done | actuator-state 实测继续支持执行链主导，主滞后更偏 `actuator_state -> joint_pos` | 进入 `11/12` |
| `11` execution chain lag | done | `state -> joint` 大 lag 在 swing 期已存在，慢侧不固定 | 不能收口为单侧固定硬件故障 |
| `12` realization probe | done | `state -> joint` 存在不健康兑现，但只能解释一部分现象 | touchdown 主残差仍交给 `05` |
| `13` dead-zone audit | done | swing `pos_des_raw` 小信号特征稳定存在 | swing lag 不能默认先归机械结构 |
| `20` real vs sim jitter compare | done | real 在 `swing / touchdown` 的实际 joint 高频抖动都高于 sim，touchdown 差异更大 | `kp` 放大器定位进一步坐实；real 不只是残差大，也更抖 |

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
| `severe_foot_flat_touchdown` | pre-audit raw FK foot-frame 口径下的 touchdown 严重不平标签 | `01/03` | 已被 2026-05-06 frame 偏置审计降级；不再作为当前主阻塞项 |
| `foot_clearance_deficit` | 摆动脚相对支撑脚高度不足 | `01` | 并发问题，当前不是第一修复入口 |
| `hip_knee_tracking_lag` | 髋/膝摆腿目标或实际响应不足 / 延迟 | `01` | 并发问题，待踝 touchdown 主因收敛后复判 |
| `command_not_flat` | touchdown 前目标本身不足以把脚底调平 | `03/04` | 早期三层判因之一；旧 sim/real 强判断已降级，不能作为当前第一修复入口 |
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
