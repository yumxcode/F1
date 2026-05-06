# Round 3C Coupled Geometry 排查计划

状态：`active`。本专项由 [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/04_tracking_lag_repair.md:1) 直接触发。

## ⚡ 当前进度速览

| 子阶段 | 状态 | 结论摘要 |
|---|---|---|
| `05A` Zero Bias Check | ✅ 完成 | controller offset、YAML direction 排除；风险在 `ankle_transmission.cc` 硬编码符号链 |
| `05B` Parallel Mapping Verification（代码侧） | ✅ 完成 | 无简单 sign bug；残差归到 mirrored code package + 机构/接触 residual |
| `05B-2` 硬件侧（left/right ankle 对称阶跃对比） | ⬜ **未执行** | 计划中，仍待现场执行 |
| `05B-3` 接触侧（足底状态检查） | ⬜ **未执行** | 计划中，与 05D Phase 2 合并 |
| `05C` Touchdown Contact Residual Classification | ✅ 完成 | `fk_foot_frame_residual_candidate 3/4`，`pitch_roll_coupled_contact_residual 1/4` |
| `05D` FK Foot-Frame / Contact 现场复核 | ⬜ **当前唯一待执行项** | Phase 0-4 均未执行，是全项目当前第一优先级 |

> 结果详见 [results/05_coupled_geometry_probe.md](../../results/forward_x_failure/05_coupled_geometry_probe.md)

## 进入条件

当前进入本专项的依据已经满足：

- `severe_foot_flat_touchdown` 仍是所有有效样本前几步的稳定主问题
- 单独调 `right_ankle_roll_joint` 参数不能关闭主问题
- 当 4 个 ankle 全部调软到 `25 / 0.5` 后：
  - 脚掌多余抖动明显减轻
  - 稳定性提升
  - 但前进不足依旧
  - 前 `4` 步根因收敛为 `coupled_geometry 3 / 4 + command_not_flat 1 / 4`

在正式进入 `05` 之前，结合最新 `13_dead_zone_audit`，需要先把边界重新划清：

- `swing` 期的小幅 `pos_des_raw` 已被 `13` 证明存在稳定死区 / 阈值敏感区特征；
- 因此 `swing` 期的一部分 lag 不应再默认归到几何残差；
- `05` 现在只接管 **touchdown residual** 和 **几何 / 映射 residual**，不再把 swing 小信号兑现不足当作主解释对象。

这说明当前最值得优先解释的是：

- 为什么执行链抖动被压住后，脚底仍以错误几何姿态 touchdown
- 为什么这种错误姿态会进一步限制前向推进

## 目标

把当前的 `coupled_geometry` 从“单轴解释不完”的标签，收紧成可执行的几类几何/映射问题：

1. `roll_axis_sign_or_zero_bias`
2. `pitch_roll_coupling_mismatch`
3. `parallel_mapping_mismatch`
4. `touchdown_contact_geometry_bias`

并给出下一轮最小验证动作，而不是继续盲目扫 ankle 参数。

同时明确 `05` 的边界：

- `swing` 期若 `pos_des_raw` 已落入死区 / 阈值敏感区，则先由 `13_dead_zone_audit` 解释；
- `05` 仅负责 touchdown 窗内仍然存在的几何残差；
- 不再把 `swing` 期小信号 lag 直接转写成几何故障。

## 当前核心假设

### H1. `roll_axis_sign_or_zero_bias`

含义：

- 关节/电机零位、方向或模型零位存在偏差
- 导致脚底在“看起来命令不大”的情况下仍以带偏置的 `roll` 姿态 touchdown

应有特征：

- 同侧 touchdown 的 `sole_roll_touch_rad` 符号稳定
- `ankle_roll` 关节位置本身不一定大，但脚底 `roll` 姿态持续偏单侧

### H2. `pitch_roll_coupling_mismatch`

含义：

- 单看 `ankle_roll` 或 `ankle_pitch` 的误差都不算极端
- 但两轴组合后，脚底法向仍明显偏斜

应有特征：

- `ankle_tracking_dominant_axis` 不稳定或经常切到 `ankle_pitch / coupled`
- `sole_roll_touch_rad` 为主，但 `sole_pitch_touch_rad` 不可忽略

### H3. `parallel_mapping_mismatch`

含义：

- 并联踝 joint-space 到 actuator-space 的映射、雅可比或零点约定存在问题
- 导致电机力矩/位置在脚底几何上没有形成预期效果

