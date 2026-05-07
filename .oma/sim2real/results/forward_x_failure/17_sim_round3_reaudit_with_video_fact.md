# Sim `03/06` Re-Audit With Video Fact (2026-05-06)

新增事实：

- 仿真视频中，**左脚**存在明显的 roll 方向外翻
- **右脚**视觉上基本水平、正常
- 仿真整体能稳定前走，**不存在 `forward_x_failure`**

因此本次复审的要求是：

1. 不把仿真和真机 failure 混用
2. 只判断仿真里“左脚外翻”是否被 `03/06` 正确读到
3. 如果旧版 `command_not_flat` 与视频矛盾，就降级或修正

## 采用的口径

本次仿真 `03` 已切到 **baseline-corrected foot-frame residual**，不再使用旧版 raw `sole_roll ≈ +/-1.57 rad` 口径。

重跑结果：

- 汇总表：[sim_t27_03_06_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_t27_03_06_summary.md:1)
- `03` 明细：[sim_t27_03_touchdown_classification.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_t27_03_touchdown_classification.csv:1)
- `06` 明细：[sim_t27_06_joint_lag_table.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_t27_06_joint_lag_table.csv:1)

## 03 复审结论

### 1. 旧版 `command_not_flat` 已不再成立为主结论

校准后 4 个 case 的总体结果变成：

| case | mean_flat_error_rad | large_residual_count | root_cause_counts |
|---|---:|---:|---|
| `2504` | `0.1046` | `1` | `residual_not_large_enough 3`, `tracking_lag 1` |
| `3505` | `0.0965` | `1` | `residual_not_large_enough 3`, `tracking_lag 1` |
| `4005` | `0.0734` | `0` | `residual_not_large_enough 3`, `filter_delay 1` |
| `5008` | `0.0894` | `1` | `residual_not_large_enough 3`, `command_not_flat 1` |

也就是说：

- 仿真里主导标签已经不是 `command_not_flat`
- 而是 **`residual_not_large_enough`**
- 这和“仿真能稳定前走”是一致的

### 2. 左右脚不对称与视频事实一致

按 touchdown 事件分侧统计：

| case | left mean_flat | right mean_flat | 侧向结论 |
|---|---:|---:|---|
| `2504` | `0.1385` | `0.0029` | 左脚明显更大 |
| `3505` | `0.1275` | `0.0034` | 左脚明显更大 |
| `4005` | `0.0642` | `0.0827` | 双侧都小，接近 |
| `5008` | `0.1171` | `0.0064` | 左脚明显更大 |

更具体地看 touchdown 类型：

- `2504 / 3505 / 5008`
  - 左脚 `3/3` 都是 `roll_negative_dominant`
  - 右脚单次 touchdown 基本是 `heel_first_like`
- `4005`
  - 左右都只有小残差，和“右脚正常、左脚轻度外翻”相比更接近中性工况

所以，**校准后的 sim `03` 已经能正确读出“左脚有 roll 外翻残余，右脚基本水平”这一视频事实。**

### 3. 仿真里的 `03` 不再支持“failure-style touchdown blockage”

因为：

- `mean_flat_error_rad` 都只有 `0.07 ~ 0.10`
- 大多数 touchdown 都是 `residual_not_large_enough`
- 整体仍稳定前走

所以当前仿真 `03` 的正确定位是：

> 仿真中存在左脚主导的轻中度 roll 外翻残余，但它没有大到足以形成 `forward_x_failure`。

## 06 复审结论

`06` 仍是降级版：

- `action -> pos_des_raw`
- `pos_des_raw -> pos_des_lpf`
- `tau_des_raw -> tau_des_lpf`
- `pos_des_raw -> pos`

### 1. 左脚 roll 的 `raw -> pos` 往往更慢

| case | left ankle roll raw->pos ms | right ankle roll raw->pos ms |
|---|---:|---:|
| `2504` | `198.18` | `0.00` |
| `3505` | `17.62` | `11.75` |
| `4005` | `24.60` | `24.60` |
| `5008` | `45.85` | `17.19` |

这和视频里的“左脚外翻更明显”是同向的：

- `2504`、`5008` 左脚 roll 明显比右脚更慢
- `3505` 左脚也略慢
- `4005` 左右接近，也正好是 `03` 里最对称的一组

### 2. 但 `06` 不能单独解释外翻

因为：

- `tau_raw -> tau_lpf` 左右完全一样
- `action -> raw`、`raw -> lpf` 也没有左右差

所以更合理的解释是：

> 左脚外翻不是上游 command 生成不对，而是更接近 `raw target -> joint realization` 这一层的左侧实现差异，外加一个小幅但真实存在的左脚 foot-frame residual。

## 最终修正后的 sim 结论

1. 仿真**没有** `forward_x_failure`。
2. 旧版 sim `03` 里把多个 case 判成 `command_not_flat`，是被 raw foot-frame 偏置误导后的错误读法。
3. 校准后，sim `03` 的主结论是：
   - 大多数 touchdown 为 `residual_not_large_enough`
   - 左脚存在轻中度 roll 外翻残余
   - 右脚基本正常、接近水平
4. sim `06` 的主结论是：
   - 左脚 roll 的 `raw->pos` 往往比右脚更慢
   - 更像左侧 realization 偏慢/偏差，而不是 policy 指令本身没给平

因此，**当前仿真与视频一致的最稳妥口径是：左脚存在可见外翻残余，但量级不足以触发 forward failure；它更像左侧局部 realization + 小残余几何问题，而不是全局 `command_not_flat`。**
