# 12 Parallel Actuation Realization Probe

## 进入前统一结论

基于 `10` 和 `11`：

- `output` 不是主瓶颈
- `sole_roll` 主要跟随执行链
- `cmd -> state` 不是主 lag 段
- 主 lag 段更像 `actuator_state -> joint_pos`
- 该 lag 普遍在 `swing` 窗就已存在
- `left/right asymmetry` 明显，但慢侧不稳定

因此，`12` 线不再讨论来源归因，也不再继续围绕 `kp/kd` 做宽口径解释。

`12` 线只聚焦：

- 为什么执行器状态已经变化，关节空间却没有及时兑现

## 当前判定口径

`12` 线默认使用下面的拆分：

1. **执行兑现不足**
   - `actuator_state -> joint_pos`

2. **几何放大保留项**
   - `joint_pos -> sole_roll`
   - 继续由 `05` 线承担

也就是说：

- `12` 解释“为什么 joint 没跟上”
- `05` 解释“为什么 joint 就算变了，foot-space 仍可能被放大成异常 sole_roll”

## 当前分析目标

后续会优先判定这几类兑现问题：

- 整体慢
- 间隙
- stick-slip / 摩擦卡滞
- 左右链不一致

## 当前工作顺序

1. 先做 `state -> joint` 兑现形态分析
2. 再做左右链不一致分析
3. 最后和 `joint -> sole_roll` 并排比较，决定哪些仍该保留给 `coupled_geometry`

## Phase A 结果

已完成 `state -> joint` 兑现形态分析，输出：

- [round3_parallel_realization_shape_detail.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_parallel_realization_shape_detail.csv:1)
- [round3_parallel_realization_shape_side_summary.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_parallel_realization_shape_side_summary.csv:1)
- [round3_parallel_realization_shape_case_summary.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_parallel_realization_shape_case_summary.csv:1)
- [round3_parallel_realization_shape_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_parallel_realization_shape_summary.md:1)

当前使用的形态标签是启发式标签：

- `overall_slow`
- `stick_slip_like`
- `backlash_like`
- `low_realization_gain`
- `mostly_linear`

## 当前阶段结论

基于 `4` 组 actuator-state 样本，这一轮结果已经可以先收成：

1. `backlash_like` 是最稳定、最普遍的标签。  
   它在左右脚、swing/touchdown 多个窗口里反复出现，说明 `state -> joint` 更像存在明显的兑现回环/迟滞，而不是纯粹线性慢一拍。

2. `low_realization_gain` 在一部分 case 中也比较突出。  
   这说明某些窗口里，执行器状态变化了，但 joint 侧只兑现出较小比例的变化量。

3. `stick_slip_like` 不是全局主标签，但在部分 case 中出现。  
   这说明当前不能简单收口成“全局摩擦卡滞”，更合理的是：
   - **主现象更像 backlash / hysteresis**
   - 部分 case 叠加 stick-slip

4. `overall_slow` 仍存在，但更像表层现象，不是唯一解释。  
   也就是说：
   - 这不是单纯“整体都慢”
   - 更像“慢 + 回环 + 部分窗口兑现增益偏低”

## Dead-zone 修正

`12` 线当前结论需要加一层修正：

1. `state -> joint` 里的 `backlash_like / low_realization_gain / stick_slip_like`，不应被默认理解为纯机械结构故障。
2. 在 `swing` 窗里，若 `action` 或 `pos_des_raw` 幅值偏小，这些标签很可能同时包含 dead-zone / small-signal realization 的成分。
3. 只有在输出幅值不小、lag 仍持续高、hysteresis / gain gap 仍强时，才更适合把残余继续往机械结构、摩擦、间隙和左右链不一致上推进。
4. 因此，`12` 线当前更准确的说法是：
   - `state -> joint` 存在不健康兑现
   - 其中一部分 swing lag 可被 dead-zone 解释
   - 剩余部分再由 backlash / hysteresis / asymmetry 承担

## 当前更合理的解释框架

