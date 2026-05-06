# 10 Execution Chain Disentanglement

## 数据源

本轮先基于 t27 诊断日志做 H2 代理判定：

- [t27_tracking_lag_b1_diag_20260428_152240.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_152240.csv:1)
- [t27_tracking_lag_b1_diag_20260428_161322.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_161322.csv:1)
- [t27_tracking_lag_b1_diag_20260428_162312.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_162312.csv:1)
- [t27_tracking_lag_b1_diag_20260428_163825.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_163825.csv:1)
- [t27_tracking_lag_b1_diag_20260428_164817.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv:1)

分析脚本：
- [.oma/sim2real/plans/forward_x_failure/scripts/10a_execution_chain_disentanglement_h2_t27.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/10a_execution_chain_disentanglement_h2_t27.py:1)

生成结果：
- [round3_t27_execution_chain_disentanglement_h2.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_t27_execution_chain_disentanglement_h2.csv:1)
- [round3_t27_execution_chain_disentanglement_h2.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_t27_execution_chain_disentanglement_h2.md:1)

随后补上 `/actuator_cmd` 与 `/actuator_states` 后，又对新日志做了 actuator-state 级别拆分：

- [t27_tracking_lag_b1_diag_20260429_161248.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260429_161248.csv:1)

分析脚本：
- [.oma/sim2real/plans/forward_x_failure/scripts/11a_execution_chain_disentanglement_actuator_t27.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/11a_execution_chain_disentanglement_actuator_t27.py:1)

生成结果：
- [round3_execution_chain_disentanglement_actuator_20260429_161248.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_disentanglement_actuator_20260429_161248.csv:1)
- [round3_execution_chain_disentanglement_actuator_20260429_161248.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_disentanglement_actuator_20260429_161248.md:1)

随后又把现有 `5` 组 t27 proxy 样本与 `1` 组 actuator-state 样本做了 cross-case 汇总：

- [round3_execution_chain_disentanglement_cross_case_compare.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_disentanglement_cross_case_compare.csv:1)
- [round3_execution_chain_disentanglement_cross_case_compare.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_disentanglement_cross_case_compare.md:1)

## 结论

先用 `pos_des_lpf -> pos` 作为执行链代理后，H2 的代理判定成立。

更准确地说：

- `lpf -> pos` 代理滞后在多数 t27 样本里明显存在
- `sole_roll` 仍主要跟随执行链，不直接跟随 output
- 高 kp 组更容易把这类迟滞放大，但没有形成稳定周期限环

## 结果摘要

| case | events | mean_abs_sole_roll | mean lpf->pos lag (ms) | mean pos->sole lag (ms) | H2 proxy support | dominant source |
|---|---:|---:|---:|---:|---:|---|
| 35/0.5 baseline | 4 | 1.6941 | 133.0428 | 0.0000 | 0.7500 | execution_chain_dominant |
| 50/0.8 right_roll | 4 | 1.7233 | 136.5278 | 18.5122 | 0.7500 | execution_chain_dominant |
| 40/0.8 right_roll | 4 | 1.6043 | 134.4351 | 71.8532 | 0.5000 | output_chain_dominant |
| 25/0.5 right_roll | 4 | 1.5744 | 141.8291 | 9.1503 | 1.0000 | execution_chain_dominant |
| 25/0.5 all_ankles | 4 | 1.6298 | 143.7665 | 16.4978 | 1.0000 | execution_chain_dominant |

## 解释

1. 这不是严格的 actuator-state 分解。
2. 但在现有日志下，`pos_des_lpf -> pos` 已经足够作为执行链代理，支持“执行链迟滞明显”的判断。
3. `sole_roll` 仍然主要跟随执行链，不支持“output 直接把脚做坏”作为主解释。

## actuator-state 实测确认

补上执行器日志后，`10` 线从“代理判定”收紧成了“代理 + actuator-state 实测确认”：

1. 前 `4` 个 touchdown 的 `sole_roll` 主导来源仍是 `execution_chain_dominant`。
2. 最贴 `sole_roll` 的信号不是 `action / pos_des_raw`，而是 `actuator_state_pos_*`。
3. `actuator_cmd -> actuator_state` 在这份日志里基本落在当前 `10 ms` 采样分辨率以内，没有再表现出独立的大滞后段。
4. 更明显的延迟仍出现在 `actuator_state -> joint_pos` 这一段，尤其左踝一侧更突出。

因此，当前更准确的说法是：

- `output` 侧并不是主要矛盾；
- `sole_roll` 仍然主要跟随执行链；
- 新增 actuator-state 证据支持“问题主要落在执行器反馈到关节/足底兑现这段”，而不是“网络直接把脚做歪”。

## actuator-state 结果摘要

| source log | events | mean_abs_sole_roll | mean action->sole lag (ms) | mean raw->sole lag (ms) | mean tau_lpf->sole lag (ms) | mean joint_pos->sole lag (ms) | mean left act cmd->state lag (ms) | mean right act cmd->state lag (ms) | mean left act state->joint lag (ms) | mean right act state->joint lag (ms) | dominant source |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `t27_tracking_lag_b1_diag_20260429_161248.csv` | 4 | 1.7463 | 8.6799 | 8.6799 | 41.2294 | 32.5495 | 0.0000 | 0.0000 | 49.9092 | 8.6799 | execution_chain_dominant |

