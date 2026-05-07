# Round 3C Coupled Geometry 排查结果

> Audit note (2026-05-06): the old strong `05C`收口依赖了未校准的 raw FK foot-frame 指标。  
> After rerun, `05C` no longer collapses to `fk_foot_frame_residual_candidate 3/4`; the calibrated labels are now split across `mapping_workpoint_residual / mixed_or_uncertain_contact_residual / pitch_roll_coupled_contact_residual / contact_geometry_residual`. See [16_real_round3_logic_audit_after_sim_contrast.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/16_real_round3_logic_audit_after_sim_contrast.md:1).
> Current consistency audit: [22_forward_x_failure_consistency_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/22_forward_x_failure_consistency_audit.md:1). Current action is `05D FK Foot-Frame / Contact`; old `parallel_mapping_mismatch` / `fk_foot_frame_residual_candidate` wording is retained only as historical pre-audit evidence.

轮次目标：在 `04_tracking_lag_repair` 已经证明”单独扫 ankle kp/kd 不能收敛主问题”的基础上，进一步回答：

1. 抖动压住后，脚底为什么仍以错误几何姿态 touchdown
2. 当前更像 `zero_bias`、`pitch_roll_coupling`、`parallel_mapping_mismatch`，还是 `contact_geometry_bias`

## ⚡ 当前进度速览

| 子阶段 | 状态 | 关键结论 |
|---|---|---|
| `05A` Zero Bias Check | ✅ 完成 | controller offset / YAML direction 排除；风险在 C++ 硬编码符号链 |
| `05B` Parallel Mapping（代码侧） | ✅ 完成 | 无简单 sign bug；残差→ mirrored code + 机构/接触 residual |
| `05B-2` 硬件侧阶跃对比 | ⬜ 未执行 | 计划中 |
| `05B-3` 接触侧足底检查 | ⬜ 未执行 | 与 05D Phase 2 合并 |
| `05C` Contact Residual Classification | ✅ 完成 / superseded-by-audit | 旧 `fk_foot_frame_residual_candidate 3/4` 强收口已降级；当前只作为 `05D` 待验证假设 |
| `05D` FK Foot-Frame 现场复核 | ⬜ **全部待执行** | Phase 0-4 均未执行，**当前第一优先级** |

## 数据与脚本

- 当前首轮分析数据：
  - [t27_tracking_lag_b1_diag_20260430_101404.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv)
- 专项脚本：
  - [05a_coupled_geometry_probe.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05a_coupled_geometry_probe.py:1)
  - [05c_coupled_geometry_cross_kp_compare.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05c_coupled_geometry_cross_kp_compare.py:1)
  - [05d_swing_attitude_cross_kp_compare.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05d_swing_attitude_cross_kp_compare.py:1)
  - [05e_parallel_mapping_verification.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05e_parallel_mapping_verification.py:1)
  - [05f_touchdown_geometry_residual_collection.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05f_touchdown_geometry_residual_collection.py:1)
  - [05g_touchdown_contact_residual_classification.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05g_touchdown_contact_residual_classification.py:1)
- 产出文件：
  - [t27_tracking_lag_b1_diag_20260428_164817_coupled_geometry_touchdown_table.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t27_tracking_lag_b1_diag_20260428_164817_coupled_geometry_touchdown_table.csv:1)
  - [t27_tracking_lag_b1_diag_20260430_101404_coupled_geometry_touchdown_table.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t27_tracking_lag_b1_diag_20260430_101404_coupled_geometry_touchdown_table.csv:1)
  - [t27_tracking_lag_b1_diag_20260430_101404_coupled_geometry_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t27_tracking_lag_b1_diag_20260430_101404_coupled_geometry_summary.md:1)
  - [t27_tracking_lag_b1_diag_20260430_101404_mapping_consistency_notes.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t27_tracking_lag_b1_diag_20260430_101404_mapping_consistency_notes.md:1)
  - [round3_zero_bias_and_mapping_check.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_zero_bias_and_mapping_check.md:1)
  - [round3_left_right_ankle_sign_chain.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_left_right_ankle_sign_chain.md:1)
  - [round3_coupled_geometry_cross_kp_compare.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_coupled_geometry_cross_kp_compare.md:1)
  - [round3_swing_attitude_cross_kp_compare.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_swing_attitude_cross_kp_compare.md:1)
  - [round3_touchdown_geometry_residual_collection.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_touchdown_geometry_residual_collection.md:1)
  - [round3_touchdown_contact_residual_classification.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_touchdown_contact_residual_classification.md:1)

