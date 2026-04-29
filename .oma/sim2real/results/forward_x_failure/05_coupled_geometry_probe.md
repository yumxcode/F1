# Round 3C Coupled Geometry 排查结果

轮次目标：在 `04_tracking_lag_repair` 已经证明“单独扫 ankle kp/kd 不能收敛主问题”的基础上，进一步回答：

1. 抖动压住后，脚底为什么仍以错误几何姿态 touchdown
2. 当前更像 `zero_bias`、`pitch_roll_coupling`、`parallel_mapping_mismatch`，还是 `contact_geometry_bias`

## 数据与脚本

- 当前首轮分析数据：
  - [t27_tracking_lag_b1_diag_20260428_164817.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv)
- 专项脚本：
  - [05a_coupled_geometry_probe.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05a_coupled_geometry_probe.py:1)
  - [05c_coupled_geometry_cross_kp_compare.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05c_coupled_geometry_cross_kp_compare.py:1)
  - [05d_swing_attitude_cross_kp_compare.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05d_swing_attitude_cross_kp_compare.py:1)
- 产出文件：
  - [t27_tracking_lag_b1_diag_20260428_164817_coupled_geometry_touchdown_table.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t27_tracking_lag_b1_diag_20260428_164817_coupled_geometry_touchdown_table.csv:1)
  - [t27_tracking_lag_b1_diag_20260428_164817_coupled_geometry_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t27_tracking_lag_b1_diag_20260428_164817_coupled_geometry_summary.md:1)
  - [t27_tracking_lag_b1_diag_20260428_164817_mapping_consistency_notes.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t27_tracking_lag_b1_diag_20260428_164817_mapping_consistency_notes.md:1)
  - [round3_zero_bias_and_mapping_check.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_zero_bias_and_mapping_check.md:1)
  - [round3_left_right_ankle_sign_chain.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_left_right_ankle_sign_chain.md:1)
  - [round3_coupled_geometry_cross_kp_compare.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_coupled_geometry_cross_kp_compare.md:1)
  - [round3_swing_attitude_cross_kp_compare.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_swing_attitude_cross_kp_compare.md:1)

## 本轮口径

- 仍采用“前 `4` 个 touchdown 优先”的口径
- 继续复用 `03a/03b` 的 touchdown 检测、FK 恢复和三层判因
- 在此基础上，新增两层几何判断：
  - `side_roll_sign_majority`
  - `cross_side_roll_pattern`

当前新增判断的核心思想是：

- 如果左右脚 touchdown 的 `sole_roll` 符号呈稳定镜像关系
- 同时 `ankle_roll q` 本身很小，但 `sole_roll` 很大
- 且 `foot-space / joint-space` 比例异常放大

则更像 `parallel_mapping_mismatch`，而不是直接归为 `roll_axis_sign_or_zero_bias`

## 主要结果

### 1. 当前前 4 步仍全部是 roll 主导

- `Dominant axis counts = {'roll': 4}`
- `Touchdown attitude counts = {'roll_positive_dominant': 2, 'roll_negative_dominant': 2}`

说明当前并不是 pitch 主导触地异常，而是稳定的 roll 主导不平触地。

### 2. 三层根因仍与前序判断一致

- `Three-layer root counts = {'coupled_geometry': 3, 'command_not_flat': 1}`

说明在 4 个 ankle 全部调软到 `25 / 0.5` 后：

- 执行链抖动已经明显下降
- `tracking_lag / filter_delay` 不再主导
- 但主问题没有消失，而是更明确地收敛到 `coupled_geometry`

### 3. refined geometry 判因已从 `zero_bias` 收紧到 `parallel_mapping_mismatch`

当前结果：

- `Suspected geometry mode counts = {'parallel_mapping_mismatch': 4}`
- `Side roll sign majority = {'left': 'positive', 'right': 'negative'}`
- `Cross-side roll pattern = bilateral_mirror_stable`

解释：