## cross-case 汇总

当前仓库中，带 `/actuator_cmd + /actuator_states` 的 t27 日志只有 `1` 组，因此 cross-case 采用：

- `5` 组 proxy case
- `1` 组 actuator-state case

统一结果是：

1. proxy 口径下，`5` 组参数中有 `4/5` 明确落在 `execution_chain_dominant`；`40/0.8 right_roll` 虽在 proxy 判据下偏向 `output_chain_dominant`，但当前应降级理解为“proxy 判据不稳”，不单独据此推翻执行链主导结论。
2. actuator-state 实测组 `4 ankles = 25/0.5` 仍是 `execution_chain_dominant`，和 proxy 主趋势一致。
3. 因此，当前最稳的结论没有变：`output` 不是主瓶颈，`sole_roll` 更主要跟随执行链，而 `coupled_geometry` 仍作为并发底层偏置保留。

基于现阶段综合判断，`40/0.8` 也应暂时归入同一解释框架：

- `output` 不是主瓶颈
- `sole_roll` 主要跟随执行链
- `coupled_geometry` 仍保留为并发底层偏置

## Dead-zone 边界

这份 `10` 线结论需要加一层修正：

1. 当 `action` / `pos_des_raw` 幅值较小，`sole_roll` 更像跟随执行链，并不等于机械结构一定是唯一主因。
2. 小信号 dead-zone / 阈值响应会让一部分 `execution_chain_dominant` 只表示“输出已发出，但还没跨过兑现门槛”。
3. 因此，`10` 线当前更准确的说法是：
   - `output` 不是主瓶颈
   - `sole_roll` 更接近执行链
   - 其中一部分 swing lag 先按死区 / 小信号兑现困难理解，而不是直接归到机械结构

也就是说，`40/0.8` 当前不再作为“output 主导”的反例使用；它只说明在 proxy 口径下，该组样本的判据稳定性更差，更需要 actuator-state 实测来确认。

需要明确一个边界：

- proxy 表里的 `exec-internal lag` 指的是 `pos_des_lpf -> pos`
- actuator-state 表里的 `exec-internal lag` 指的是 `actuator_state -> joint_pos`

这两个量不是同一个物理定义，因此不能把数值直接一一对应；它们只能用于“方向一致性”判断，不能做绝对大小的横向等同。

## 后续保留项（进度标记）

> 以下均为**明确延迟**的验证项，不是当前第一优先级。当前第一优先级是 `05D FK Foot-Frame / Contact` 现场复核（见 [00_forward_x_failure_progress_review.md](./00_forward_x_failure_progress_review.md)）。只有在重开执行链复核时才执行。

- ⬜ 补录高 `kp` actuator-state 日志（优先 `40/0.8`，其次 `50/0.8`），用于直接验证”proxy 不稳但执行链仍主导”
- ⬜ 在相同 kp 条件下补更多 actuator-state 日志，对比高/低 kp 下 `actuator_state -> joint_pos` 差异的稳定性
- ⬜ 左右踝不对称复核：确认左踝 `state -> joint` 更慢是稳定现象还是单次波动
- ✅ 保留 `coupled_geometry` 主线（actuator-state 实测未推翻 swing/touchdown 的镜像 roll 偏置，已纳入 `05` 边界）

## 指标字典

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `mean_abs_sole_roll` | touchdown 窗 `abs(sole_roll)` 均值 | 量化脚底 roll 不平程度 |
| `mean lpf->pos lag (ms)` | `pos_des_lpf -> pos` 的 proxy 执行链滞后 | 旧日志无 actuator-state 时的执行链代理 |
| `mean pos->sole lag (ms)` | `pos -> sole_roll` 的局部滞后 | 判断 joint-space 到 foot-space 表现是否同步 |
| `H2 proxy support` | proxy 口径是否支持执行链复合延迟假设 | 只能作方向判断，不作 actuator-state 绝对量替代 |
| `action->sole lag` | action 到 `sole_roll` 的滞后 | 判断 output 链与 foot-space 表现的贴近程度 |
| `raw->sole lag` | `pos_des_raw` 到 `sole_roll` 的滞后 | 判断 raw target 与 foot-space 表现的贴近程度 |
| `tau_lpf->sole lag` | LPF target 到 `sole_roll` 的滞后 | 判断滤波目标链路的表现 |
| `joint_pos->sole lag` | joint position 到 `sole_roll` 的滞后 | 判断 joint-space 到 foot-space 的近端关系 |
| `actuator_cmd -> actuator_state` | 驱动命令到 actuator 反馈的滞后 | 当前不是主滞后段 |
| `actuator_state -> joint_pos` | actuator 反馈到 joint-space 位置的滞后 | 当前更明显的执行链主滞后段 |
| `dominant source` | `sole_roll` 更贴近 output 链或 execution 链的分类 | 当前统一口径为 execution-chain 主导，`40/0.8` proxy 反例降级 |
