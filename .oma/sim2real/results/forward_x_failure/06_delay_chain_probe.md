# Round 3D Delay Chain Probe 结果

本轮基于同一时间戳的三份日志：

- [t25_action_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t25_action_20260326_102002.csv)
- [t23_joint_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t23_joint_20260326_102002.csv)
- [t3_current_20260326_102002.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t3_current_20260326_102002.csv)

分析脚本：

- [06_delay_chain_probe.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/06_delay_chain_probe.py:1)

## 主要结果

### 1. `action -> target`

所有 lower-body 关节在当前数据上都给出：

- `action->target = 0.0 ms`

这说明：

- policy 输出到关节目标的链路没有显示出可测的额外滞后
- 当前问题不是 policy 输出本身晚了

### 2. `target -> current`

四个 ankle 关节大致在：

- `20 ~ 30 ms`

膝和髋大致也在：

- `20 ~ 30 ms`

这说明：

- 执行器电流响应存在稳定的几十毫秒级延迟
- 但这一段不是 ankle 独有，髋和膝也有类似量级

### 3. `current -> pos`

当前数据里，ankle 的均值大约在：

- `102.5 ms`

hip 约：

- `81.7 ms`

knee 约：

- `145.0 ms`

这说明：

- 电流到关节位姿的机械响应存在明显延迟
- 但 ankle 并不是最慢的一组，至少在这份数据里 knee 更慢

### 4. `target -> pos`

当前数据里，ankle 约：

- `75.0 ms`

hip 约：

- `121.7 ms`

knee 约：

- `135.0 ms`

这说明：

- 总响应延迟确实存在
- 但它不是 ankle 单独拖慢出来的
- 因此当前 touchdown roll 问题不能简单归因成“ankle 统一太慢”

## 结论

这组日志支持以下判断：

1. `action -> target` 没有明显延迟，模型输出链不是主要瓶颈
2. `target -> current` 和 `current -> pos` 都有明显延迟，问题更偏执行链
3. ankle 不是这组数据里最慢的关节组，因此当前 `roll` 镜像偏置不太像单纯的 ankle 通用迟滞
4. 结合前面的 `coupled_geometry` 结果，更合理的方向仍是：
   - `parallel_mapping / sign-convention / foot-space geometry`
   - 叠加硬件性能衰减或接触几何变化

## 对 Round 3 结论的回看

把这次延迟链结果合回 Round 3 后，前序结论需要收紧成下面几条：

1. `command_not_flat` 不能再解释成“模型输出晚了”
   - `action -> target` 在当前日志里近似 `0 ms`
   - 因此上游 policy 输出到关节目标的发布链不是主要延迟源

2. `tracking_lag` 仍然成立，但更准确地说是“执行链跟不上”
   - `target -> current` 约 `20 ~ 30 ms`
   - `current -> pos` 约 `80 ~ 145 ms`
   - 说明晚到主要出现在执行器/通信/机构响应，而不是 policy 输出本身

3. `coupled_geometry` 仍然不能被延迟链单独解释掉
   - 摆动期的左右镜像 `roll` 偏置已经在前面的 swing 统计里出现
   - 这类几何签名不是单纯的时间滞后就能生成的

4. `filter_delay` 仍未获得强证据
   - 在这批数据里，`10 / 20 / 30 ms` delay sweep 标签保持稳定
   - 说明当前问题不是“raw 有了但 lpf 慢很多”这一类单独滤波迟到

因此，Round 3 的更稳妥口径应改成：

- `tracking_lag` 是真实存在的执行链问题
- 但它不是 policy 输出延迟
- 也不是当前 `coupled_geometry` 的唯一解释
- 当前主线仍应放在 `parallel_mapping / sign-convention / foot-space geometry`，同时把执行链延迟作为并发因素保留

## 后续建议

如果要把“真实电机变化推导出的 ankle 变化”做得更准，下一轮应补录：

- `/actuator_states`

因为当前 `t3_current` 里的 `current_*` 只能算执行器侧的近似反馈，不是完整的 motor state trajectory。

## 指标字典

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `action -> target` | policy 输出到 joint target 的估计延迟 | 当前近似 `0 ms`，排除 output 发布链为主瓶颈 |
| `target -> current` | joint target 到电流响应的估计延迟 | 表示执行器响应存在几十毫秒级延迟 |
| `current -> pos` | 电流响应到 joint position 的估计延迟 | 表示机构 / 关节位姿兑现明显滞后 |
| `target -> pos` | joint target 到 joint position 的总响应延迟 | 用于判断执行链总体慢，但不能直接解释 foot-space residual |
| `ankle_lag_mean_ms` | ankle 关节组的平均延迟 | 与 hip/knee 对比，避免把问题误读成 ankle 独有 |
| `hip_lag_mean_ms` | hip 关节组的平均延迟 | 作为执行链横向对照 |
| `knee_lag_mean_ms` | knee 关节组的平均延迟 | 当前日志中 knee 甚至更慢，弱化“ankle 统一太慢”解释 |
| `execution_想·chain_delay` | target/current/pos 链路中的综合延迟 | 并发放大器，不替代 `05` 的 contact residual |

## 与后续窗口化分析的统一口径

后续 `07 / 08 / 09` 的结果没有推翻这条延迟链，但把它的作用边界收紧了：

1. `action -> target ≈ 0 ms`，所以模型输出链不是主延迟源。
2. `target -> current` 与 `current -> pos` 的滞后是真实存在的，但它们是执行链复合量，不是单一固定常数。
3. `lpf -> pos` 这类局部滞后只能解释“接触窗内什么时候更晚响应”，不能单独解释 swing 期的镜像 roll 偏置。
4. 因此延迟链是并发放大器，不是 `coupled_geometry` 的唯一根因。