应有特征：

- 调软 4 个 ankle 后高频抖动下降，但 `coupled_geometry` 仍主导
- 说明“力太大”不是主因，映射关系本身更可疑

### H4. `touchdown_contact_geometry_bias`

含义：

- 真机触地接触面、鞋底/足底接触线、地面接触偏置，和模型里的脚底几何不一致

应有特征：

- 关节层指标不算极端
- 但 touchdown 姿态长期偏向某一类接触边缘

## 排查策略

### Phase A. 基于前几步的 touchdown 姿态聚类

只看前 `4` 个 touchdown，统计：

- `sole_roll_touch_rad`
- `sole_pitch_touch_rad`
- 左右脚符号与量级

目标：

- 判断是否存在稳定单侧偏置
- 判断 `roll` 是否始终主导
- 判断 pitch 是否在若干样本中明显参与
- 与 `13` 的 swing dead-zone 口径分开：这里只解释 touchdown residual，不回头吃掉 swing 小信号兑现不足

输出：

- `左/右脚 touchdown 姿态分布表`
- `roll_positive / roll_negative` 计数
- `pitch 次级参与度` 统计

### Phase B. joint-space 与 foot-space 的偏置对照

对每个 touchdown 比较：

1. `ankle_pitch_joint / ankle_roll_joint` 实际位置
2. `sole_pitch / sole_roll`
3. `ankle_pitch_err_touch / ankle_roll_err_touch`

目标：

- 判断是关节位置本身偏了，还是“关节看着不大，脚底几何却偏得很厉害”

输出：

- `joint_to_sole_bias_table`
- `关节偏置 vs 脚底姿态偏置` 排序表

### Phase C. 并联映射一致性检查

沿代码和日志对照排查：

1. 并联踝左右 actuator 的方向符号
2. joint -> actuator 的 `position / velocity / effort / kp / kd` 赋值关系
3. 当前 walk 路径里 actuator MIT 实际是否退化为 torque-only
4. 这种退化是否会放大脚底几何偏置

目标：

- 判断问题主要在“动力太大”，还是在“映射关系不对”

输出：

- `mapping_consistency_checklist`
- `高风险映射点列表`

### Phase D. 触地接触偏置假设复核

如果 A/B/C 之后仍无法解释，则单独列出接触几何偏置假设：

- 脚底接触面与模型不一致
- 足底滚动中心与 FK body 参考点不一致
- 触地判定脚底刚性面与真实接触边缘不一致

目标：

- 避免把所有几何残差都误归因到控制器

## 需要产出的具体材料

1. `coupled_geometry_touchdown_table.csv`
   - 每次前 `4` 步 touchdown 的：
   - `sole_pitch / sole_roll`
   - `ankle_pitch / ankle_roll q`
   - `ankle_pitch / ankle_roll err`
   - `touchdown_attitude_type`
   - `suspected_geometry_mode`

2. `coupled_geometry_summary.md`
   - 说明当前更像哪一种几何问题

3. `mapping_consistency_notes.md`
   - 沿代码链路记录映射一致性检查结果

## 分析脚本

- 主脚本：
  - [.oma/sim2real/plans/forward_x_failure/scripts/05a_coupled_geometry_probe.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05a_coupled_geometry_probe.py:1)
  - [.oma/sim2real/plans/forward_x_failure/scripts/05b_zero_bias_and_mapping_check.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05b_zero_bias_and_mapping_check.py:1)
  - [.oma/sim2real/plans/forward_x_failure/scripts/05c_coupled_geometry_cross_kp_compare.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05c_coupled_geometry_cross_kp_compare.py:1)
  - [.oma/sim2real/plans/forward_x_failure/scripts/05d_swing_attitude_cross_kp_compare.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05d_swing_attitude_cross_kp_compare.py:1)
  - [.oma/sim2real/plans/forward_x_failure/scripts/05e_parallel_mapping_verification.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05e_parallel_mapping_verification.py:1)
  - [.oma/sim2real/plans/forward_x_failure/scripts/05f_touchdown_geometry_residual_collection.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05f_touchdown_geometry_residual_collection.py:1)
  - [.oma/sim2real/plans/forward_x_failure/scripts/05g_touchdown_contact_residual_classification.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05g_touchdown_contact_residual_classification.py:1)