- 左脚 touchdown 的 `sole_roll` 稳定为正
- 右脚 touchdown 的 `sole_roll` 稳定为负
- 这种左右镜像关系是稳定的，不像随机零偏
- 同时 `ankle_roll_q_touch_rad` 很小，但 `sole_roll_touch_rad` 很大
- `roll_to_joint_gain_ratio` 异常高，说明 foot-space 倾斜相对 joint-space 运动被明显放大

因此这批样本当前更像：

- `parallel_mapping_mismatch`

而不是第一版启发式里过于宽泛的：

- `roll_axis_sign_or_zero_bias`

### 4. 当前首轮不支持把问题先归到 `pitch_roll_coupling_mismatch`

原因是：

- `sole_roll_touch_rad` 明显主导
- `sole_pitch_touch_rad` 很小
- 当前 `pitch` 参与不足以成为第一解释

所以 `pitch_roll_coupling_mismatch` 先保留，但不是首轮主线。

## 当前最可信的阶段结论

基于当前这组“4 ankles = 25 / 0.5”的首轮数据，可以先把 `05` 线收紧成：

1. 调软后抖动下降，说明“纯粹力太大”不是主问题本体
2. touchdown 仍稳定呈现左右脚镜像 `roll` 偏置
3. `ankle_roll q` 很小，但 `sole_roll` 很大
4. 因此当前更值得优先怀疑的是：
   - 并联踝 `joint -> actuator -> foot-space` 映射关系
   - joint-space 与 foot-space 的零位/方向约定
   - FK 参考脚体与真实足底接触几何之间的偏差

## 与延迟链、kp 扫参结果合并后的统一结论

后续的 `06 / 07 / 08 / 09` 分析把这条线进一步收紧为：

1. `sole_roll` 在 swing 和 touchdown 两个窗口里，整体更偏执行链响应，而不是即时 `output`。
2. 高 `kp` 会放大 touchdown 窗内的局部相位滞后，但没有形成稳定、可重复的周期限环。
3. 低 `kp` 能压住抖动，但并没有消掉稳定的左右镜像 `roll` 偏置。
4. 因此当前更像是：
   - 执行链延迟 + 接触非线性
   - 叠加并联踝几何/映射偏置
   - `kp` 只是在改变表现形式，而不是关闭主问题

所以 `coupled_geometry` 现在不应再被理解成“只靠延迟就能解释掉”的标签，而应被理解成：

**一个始终存在的几何/映射偏置，被执行链迟滞和接触工况进一步放大。**

## 05A Zero Bias Check 结果

基于：

- [05b_zero_bias_and_mapping_check.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05b_zero_bias_and_mapping_check.py:1)
- [round3_zero_bias_and_mapping_check.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_zero_bias_and_mapping_check.md:1)

当前得到 4 个直接结论：

1. `controller joint_offset` 不是当前 touchdown roll 偏置的直接来源
   - `left/right ankle pitch/roll joint_offset` 全部配置为 `0.0`

2. `dcu_x1.yaml` 的 ankle transmission `direction_left / direction_right` 也不是直接来源
   - 左右踝都配置成 `1.0 / 1.0`

3. 更高优先级的符号风险在 `ankle_transmission.cc`
   - 左踝 `TransformActuatorToJoint()` 中存在额外：
     - `qm5 *= -1`
     - `qm6 *= -1`
     - `q6 *= -1`
   - 右踝 `TransformActuatorToJoint()` 中不存在对应的同类处理
   - 这意味着 left/right 对称性并不是由 yaml 保证，而是部分硬编码在 C++ 符号链里

4. 映射表零位邻域本身是可达且平滑的
   - `ankle_trans_x1.yaml` 中最接近 `(q5=0, q6=0)` 的离散点为：
     - `q5 = 0.001402`
     - `q6 = 0.000769`
   - 说明“映射表根本没有零位附近数据”不是当前问题
   - 但局部导数显示 `q5/q6` 对 `qm5/qm6` 已经存在明显耦合，不是解耦的一轴一轴关系

因此这一步的收口是：

- `zero offset in controller config` 不是主因
- `yaml transmission direction` 不是主因
- 当前更像：
  - `parallel_mapping / sign-convention verification`

