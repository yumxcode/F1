# 13 Dead Zone Audit

## 这次新增的数据

这一次只看 `swing` 线，主证据限定为：

- `pos_des_raw_right_ankle_roll_joint`

不再把 `action` 作为当前结论依据。`action` 的统计已经转到 `11e`，这里只用 `pos_des_raw` 来判断小信号死区是否稳定存在。

窗口仍沿用当前统一口径：

- `swing = touchdown - 350 ms .. touchdown - 20 ms`

只取每个日志前 `4` 个 `right touchdown` 事件。

## 统计结果

基于所有本地 `t27_tracking_lag_b1_diag_*.csv` 的 swing-only `pos_des_raw` 统计：

| case | csv | events | mean pos_des_raw | mean_abs_pos_des_raw | mean small-signal ratio | min_abs_pos_des_raw | max_abs_pos_des_raw |
|---|---|---:|---:|---:|---:|---:|---:|
| 35/0.5 retest_copy | t27_tracking_lag_b1_diag_20260428_152240.csv | 3 | 0.0878 | 0.0878 | 0.5722 | 0.0247 | 0.1923 |
| 50/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_161322.csv | 3 | -0.1054 | 0.1722 | 0.3619 | 0.0269 | 0.4555 |
| 40/0.8 right_roll | t27_tracking_lag_b1_diag_20260428_162312.csv | 3 | -0.1177 | 0.1742 | 0.4632 | 0.0207 | 0.3991 |
| 25/0.5 right_roll | t27_tracking_lag_b1_diag_20260428_163825.csv | 3 | -0.0850 | 0.1247 | 0.6429 | 0.0011 | 0.4307 |
| 25/0.5 all_ankles | t27_tracking_lag_b1_diag_20260428_164817.csv | 3 | -0.0577 | 0.1193 | 0.5685 | 0.0003 | 0.3813 |
| 25/0.5 all_ankles actuator | t27_tracking_lag_b1_diag_20260429_161248.csv | 3 | -0.0535 | 0.1069 | 0.7016 | 0.0016 | 0.3791 |
| 25/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100024.csv | 3 | -0.0167 | 0.0816 | 0.8119 | 0.0039 | 0.4335 |
| 30/0.4 all_ankles | t27_tracking_lag_b1_diag_20260430_100314.csv | 3 | -0.0733 | 0.0937 | 0.7951 | 0.0010 | 0.4993 |
| 35/0.5 all_ankles | t27_tracking_lag_b1_diag_20260430_100705.csv | 3 | -0.0018 | 0.0779 | 0.7895 | 0.0006 | 0.4359 |
| 40/0.8 all_ankles | t27_tracking_lag_b1_diag_20260430_101404.csv | 3 | -0.0933 | 0.1434 | 0.5672 | 0.0047 | 0.4392 |

### 0.05 粒度分箱

`|pos_des_raw|` 的 0.05 分箱进一步说明，`swing` 期的小信号主要集中在 `0.00 ~ 0.10 rad`，而且不同 kp case 之间只是把分布往更大区间推开一点，并没有改变“swing 期本身就是小幅输出主导”的事实。

典型现象：

- `25/0.4`、`30/0.4`、`35/0.5` 的 `0.00 ~ 0.10 rad` 占比最高，说明小信号兑现最强。
- `50/0.8`、`40/0.8` 虽然会把一部分样本推到 `0.10 ~ 0.20 rad` 甚至更高，但 `0.00 ~ 0.10 rad` 仍然占有相当比例，不是完全离开死区区间。
- `25/0.5 all_ankles actuator` 的 `0.00 ~ 0.10 rad` 占比更高，说明把四个 ankle 一起调软后，swing 期更集中在低幅值、小信号区间，稳定性更强，但推进也更弱。

#### 目标区间三段表

以下按 `|pos_des_raw|` 的 swing-only 分布，统计三段比例：

- `0.00 ~ 0.05 rad`
- `0.05 ~ 0.10 rad`
- `> 0.10 rad`

| case | 0.00 ~ 0.05 | 0.05 ~ 0.10 | > 0.10 | samples |
|---|---:|---:|---:|---:|
| `25/0.4 all_ankles` | `40.2%` | `40.2%` | `19.5%` | `82` |
| `30/0.4 all_ankles` | `64.0%` | `12.0%` | `24.0%` | `75` |
| `35/0.5 all_ankles` | `49.4%` | `27.6%` | `23.0%` | `87` |
| `40/0.8 all_ankles` | `40.0%` | `18.8%` | `41.3%` | `80` |
| `50/0.8 right_roll` | `9.6%` | `24.7%` | `65.8%` | `73` |

这个表的直接含义是：

- `30/0.4` 的 `swing` 期最集中在 `0.00 ~ 0.05 rad`，也就是最小信号区。
- `35/0.5`、`25/0.4` 仍然有很高比例落在 `0.10 rad` 以下，说明 swing 期还是明显偏小。
- `40/0.8` 和 `50/0.8` 明显把分布往更大幅值段推开了，但它们并没有完全摆脱 `0.00 ~ 0.10 rad` 区间。
- `50/0.8` 最明显地把 swing 输出推到了 `> 0.10 rad`，但这并不自动意味着更健康，只说明它更少停留在小信号区。

#### case-level swing 判读

按当前三段表，swing 期可以做一个更实用的工程判读：

| case | swing 判读 |
|---|---|
| `30/0.4 all_ankles` | `dead_zone_dominant` |
| `25/0.4 all_ankles` | `mixed_dead_zone_and_realization`，偏死区 |
| `35/0.5 all_ankles` | `mixed_dead_zone_and_realization`，偏死区 |
| `40/0.8 all_ankles` | `mixed_dead_zone_and_realization` |
| `50/0.8 right_roll` | `realization_dominant`，死区不是主导 |

这张表的作用不是给最终物理真因盖章，而是告诉后续分析：

- 哪些 swing lag 可以先按 dead-zone / small-signal realization 收口
- 哪些 swing lag 仍要继续看执行兑现或几何残余

## 统一结论

这批数据支持下面这条更收敛的解释：

1. **`swing` 窗里，`right_ankle_roll` 的 `pos_des_raw` 确实偏小。**  
   各 case 的 `mean_abs_pos_des_raw` 大致在 `0.0779 ~ 0.1742 rad`，不少窗口里 `abs(pos_des_raw) <= 0.10 rad` 的占比仍然很高。

2. **这个小信号特征是稳定存在的，不是只在低 kp case 才出现。**  
   `25/0.4`、`30/0.4`、`35/0.5` 之外，`40/0.8`、`50/0.8` 也都有明显的小幅 `pos_des_raw` 区间。  
   所以 swing 期的一部分 lag，不能再默认优先解释成机械结构问题。

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
  - 其中 `30/0.4` 更接近 `dead_zone_dominant`
  - `25/0.4`、`35/0.5`、`40/0.8` 更像 `mixed_dead_zone_and_realization`
  - `50/0.8` 的 swing 期已经明显偏离死区主导

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