- 当前脚本职责：
  - 直接复用 `03a/03b` 的 touchdown 检测、FK 和三层判因逻辑
  - 只取最新有效日志的前 `4` 个 touchdown
  - 产出 `coupled_geometry_touchdown_table.csv`
  - 产出 `coupled_geometry_summary.md`
  - 产出 `mapping_consistency_notes.md`
  - 产出 `round3_zero_bias_and_mapping_check.md`
  - 横向产出 `round3_coupled_geometry_cross_kp_compare.md`
  - 补充摆动腿腾空期产出 `round3_swing_attitude_cross_kp_compare.md`
  - 产出 `round3_touchdown_geometry_residual_collection.md`
  - 产出 `round3_touchdown_contact_residual_classification.md`

## 本阶段通过标准

满足以下任一条，即认为 `coupled_geometry` 已从模糊标签进入可执行状态：

1. 能明确指出主导问题更像：
   - `zero_bias`
   - `pitch_roll_coupling`
   - `parallel_mapping_mismatch`
   - `contact_geometry_bias`
2. 能给出下一轮最小验证动作，并且该动作不再是单纯扫 ankle `kp/kd`

补充判据：

- 若 touchdown residual 已能被 `05` 解释，而 swing lag 被 `13` 解释，则 `05` 的边界收口成立。

## 下一步动作

1. ✅ 先基于现有有效日志，产出 `前 4 步 touchdown 几何聚类表`（`05A`，已完成）
2. ✅ 再沿代码做并联映射一致性检查（`05B` 代码侧，已完成）
3. ✅ 执行 `05A zero bias check`（只负责 touchdown residual，已完成）
4. ✅ 进入 `05B parallel mapping verification`
   - ✅ 代码侧验证 left/right actuator ownership 自洽，简单 sign bug 已排除
   - ✅ 残差收敛到：mirrored code package + 机构/映射表失配 + `joint_pos -> sole_roll` foot-space / contact residual
   - ⬜ `05B-2` 硬件侧（left/right ankle 对称阶跃对比）**未执行**
   - ⬜ `05B-3` 接触侧（足底状态检查）**未执行**（与 05D Phase 2 合并）
5. ✅ 进入 `05C touchdown contact residual classification`
   - ✅ swing 小信号死区由 `13` 接管，已明确边界
   - ✅ `actuator_state -> joint_pos` realization lag 由 `12` 接管，已明确边界
   - ✅ 当前分类结果：`fk_foot_frame_residual_candidate = 3/4`，`pitch_roll_coupled_contact_residual = 1/4`
   - ⬜ `05D` **当前第一优先级**：现场校准 FK foot frame → 拆分 `real_contact_edge_bias / foot_frame_reference_mismatch / dynamic_contact_deformation_or_release`

## 动态 Touchdown 检查计划

只保留 `walk` 前几步 touchdown 阶段的动态检查项，不使用静态 `zero/stand` 站姿作为主判断依据。

### 检查窗口

- 每次只看进入 `walk` 后前 `4` 个 touchdown
- 每个 touchdown 取：
  - `first_contact - 50 ms`
  - `touchdown`
  - `touchdown + 100 ms`

### 检查项 A：脚底姿态与接触顺序（✅ 已完成）

1. 记录 `sole_roll_touch_rad / sole_pitch_touch_rad`
2. 判断左右脚 touchdown 时是否持续保持：
   - 左脚一侧固定符号
   - 右脚相反符号
3. 目测确认：
   - 是否总是同一边缘先着地
   - 是否 touchdown 后立刻出现接触抖动

通过标准：

- 若左右脚持续呈镜像 `roll` 偏置，则继续优先怀疑 `parallel_mapping / sign convention / foot-space geometry`

### 检查项 B：接触后短时抖动（✅ 已完成）

1. 观察 `touchdown ~ +100 ms` 内：
   - 脚掌是否在地面 `roll` 方向高频来回打
2. 对比高 `kp` 与低 `kp`：
   - 高 `kp` 是否放大抖动
   - 低 `kp` 是否只压住抖动，但不改变 touchdown 初始偏置方向

通过标准：

- 若抖动只随 `kp` 变化，而 touchdown 初始偏置方向不变，则 `kp` 不是主因，只是表现放大器

### 检查项 C：左右踝动态对称性（✅ 已完成，见 05B 横向对比）