而不是继续把问题定义成纯 `zero_bias`

## 横向对比：不要只盯 `25 / 0.5`

基于：

- [05c_coupled_geometry_cross_kp_compare.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05c_coupled_geometry_cross_kp_compare.py:1)
- [round3_coupled_geometry_cross_kp_compare.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_coupled_geometry_cross_kp_compare.md:1)

当前已把这些数据放到同一个 `coupled_geometry` 视角下横向比较：

- `35 / 0.5 baseline`
- `35 / 0.5 retest`
- `50 / 0.8 right_roll`
- `40 / 0.8 right_roll`
- `25 / 0.5 right_roll`
- `4 ankles = 25 / 0.5`

### 1. 高 `kp` 和低 `kp` 都保留了同一个几何签名

6 组有效数据前 `4` 步的共同点是：

- `cross_side_roll_pattern = bilateral_mirror_stable`
- `dominant_mode = parallel_mapping_mismatch`

这说明：

- `coupled_geometry` 不是低 `kp` 特有伪影
- 也不是某一组参数下偶然生成的现象
- 无论高 `kp` 还是低 `kp`，左右脚都稳定保留“左正右负”的镜像 `roll` 签名

### 2. `kp` 改变的是表象，不是镜像几何签名本身

横向结果显示：

- 高 `kp`：
  - 更容易在现场表现出 touchdown 后接触抖动
  - 但 `bilateral_mirror_stable` 仍在
- 低 `kp`：
  - 抖动减轻
  - 但 `bilateral_mirror_stable` 仍在

这说明：

- `kp` 更像是在调节“这个镜像几何问题如何被表现出来”
- 而不是决定“这个镜像几何问题是否存在”

### 3. 低 `kp` 甚至会让 foot-space / joint-space 放大更明显

`mean_roll_to_joint_gain_ratio`：

- `35 / 0.5 baseline`: `27.37`
- `50 / 0.8 right_roll`: `27.32`
- `40 / 0.8 right_roll`: `17.34`
- `25 / 0.5 right_roll`: `93.71`
- `4 ankles = 25 / 0.5`: `372.28`

这不是在说低 `kp` 更差，而是在说明：

- 当控制链被调软、抖动被压住后
- `foot-space` 相对 `joint-space` 的异常放大关系反而更裸露了

所以从 `coupled_geometry` 诊断角度看：

- 低 `kp` 不是把几何问题修掉
- 而是把执行链噪声降下去后，让几何/映射残差更清楚

### 4. 当前最可信的横向结论

把高 `kp` 和低 `kp` 一起看后，当前更合理的结论是：

1. 高 `kp` 下看到的接触抖动，并不推翻 `coupled_geometry`
2. 低 `kp` 下看到的稳定踏步，也不说明几何问题消失
3. 两端参数都保留了同一个稳定的左右脚镜像 `roll` 签名
4. 因此当前更像：
   - 一个始终存在的 `parallel_mapping / sign-convention / foot-space geometry` 问题
   - `kp` 只是改变了它在接触阶段的表现形式

## 补充：摆动腿腾空期的 pitch / roll 变化

基于：

- [05d_swing_attitude_cross_kp_compare.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05d_swing_attitude_cross_kp_compare.py:1)
- [round3_swing_attitude_cross_kp_compare.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_swing_attitude_cross_kp_compare.md:1)

又补了一层关键证据：左右摆动腿在腾空阶段就已经带着稳定的镜像 `roll` 偏置，而不是到 touchdown 才突然出现。

### 1. swing roll 镜像签名在高 kp / 低 kp 下都存在

对比：

- `35 / 0.5 baseline`
- `50 / 0.8 right_roll`
- `25 / 0.5 right_roll`
- `4 ankles = 25 / 0.5`

共同点：

- 左摆动腿 `sole_roll` 在腾空中段、touchdown 前 `20 ms`、touchdown 时刻都稳定为正
- 右摆动腿 `sole_roll` 在同样窗口内都稳定为负

这说明：

