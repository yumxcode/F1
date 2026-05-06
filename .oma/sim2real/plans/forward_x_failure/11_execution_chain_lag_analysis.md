# 11_execution_chain_lag_analysis

状态：`done`

## 进入条件

上一轮 `10` 线已经收口到统一结论：

- `output` 不是主瓶颈
- `sole_roll` 主要跟随执行链
- `coupled_geometry` 仍保留为并发底层偏置

因此，当前不再继续争论“是不是 output 做坏了”，而是正式进入执行链 lag 分析。

## 目标

把当前执行链问题从“来源判定”推进到“滞后分段定位”。

重点只回答这 3 个问题：

1. 执行链 lag 主要落在哪一段
2. 这个 lag 是 swing 期已有，还是 touchdown 接触后被放大
3. 左右踝是否存在稳定不对称

## 当前工作假设

### L1. `actuator_cmd -> actuator_state` 不是主滞后段

依据：

- 现有 actuator-state 日志下，这一段在当前 `10 ms` 采样分辨率内未表现出独立大滞后

当前状态：`保留`

说明：

- 多样本复核后，这一段并非在所有 case / 所有窗口都严格为 `0`
- 但它仍不是当前最大、最稳定的 lag 段

### L2. `actuator_state -> joint_pos` 是当前更主要的执行链 lag 段

依据：

- `11a` 的 actuator-state 实测里，更明显的迟滞落在这一段

### L3. lag 在 touchdown 接触窗会被进一步放大

依据：

- 高 `kp` 组在 `09` 中表现出更大的局部相位滞后
- `sole_roll` 仍主要跟随执行链

当前状态：`待复核`

说明：

- 现有唯一 actuator-state 样本并不支持“touchdown 窗 lag 比 swing 更大”
- 当前样本里更像是 lag 在 `swing` 期就已明显存在

## 分析范围

只看前 `4` 个 touchdown，对每个事件分两个窗口：

1. `swing` 窗：`touchdown - 350 ms` 到 `touchdown - 20 ms`
2. `touchdown` 窗：`touchdown - 50 ms` 到 `touchdown + 100 ms`

## 核心指标

### 执行链分段 lag

- `actuator_cmd -> actuator_state lag`
- `actuator_state -> joint_pos lag`
- `joint_pos -> sole_roll lag`

### 左右不对称

- `left/right actuator_state -> joint_pos lag mean`
- `left/right actuator_state -> joint_pos lag std`
- `left/right joint_pos -> sole_roll lag mean`

### 窗口放大效应

- `swing lag`
- `touchdown lag`
- `touchdown - swing` 增量

## 最小测试计划

### Phase A. 现有 actuator-state 数据重分窗

状态：`done`

动作：

- 对已有 `t27_tracking_lag_b1_diag_20260429_161248.csv` 重做：
  - `swing` 窗
  - `touchdown` 窗
- 输出 left/right 分段 lag 表

目标：

- 确认当前唯一 actuator-state 样本里，lag 是腾空期已有还是 touchdown 才明显放大

当前结果：

- `actuator_cmd -> actuator_state` 在两个窗口都近似 `0 ms`
- `actuator_state -> joint_pos` 在 `swing` 期就已明显存在
- 当前样本不支持“touchdown 窗是主放大窗口”，反而更像 `pre-contact lag`
- 该结论已被后续 `4` 组 actuator-state 多样本复核继续支持

### Phase B. 左右踝不对称复核

状态：`done`

动作：

- 在同一份 actuator-state 日志里，独立统计：
  - 左踝 `state -> joint`
  - 右踝 `state -> joint`

目标：

- 判断左踝更慢是否稳定成立

当前结果：

- 多样本复核表明，左右不对称是存在的
- 但“慢的是左还是右”目前不稳定
- 因此当前应收口为：
  - 存在 `left/right asymmetry`
  - 但不能收口为单侧固定故障

### Phase C. 高 kp actuator-state 复测

状态：`deferred`

动作：

- 优先补：
  - `40 / 0.8`
- 其次补：
  - `50 / 0.8`

目标：

- 判断高 `kp` 下执行链 lag 是否稳定增大
- 判断 `40/0.8` 的 proxy 判据不稳，是否在 actuator-state 口径下仍回到执行链主导

## 成功标准

本专项至少要收敛出下面两条中的一条：

1. 当前主滞后段明确是 `actuator_state -> joint_pos`
2. lag 的主要放大窗口明确是 `touchdown`，还是 `swing`

当前进展：

- 第 1 条已得到较强支持
- 第 2 条当前已更偏向 `swing`

## 与主线的关系

如果 `11` 能确认执行链主滞后段和窗口放大位置，就可以把后续问题进一步拆成：

- 执行链兑现不足
- `coupled_geometry` 叠加偏置

如果 `11` 仍无法收敛，就要把硬件排查优先级继续上调。

当前收口见 [11_execution_chain_lag_analysis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/11_execution_chain_lag_analysis.md:1)：主滞后段仍更像 `actuator_state -> joint_pos`；大 lag 在 `swing` 期已存在；左右不对称存在但慢侧不稳定，不能收口为单侧固定故障。