1. 对比左右脚前 `4` 步的：
   - `ankle_roll_q_touch_rad`
   - `ankle_roll_err_touch_rad`
   - `sole_roll_touch_rad`
2. 判断是否存在：
   - 关节量不大，但脚底量始终很大
   - 左右脚保持镜像而非随机漂移

通过标准：

- 若 `joint-space` 小、`foot-space` 大，且左右脚镜像稳定，则继续支持 `coupled_geometry -> parallel_mapping_mismatch`

### 检查项 D：硬件性能衰减触发迹象（✅ 已分析，结论见 05 结果文档）

1. 在 touchdown 后 `+100 ms` 内对比左右脚：
   - 是否单侧更容易抖
   - 是否单侧更容易粘滞后再突然释放
   - 是否单侧回程明显更慢
2. 结合现场视频/手感记录：
   - 是否存在单侧支链松旷、摩擦、回差异常

通过标准：

- 若镜像偏置结构长期存在，但只有某一侧动态响应变差，则提高“硬件性能衰减/机械问题”优先级

### 检查项 E：05C FK foot-frame residual candidate（✅ 05C 完成；⬜ 05D 现场验证待执行）

1. 对齐日志 touchdown timestamp 和现场视频：
   - 只看进入 `walk` 后前 `4` 个 touchdown
   - 判断是否固定内侧或外侧边缘先接触
2. 复核 foot frame 与真实接触面：
   - FK 里的 `link_*_ankle_roll` foot body frame 是否对应真实脚底板平面
   - 鞋底/脚底是否存在磨损、变形、松动或局部凸起
3. 对 `pitch_roll_coupled_contact_residual` 单独标注：
   - 若 `sole_pitch` 参与明显，不能按纯 roll 边缘问题处理
   - 需要同步看 pitch 触地角、膝伸展时机和足底滚动路径

通过标准：

- 若多数 case 仍是 `fk_foot_frame_residual_candidate`，则下一轮优先执行静态 FK foot-frame 校准，再决定是否修 contact frame
- 若 `pitch_roll_coupled_contact_residual` 占比上升，则回到 `pitch + roll` 联合 touchdown 姿态，而不是只看 roll

## 05D FK Foot-Frame / Contact 现场试验方案（⬜ 全部待执行，当前第一优先级）

> **状态**：Phase 0-4 均未执行。这是当前整个 `forward_x_failure` 问题的唯一第一优先级。

### 试验目标

围绕 `05C` 的主结论继续下钻：

**touchdown 时 `joint-space` 角度不大但 FK `sole_roll` 很大。先判断这个 FK `sole_roll` 是否能代表真实脚底接触平面；如果能，再判断是否是实际接触边缘导致。**

这里的 `joint-space` 角度特指日志中的：

- `pos_left_ankle_roll_joint`
- `pos_right_ankle_roll_joint`

取法是：在每次 touchdown 时间点，用该时间点之前最近一帧日志中的 `pos_{side}_ankle_roll_joint` 作为 `ankle_roll_q_touch_rad`，再对前 `4` 个 touchdown 求 `mean_abs_ankle_roll_q`。

### Phase 0：FK 指标口径确认（⬜ 待执行）

目的：在不让机器人运动的情况下，把 FK 指标、MJCF body frame、真实脚底测量字段和现场记录模板统一起来，避免后续把 FK 派生姿态误读成真实脚底姿态。

执行步骤：

1. **确认 FK 源头**
   - 打开 `real2sim/round3_landing_window_analysis.py`。
   - 确认 `FOOT_BODIES` 当前为：
     - `left -> link_left_ankle_roll`
     - `right -> link_right_ankle_roll`
   - 确认 `sole_roll / sole_pitch` 的计算链路为：
     - 读取日志 `base_euler_x/y/z`
     - 读取 `pos_<joint>`
     - `mujoco.mj_forward`
     - 读取 `data.xmat[link_*_ankle_roll]`
     - `matrix_to_roll_pitch_yaw`

2. **统一字段命名**
   - 后续现场记录和结果表中，FK 派生量统一写成：
     - `fk_body_name`
     - `fk_sole_roll_rad`
     - `fk_sole_pitch_rad`
     - `fk_sole_normal_z`
   - 外部实测量统一写成：
     - `measured_sole_roll_rad`
     - `measured_sole_pitch_rad`
     - `measurement_method`
   - 接触观测统一写成：
     - `contact_edge_label`
     - `contact_mark_evidence`
     - `video_evidence`