- 当前镜像 `roll` 偏置不是单纯 touchdown 后抖动带来的二次现象
- 更像 swing 阶段就已经存在的 foot-space 几何偏置

### 2. 高 kp 主要放大的是 swing 末段 pitch，而不是消除 roll 镜像

代表性对比：

- `50 / 0.8 right_roll`
  - 右摆动腿 `mean_abs_sole_pitch = 0.2746 rad`
  - 右摆动腿 `pitch@-20ms = -0.3917 rad`
- `25 / 0.5 right_roll`
  - 右摆动腿 `mean_abs_sole_pitch = 0.0342 rad`
  - 右摆动腿 `pitch@-20ms = -0.0698 rad`

说明：

- 高 `kp` 不只是把 touchdown 后的接触抖动放大
- 它还会把摆动末段，尤其右腿的 `pitch` 动作拉得更激进
- 低 `kp` 可以把这段压平，但没有消掉底层的 swing roll 镜像偏置

### 3. 对 coupled_geometry 的更新理解

当前更合理的连续链条是：

1. swing 阶段已经存在左右镜像 `roll` 偏置
2. touchdown 把这条偏置带入接触
3. 高 `kp` 进一步把它放大成：
   - 更激进的 swing pitch
   - 更明显的 touchdown 后 `roll` 高频抖动
4. 低 `kp` 则表现为：
   - 抖动减轻
   - 但镜像 `roll` 偏置仍保留

因此，`05` 线当前应统一看成三段连续表现：

- `swing-phase mirror roll bias`
- `touchdown mirror roll bias`
- `post-touch oscillation`

### 4. 与 06 延迟链的关系

基于 [06_delay_chain_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/06_delay_chain_probe.md:1) 的结果，需要把 `05` 线的解释边界再说清楚：

- `action -> target` 近似 `0 ms`
  - 所以 swing / touchdown 的镜像 `roll` 偏置，不能解释成 policy 输出链晚了
- `target -> current` 和 `current -> pos` 确实有延迟
  - 所以接触后的抖动里，执行链延迟是并发因素
- 但 `swing-phase mirror roll bias` 仍然存在
  - 说明 `coupled_geometry` 不是靠延迟链单独生成的

因此当前更稳妥的总口径是：

1. 几何/映射问题是底层主线
2. 执行链延迟是并发因素
3. 高 `kp` 时的抖动放大，是这两者叠加后的表象

## 新输入下的判断更新：硬件性能衰减优先级上升

新增现场事实：

- 这份代码此前是能正常走的
- 当前问题是在“代码未变”的前提下重新暴露出来

这会改变当前的优先级判断。

### 1. 代码静态不对称仍然成立，但它不再是“新问题突然出现”的充分解释

从代码看，left/right ankle transmission 确实存在静态不对称：

| 链路 | left ankle | right ankle |
|---|---|---|
| actuator -> joint position source | `qm5 <- actr_right`, `qm6 <- actr_left` | `qm5 <- actr_left`, `qm6 <- actr_right` |
| extra sign flip on `qm5` | `yes` | `no` |
| extra sign flip on `qm6` | `yes` | `no` |
| extra sign flip on `q6` | `yes` | `no` |
| joint -> actuator pitch target | `actr_right <- joint_pitch` | `actr_left <- joint_pitch` |
| joint -> actuator roll target | `actr_left <- joint_roll` | `actr_right <- joint_roll` |

这个不对称是真实存在的。

但如果：

- 同一份代码过去能稳定行走
- 现在没有引入新的 transmission 改动

那么这类静态不对称更像是**原本系统一直带着的结构约定**，而不是最近才突然生成的根因。

因此它当前更适合作为：

- `高风险解释框架`

而不是直接当成：

- `问题最近出现的唯一原因`

### 2. “以前能走，现在不走”会显著抬高物理损坏/性能衰减的先验概率

在当前证据下，优先级应上升的硬件类解释包括：

1. 并联踝某一侧执行器效率下降
   - 电机出力下降
   - 减速器/丝杠/传动摩擦上升
   - 供电或驱动能力衰减