基于 `11` 和 `12A`，`state -> joint` 这段现在更像：

- 主体：`backlash / hysteresis like realization`
- 并发：`low_realization_gain`
- 局部：`stick_slip_like`

而不是：

- 单纯通信晚
- 单纯全局线性响应慢
- 单纯固定单侧故障

## 左右链不一致的当前口径

`12A` 继续支持：

- `left/right asymmetry` 明显存在
- 但“哪一侧更差”仍不稳定

因此，当前依然不能把问题收口成：

- 左侧固定损坏
- 或右侧固定损坏

更合理的表述是：

- **并联两支链的兑现模式不一致**
- 但不一致模式会随参数和窗口变化

## Phase C 结果

已完成 `state -> joint` 与 `joint -> sole_roll` 的同窗分离分析，输出：

- [round3_realization_vs_geometry_separation.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_realization_vs_geometry_separation.csv:1)
- [round3_realization_vs_geometry_separation.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_realization_vs_geometry_separation.md:1)

当前使用 3 类标签：

- `realization_dominant`
- `mixed_with_geometry_residual`
- `geometry_residual_dominant`

## Phase C 当前阶段结论

这一轮没有支持“执行兑现不足已经足够解释全部 sole_roll”。

更准确地说：

1. **`swing` 窗里，执行兑现不足有时已足以主导**  
   典型是 `30/0.4 all_ankles / swing`：  
   `state -> joint = 93.5 ms`，而 `joint -> sole = 26.1 ms`，这类样本可以先收进 `realization_dominant`。

2. **多数 `swing` case 仍是混合型**  
   如 `25/0.4`、`35/0.5`、`40/0.8` 的 `swing` 窗，`state -> joint` 已经明显不健康，但它还不足以单独解释最终 `sole_roll`，因此更合理地保留为 `mixed_with_geometry_residual`。

3. **`touchdown` 窗更多保留给 geometry residual**  
   `25/0.4 touchdown`、`35/0.5 touchdown`、`40/0.8 touchdown` 都表现为：  
   `state -> joint` 已经收敛到较低或偏紧区间，但 `joint -> sole_roll` 仍显著偏高，说明最终 touchdown 异常不能只用执行兑现不足来解释。

按 `8` 个 case/window 汇总：

- `realization_dominant = 1`
- `mixed_with_geometry_residual = 4`
- `geometry_residual_dominant = 3`

## 12 线的当前边界更新

基于 `12A + 12B + 12C`，`12` 线现在可以收成：

1. `state -> joint` 的确存在系统性不健康兑现，主形态更像：
   - `backlash / hysteresis like realization`
   - `low_realization_gain`
   - `mode-dependent left/right asymmetry`

2. 这条线足以解释：
   - 为什么 `output` 已经给了调平/变化意图，但 `joint_pos` 仍经常来不及兑现
   - 为什么 `swing` 窗已经出现明显 lag

3. 但这条线**不能替代** `05` 去解释最终 touchdown 的主要 `sole_roll` 异常  
   因为在多个 `touchdown` case 中，`joint -> sole_roll` 残差仍然明显偏大。

因此，当前最合理的主线分工是：

- `12`：负责解释 `actuator_state -> joint_pos`
- `05`：继续负责解释 `joint_pos -> sole_roll`

进一步结合 touchdown residual collection：

- `25/0.4 all_ankles`：`foot_space_or_contact_residual_dominant`
- `30/0.4 all_ankles`：`mixed_with_strong_foot_space_residual`
- `35/0.5 all_ankles`：`foot_space_or_contact_residual_dominant`
- `40/0.8 all_ankles`：`foot_space_or_contact_residual_dominant`

所以这条边界现在可以再收紧一层：

- `12` 不再试图单独解释 touchdown 最终 `sole_roll`
- `05` 正式接管 touchdown 窗里在 `state -> joint` 已分离后仍然残留的 foot-space / contact residual