## 本轮口径

- 仍采用“前 `4` 个 touchdown 优先”的口径
- 继续复用 `03a/03b` 的 touchdown 检测、FK 恢复和三层判因
- 在此基础上，新增两层几何判断：
  - `side_roll_sign_majority`
  - `cross_side_roll_pattern`

在加入 `13_dead_zone_audit` 之后，这一轮的口径边界需要重新写清：

- `swing` 期的小幅 `pos_des_raw` 已经可以先按 dead-zone / small-signal realization 解释；
- 所以 `05` 不再把 swing 期 lag 作为主证据；
- `05` 只接管 touchdown residual 和 touchdown 窗里的几何 / 映射残差。

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

### Dead-zone 边界

`13_dead_zone_audit` 已经把 `swing` 期的 `pos_des_raw` 小信号区间收敛出来了，因此 `05` 这里需要明确：

- `swing` 期 lag 不再作为 `coupled_geometry` 的主证据；
- `touchdown` 期仍然保留左右脚镜像 `roll` 偏置、`roll_to_joint_gain_ratio` 放大和接触边缘偏置；
- 也就是说，`05` 现在只解释 touchdown residual，不再吞掉 swing dead-zone。

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

在 `13_dead_zone_audit` 收口之后，`05A` 的解释边界需要明确为：

- 这里只解释 touchdown residual
- 不再把 swing 期的小信号兑现不足、dead-zone 或阈值敏感区误归到 zero bias
- 因此下面四条结论只对应 touchdown 阶段的几何/映射偏置，不代表 swing lag 的来源

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

## 05B Parallel Mapping Verification 结果

基于：

- [.oma/sim2real/plans/forward_x_failure/scripts/05e_parallel_mapping_verification.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05e_parallel_mapping_verification.py:1)
- [round3_parallel_mapping_verification.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_parallel_mapping_verification.md:1)

`05B` 当前把代码侧结论收紧成三条：

1. 没发现“简单一行写错”的 left/right actuator 归属 bug
   - 左踝 `pitch/roll` 读状态和回写命令的 actuator 归属是自洽的
   - 右踝同样自洽
   - 所以当前不是那种“读左发右”或“pitch/roll 接错”的低级错误

2. left/right 映射不是平凡对称，而是硬编码的镜像符号包
   - 左踝 `actuator -> joint` 里显式做了 `qm5/qm6/q6` 翻转
   - 右踝不做这组三连翻转，而是在相位和反解公式里补镜像
   - 这说明系统依赖 `ankle_transmission.cc` 里的 side-specific 符号约定，而不是只靠 YAML

3. `05B` 没有把 touchdown residual 解释完
   - 代码层没有暴露出一个足以直接解释问题的“单点 sign bug”
   - 但 touchdown 结果仍稳定表现为 `bilateral_mirror_stable + parallel_mapping_mismatch`
   - 因此剩余高优先级解释收敛到：
     - mirrored code package 与真实机构 / 映射表工作点的数值失配
     - 硬件侧 realization asymmetry
     - `joint_pos -> sole_roll` 的 foot-space / 接触几何 residual

因此 `05B` 的当前收口是：

- `parallel_mapping / sign-convention` 仍是主线
- 但它现在更像“镜像硬编码包 + 机构 / 表 / 接触 residual”的组合问题
- 不是简单的 controller offset、YAML direction 或单条 sign 语句错误

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

## Dead-zone 边界

`05` 线也要和死区一起读：

1. `swing` 期的稳定镜像 `roll` 偏置，不一定都应先归到几何映射错误；其中一部分可能与小信号死区 / 阈值响应共存。
2. 但 `touchdown` 期的稳定镜像 `roll` 残差，以及 `ankle_roll q` 很小而 `sole_roll` 仍很大的放大关系，仍然更适合保留给 `parallel_mapping_mismatch` / `coupled_geometry`。
3. 因此，`05` 的边界现在应理解为：
   - `swing` 期保留 dead-zone 解释空间
   - `touchdown` 期的 geometry residual 仍是主解释

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

