# 12_parallel_actuation_realization_probe

状态：`done`

## 进入条件

`11` 线已经把执行链 lag 收到下面这组结论：

- `output` 不是主瓶颈
- `cmd -> state` 不是主 lag 段
- 主 lag 段更像 `actuator_state -> joint_pos`
- 该 lag 普遍在 `swing` 窗就已存在
- `left/right asymmetry` 明显，但慢侧不稳定

因此，当前正式进入 `12`：

**专门解释为什么执行器状态已经变化，但关节空间没有及时兑现。**

## 目标

把 `state -> joint` 这段再往下拆，优先区分：

1. 并联映射兑现问题
2. 机械间隙/摩擦/卡滞
3. 左右链不一致
4. 接触或预接触负载影响

## 当前工作假设

### P1. `state -> joint` lag 主要不是通信问题，而是并联执行兑现问题

依据：

- `cmd -> state` 不是主滞后段
- 大 lag 已经落在 `state -> joint`

### P2. `state -> joint` lag 在 swing 期已存在，说明不完全依赖 touchdown 接触

依据：

- `11` 线的 `4` 组 actuator-state 复核里，`swing` 窗 lag 普遍大于 `touchdown`

### P3. 左右不对称来自并联两支链兑现不一致，而不是固定单侧故障

依据：

- `left/right asymmetry` 存在
- 但慢侧在不同 case 中会翻转

## 核心问题

当前 `12` 线只回答这 3 个问题：

1. `state -> joint` 更像线性兑现不足，还是非线性 stick-slip / 间隙问题
2. 左右并联两支链是否存在不一致的兑现模式
3. `joint_pos -> sole_roll` 是否只是下游几何放大，还是上游兑现不足已足以解释主要问题

## 核心指标

### 执行兑现指标

- `state -> joint lag`
- `state -> joint corr`
- `state -> joint gain`
- `state -> joint hysteresis area`

### 左右链一致性指标

- `left/right state->joint lag gap`
- `left/right state->joint gain gap`
- `left/right lag sign flip count`

### 非线性迹象

- 小幅变化时是否长时间不动
- 过阈值后是否突然跃迁
- 同一窗口内是否存在回程不一致

## 最小测试计划

### Phase A. state->joint 兑现形态分析

状态：`done`

动作：

- 对已有 `4` 组 actuator-state 日志
- 逐事件分析 `actuator_state_pos` 与 `joint_pos`
- 输出：
  - lag
  - corr
  - gain
  - 单窗内非线性指标

目标：

- 判断更像“整体慢”，还是“卡滞/跃迁”

当前结果：

- `backlash_like` 是最普遍、最稳定的主标签
- `low_realization_gain` 在部分 case 中突出
- `stick_slip_like` 只在部分窗口出现，不是全局主标签
- 当前更像“backlash / hysteresis + 部分窗口 gain 偏低”，而不是单纯线性整体慢

### Phase B. 左右链不一致分析

状态：`done`

动作：

- 独立比较左右 ankle 两条执行链
- 统计不同 case 中：
  - 哪一侧更慢
  - 哪一侧 gain 更低
  - 哪一侧回程更差

目标：

- 判断是否存在稳定的“左右兑现模式不一致”

当前结果：

- `left/right asymmetry` 仍然明显
- 但 lag / gain / shape 三条轴上的“更差侧”并不统一
- 当前更合理的收口是：
  - 存在左右链不一致
  - 它更像 `mode-dependent asymmetry`
  - 不能收口为固定单侧故障

### Phase C. 兑现不足 vs geometry 放大分离

状态：`done`

动作：

- 把 `state -> joint` 与 `joint -> sole_roll` 两段放在同一窗口内比较
- 看：
  - 若 `joint` 本身变化已经很滞后，是否足以解释主要 `sole_roll`
  - 若 `joint` 变化并不夸张，但 `sole_roll` 仍异常，则剩余部分保留给 `coupled_geometry`

目标：

- 为后续主线划清：
  - 哪部分是执行兑现不足
  - 哪部分是几何/foot-space 放大

当前结果：

- `12C` 没有支持“执行兑现不足已经足够解释全部 sole_roll”。
- 更合理的收口是：
  - `swing` 窗里，执行兑现不足有时已足以主导（如 `30/0.4`）
  - 但大多数 `swing` case 仍是 `mixed_with_geometry_residual`
  - `touchdown` 窗里则更多落成 `geometry_residual_dominant`
- 当前 `8` 个 case/window 的分离结果：
  - `realization_dominant = 1`
  - `mixed_with_geometry_residual = 4`
  - `geometry_residual_dominant = 3`
- 因此 `12` 线当前更适合作为：
  - 解释 `state -> joint` 为什么已经明显不健康
  - 但不能替代 `05` 线去解释最终 `sole_roll` 的主要 touchdown 异常

## 成功标准

本专项至少要收敛出下面两条中的一条：

1. `state -> joint` 已能明确解释为某类兑现问题（整体慢 / 间隙 / stick-slip / 左右链不一致）
2. `state -> joint` 只能解释部分现象，剩余主问题继续交给 `coupled_geometry`

## 与主线的关系

如果 `12` 收敛成功，后续主线就可以拆成：

- `12`: 并联执行兑现不足
- `05`: 几何/映射偏置

如果 `12` 仍不能收敛，再把硬件排查优先级继续上调。

当前收口见 [12_parallel_actuation_realization_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/12_parallel_actuation_realization_probe.md:1)：`state -> joint` 存在不健康兑现，主形态更像 `backlash / hysteresis` 并发 `low_realization_gain` 与 `mode-dependent asymmetry`；但 touchdown 主残差仍应交给 `05` 的 `joint_pos -> sole_roll` foot-space / contact residual。
