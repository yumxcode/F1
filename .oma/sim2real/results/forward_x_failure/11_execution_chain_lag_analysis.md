# 11 Execution Chain Lag Analysis

## 进入前统一结论

上一轮 `10` 线已经收口为：

- `output` 不是主瓶颈
- `sole_roll` 主要跟随执行链
- `coupled_geometry` 仍保留为并发底层偏置

因此，`11` 线不再讨论来源归因，而是只聚焦：

- 执行链 lag 落在哪一段
- lag 在哪个窗口被放大
- 左右踝是否存在稳定不对称

## 当前已知事实

基于 [10_execution_chain_disentanglement.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/10_execution_chain_disentanglement.md:1)：

1. `actuator_cmd -> actuator_state` 在当前 `10 ms` 采样分辨率下未见独立大滞后。
2. 更明显的迟滞落在 `actuator_state -> joint_pos`。
3. `sole_roll` 仍主要跟随执行链，不直接跟随 `action / pos_des_raw`。
4. `40/0.8` 当前降级为 proxy 判据不稳，不再单独作为 output 主导反例。

## 本轮分析边界

`11` 线只回答执行链 lag 本身，不重复做：

- output vs execution source 归因
- `kp/kd` 扫参优劣判断
- `coupled_geometry` 的映射/符号链归因

这些内容已分别由 `08/09/10/05` 承担。

## 原计划与完成状态

本线原计划按下面顺序推进；当前 `Phase A/B` 已完成，`Phase C` 已降级为保留验证项，不是当前第一优先级：

1. ✅ 对现有 actuator-state 日志按 `swing / touchdown` 重分窗（Phase A，已完成）
2. ✅ 独立统计 left/right 的 `actuator_state -> joint_pos lag`（Phase B，已完成；结论：不对称存在，但慢侧不稳定）
3. ⬜ 再补高 `kp` actuator-state 数据，优先 `40/0.8`（Phase C，**已延迟**，仅在重开执行链复核时执行，当前不是第一优先级）

## Phase A 结果

已对现有 actuator-state 日志完成 `swing / touchdown` 重分窗分析：

- [round3_execution_chain_lag_windowed_20260429_161248.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_lag_windowed_20260429_161248.csv:1)
- [round3_execution_chain_lag_windowed_20260429_161248.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_lag_windowed_20260429_161248.md:1)

当前样本给出的直接结果：

1. `actuator_cmd -> actuator_state` 在 `swing` 与 `touchdown` 两个窗口中都近似 `0 ms`，支持“命令接受段不是主滞后段”。
2. `actuator_state -> joint_pos` 在当前样本中 **不是 touchdown 才突然放大**，而是 **swing 期就已经明显存在**。
3. 当前样本里，`swing` 窗平均 `state -> joint lag` 约 `81.37 ms`，`touchdown` 窗约 `29.29 ms`。
4. 左右不对称明显：
   - `swing` 窗左踝 `state -> joint lag` 均值约 `156.24 ms`
   - `swing` 窗右踝 `state -> joint lag` 均值约 `6.51 ms`
   - `touchdown` 窗左踝约 `49.91 ms`
   - `touchdown` 窗右踝约 `8.68 ms`

## 当前阶段结论

基于这份唯一 actuator-state 样本，`11` 线现阶段应暂时收成：

- `actuator_cmd -> actuator_state` 不是主滞后段
- 主滞后段仍更像 `actuator_state -> joint_pos`
- 该滞后在当前样本里 **接触前就已经存在**，而不是只在 touchdown 窗才出现
- 左踝明显比右踝更慢，左右不对称优先级上升

这意味着：

- 原先 `L3: lag 在 touchdown 接触窗会被进一步放大`，在当前样本上**没有得到支持**
- 当前更合理的说法是：
  - touchdown 可能会改变 `sole_roll` 表现
  - 但执行链 lag 本身更像是 **pre-contact 已存在** 的问题

## 多样本 actuator-state 复核

随后对 `4` 组 all-ankle actuator-state 日志做了同口径复核：

- `25 / 0.4`
- `30 / 0.4`
- `35 / 0.5`
- `40 / 0.8`

输出文件：

- [round3_execution_chain_lag_multi_sample_summary.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_lag_multi_sample_summary.csv:1)
- [round3_execution_chain_lag_multi_sample_detail.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_lag_multi_sample_detail.csv:1)
- [round3_execution_chain_lag_multi_sample_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_lag_multi_sample_summary.md:1)

这 `4` 组样本共同支持：

1. `state -> joint` 的大 lag 普遍在 `swing` 窗就已经存在，不是 touchdown 才突然出现。
2. `touchdown` 窗的 `state -> joint lag` 在这 `4` 组里都比 `swing` 更小。
3. 因此，当前不再把“touchdown 接触放大 lag”作为默认主解释；更合理的主解释是 **pre-contact execution lag**。

窗口均值概览：