3. **建立 frame 定义表**
   - 为左右脚各建一行，表名为 `fk_frame_definition_check`。
   - 至少包含下面字段：
     - `side`
     - `fk_body_name`
     - `mjcf_body_parent`
     - `fk_frame_claim`
     - `real_sole_plane_definition`
     - `contact_layer_definition`
     - `known_offset_or_unknown`
     - `phase1_required`
   - `fk_frame_claim` 只能写保守描述，例如 `ankle_roll_link_body_frame`，不能写 `real_sole_plane`，除非 Phase 1 已验证。

4. **准备现场记录模板**
   - 建立 `05d_fk_foot_frame_contact_template.csv` 或同等表格。
   - 表头至少包含：
     - `case_id`
     - `phase`
     - `side`
     - `pose_name`
     - `commanded_ankle_roll_rad`
     - `commanded_ankle_pitch_rad`
     - `logged_ankle_roll_rad`
     - `logged_ankle_pitch_rad`
     - `fk_sole_roll_rad`
     - `fk_sole_pitch_rad`
     - `measured_sole_roll_rad`
     - `measured_sole_pitch_rad`
     - `measurement_method`
     - `contact_edge_label`
     - `evidence_file`
     - `operator_note`

5. **设定 Phase 1 判定阈值**
   - 静态 FK 与真实测量的建议容差：
     - `abs(fk_sole_roll_rad - measured_sole_roll_rad) <= 0.05 rad`
     - `abs(fk_sole_pitch_rad - measured_sole_pitch_rad) <= 0.05 rad`
   - 若符号不一致，即使绝对误差较小，也标记为 `frame_sign_mismatch_risk`。
   - 若任一侧超过容差，Phase 3 的动态视频不能直接用 FK `sole_roll` 量级下结论。

6. **更新现场口径**
   - 所有后续记录里禁止单独写 `sole_roll` 表示真实脚底 roll。
   - 未通过 Phase 1 前，只能写 `fk_sole_roll_rad`。
   - `fk_foot_frame_residual_candidate` 继续保持候选标签，不升级为 `real_contact_edge_bias`。

通过标准：

- 完成 `fk_frame_definition_check` 表。
- 完成 `05d_fk_foot_frame_contact_template.csv` 或等价记录模板。
- 明确 Phase 1 的 roll/pitch 容差和符号一致性判据。
- 文档和现场记录字段中不再把 FK `sole_roll` 直接写成真实脚底 roll。

### Phase 1：静态 Foot-Frame 对齐（⬜ 待执行）

目的：确认 FK foot frame 的“脚底平”是否等于真实脚底板平。

执行：

1. **主测量采用悬空 / 上架无接触状态。**
   - 机器人必须上架、安全吊挂或支撑到脚底离地。
   - 目的不是测试接触，而是测试“同一组 joint 角下，FK foot frame 和真实脚底平面是否一致”。
   - 不要让脚底受地面挤压，否则鞋底变形、回差和接触边缘会混进 frame 校准。
2. **可选复核采用轻触地 / 站立承重状态。**
   - 只在悬空测量完成后做。
   - 轻触地用于看接触层压缩后是否改变脚底平面。
   - 站立位用于记录实际工作姿态，但不能替代悬空 frame 校准。
3. 悬空状态下分别进入：
   - 零位
   - 站立位
   - 左右 ankle roll 小角度扫描：`-0.10 / 0 / +0.10 rad`
   - 左右 ankle pitch 小角度扫描：`-0.10 / 0 / +0.10 rad`
4. 记录日志中的：
   - `pos_left/right_ankle_roll_joint`
   - `pos_left/right_ankle_pitch_joint`
   - FK 输出的 `fk_sole_roll / fk_sole_pitch`
5. 用简易方法测真实脚底板相对地面的 `measured_sole_roll / measured_sole_pitch`。

简易测量方法：

1. **手机角度计方法，优先推荐。**
   - 在脚底板上贴一块小平板、硬卡片或亚克力片，保证它贴合真实接触平面。
   - 手机打开系统指南针 / 水平仪 / angle meter app。
   - 手机短边横跨脚底左右方向，读 `roll`；手机长边沿前后方向，读 `pitch`。
   - 每个姿态读 `3` 次，取中位数。
   - 左右脚测量方向必须一致；若换边后手机方向反了，需要记录 `measurement_sign_convention`。
