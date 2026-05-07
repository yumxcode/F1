# 13 Dead Zone Audit

## 这次新增的数据

这一次只看 `swing` 线，主证据限定为：

- `pos_des_raw_right_ankle_roll_joint`

不再把 `action` 作为当前结论依据。`action` 的统计已经转到 `11e`，这里只用 `pos_des_raw` 来判断小信号死区是否稳定存在。

窗口仍沿用当前统一口径：

- `swing = touchdown - 350 ms .. touchdown - 20 ms`

只取每个日志前 `4` 个 `right touchdown` 事件，事件源改为当前 `ROUND3A.detect_touchdowns()`，不再使用旧 `right_contact: 0 -> 1` proxy。

## 统计结果

基于所有本地 `t27_tracking_lag_b1_diag_*.csv` 的 swing-only `pos_des_raw` 统计：

| case | csv | events | mean pos_des_raw | mean_abs_pos_des_raw | mean small-signal ratio | min_abs_pos_des_raw | max_abs_pos_des_raw |
|---|---|---:|---:|---:|---:|---:|---:|
| 35/0.5 retest_copy | t27_tracking_lag_b1_diag_20260428_152240.csv | 4 | 0.0226 | 0.0397 | 0.9167 | 0.0001 | 0.1923 |
| 50/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_161322.csv | 4 | 0.0218 | 0.0361 | 0.9626 | 0.0000 | 0.3005 |
| 40/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_162312.csv | 4 | 0.0023 | 0.0436 | 0.9320 | 0.0000 | 0.3608 |
| 25/0.5 right_roll | t27_tracking_lag_b1_diag_20260428_163825.csv | 4 | 0.0034 | 0.0386 | 0.9396 | 0.0005 | 0.3917 |
| 25/0.5 all_ankles | t27_tracking_lag_b1_diag_20260428_164817.csv | 4 | -0.0027 | 0.0529 | 0.9026 | 0.0005 | 0.5990 |
| 25/0.5 all_ankles actuator | t27_tracking_lag_b1_diag_20260429_161248.csv | 4 | -0.0248 | 0.0724 | 0.7749 | 0.0011 | 0.3441 |
| 25/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100024.csv | 4 | 0.0241 | 0.0466 | 0.9394 | 0.0002 | 0.2078 |
| 30/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100314.csv | 4 | 0.0128 | 0.0427 | 0.9240 | 0.0022 | 0.2059 |
| 35/0.5 all_ankles | t27_tracking_lag_b1_diag_20260430_100705.csv | 3 | 0.0149 | 0.0694 | 0.8491 | 0.0001 | 0.4410 |
| 40/0.8 all_ankles | t27_tracking_lag_b1_diag_20260430_101404.csv | 4 | -0.0035 | 0.0365 | 0.9302 | 0.0008 | 0.2717 |

### 0.05 粒度分箱

`|pos_des_raw|` 的 0.05 分箱进一步说明，`swing` 期的小信号主要集中在 `0.00 ~ 0.10 rad`，而且这一结论在新 touchdown detector 下更强了：大多数 case 的样本主峰都落在 `0.00 ~ 0.05 rad`。

典型现象：

- `25/0.4`、`30/0.4`、`35/0.5 retest_copy`、`40/0.8 all_ankles` 的 `0.00 ~ 0.10 rad` 占比都接近或超过 `90%`。
- `50/0.8 right_roll` 在旧触地口径下曾看起来更像“大输出”，但新 detector 对齐后，`0.00 ~ 0.10 rad` 也达到 `96%`，不再支持“已明显脱离小信号区”的旧读法。
- `25/0.5 all_ankles actuator` 仍是当前表里相对“更大输出”的 case，但 `0.00 ~ 0.10 rad` 也还有 `77%`，仍属于小信号主导。

#### 目标区间三段表

以下按 `|pos_des_raw|` 的 swing-only 分布，统计三段比例：

- `0.00 ~ 0.05 rad`
- `0.05 ~ 0.10 rad`
- `> 0.10 rad`

| case | 0.00 ~ 0.05 | 0.05 ~ 0.10 | > 0.10 | samples |
|---|---:|---:|---:|---:|
| `25/0.4 all_ankles` | `64.1%` | `29.8%` | `6.1%` | `131` |
| `30/0.4 all_ankles` | `77.7%` | `14.6%` | `7.7%` | `130` |
| `35/0.5 all_ankles` | `56.0%` | `29.0%` | `15.0%` | `100` |
| `40/0.8 all_ankles` | `81.5%` | `11.5%` | `6.9%` | `130` |
| `50/0.8 right_roll` | `82.7%` | `13.5%` | `3.8%` | `133` |

这个表的直接含义是：

- `40/0.8`、`50/0.8` 在新 detector 下都回到以 `0.00 ~ 0.05 rad` 为主，不再支持“高 kp case swing 已脱离 dead-zone 主导”的旧结论。
- `35/0.5 all_ankles` 仍然是这组里相对更大的一个，但绝大多数样本依旧落在 `0.10 rad` 以下。

#### case-level swing 判读