## 当前建议的下一步（进度标记）

1. ✅ `05B-1` 代码侧 — 已完成
   - left/right actuator ownership 自洽性已核查，额外 sign flip 与机械定义基本一致
   - 简单 sign bug 已排除

2. ⬜ `05B-2` 硬件侧 — **未执行**
   - 做 left/right ankle 双电机小幅对称阶跃对比
   - 重点看单侧出力下降、摩擦增大或回程不一致

3. ⬜ `05B-3` 接触侧 — **未执行**（计划与 `05D Phase 2` 足底几何复核合并执行）

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
2. `05B parallel mapping verification` 已完成首轮代码侧核查
   - 简单 sign bug 已基本排除
   - 当前主怀疑点收敛为 mirrored code package 与真实机构 / 接触 residual 的失配
3. 同时把“并联踝物理损坏/性能衰减”升为并行主线
   - 因为“同代码以前能走”显著提高了硬件触发源的先验概率
4. 暂不继续扫 ankle `kp/kd`
   - 当前证据已经不支持继续靠单参数调节解决主问题

## 05B 下一层：Touchdown Foot-Space / Contact Residual 收口

基于：

- [.oma/sim2real/plans/forward_x_failure/scripts/05f_touchdown_geometry_residual_collection.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05f_touchdown_geometry_residual_collection.py:1)
- [round3_touchdown_geometry_residual_collection.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_touchdown_geometry_residual_collection.md:1)
- [round3_touchdown_geometry_residual_collection.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_touchdown_geometry_residual_collection.csv:1)

这一步把：

- `12C` 已经分离出来的 `state -> joint` residual
- 与 `05` 里剩下的 `joint -> sole_roll` residual

放进同一个 touchdown 窗统一对照，只回答一个问题：

**在上游 realization residual 固定之后，还剩下多少 residual 必须留给 foot-space / contact geometry。**

### 当前结果

4 组 `all_ankles` touchdown case 的读法是：

- `25/0.4 all_ankles` -> `foot_space_or_contact_residual_dominant`
- `30/0.4 all_ankles` -> `mixed_with_strong_foot_space_residual`
- `35/0.5 all_ankles` -> `foot_space_or_contact_residual_dominant`
- `40/0.8 all_ankles` -> `foot_space_or_contact_residual_dominant`

残差计数：

- `foot_space_or_contact_residual_dominant = 3`
- `mixed_with_strong_foot_space_residual = 1`

这些 case 的共同特征仍然一致：

- `cross_side_roll_pattern = bilateral_mirror_stable`
- `dominant_geometry_mode = parallel_mapping_mismatch`
- `mean_abs_sole_roll ≈ 1.62 ~ 1.84 rad`
- `mean_roll_to_joint_gain_ratio` 仍然显著偏高

### 对 05 / 12 边界的收口

现在这条边界可以写硬一些：

- `12` 负责解释：
  - `actuator_state -> joint_pos`
  - 也就是 realization lag / backlash / hysteresis / low gain
- `05` 负责解释：
  - touchdown 窗里，在 `state -> joint` 已经分离之后，仍然残留的 `joint_pos -> sole_roll`
  - 也就是 foot-space / contact residual

换句话说：

- `05` 现在不再需要为上游 realization lag 背锅
- `12` 也不能再试图单独解释 touchdown 最终 `sole_roll`

### 当前 05 主结论

在 dead-zone 先行筛掉 `swing` 小信号之后，再经过 `05A`、`05B` 和这一步 touchdown residual 收口，当前最可信的结论是：

1. 代码层没有暴露出简单 sign bug
2. `state -> joint` 的 realization residual 是真实存在的，但已被 `12` 单独接管
3. touchdown 最终的主要残差，当前更应该保留为：
   - `foot-space / contact residual`
   - 表现形式上对应：
     - `bilateral_mirror_stable`
     - `parallel_mapping_mismatch`
     - `joint-space small / foot-space large`

## 05C Touchdown Contact Residual Classification

基于：

