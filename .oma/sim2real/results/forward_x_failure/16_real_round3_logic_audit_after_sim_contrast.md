# Real Round3 Logic Audit After Sim Contrast (2026-05-06)

本次审计的触发原因很直接：

- 仿真 4 个工况都能稳定前走，没有 `forward_x_failure`
- 但旧版 `03` 逻辑仍把它们大量判成 `command_not_flat`

因此需要回过头审查真机 `03 / 05 / 06` 的核心判断链，看是否把“FK foot frame 量”误当成了“真实脚底平面 / 接触真值”。

## 审计结论

### 1. `03` 的旧主结论存在逻辑问题

旧版 `03a` 直接把 MuJoCo FK 的 `link_*_ankle_roll` body 姿态当成脚底平面姿态，再用它计算 `foot_flat_error_touch_rad`。  
这会把每侧脚自带的固定 frame 偏置一起算进去。

在真机和仿真里都能看到同样现象：

- ankle `q/raw` 往往只有几度到十几度量级
- 原始 `sole_roll_touch_rad` 却长期在 `+-1.57 rad` 左右

这说明旧版：

- `severe_foot_flat_touchdown`
- `roll dominant`
- `1.6 ~ 1.9 rad` 的 foot-flat error

都被 **固定 frame 偏置显著污染**，不能再当成“真实脚底严重横着着地”的直接证据。

### 2. `03` 已改成 baseline-corrected foot-frame residual

修正方式：

- 在同一条日志里，选双脚稳定接触、基座近似平稳的时刻
- 估计每侧 foot frame 的 `roll/pitch` 基线偏置
- touchdown 指标改用 **baseline-corrected foot-frame residual**

重跑真机 `t26_round3_diag_20260427_170011.csv` 后：

- 新 summary: [t26_round3_diag_20260427_170011_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_summary.md:1)
- 新 classification: [t26_round3_diag_20260427_170011_ankle_attitude_classification.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_ankle_attitude_classification.md:1)

关键变化：

| 项 | 旧口径 | 新口径 |
|---|---|---|
| touchdown 平均 foot-flat | `1.6766 rad` | `0.2441 rad` |
| 主旗标 | `8/8 severe_foot_flat_touchdown` | `6/8 large_foot_frame_residual_touchdown`，另有 `foot_clearance_deficit 1`、`hip_knee_tracking_lag 1` |
| touchdown 主导轴 | `roll 8/8` | `pitch 6/8`, `roll 2/8` |
| 三层 root cause | `command_not_flat 4 / tracking_lag 2 / coupled_geometry 2` | `coupled_geometry 3 / command_not_flat 3 / tracking_lag 1 / residual_not_large_enough 1` |

所以真机 `03` 现在不能再表述为：

> “8/8 都是 roll 主导严重斜脚触地”

更准确的口径应是：

> 真机 touchdown 仍存在可观的 baseline-corrected foot-frame residual，但强度和主导轴都比旧版结论温和；旧版 `1.6 ~ 1.9 rad` 与 `8/8 roll` 主要是 raw foot frame 偏置放大的结果。

### 3. `05` 的旧强结论需要明显降级

`05` 里凡是直接吃旧版 `sole_roll_touch_rad / foot_flat_error_touch_rad` 的推断，都受到同一 frame 偏置污染。

本次已重跑：

- 单 case probe: [t27_tracking_lag_b1_diag_20260430_101404_coupled_geometry_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t27_tracking_lag_b1_diag_20260430_101404_coupled_geometry_summary.md:1)
- cross-kp compare: [round3_coupled_geometry_cross_kp_compare.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_coupled_geometry_cross_kp_compare.md:1)
- residual collection: [round3_touchdown_geometry_residual_collection.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_touchdown_geometry_residual_collection.md:1)
- `05C` 分类: [round3_touchdown_contact_residual_classification.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_touchdown_contact_residual_classification.md:1)

关键变化：

1. `05A` 不再支持“稳定的大 pure-roll touchdown”这个旧印象  
   在 `20260430_101404` case 上，主导轴已经变成：
   - `roll 2`
   - `pitch 2`

2. `05C` 不再支持旧版那种强收口  
   旧版是：
   - `fk_foot_frame_residual_candidate 3/4`
   - `pitch_roll_coupled_contact_residual 1/4`

   重跑后变成：
   - `mapping_workpoint_residual 1`
   - `mixed_or_uncertain_contact_residual 1`
   - `pitch_roll_coupled_contact_residual 1`
   - `contact_geometry_residual 1`

3. 低 `kp/kd` case 的证据也被削弱  
   `05C` cross-kp compare 里：
   - `25/0.5 right_roll` -> `residual_not_large_enough`
   - `25/0.5 all_ankles` -> `residual_not_large_enough`

所以，真机 `05` 现在不能再写成：

> “当前最强候选已经稳定收敛为 FK foot-frame / contact residual”

更准确的口径应是：

> 执行链之外，真机 touchdown 仍有 baseline-corrected foot-frame residual；但在校准后口径下，`05` 只能支持“残余几何 / 映射 / 接触问题仍存在，但证据分散，且必须先验证 FK foot frame 真值性”，不能再支持旧版那种单一路径强收口。

### 4. `06` 本身逻辑基本成立，但解释边界要收紧

`06` 的延迟链分析本身没有依赖旧版 raw foot frame：

- `action -> target`
- `target -> current`
- `current -> pos`
- `target -> pos`

这些判断依然可用。

所以 `06` 的保留结论是：

1. `action -> target` 近似 `0 ms`
2. 主要延迟确实在执行链，而不是 policy output 发布链
3. ankle 不是唯一最慢组

但 `06` 不能再和旧版 `03/05` 一起推出：

> “执行链 lag 放大了一个已经确认的严重 roll 斜脚 touchdown”

现在更稳妥的说法是：

> `06` 证明执行链 lag 是并发问题；但 touchdown 几何残差的强度和类型，要以校准后的 `03/05` 为准，不能再用旧版 raw sole_roll 结论。

## 新的阶段性口径

基于这轮审计，真机 `forward_x_failure` 的更稳妥表述应改成：

1. 真机确实存在 forward x 失败。
2. 旧版 `03` 中“`8/8 severe_foot_flat_touchdown`、`8/8 roll dominant`、`mean 1.6766 rad`”是被 raw foot frame 偏置放大的结论，已失效。
3. 校准后，真机 touchdown 仍有 **中等强度的 foot-frame residual**，`t26` 前 8 个 touchdown 的平均值约 `0.2441 rad`。
4. 真机 `03` 现在更像：
   - `pitch 6/8`, `roll 2/8`
   - `coupled_geometry 3 / command_not_flat 3 / tracking_lag 1 / residual_not_large_enough 1`
5. 真机 `05` 现在只能支持：
   - 执行链之外仍有几何 / 映射 / 接触残差
   - 但其类型不再稳定收敛到旧版 `fk_foot_frame_residual_candidate`
   - `05D` 的 FK frame / 真实 sole-contact 对齐验证仍然是必要前置条件
6. 真机 `06` 继续保留为执行链并发问题，不再承担旧版 `03/05` 的强收口。

## 需要同步废止的旧口径

以下表述不应再作为当前结论引用：

- `8/8 = severe_foot_flat_touchdown`
- `mean foot-flat error ≈ 1.6766 rad`
- `8/8 roll dominant`
- `05C = fk_foot_frame_residual_candidate 3/4, pitch_roll_coupled_contact_residual 1/4`

这些都只能视为 **审计前的旧口径**。