按当前三段表，swing 期可以做一个更实用的工程判读：

| case | swing 判读 |
|---|---|
| `25/0.4 all_ankles` | `dead_zone_dominant` |
| `30/0.4 all_ankles` | `dead_zone_dominant` |
| `35/0.5 all_ankles` | `mixed_dead_zone_and_realization`，偏死区 |
| `40/0.8 all_ankles` | `dead_zone_dominant` |
| `50/0.8 right_roll` | `dead_zone_dominant` |

这张表的作用不是给最终物理真因盖章，而是告诉后续分析：

- 哪些 swing lag 可以先按 dead-zone / small-signal realization 收口
- 哪些 swing lag 仍要继续看执行兑现或几何残余

## 统一结论

这批数据支持下面这条更收敛的解释：

1. **`swing` 窗里，`right_ankle_roll` 的 `pos_des_raw` 在新 detector 下更偏小。**  
   各 case 的 `mean_abs_pos_des_raw` 大致在 `0.0361 ~ 0.0724 rad`，`abs(pos_des_raw) <= 0.10 rad` 的占比大多在 `0.85 ~ 0.96`。

2. **这个小信号特征是稳定存在的，不是只在低 kp case 才出现。**  
   `40/0.8`、`50/0.8` 在修正触地事件后同样落回小信号主导区。  
   所以 swing 期的一部分 lag，更不应该默认先解释成机械结构问题。

3. **`swing` 期更合理的优先解释是小信号死区 / 阈值敏感区 / 低幅值兑现困难。**  
   也就是：
   - 目标已经给出
   - 但幅值太小，执行链还没跨过有效兑现门槛
   - 局部 lag 会被放大

4. **`touchdown` 残差仍然不在 A 线里。**  
   touchdown 期的几何残差仍应保留给 `05 / 12C`，不能被 dead-zone 全部替代。

## 对现有 plan 实验的统一审视

### `11` 线

`11` 线里的 `state -> joint` 大 lag，至少一部分 swing lag 现在应该先按小信号死区和低幅值兑现困难去理解。  
也就是说：

- `cmd -> state` 不是主瓶颈，这点不变
- `state -> joint` 仍是主 lag 段，这点不变
- 但 `swing` 期的 lag 不再默认等价于“机械结构故障”
  - `25/0.4`、`30/0.4`、`40/0.8` 现在都更接近 `dead_zone_dominant`
  - `35/0.5` 保留为 `mixed_dead_zone_and_realization`
  - `50/0.8 right_roll` 不再保留 `realization_dominant` 旧读法

### `12` 线

`12` 线里的 `backlash_like / low_realization_gain / mode-dependent asymmetry` 仍成立，  
但它们更像是：

- 执行兑现不足的行为特征
- 其中一部分 swing 窗口是死区敏感区
- 另一部分窗口才更像结构性迟滞或摩擦

### `05` 线

`05` 线的 `coupled_geometry` 仍然成立，尤其是 touchdown residual。  
但 `05` 不能再被用来解释所有 lag：

- `swing` 期的部分 lag 可能只是死区下的低幅值响应慢
- `touchdown` 期的几何残差仍要保留给 `05`

## 计划调整

后续审查 plan 实验时，默认采用下面的优先级：

1. 先看 `swing` 期输出幅值是否已经落入死区 / 阈值敏感区。
2. 再看执行兑现是否真的异常。
3. 最后才把 residual 归到机械结构或 geometry。

## 结果文件引用

- [swing dead-zone summary](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_dead_zone_swing_pos_des_raw_summary.md:1)
- [swing dead-zone CSV](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_dead_zone_swing_pos_des_raw_summary.csv:1)

## 指标字典

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `pos_des_raw` | 网络 action 缩放、叠加 init、限幅后的 joint-space 原始目标 | 本线唯一主证据来源；不再用 `action` 直接下结论 |
| `mean_abs_pos_des_raw` | swing 窗 `abs(pos_des_raw)` 均值 | 判断输出目标是否整体偏小 |
| `small_signal_ratio` | `abs(pos_des_raw)` 落入小信号区的样本占比 | 判断 dead-zone / threshold-sensitive 风险 |
| `min_abs_pos_des_raw` | swing 窗最小绝对目标幅值 | 判断是否长期贴近零附近 |
| `max_abs_pos_des_raw` | swing 窗最大绝对目标幅值 | 判断该窗口是否曾明显跨过兑现门槛 |
| `0.05 rad bin` | 以 `0.05 rad` 为粒度的幅值分箱 | 细化小信号区分布 |
| `dead_zone_dominant` | swing lag 优先由小信号死区解释 | 当前用于修正 `11` 线部分 case |
| `mixed_dead_zone_and_realization` | 小信号死区与执行兑现不足并存 | 当前用于修正 `11/12` 线部分 case |
| `realization_dominant` | 输出幅值不小但兑现仍差 | 再转向结构性迟滞、摩擦、回差和左右不一致 |
| `touchdown residual` | touchdown 期 `joint_pos -> sole_roll` 残差 | 不由 `13` 解释，仍交给 `05/12C` |