- [.oma/sim2real/plans/forward_x_failure/scripts/05g_touchdown_contact_residual_classification.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/05g_touchdown_contact_residual_classification.py:1)
- [round3_touchdown_contact_residual_classification.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_touchdown_contact_residual_classification.md:1)
- [round3_touchdown_contact_residual_classification.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_touchdown_contact_residual_classification.csv:1)

`05C` 不再重新讨论 `swing` 期小信号死区，也不再把 `actuator_state -> joint_pos` 的 realization residual 混进来。它只围绕 touchdown 窗，把 `05B` 剩下的 `joint_pos -> sole_roll` 残差细分为 foot-space / contact 层的具体类型。

### 当前分类结果

4 组 `all_ankles` touchdown case 的分类为：

| case | 05C label | 关键读法 |
|---|---|---|
| `25/0.4 all_ankles` | `fk_foot_frame_residual_candidate` | `abs_sole_roll=1.7768`，`abs_ankle_roll_q=0.0467`，关节量小但 FK foot body roll 很大，pitch 参与低 |
| `30/0.4 all_ankles` | `fk_foot_frame_residual_candidate` | `abs_sole_roll=1.7249`，`abs_ankle_roll_q=0.0351`，同样是 FK foot-space 放大主导 |
| `35/0.5 all_ankles` | `pitch_roll_coupled_contact_residual` | `abs_sole_roll=1.8361`，`abs_sole_pitch=0.1849`，pitch 参与已经不可忽略 |
| `40/0.8 all_ankles` | `fk_foot_frame_residual_candidate` | `abs_sole_roll=1.6852`，`abs_ankle_roll_q=0.1082`，仍是 FK foot frame / contact candidate 更优先 |

计数：

- `fk_foot_frame_residual_candidate = 3 / 4`
- `pitch_roll_coupled_contact_residual = 1 / 4`

### 05C 收口

当前最硬的新增结论是：

1. touchdown residual 已经不能再主要归因到 `output` 或 `state -> joint`。
2. 在多数 case 里，剩余残差更像：
   - FK foot body frame 与真实足底接触面的参考不一致
   - 真实足底接触边缘先落地
   - 或 touchdown 接触线 / 滚动中心和模型不一致
3. `35/0.5 all_ankles` 不能简化成纯 roll 接触边缘问题，因为 `sole_pitch` 参与较明显，应保留 `pitch_roll_coupled_contact_residual` 标签。
4. `parallel_mapping_mismatch` 仍作为表现层签名保留，但 05C 之后它不应被读成“代码里一定有 sign bug”；它更具体地落到了 foot-space / contact frame 与真实接触几何的失配。
5. 由于 `mean_abs_sole_roll` 来自 MuJoCo FK 的 `link_*_ankle_roll` body frame，05C 不能证明真实脚底接触面一定有同等大 roll；旧 `contact_edge_or_foot_frame_residual` 口径现降级为 `fk_foot_frame_residual_candidate`。

### “关节角不大”的计算口径

`fk_foot_frame_residual_candidate` 中的“关节角不大”，当前指的是 touchdown 时刻真实 joint-space 里的 ankle roll 位置，而不是通过 FK 从脚底姿态反推出来的角。

脚本链路是：

1. `05f_touchdown_geometry_residual_collection.py` 调用 `05a_coupled_geometry_probe.py`
2. `05a` 先用 `03a` 检测 touchdown，再用 `row_at_or_before(diag_rows, touchdown_time_sec)` 找到 touchdown 时间点之前最近一帧原始诊断日志
3. 按 touchdown 的左右脚选择字段：
   - 左脚：`pos_left_ankle_roll_joint`
   - 右脚：`pos_right_ankle_roll_joint`
4. 写入：
   - `ankle_roll_q_touch_rad`
   - `abs_ankle_roll_q_touch_rad = abs(ankle_roll_q_touch_rad)`
5. 对每组 case 的前 `4` 个 touchdown 求平均：
   - `mean_abs_ankle_roll_q`

因此表里的：

- `mean_abs_ankle_roll_q = 0.035 ~ 0.118 rad`

含义是：touchdown 时刻，日志里的真实 ankle roll joint 位置绝对值平均大约只有 `2.0° ~ 6.8°`。

