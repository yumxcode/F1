# Round 3C Coupled Geometry 排查计划

状态：`active`。本专项由 [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/04_tracking_lag_repair.md:1) 直接触发。

## 进入条件

当前进入本专项的依据已经满足：

- `severe_foot_flat_touchdown` 仍是所有有效样本前几步的稳定主问题
- 单独调 `right_ankle_roll_joint` 参数不能关闭主问题
- 当 4 个 ankle 全部调软到 `25 / 0.5` 后：
  - 脚掌多余抖动明显减轻
  - 稳定性提升
  - 但前进不足依旧
  - 前 `4` 步根因收敛为 `coupled_geometry 3 / 4 + command_not_flat 1 / 4`

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
- 当前脚本职责：
  - 直接复用 `03a/03b` 的 touchdown 检测、FK 和三层判因逻辑
  - 只取最新有效日志的前 `4` 个 touchdown
  - 产出 `coupled_geometry_touchdown_table.csv`
  - 产出 `coupled_geometry_summary.md`
  - 产出 `mapping_consistency_notes.md`
  - 产出 `round3_zero_bias_and_mapping_check.md`
  - 横向产出 `round3_coupled_geometry_cross_kp_compare.md`
  - 补充摆动腿腾空期产出 `round3_swing_attitude_cross_kp_compare.md`

## 本阶段通过标准

满足以下任一条，即认为 `coupled_geometry` 已从模糊标签进入可执行状态：

1. 能明确指出主导问题更像：
   - `zero_bias`
   - `pitch_roll_coupling`
   - `parallel_mapping_mismatch`
   - `contact_geometry_bias`
2. 能给出下一轮最小验证动作，并且该动作不再是单纯扫 ankle `kp/kd`

## 下一步动作

1. 先基于现有有效日志，产出 `前 4 步 touchdown 几何聚类表`
2. 再沿代码做并联映射一致性检查
3. 最后决定是：
   - 开 `05A zero bias check`
   - 还是开 `05B parallel mapping verification`

## 动态 Touchdown 检查计划

只保留 `walk` 前几步 touchdown 阶段的动态检查项，不使用静态 `zero/stand` 站姿作为主判断依据。

### 检查窗口

- 每次只看进入 `walk` 后前 `4` 个 touchdown
- 每个 touchdown 取：
  - `first_contact - 50 ms`
  - `touchdown`
  - `touchdown + 100 ms`

### 检查项 A：脚底姿态与接触顺序

1. 记录 `sole_roll_touch_rad / sole_pitch_touch_rad`
2. 判断左右脚 touchdown 时是否持续保持：
   - 左脚一侧固定符号
   - 右脚相反符号
3. 目测确认：
   - 是否总是同一边缘先着地
   - 是否 touchdown 后立刻出现接触抖动

通过标准：

- 若左右脚持续呈镜像 `roll` 偏置，则继续优先怀疑 `parallel_mapping / sign convention / foot-space geometry`

### 检查项 B：接触后短时抖动

1. 观察 `touchdown ~ +100 ms` 内：
   - 脚掌是否在地面 `roll` 方向高频来回打
2. 对比高 `kp` 与低 `kp`：
   - 高 `kp` 是否放大抖动
   - 低 `kp` 是否只压住抖动，但不改变 touchdown 初始偏置方向

通过标准：

- 若抖动只随 `kp` 变化，而 touchdown 初始偏置方向不变，则 `kp` 不是主因，只是表现放大器

### 检查项 C：左右踝动态对称性

1. 对比左右脚前 `4` 步的：
   - `ankle_roll_q_touch_rad`
   - `ankle_roll_err_touch_rad`
   - `sole_roll_touch_rad`
2. 判断是否存在：
   - 关节量不大，但脚底量始终很大
   - 左右脚保持镜像而非随机漂移

通过标准：

- 若 `joint-space` 小、`foot-space` 大，且左右脚镜像稳定，则继续支持 `coupled_geometry -> parallel_mapping_mismatch`

### 检查项 D：硬件性能衰减触发迹象

1. 在 touchdown 后 `+100 ms` 内对比左右脚：
   - 是否单侧更容易抖
   - 是否单侧更容易粘滞后再突然释放
   - 是否单侧回程明显更慢
2. 结合现场视频/手感记录：
   - 是否存在单侧支链松旷、摩擦、回差异常

通过标准：

- 若镜像偏置结构长期存在，但只有某一侧动态响应变差，则提高“硬件性能衰减/机械问题”优先级