## 12C 指标字典表

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `mean_state_joint_lag_ms` | 同一窗口内，`actuator_state -> joint_pos` 的平均滞后时间 | 判断执行兑现不足是否已经达到高风险或不可接受水平 |
| `mean_joint_sole_lag_ms` | 同一窗口内，`joint_pos -> sole_roll` 的平均滞后时间 | 判断 foot-space 残差是否仍明显偏大，应继续保留给 `05` |
| `mean_abs_sole_roll` | 该窗口内 `sole_roll` 绝对值均值 | 表征最终足底 roll 异常的严重程度 |
| `mean_cmd_state_left_lag_ms` | 左侧 `actuator_cmd -> actuator_state` 的平均滞后时间 | 复核命令到执行器响应段是否构成主瓶颈 |
| `mean_cmd_state_right_lag_ms` | 右侧 `actuator_cmd -> actuator_state` 的平均滞后时间 | 同上，用于左右对照 |
| `lag_gap_ms` | 左右两侧 `state -> joint lag` 的差值 | 判断左右链在兑现速度上的不一致程度 |
| `gain_gap` | 左右两侧 `state -> joint gain` 的差值 | 判断左右链在兑现幅值上的不一致程度 |
| `left_shape` | 左侧 `state -> joint` 的兑现形态标签集合 | 给 `12C` 提供该窗口的兑现形态背景，例如 `backlash_like` / `low_realization_gain` |
| `right_shape` | 右侧 `state -> joint` 的兑现形态标签集合 | 同上，用于与左侧对照 |
| `geometry jump` | 这里不是独立输出列，而是分析时使用的概念：`joint -> sole_roll lag` 明显高于 `state -> joint lag` | 用来判断从 joint-space 到 foot-space 是否还存在额外放大或残差 |
| `realization_dominant` | `12C` 分离标签：`state -> joint` 已经高风险/不可接受，且足以主导当前窗口异常 | 表示这一窗口里执行兑现不足是主解释 |
| `mixed_with_geometry_residual` | `12C` 分离标签：`state -> joint` 已明显不健康，但还不足以单独解释 `sole_roll` | 表示执行兑现不足和 geometry residual 同时存在 |
| `geometry_residual_dominant` | `12C` 分离标签：`state -> joint` 已较低或偏紧，但 `joint -> sole_roll` 仍明显偏高 | 表示该窗口里主要残差应继续交给 `05 coupled_geometry` |
| `rationale` | 对单个 case/window 的文字化解释 | 便于人工复核该标签为什么成立，而不是只看分类结果 |

## 12C 标签阅读方式

- 如果一个窗口是 `realization_dominant`：
  - 先优先从 `12` 线继续追 `state -> joint` 的兑现问题
- 如果一个窗口是 `geometry_residual_dominant`：
  - 不再试图只靠执行链解释，应直接回到 `05` 线看 `joint -> sole_roll`
- 如果一个窗口是 `mixed_with_geometry_residual`：
  - 说明两条线都还在起作用，不能单边收口

## `state -> joint` 与 `joint -> sole_roll` 的分段逻辑

`12C` 不是按主观现象拆段，而是按当前可观测信号链拆段：

`actuator_cmd -> actuator_state -> joint_pos -> sole_roll`

在这个链里，当前只把后两段拿来做主分离：

1. `state -> joint`
2. `joint -> sole_roll`

对应含义分别是：

- `state -> joint`
  - 从 `actuator_state_pos_*` 到 `pos_<side>_ankle_roll_joint`
  - 解释“执行器已经在动，为什么 joint 还没及时兑现”

- `joint -> sole_roll`
  - 从 `pos_<side>_ankle_roll_joint` 到 `<side>_sole_roll`
  - 解释“joint 就算变了，为什么 foot-space 的 `sole_roll` 仍然异常”

这也是当前 `12` 与 `05` 的边界：

- `12` 负责 `actuator_state -> joint_pos`
- `05` 负责 `joint_pos -> sole_roll`

## lag 的计算逻辑