同时脚底姿态：

- `mean_abs_sole_roll = 1.68 ~ 1.84 rad`

也就是脚底 roll 绝对值平均约 `96° ~ 105°`。这个量级差异形成：

- `roll_to_joint_gain_ratio = abs(sole_roll_touch_rad) / max(abs(ankle_roll_q_touch_rad), 1e-6)`

所以当前判定的关键不是“ankle joint 一点没动”，而是：

**真实 ankle roll joint 角的量级远小于脚底 roll 姿态量级，且这种放大在左右脚 touchdown 中稳定镜像出现。**

在 `05g` 的分类阈值里，`joint_small_foot_large` 的条件是：

- `abs_joint_roll <= 0.12 rad`
- `abs_sole_roll >= 1.0 rad`
- `roll_gain >= 10.0`

满足这个条件且 pitch 参与低时，才会归到 `fk_foot_frame_residual_candidate`。这个标签只代表“FK foot body 姿态相对 joint-space 异常放大”的候选残差，不直接等同于真实脚底 roll。

### 下一轮最小验证

`05C` 后的最小现场验证不应再继续扫 `kp/kd`，而应直接围绕 FK foot frame / contact：

1. 静态 FK foot-frame 对齐：
   - 上架或安全支撑，做零位、站立位和 ankle 小角度 sweep
   - 同时记录 FK `sole_roll / sole_pitch` 与实测脚底平面 roll/pitch
   - 先判断 FK foot body frame 是否能代表真实脚底接触平面
2. 足底几何复核：
   - 检查鞋底/脚底左右边缘磨损、变形、松动
   - 用平面板确认真实接触平面
3. touchdown 同步视频 / 接触证据：
   - 只拍进入 walk 后前 `4` 个 touchdown
   - 对齐日志中的 touchdown timestamp
   - 判断是否固定边缘先着地
   - 优先增加压敏纸、碳粉纸、FSR、AprilTag / ArUco 等接触或姿态证据
4. 接触线复核：
   - 记录 touchdown 后 `+100 ms` 内是否沿 roll 方向绕某一边缘滚动
   - 若高低 `kp` 都保持同一接触边缘，则优先按 contact geometry residual 处理

## 05D 下一步试验方案：FK Foot-Frame / Contact 现场复核（⬜ 全部待执行）

> **状态**：以下 Phase 0-4 均未执行。这是当前整个 `forward_x_failure` 问题的**唯一第一优先级**。
> 详细执行方案见计划文件 [plans/05_coupled_geometry_probe.md](../../plans/forward_x_failure/05_coupled_geometry_probe.md)。

### 目标

按顺序回答三个问题：

1. MuJoCo FK 的 `link_*_ankle_roll` body frame 是否能代表真实脚底接触平面？
2. 如果能代表，touchdown 大 `fk_sole_roll` 是否对应真实脚底固定边缘先接触？
3. 如果静态一致但动态不一致，是否存在接触线偏移、负载变形或回差释放？

### Phase 0：FK 指标口径确认（⬜ 待执行）

目的：先统一 FK 指标来源、字段命名、frame 定义表和现场记录模板。Phase 0 不要求机器人运动；它是 Phase 1 静态测量前的口径锁定。

执行步骤：

1. 确认 FK 源头：
   - `FOOT_BODIES = left -> link_left_ankle_roll, right -> link_right_ankle_roll`
   - `base_euler + joint pos -> mujoco.mj_forward -> data.xmat -> matrix_to_roll_pitch_yaw`
2. 统一字段命名：
   - FK 派生量：`fk_body_name / fk_sole_roll_rad / fk_sole_pitch_rad / fk_sole_normal_z`
   - 外部实测量：`measured_sole_roll_rad / measured_sole_pitch_rad / measurement_method`
   - 接触观测：`contact_edge_label / contact_mark_evidence / video_evidence`
3. 建立 `fk_frame_definition_check` 表，至少包含：
   - `side`
   - `fk_body_name`
   - `mjcf_body_parent`
   - `fk_frame_claim`
   - `real_sole_plane_definition`
   - `contact_layer_definition`
   - `known_offset_or_unknown`
   - `phase1_required`