- `25 / 0.4`: `swing 71.81 ms`，`touchdown 23.56 ms`
- `30 / 0.4`: `swing 93.55 ms`，`touchdown 26.05 ms`
- `35 / 0.5`: `swing 66.05 ms`，`touchdown 4.63 ms`
- `40 / 0.8`: `swing 37.75 ms`，`touchdown 20.59 ms`

## 对 `cmd -> state` 的修正理解

此前基于单样本，我们把 `cmd -> state` 近似看成 `0 ms` 段。

在 `4` 组复核后，这个说法需要收紧：

- `cmd -> state` 仍然不是当前最主要的大 lag 段
- 但它并非在所有 case / 所有窗口都严格为 `0`
- 当前更合理的说法是：
  - `cmd -> state` 不是主瓶颈
  - `state -> joint` 仍是主滞后段

## 左右不对称的当前口径

多样本结果里，左右不对称是存在的，但**符号不稳定**：

- `25 / 0.4`：左慢于右
- `30 / 0.4`：左略慢于右
- `35 / 0.5`：右慢于左
- `40 / 0.8`：右慢于左

因此，当前不能把“左踝一定更慢”当作稳定结论。

更准确的表述是：

- **存在显著 left/right asymmetry**
- 但**慢的是哪一侧还不稳定**
- 现阶段更像“并联执行链左右不一致”，而不是“固定左侧硬件故障”

## 当前判定口径

在 `11` 线中，默认使用下面的解释框架：

- 主解释：执行链 lag
- 并发偏置：`coupled_geometry`
- 额外修正：小信号死区 / 阈值响应需要优先排查，不能把所有 `swing` 期 lag 都默认归到机械结构
- 非主解释：output 链

也就是说，后续所有 `11` 线分析都默认在这个前提下展开，除非 actuator-state 新证据明确推翻它。

## 0.6 m/s 步态下的延迟预算口径

对当前 `0.6 m/s` 前进步态，判断 `state -> joint` 是否可接受，不应看“是否为 0”，而应看它在 touchdown 前有效控制窗口里占了多少预算。

当前统一采用下面这组工程口径：

| `state -> joint_pos` 延迟 | 判断 |
|---|---|
| `< 15~20 ms` | 较健康，通常不会明显吃掉 touchdown 前调平预算 |
| `15~30 ms` | 可接受但偏紧，策略和几何偏置必须足够干净 |
| `30~50 ms` | 高风险，已明显侵占 touchdown 前有效控制窗口 |
| `> 50 ms` | 当前问题场景下基本不可接受 |

需要明确两点：

1. 这套口径主要针对 **摆腿后段到 touchdown 前后** 的局部窗口，不是整步全局平均。
2. 延迟是否稳定，与延迟均值同样重要；若窗口内波动很大，即使均值不高，也会明显伤害调平兑现。

基于这套预算，`11` 线当前看到的 `swing` 窗 `state -> joint` 大 lag，已经处在明确风险区间内。

## Dead-zone 修正

后续回看 `11` 线时，需要把下面这条作为修正口径：

1. `swing` 窗里如果 `action` / `pos_des_raw` 幅值已经明显偏小，lag 的一部分应先按 dead-zone / small-signal realization 理解。
2. 只有当输出幅值并不小、lag 仍持续偏大，才优先把残差往机械结构、间隙、摩擦和左右不一致上推进。
3. 因此，`11` 线里的 `state -> joint lag` 不再默认等同于“机械结构迟滞”，而是“执行兑现不足 + 死区敏感 + 结构残余”的组合。

## 指标字典

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `cmd -> state lag` | actuator 命令到 actuator 反馈的延迟 | 当前不是主滞后段 |
| `state -> joint lag` | actuator 反馈到 joint-space 位置的延迟 | 当前更主要的执行链 lag 段 |
| `joint -> sole lag` | joint position 到 `sole_roll` 的延迟 | 判断 joint-space 到 foot-space 的额外表现滞后 |
| `swing_window` | touchdown 前腾空窗口 | 判断 lag 是否在接触前已存在 |
| `touchdown_window` | touchdown 附近窗口 | 判断接触是否进一步放大 lag |
| `lag_gap_ms` | 左右踝 lag 差值 | 判断左右链不一致程度 |
| `dominant_lag_side` | 当前窗口中 lag 更大的侧 | 当前会随样本 / 窗口变化，不作为固定单侧故障 |
| `0.6mps_delay_budget` | 0.6 m/s 步态下对 touchdown 前控制窗口的延迟预算 | `<15~20 ms` 较健康，`>50 ms` 基本不可接受 |
| `dead_zone_dominant` | 输出幅值偏小导致 lag 优先按死区理解 | `13` 对 `11` 的修正口径 |
| `mixed_dead_zone_and_realization` | 小信号死区与执行兑现不足同时存在 | swing lag 的当前主要解释框架之一 |