2. 并联机构机械间隙、松动或局部损伤
   - 连杆松旷
   - 轴承或关节副异常
   - 左右两支链受力不一致

3. 编码器零位或传感器侧漂移
   - 电机侧零位仍“看起来正常”
   - 但 joint-space / foot-space 实际对应关系已偏

4. 足底接触几何变化
   - 鞋底/脚底磨损
   - 接触边缘形态变化
   - 足底滚动中心偏移

### 3. 当前更合理的综合判断

现在更可信的说法不是：

- “代码里有不对称，所以根因已经找到”

而是：

- 代码链中确实存在 left/right 不完全对称的符号与映射结构
- 这使系统**天然对硬件退化、装配偏差、零位漂移更敏感**
- 一旦并联踝某一侧出现性能衰减，现象就很容易表现成当前看到的：
  - touchdown 后稳定镜像 `roll` 偏置
  - 高 `kp` 时地面高频抖动
  - 低 `kp` 时抖动减轻但前进不足

也就是说：

**代码结构更像“脆弱性放大器”，硬件衰减更像“当前问题的触发源”。**

## 当前建议的下一步

在 `05B parallel mapping verification` 继续推进的同时，把硬件排查提到并行主线：

1. `05B-1` 代码侧
   - 继续核 left/right `actuator -> joint` 与 `joint -> actuator` 是否严格互逆
   - 确认额外 sign flip 是否与 mapping table、机械定义完全一致

2. `05B-2` 硬件侧
   - 做 left/right ankle 双电机小幅对称阶跃对比
   - 比较响应延迟、峰值、稳态误差、回零一致性
   - 重点看是否存在单侧出力下降、摩擦增大或回程不一致

3. `05B-3` 接触侧
   - 检查足底/鞋底状态是否变化
   - 复核是否存在单侧接触边缘先落地、磨损不一致

## 动态 Touchdown 检查计划

本轮之后，`05` 线只保留动态 touchdown 检查作为主判断依据，不再把静态 `zero/stand` 站姿作为主证据。

### 检查窗口

- 只看进入 `walk` 后前 `4` 个 touchdown
- 每次取：
  - `first_contact - 50 ms`
  - `touchdown`
  - `touchdown + 100 ms`

### 检查项

1. 脚底姿态与接触顺序
   - 看 `sole_roll_touch_rad / sole_pitch_touch_rad`
   - 看是否持续保持左右脚镜像 `roll` 偏置
   - 目测确认是否总是同一边缘先落地

2. 接触后短时抖动
   - 看 `touchdown ~ +100 ms` 是否出现 `roll` 方向高频来回打
   - 对比高 `kp` / 低 `kp` 时，抖动是否变化但初始偏置方向不变

3. 左右踝动态对称性
   - 看 `ankle_roll_q_touch_rad`
   - 看 `ankle_roll_err_touch_rad`
   - 看 `sole_roll_touch_rad`
   - 判断是否出现“joint-space 小、foot-space 大、左右脚镜像稳定”

4. 硬件性能衰减触发迹象
   - 看是否单侧更容易抖
   - 看是否存在粘滞后突然释放
   - 看是否回程更慢或更不一致

### 当前使用原则

- 若高 `kp` 和低 `kp` 都保留相同的左右脚镜像 `roll` 偏置，则主因继续优先归到 `parallel_mapping / sign-convention / foot-space geometry`
- 若镜像偏置长期存在，但只有单侧动态响应明显变差，则提高“并联踝物理损坏/性能衰减”优先级

## 下一步动作

1. `05A zero bias check` 已完成首轮收口
   - controller offset / yaml direction 已基本排除
2. 正式进入 `05B parallel mapping verification`
   - 细查 `ankle_transmission.cc` 中 left/right actuator->joint 与 joint->actuator 的符号链是否互逆、一致
3. 同时把“并联踝物理损坏/性能衰减”升为并行主线
   - 因为“同代码以前能走”显著提高了硬件触发源的先验概率
4. 暂不继续扫 ankle `kp/kd`
   - 当前证据已经不支持继续靠单参数调节解决主问题