4. 准备 `05d_fk_foot_frame_contact_template.csv` 或等价表格，至少包含：
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
5. 锁定 Phase 1 判据：
   - `abs(fk_sole_roll_rad - measured_sole_roll_rad) <= 0.05 rad`
   - `abs(fk_sole_pitch_rad - measured_sole_pitch_rad) <= 0.05 rad`
   - 符号不一致时标记 `frame_sign_mismatch_risk`
6. 更新现场口径：
   - 未通过 Phase 1 前，禁止把 FK `sole_roll` 直接写成真实脚底 roll。
   - `fk_foot_frame_residual_candidate` 保持候选标签，不升级为 `real_contact_edge_bias`。

通过标准：

- 完成 `fk_frame_definition_check` 表。
- 完成 `05d_fk_foot_frame_contact_template.csv` 或等价记录模板。
- 明确 Phase 1 的 roll/pitch 容差和符号一致性判据。
- 后续记录字段中不再使用无前缀 `sole_roll` 表示真实脚底 roll。

### Phase 1：静态 Foot-Frame 对齐（⬜ 待执行）

目的：确认 FK foot frame 的”脚底平”是否等于真实脚底板平。

执行：

1. 主测量采用悬空 / 上架无接触状态，避免地面接触、鞋底压缩和回差混入 frame 校准。
2. 可选复核采用轻触地 / 站立承重状态，只用于观察接触层压缩后的变化，不能替代悬空 frame 校准。
3. 悬空状态下分别进入零位、站立位，以及 ankle roll/pitch 小角度 sweep：`-0.10 / 0 / +0.10 rad`。
4. 记录日志中的：
   - `pos_left/right_ankle_roll_joint`
   - `pos_left/right_ankle_pitch_joint`
   - FK `fk_sole_roll / fk_sole_pitch`
5. 用简易方法测真实脚底板相对地面的 `measured_sole_roll / measured_sole_pitch`。

简易测量方法：

1. 手机角度计方法，优先推荐：
   - 在脚底板上贴小平板、硬卡片或亚克力片。
   - 手机短边横跨左右方向读 `roll`，长边沿前后方向读 `pitch`。
   - 每个姿态读 `3` 次，取中位数。
   - 左右脚测量方向必须一致，并记录符号约定。
2. 纸片 / 楔块塞尺方法：
   - 平板贴脚底，另一侧用纸片或薄垫片塞到刚好接触。
   - 记录厚度差 `delta_h` 和脚底宽度 / 长度 `L`。
   - 近似角度：`angle_rad = atan(delta_h / L)`。
3. 直尺 + 拍照方法：
   - 脚底边缘贴标记点，正前 / 正侧方固定手机拍照。
   - 由两点高度差估算 `atan(delta_h / L)`。
   - 只用于确认符号和大偏差。

判定：

- 若静态下 FK 与真实脚底平面固定偏差大于 `0.05 rad` 或符号不一致，归为 `foot_frame_reference_mismatch`。
- 若静态下 FK 与真实脚底一致，才进入 Phase 2/3，把 touchdown 大 roll 当作真实接触问题继续查。
- 若只有简易测量，`0.05 rad` 作为强证据阈值，`0.03 ~ 0.05 rad` 作为灰区，需要重复测量或换方法复核。

### Phase 2：足底/鞋底几何复核（⬜ 待执行，可与 05B-3 合并）

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

目的：确认是否固定内侧或外侧边缘先着地。

执行：

1. 使用当前已能稳定复现问题的 walk 流程。
2. 每组只取进入 `walk` 后前 `4` 个 touchdown。
3. 同步保存诊断日志和现场视频。
4. 视频至少拍：
   - 正前方或正后方，用于看 roll 方向内/外侧边缘
   - 侧方，用于看 pitch 是否参与
5. 优先增加至少一种接触证据：
   - 脚底内外侧贴薄纸 / 碳粉纸 / 压敏纸
   - 脚侧贴 AprilTag / ArUco / 标记点
   - 分区 FSR 或触点开关
6. 每一步人工标注：
   - `side`
   - `touchdown_time`
   - `inner_edge_first / outer_edge_first / flat / unclear`
   - `heel_or_toe_pitch_participates`
   - `post_touch_roll_oscillation`