这两段 lag 都不是人工读图得到的，而是用同一套窗口化对齐逻辑算出来的。

核心过程：

1. 先在同一 touchdown 事件上选局部窗口
   - `swing = touchdown - 350 ms .. touchdown - 20 ms`
   - `touchdown = touchdown - 50 ms .. touchdown + 100 ms`

2. 对窗口内两条序列分别做一阶差分  
   目的不是看绝对值，而是看“变化趋势什么时候最像”

3. 对差分后的序列做 `z-score` 归一化  
   这样不同量纲、不同幅值的信号可以比较

4. 在 `0 .. 200 ms` 的 lag 范围内做枚举搜索  
   找到相关性最高的那个 lag

5. 把最佳 lag 从采样点数换算成 ms

所以：

- `state -> joint lag`
  - 表示在这个局部窗口里，joint 的变化趋势比 actuator_state 晚了多少

- `joint -> sole_roll lag`
  - 表示在这个局部窗口里，sole_roll 的变化趋势比 joint 晚了多少

## 为什么要分成这两段

因为这两段对应的是不同问题域：

### `state -> joint`

更接近：

- 并联执行兑现
- 机械间隙
- 摩擦 / stick-slip
- 左右支链不一致
- 预接触负载影响

### `joint -> sole_roll`

更接近：

- joint-space 到 foot-space 的几何放大
- pitch / roll 耦合
- 足底接触几何
- touchdown 接触边缘与滚动中心偏置

所以 `12C` 的目标不是把问题一次性解释完，而是先分清：

- 哪些窗口里，执行兑现不足已经足够主导
- 哪些窗口里，即使 joint 已经相对收敛，foot-space 残差仍然明显

## `12C` 如何用两段 lag 做分离

当前分离规则是启发式的，但口径统一：

### `realization_dominant`

当：

- `state -> joint` 已经高风险或不可接受
- 且 `joint -> sole_roll` 相对更小

则解释为：

- joint-space 这层已经明显不健康
- 当前窗口主要由执行兑现不足主导

### `geometry_residual_dominant`

当：

- `state -> joint` 已较低或偏紧
- 但 `joint -> sole_roll` 仍明显偏高

则解释为：

- 执行兑现不足不能单独解释最终 `sole_roll`
- 主要残差继续保留给 `05 coupled_geometry`

### `mixed_with_geometry_residual`

当：

- 两段都不健康
- 或 `state -> joint` 虽然不健康，但仍不足以单独解释最终 `sole_roll`

则解释为：

- 执行兑现不足和 geometry residual 同时在起作用
- 当前不能单边收口

## 当前边界

这套分离仍然是**信号链分离**，不是严格的物理真值分解。

也就是说：

- `state -> joint` 里仍然混有机构、负载和并联映射因素
- `joint -> sole_roll` 里仍然混有几何和接触因素

但在当前日志条件下，这已经足够把问题稳定分成：

- 上游兑现不足
- 下游 geometry residual

供 `12` 和 `05` 两条线并行推进。

## 当前边界

这轮结果仍然是**行为特征级**判断，不是硬件真值诊断。

也就是说：

- `backlash_like` 不等于已经证明“机械间隙一定存在”
- `stick_slip_like` 不等于已经证明“摩擦一定异常”

它们当前的作用是：

- 为下一步现场硬件检查缩小方向
- 为 `12B` 左右链不一致分析提供更具体的指标

## Phase B 结果

已完成左右链不一致的量化统计，输出：

- [round3_left_right_asymmetry_summary.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_left_right_asymmetry_summary.csv:1)
- [round3_left_right_asymmetry_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_left_right_asymmetry_summary.md:1)

这一轮把 `left/right asymmetry` 沿 3 条轴分开统计：

1. lag gap
2. gain gap
3. shape severity gap

## 当前阶段结论更新

`12B` 进一步把“左右不一致”这件事收紧成：

1. **不一致是真实存在的**  
   无论在 `swing` 还是 `touchdown`，`lag gap` 和 `gain gap` 都不是小量。