2. **纸片 / 楔块塞尺方法。**
   - 用一块平板贴住脚底接触面。
   - 观察内外侧或前后侧哪边先接触，另一侧用纸片、卡片或薄垫片塞入直到刚好接触。
   - 记录垫片厚度差 `delta_h` 和脚底宽度 / 长度 `L`。
   - 近似角度：`angle_rad = atan(delta_h / L)`。
   - 用于判断是否存在明显固定偏置；精度不如手机角度计。
3. **直尺 + 拍照方法。**
   - 在脚底边缘贴两到三个高对比标记点。
   - 手机固定在正前 / 正侧方，尽量远拍减少透视。
   - 用照片中左右或前后两点高度差估算 `atan(delta_h / L)`。
   - 只作为备选，用于确认符号和大偏差，不作为唯一精确量。

判定：

- 若静态下 FK 与真实脚底平面固定偏差大于 `0.05 rad` 或符号不一致，先归为 `foot_frame_reference_mismatch`。
- 若静态下 FK 与真实脚底一致，才允许进入 Phase 2，把 touchdown 大 roll 当作真实接触问题继续查。
- 若只有简易测量，建议把 `0.05 rad` 作为强证据阈值，把 `0.03 ~ 0.05 rad` 作为灰区；灰区需要重复测量或换方法复核。

### Phase 2：足底/鞋底几何复核（⬜ 待执行）

目的：排除真实接触面已经变化。

检查：

1. 左右鞋底/脚底内外侧边缘是否磨损不一致。
2. 脚底板是否有翘曲、松动、局部凸起。
3. 足底橡胶或接触层是否厚度不均。
4. 用平面板贴合脚底，检查真实接触平面是否和结构件平面一致。

判定：

- 若脚底真实接触面有固定偏置，优先修 foot contact geometry，而不是继续调 ankle `kp/kd`。
- 若脚底物理几何正常，再进入动态 touchdown 验证。

### Phase 3：Touchdown 同步视频 / 接触证据（⬜ 待执行）

执行：

1. 只记录进入 `walk` 后前 `4` 个 touchdown。
2. 同步保存诊断日志和现场视频。
3. 视频至少包含：
   - 正前方或正后方，用于看内/外侧边缘
   - 侧方，用于看 heel/toe pitch 参与
4. 每一步人工标注：
   - `inner_edge_first`
   - `outer_edge_first`
   - `flat`
   - `heel_or_toe_pitch_participates`
   - `post_touch_roll_oscillation`
5. 优先增加至少一种接触证据：
   - 脚底内外侧贴薄纸 / 碳粉纸 / 压敏纸
   - 脚侧贴 AprilTag / ArUco / 标记点
   - 分区 FSR 或触点开关

判定：

- 若 Phase 1 已证明 FK frame 可信，且固定边缘先着地与 `fk_sole_roll` 符号稳定对应，则归为 `real_contact_edge_bias`。
- 若 Phase 1 未通过，即使视频有边缘接触，也不能直接使用旧 `sole_roll` 量级下结论，需要先修 foot frame 参考。
- 若 pitch 明显参与，则该步保留为 `pitch_roll_coupled_contact_residual`。

### Phase 4：高低 Kp 对照（⬜ 待执行，依赖 Phase 1 通过）

只做两组即可：

1. 低 `kp` 稳定组：`25/0.4 all_ankles` 或 `30/0.4 all_ankles`
2. 高 `kp` 对照组：`40/0.8 all_ankles`

判定：

- 若 Phase 1/2/3 已确认真实接触边缘，且高低 `kp` 的初始接触边缘一致，高 `kp` 只是抖动更强，则 `kp` 是放大器。
- 若高 `kp` 才出现边缘切换或明显打地，则说明接触非线性和高增益互相激发。
- 若 Phase 1 未通过，不执行本 Phase；先修 FK / foot frame 参考。

### 05D 输出分类

试验完成后，把 `fk_foot_frame_residual_candidate` 继续拆成：

1. `real_contact_edge_bias`
2. `foot_frame_reference_mismatch`
3. `dynamic_contact_deformation_or_release`

输出要求：

- 每个分类必须给出对应证据来源：`static_frame_check / sole_geometry_check / synced_video / contact_mark / kp_ablation`。
- 没有 Phase 1 静态校准证据时，不能把 FK `sole_roll` 当成真实脚底 roll 直接下结论。