判定：

- 若 Phase 1 已通过，且视频 / 接触证据显示固定边缘先接触与 `fk_sole_roll` 符号稳定对应，则归为 `real_contact_edge_bias`。
- 若 Phase 1 未通过，即使视频有边缘接触，也不能直接使用旧 FK `sole_roll` 量级下结论，需先修 foot frame 参考。
- 若视频显示脚尖/脚跟先参与，再叠加 roll，则对应样本应归到 `pitch_roll_coupled_contact_residual`。

### Phase 4：高低 Kp 对照复核（⬜ 待执行，依赖 Phase 1 通过）

目的：验证 `kp` 是否只是放大器。

建议只做两组：

1. 低 `kp` 稳定组：`25/0.4 all_ankles` 或 `30/0.4 all_ankles`
2. 高 `kp` 对照组：`40/0.8 all_ankles`

每组只看前 `4` 个 touchdown。

判定：

- 若 Phase 1/2/3 已确认真实接触边缘，且高低 `kp` 的初始接触边缘一致，但高 `kp` 抖动更强，则 `kp` 是接触问题放大器。
- 若高 `kp` 才出现接触边缘切换或明显打地，则说明接触非线性和高增益互相激发。
- 若 Phase 1 未通过，不执行本 Phase；先修 FK / foot frame 参考。

### 通过标准

`05D` 通过后，应能把 `05C` 的 `fk_foot_frame_residual_candidate` 继续拆成以下三类之一：

1. `real_contact_edge_bias`
   - 真实脚底固定边缘先接触
2. `foot_frame_reference_mismatch`
   - FK foot frame 与真实脚底平面不一致
3. `dynamic_contact_deformation_or_release`
   - 静态正常，动态 touchdown 才出现接触线偏移、变形或回差释放

输出要求：

- 每个分类必须给出对应证据来源：`static_frame_check / sole_geometry_check / synced_video / contact_mark / kp_ablation`。
- 没有 Phase 1 静态校准证据时，不能把 FK `sole_roll` 当成真实脚底 roll 直接下结论。

## 指标字典

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `mean_abs_sole_roll` | touchdown / 窗口内 FK `abs(sole_roll)` 均值 | 量化 MuJoCo foot body roll，不是真实脚底直接测量值 |
| `mean_abs_ankle_roll_q` | touchdown 时 `abs(pos_<side>_ankle_roll_joint)` 均值 | 判断 joint-space roll 角是否足以解释 foot-space roll |
| `roll_to_joint_gain_ratio` | `abs(sole_roll) / max(abs(ankle_roll_q), 1e-6)` | 识别 foot-space 相对 joint-space 的异常放大 |
| `parallel_mapping_mismatch` | 并联踝映射 / sign package 的左右镜像风险 | 05B 后保留为代码 / transmission 侧解释线索 |
| `controller_offset_clear` | controller `joint_offset` 未解释当前残差 | 排除 controller offset 作为第一解释 |
| `yaml_direction_clear` | YAML direction 未解释当前残差 | 排除简单方向配置错误 |
| `simple_actuator_ownership_sign_bug_clear` | 未发现单一 actuator 归属或符号 bug | 排除简单 sign bug，转向耦合 sign package / foot frame |
| `touchdown_geometry_residual` | `joint_pos -> sole_roll` 仍解释不完的剩余量 | `05` 的当前主解释权边界 |
| `fk_foot_frame_residual_candidate` | joint 角不大但 FK `sole_roll` 大，pitch 参与低 | 降级后的候选标签；需先验证 FK foot frame |
| `pitch_roll_coupled_contact_residual` | touchdown 残差中 pitch 和 roll 共同参与 | 少数 case 保留，不按纯 roll 边缘问题处理 |
| `real_contact_edge_bias` | 真实脚底固定边缘先接触 | `05D` 待判定输出标签 |
| `foot_frame_reference_mismatch` | FK foot frame 与真实脚底接触平面不一致 | `05D` 待判定输出标签 |
| `dynamic_contact_deformation_or_release` | 静态正常但动态接触时发生变形、接触线偏移或回差释放 | `05D` 待判定输出标签 |