2. **它不是一个固定单侧故障模型**  
   如果是固定单侧故障，应该在 lag / gain / shape 三条轴上都长期同侧更差。  
   但当前结果是：
   - `lag` 轴多数表现为 `left_worse`
   - `gain` 轴在 `swing` 窗并不稳定，`touchdown` 窗才偏 `left_worse`
   - `shape severity` 轴在 `swing` 窗更偏 `right_worse`

3. **当前更像 mode-dependent asymmetry**  
   也就是：
   - 左右链不一致是真的
   - 但不一致模式会随窗口和指标改变
   - 因此更像并联两支链的兑现模式不一致，而不是“左边固定坏了”或“右边固定坏了”

## 当前最合理的解释框架

基于 `12A + 12B`，`12` 线当前更合理的解释是：

- 主体：`backlash / hysteresis like realization`
- 并发：`low_realization_gain`
- 结构特征：`mode-dependent left/right asymmetry`

这比“单侧固定硬件故障”更符合现有数据。

## 0.6 m/s 步态下的延迟预算口径

`12` 线后续对 `state -> joint` 的判断，统一采用与 `11` 相同的工程预算：

| `state -> joint_pos` 延迟 | 判断 |
|---|---|
| `< 15~20 ms` | 较健康 |
| `15~30 ms` | 可接受但偏紧 |
| `30~50 ms` | 高风险 |
| `> 50 ms` | 当前问题场景下基本不可接受 |

这套预算只用于：

- 摆腿后段
- touchdown 前后局部窗口

不用于整步全局平均的宽口径解释。

因此，`12A` 中那些持续落在 `30~50 ms` 甚至更高的 `state -> joint` 窗口，后续默认按风险项处理，而不是按“正常并联结构都会有一点延迟”放过。

## 指标字典表

| 指标 | 含义 | 当前用途 |
|---|---|---|
| `state -> joint lag` | 执行器状态变化，到关节实际位置变化之间的滞后时间 | 判断主 lag 是否落在执行兑现段 |
| `state -> joint corr` | 执行器状态与关节位置在对齐后趋势有多一致 | 判断这段兑现关系是否稳定、是否像线性关系 |
| `state -> joint gain` | 执行器状态变化，最终在关节侧兑现出的比例 | 判断 joint 是否只兑现出一小部分变化量 |
| `state -> joint hysteresis area` | `actuator_state` 与 `joint_pos` 形成的回环面积大小 | 判断是否存在明显回环、空程、迟滞感 |
| `stiction_ratio` | actuator 已经在动、但 joint 仍局部长时间不动的比例 | 判断是否有 stick-slip / 粘滞倾向 |
| `left/right state->joint lag gap` | 左右两条链在 `state -> joint lag` 上的差值 | 判断左右链是否兑现不一致 |
| `left/right state->joint gain gap` | 左右两条链在兑现幅值比例上的差值 | 判断左右链是否存在兑现效率差异 |
| `left/right lag sign flip count` | 多组样本中“哪侧更慢”结论翻转的次数 | 判断是否是固定单侧问题，还是模式会随工况翻转 |
| `overall_slow` | 形态标签：lag 本身已经很大 | 表示“整体慢”是主要表面特征 |
| `backlash_like` | 形态标签：更像存在回环、空程、迟滞 | 当前最稳定的主标签，用于支持“兑现回环/迟滞”判断 |
| `stick_slip_like` | 形态标签：更像粘住后再突然释放 | 用于识别局部卡滞/摩擦异常窗口 |
| `low_realization_gain` | 形态标签：执行器变化大，但 joint 兑现比例低 | 用于识别“变化传不过去”的窗口 |
| `mostly_linear` | 形态标签：该窗口里更像普通线性兑现 | 说明这段窗口没有强烈落入其他异常类型 |
| `joint -> sole_roll lag` | 关节变化到足底 `sole_roll` 变化之间的滞后 | 用于后续 `12C` 区分执行兑现不足和几何放大 |
