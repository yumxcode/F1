# 34 Ankle Resonance Peak Validation

## 结论摘要

基于现有 real / sim 走路日志，已经统计了控制输入频率、幅值增益、残差峰和 target 频谱污染检查。该结果用于定位欠阻尼风险对象，不替代 step/sine 的严格阻尼比辨识。按严格窗口级判据：

```text
freq_gap_hz <= 1.0
amplitude_gain > 1.0
residual_target_power_ratio >= 3.0
```

当前 `strict resonance_candidate = 0 / 384`。

这不等于“没有谐振风险”。拆开看，风险集中在：

```text
real right_ankle_roll
kp40_kd0.8
touchdown 为主，少量 swing 也有高 gain
```

如果把频率接近阈值从 `1.0 Hz` 放宽到 `1.5 Hz`，出现 1 个候选：

```text
real kp40_kd0.8 touchdown step 5 right_ankle_roll
target_dominant_freq_hz = 6.25
f_modal_candidate_hz   = 5.00
freq_gap_hz            = 1.25
amplitude_gain         = 4.09
residual_target_ratio  = 21.11
```

如果放宽到 `2.0 Hz`，出现 6 个候选，全部是 `real right_ankle_roll`。因此当前数据支持的表述是：

> 现有走路日志已经把低阻尼放大风险收敛到 real `right_ankle_roll`，尤其 `kp40_kd0.8 touchdown`：target 频率接近残差模态、joint 幅值放大、且 residual 相对 target 有额外功率放大。严格的 `zeta_step` 与 `f_n_closed_loop` 仍需 step/sine 专项实验给出。

## 输出文件

本轮生成了两张表：

| 文件 | 内容 |
|---|---|
| `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_ankle_resonance_window_detail.csv` | 384 个窗口级样本，包含频率、gain、ratio 和候选标记 |
| `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_ankle_resonance_summary.csv` | 32 个分组汇总，按 dataset/kp/window/joint 聚合 |

## 已统计指标

### 1. 欠阻尼相关指标

现有走路日志不能直接给出 `zeta_step`、`log_decrement_delta`、`settling_time_ms`，这些需要 step 或 sine sweep 专项实验。

现有数据可统计的替代指标：

| 指标 | 已统计 | 说明 |
|---|---:|---|
| `joint_direction_change_rate_hz` | yes | joint 折返频率，反映响应抖动或反复修正 |
| `target_direction_change_rate_hz` | yes | target 折返频率，不能直接等价为控制频率 |
| `target_dir_chg_half_hz` | yes | `target_direction_change_rate_hz / 2`，作为粗略折返周期频率 |
| `tracking_err_rms_rad` | yes | 跟踪误差强度 |
| `vibration_band_power` | yes | `5~30 Hz` residual band power |
| `closed_loop_dominant_full_log` | yes | full-log residual 峰是否显著强于 target |

当前 walking data 支持低阻尼风险定位；严格阻尼比仍需要 step test 的 `zeta_step`。

### 2. 谐振幅值相关指标

已统计：

| 指标 | 定义 |
|---|---|
| `amplitude_gain` | `joint_range_rad / target_range_rad` |
| `pct_amplitude_gain_gt_1` | 分组内 `amplitude_gain > 1` 的窗口比例 |
| `residual_target_power_ratio` | full-log `PSD_residual(f_peak) / PSD_target(f_peak)` |
| `residual_target_power_ratio_db` | 上述 ratio 的 dB 值 |
| `closed_loop_dominant_full_log` | `residual_target_power_ratio >= 3` |

关键统计：

| group | `gain>1` 窗口 | `ratio>=3` 窗口 | 严格候选 |
|---|---:|---:|---:|
| real ankle_pitch swing | 12/48 | 0/48 | 0 |
| real ankle_pitch touchdown | 17/48 | 0/48 | 0 |
| real ankle_roll swing | 11/48 | 12/48 | 0 |
| real ankle_roll touchdown | 17/48 | 12/48 | 0 |
| sim ankle_pitch swing | 5/48 | 0/48 | 0 |
| sim ankle_pitch touchdown | 2/48 | 0/48 | 0 |
| sim ankle_roll swing | 0/48 | 0/48 | 0 |
| sim ankle_roll touchdown | 14/48 | 0/48 | 0 |

读法：

- real `ankle_roll` 是唯一有 `ratio>=3` 的轴向。
- sim 没有任何 `ratio>=3`，说明 residual 相对 target 的额外功率放大主要是 real 侧现象。
- touchdown 的 `gain>1` 比 swing 更贴近“控制输入激发响应放大”假设。

### 3. 固有频率 / 模态频率相关指标

现有走路数据只能提供：

```text
frequency_source = walking_residual_candidate
```

已统计：

| 指标 | 定义 |
|---|---|
| `f_modal_candidate_hz` | full-log residual peak，作为走路状态下闭环模态候选 |
| `f_residual_peak_hz` | 同上 |
| `full_log_target_peak_hz` | target 频谱峰 |
| `residual_target_power_ratio` | residual 峰是否强于 target 同频能量 |

关键分布：

| group | `target_dominant_freq_hz` median range | `f_modal_candidate_hz` 典型范围 | 说明 |
|---|---|---|---|
| real ankle_pitch swing | `3.03~3.13 Hz` | `5.6~7.8 Hz` | target 与模态候选分离 |
| real ankle_pitch touchdown | `6.67~13.33 Hz` | `5.6~7.8 Hz` | 部分 touchdown 接近 |
| real ankle_roll swing | `3.03~3.13 Hz` | `5.0~5.7 Hz` | swing 频率偏低 |
| real ankle_roll touchdown | `6.67 Hz` | `5.0~5.7 Hz` | 最接近谐振假设 |
| sim ankle_pitch touchdown | `6.67~7.14 Hz` | `5.7 Hz` | 频率接近，但无 residual/target 放大 |
| sim ankle_roll touchdown | `6.46~7.14 Hz` | `5.7~7.1 Hz` | 频率接近，但无 residual/target 放大 |

因此，频率接近不是充分条件。sim 也有频率接近，但没有 `ratio>=3`，说明必须联合 gain 和 residual/target ratio 判断。

### 4. 控制频率与固有频率对齐指标

已统计：

| 指标 | 定义 |
|---|---|
| `target_dominant_freq_hz` | 小窗口 target 主频 |
| `target_dir_chg_half_hz` | target 折返频率的一半 |
| `freq_gap_hz` | `abs(target_dominant_freq_hz - f_modal_candidate_hz)` |
| `freq_ratio` | `target_dominant_freq_hz / f_modal_candidate_hz` |
| `freq_close` | `freq_gap_hz <= 1.0` |

汇总：

| group | `freq_close` 窗口 | `gain>1` 窗口 | `ratio>=3` 窗口 | 严格候选 |
|---|---:|---:|---:|---:|
| real ankle_pitch swing | 6 | 12 | 0 | 0 |
| real ankle_pitch touchdown | 18 | 17 | 0 | 0 |
| real ankle_roll swing | 0 | 11 | 12 | 0 |
| real ankle_roll touchdown | 8 | 17 | 12 | 0 |
| sim ankle_pitch swing | 6 | 5 | 0 | 0 |
| sim ankle_pitch touchdown | 33 | 2 | 0 | 0 |
| sim ankle_roll swing | 1 | 0 | 0 | 0 |
| sim ankle_roll touchdown | 37 | 14 | 0 | 0 |

主要矛盾：

- real `ankle_roll` 有强 `ratio>=3`，但 `freq_gap_hz <= 1.0` 的窗口少。
- sim touchdown 频率很接近，但没有 residual/target 放大。
- real `ankle_pitch` 有一些频率接近和 gain>1，但没有 residual/target 放大。

## 近似候选

严格阈值没有候选。为了排查工程风险，额外看了 relaxed 频率阈值：

```text
freq_gap_hz <= 1.5 -> 1 个候选
freq_gap_hz <= 2.0 -> 6 个候选
```

`1.5 Hz` 候选：

| dataset | kp | window | step | side | joint | target freq | modal candidate | gap | gain | ratio |
|---|---|---|---:|---|---|---:|---:|---:|---:|---:|
| real | kp40_kd0.8 | touchdown | 5 | right | ankle_roll | 6.25 | 5.00 | 1.25 | 4.09 | 21.11 |

`2.0 Hz` 下的 6 个候选全部来自 `real right_ankle_roll`：

| kp | window | step | gain | target freq | modal candidate | gap | ratio |
|---|---|---:|---:|---:|---:|---:|---:|
| kp25_kd0.4 | touchdown | 1 | 1.29 | 6.67 | 5.00 | 1.67 | 4.56 |
| kp40_kd0.8 | touchdown | 1 | 1.04 | 6.67 | 5.00 | 1.67 | 21.11 |
| kp40_kd0.8 | swing | 4 | 4.13 | 3.13 | 5.00 | 1.88 | 21.11 |
| kp40_kd0.8 | touchdown | 5 | 4.09 | 6.25 | 5.00 | 1.25 | 21.11 |
| kp40_kd0.8 | swing | 6 | 8.67 | 3.03 | 5.00 | 1.97 | 21.11 |
| kp40_kd0.8 | touchdown | 6 | 1.72 | 6.67 | 5.00 | 1.67 | 21.11 |

这些不应被写成“已确认谐振”，但应作为下一轮专项实验优先对象。

## 当前判断

### 支持的结论

1. `real ankle_roll` 比 `sim ankle_roll` 更有异常放大迹象。
2. `real ankle_roll` 的 residual/target power ratio 显著更高，说明不是 target 同频成分就能完全解释。
3. `touchdown` 的 target 主频约 `6~7 Hz`，更接近 residual 模态候选。
4. `kp40_kd0.8 right_ankle_roll` 是当前最强风险对象。

### 不支持的结论

1. 不能说所有 `5~7 Hz` 残差峰都是踝关节固有频率。
2. 不能从现有走路数据直接确认 `zeta` 或严格欠阻尼。
3. 不能用 `target_direction_change_rate_hz` 直接替代控制频率。
4. 不能说 sim/real 都存在同样的谐振机制；sim 更像 target 驱动或正常跟随。

## 下一步建议

优先做一个最小专项实验：

```text
right_ankle_roll
Kp40/Kd0.8
Kp35/Kd1.5 对照
step + sine sweep
```

需要输出：

```text
zeta_step
ringdown_freq_hz
f_n_closed_loop_hz
peak_gain_at_freq
settling_time_ms
```

如果 `Kp40/Kd0.8` 的 `f_n_closed_loop_hz` 落在 `5~7 Hz`，且 `Kd1.5` 显著降低 peak gain 和 settling time，则可以把当前 walking-data 近似候选升级为更强的谐振证据。

## 专项阶跃实验追加记录

本节用于持续追加 `analyze_ankle_identifier_csv.py` 的 step ringdown 结果。以下记录来自现场口述输出，未附原始 CSV；后续有 CSV 时应补充 `csv_path` 并保留同一表头继续追加。

### 结果表

记录按 `amp_rad` 分组。同一阶跃幅值内先放悬空首测，再放复测，便于后续追加触地工况并做同幅值对照。

#### `amp_rad = 0.050`

| 日期 | 工况 | joint | kp | kd | amp_rad | repeat | tracking_ratio | tail_tracking_ratio | active_overshoot_ratio | rise_time_sec | peak_time_sec | response_class | ringdown_valid | zeta_step | ringdown_freq_hz | f_n_closed_loop_hz | ringdown_overshoot_ratio | settling_time_ms | peak_count | valid_log_pairs | primary_peak_velocity | primary_peak_effort | 备注 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 2026-05-11 | 悬空 | `right_ankle_roll_joint` | 35 | 0.5 | 0.050 | 1 | 0.954175 | 1.052200 | 0.193796 | 0.039837 | 0.088973 | `single_overshoot` | true | 0.072442 | 3.453893 | 3.462991 | 1.098940 | not_settled_within_post_hold | 14 | 2 | 1.124950 | 2.527606 | 中大幅能跟踪，但释放后低阻尼振荡明显；4 s post_hold 未收敛。 |
| 2026-05-11 | 悬空复测 | `right_ankle_roll_joint` | 35 | 0.5 | 0.050 | 1 | 0.998483 | 1.075476 | 0.264116 | 0.040554 | 0.106082 | `single_overshoot` | true | 0.089228 | 18.860629 | 18.936161 | 1.071500 | not_settled_within_post_hold | 3 | 2 | 1.178458 | 2.552674 | 0.05 rad 复测跟踪更接近 1，但 active 超调和 ringdown 频率高于首次；同幅值复测差异大，提示释放初态、摩擦/间隙或峰值检测敏感。 |
| 2026-05-11 | 悬空复测2 | `right_ankle_roll_joint` | 35 | 0.5 | 0.050 | 1 | 0.900629 | 0.969679 | 0.166179 | 0.039229 | 0.091024 | `oscillatory_but_settling` | true | 0.092612 | 16.990164 | 17.063499 | 1.036160 | not_settled_within_post_hold | 37 | 2 | 1.153267 | 2.503776 | 0.05 rad 第二次复测 post_hold 仅 2.29 s，不完全可比；active 超调较低，但 ringdown 仍不收敛，`f_n` 接近 0.05 首次复测和 0.15 复测。 |
| 2026-05-11 | 触地 | `right_ankle_roll_joint` | 35 | 0.5 | 0.050 | 1 | 0.115942 | 0.157965 | 0.000000 | not_available | 0.256881 | `undershoot_soft` | true | 0.002260 | 12.283720 | 12.283751 | 0.279940 | not_settled_within_post_hold | 40 | 2 | 0.468019 | 4.701849 | 触地后 active 段严重欠跟踪：`actual_step=0.005797`，仅达命令约 11.6%；`peak_time=0.256881s` 超 walking 预算，`final_tracking_ratio=0.025269`。释放后仍有低阻尼 ringdown，`zeta_step=0.002260`，post_hold 约 3.24s 未收敛；与悬空同幅值形成强烈接触退化对照。 |
| 2026-05-11 | 触地复测2 | `right_ankle_roll_joint` | 35 | 0.5 | 0.050 | 1 | 0.150808 | 0.146771 | 0.000000 | not_available | 0.214784 | `undershoot_soft` | true | 0.019401 | 26.753415 | 26.758451 | 0.452340 | not_settled_within_post_hold | 107 | 1 | 0.354616 | 4.850121 | 触地复测2 仍严重欠跟踪：`actual_step=0.007540`，约 15.1%；`peak_time=0.214784s` 仍超 walking 预算，`final_tracking_ratio=0.082281`。post_hold 完整约 4.0s 仍不收敛；ringdown 峰值数增至 107、有效递减峰对仅 1，`f_n=26.758451 Hz` 更可能受高频小峰/折返影响，不能单独作为稳定模态。 |
| 2026-05-11 | 触地复测3 | `right_ankle_roll_joint` | 35 | 0.5 | 0.050 | 1 | 0.148449 | 0.155559 | 0.000000 | not_available | 0.034049 | `undershoot_soft` | false | — | 8.823529 | — | 0.418000 | not_settled_within_post_hold | 7 | 0 | 0.350942 | 4.975224 | 触地复测3 仍严重欠跟踪：`actual_step=0.007422`，约 14.8%；这次 `peak_time=0.034049s` 回到 good，但 active 窗口仍未收敛。ringdown 无有效同号递减峰对，`invalid_reason=no_decreasing_same_sign_peak_pairs`；post_hold 约 2.23s 未收敛，`f_n` 不可用。 |

#### `amp_rad = 0.100`

| 日期 | 工况 | joint | kp | kd | amp_rad | repeat | tracking_ratio | tail_tracking_ratio | active_overshoot_ratio | rise_time_sec | peak_time_sec | response_class | ringdown_valid | zeta_step | ringdown_freq_hz | f_n_closed_loop_hz | ringdown_overshoot_ratio | settling_time_ms | peak_count | valid_log_pairs | primary_peak_velocity | primary_peak_effort | 备注 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 2026-05-11 | 悬空 | `right_ankle_roll_joint` | 35 | 0.5 | 0.100 | 1 | 0.948378 | 0.997384 | 0.319234 | 0.034508 | 0.092020 | `oscillatory_but_settling` | true | 0.201689 | 10.807306 | 11.034061 | 0.996620 | not_settled_within_post_hold | 3 | 2 | 2.498135 | 4.723539 | 0.1 rad 下 active 超调更大；`f_n_closed_loop_hz=11.034061 Hz`。频率较 0.05 rad 明显变化，提示非线性或峰值估计受样本影响。 |
| 2026-05-11 | 悬空复测 | `right_ankle_roll_joint` | 35 | 0.5 | 0.100 | 1 | 0.978835 | 1.025537 | 0.368967 | 0.035150 | 0.090961 | `oscillatory_but_settling` | true | 0.245432 | 27.042672 | 27.895905 | 0.992700 | not_settled_within_post_hold | 97 | 2 | 2.501441 | 4.866710 | 0.1 rad 复测 active 跟踪略好但超调更大；`peak_count=97`、有效递减峰对仅 2，ringdown 频率接近 0.15 rad 结果，仍不能视为稳定单一模态。 |
| 2026-05-11 | 悬空复测2 | `right_ankle_roll_joint` | 35 | 0.5 | 0.100 | 1 | 0.963795 | 1.013352 | 0.346982 | 0.034139 | 0.092976 | `oscillatory_but_settling` | true | 0.166430 | 14.561622 | 14.767582 | 0.992700 | not_settled_within_post_hold | 4 | 3 | 2.484668 | 4.795113 | 0.1 rad 第二次复测 active 指标接近前两次，ringdown 频率回到约 14.8 Hz；峰值数量较少、有效递减峰对 3，比 97 峰那次更干净。 |
| 2026-05-11 | 触地 | `right_ankle_roll_joint` | 35 | 0.5 | 0.100 | 1 | 0.205020 | 0.250806 | 0.000000 | not_available | 0.249939 | `undershoot_soft` | true | 0.037032 | 11.180287 | 11.187961 | 0.254530 | not_settled_within_post_hold | 8 | 1 | 0.761766 | 7.550002 | 触地 `0.1 rad` 比 `0.05 rad` 幅值兑现略高，但仍严重欠跟踪：`actual_step=0.020502`，约 20.5%；`peak_time=0.249939s` 超 walking 预算，active 未收敛，`final_tracking_ratio=-0.022942`。释放后 ringdown 有效但只有 1 个有效递减峰对，post_hold 约 2.40s 未收敛。 |
| 2026-05-11 | 触地复测 | `right_ankle_roll_joint` | 35 | 0.5 | 0.100 | 1 | 0.170880 | 0.187377 | 0.000000 | not_available | 0.237006 | `undershoot_soft` | true | 0.056743 | 2.602296 | 2.606496 | 0.115490 | not_settled_within_post_hold | 8 | 1 | 0.793933 | 6.829446 | 触地 `0.1 rad` 复测仍严重欠跟踪：`actual_step=0.017088`，约 17.1%；`peak_time=0.237006s` 仍超 walking 预算，active 未收敛，`final_tracking_ratio=0.011752`。post_hold 约 2.88s 未收敛；ringdown 有效但只有 1 个有效递减峰对，`f_n=2.606496 Hz` 与首测差异大，暂按释放段估计不稳定处理。 |
| 2026-05-11 | 触地复测2 | `right_ankle_roll_joint` | 35 | 0.5 | 0.100 | 1 | 0.224421 | 0.263418 | 0.000000 | not_available | 0.267927 | `undershoot_soft` | true | 0.043891 | 11.857118 | 11.868555 | 0.208560 | not_settled_within_post_hold | 37 | 3 | 0.756655 | 7.282916 | 触地 `0.1 rad` 复测2 幅值兑现略高但仍严重欠跟踪：`actual_step=0.022442`，约 22.4%；`peak_time=0.267927s` 仍超 walking 预算，active 未收敛，`final_tracking_ratio=0.054615`。post_hold 约 3.17s 未收敛；ringdown 有 3 个有效递减峰对，`f_n=11.868555 Hz` 与首测约 11.19 Hz 接近。 |

#### `amp_rad = 0.150`

| 日期 | 工况 | joint | kp | kd | amp_rad | repeat | tracking_ratio | tail_tracking_ratio | active_overshoot_ratio | rise_time_sec | peak_time_sec | response_class | ringdown_valid | zeta_step | ringdown_freq_hz | f_n_closed_loop_hz | ringdown_overshoot_ratio | settling_time_ms | peak_count | valid_log_pairs | primary_peak_velocity | primary_peak_effort | 备注 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 2026-05-11 | 悬空 | `right_ankle_roll_joint` | 35 | 0.5 | 0.150 | 1 | 0.918028 | 0.960157 | 0.354617 | 0.033454 | 0.091262 | `sustained_oscillation` | true | 0.169698 | 27.143251 | 27.542726 | 0.974387 | 3985.041 | 108 | 3 | 3.827732 | 7.153489 | 0.15 rad 下 active 超调继续增大；post_hold 约 4 s 才贴近阈值，`peak_count=108` 但有效递减峰对仅 3，说明有大量小峰/噪声或高频折返参与峰值检测。 |
| 2026-05-11 | 悬空复测 | `right_ankle_roll_joint` | 35 | 0.5 | 0.150 | 1 | 0.921648 | 0.964132 | 0.357078 | 0.034237 | 0.099110 | `sustained_oscillation` | true | 0.125624 | 16.130073 | 16.258876 | 0.983540 | 278.026 | 5 | 4 | 3.847833 | 7.058158 | 0.15 rad 复测 active 指标与首次接近，但 ringdown 频率从约 27.5 Hz 变为约 16.3 Hz，峰值数量从 108 降到 5；复测的峰值衰减估计更干净，但仍显示释放超调接近整步幅。 |
| 2026-05-11 | 悬空复测2 | `right_ankle_roll_joint` | 35 | 0.5 | 0.150 | 1 | 0.922447 | 0.964277 | 0.357224 | 0.034456 | 0.088048 | `sustained_oscillation` | true | 0.125624 | 15.155821 | 15.276844 | 0.983540 | 287.913 | 5 | 4 | 3.829759 | 7.105780 | 0.15 rad 第二次复测与上一次 0.15 复测高度一致；post_hold 约 2.25 s，`f_n` 约 15.3 Hz，仍有接近整步幅的释放超调。 |
| 2026-05-11 | 触地 | `right_ankle_roll_joint` | 35 | 0.5 | 0.150 | 1 | 0.401219 | 0.480927 | 0.000000 | not_available | 0.322080 | `undershoot_soft` | true | 0.001932 | 8.453790 | 8.453806 | 0.345873 | not_settled_within_post_hold | 22 | 2 | 1.497646 | 9.231860 | 触地 `0.15 rad` 幅值兑现明显高于 `0.05/0.10`，但仍欠跟踪：`actual_step=0.060183`，约 40.1%；`peak_time=0.322080s` 超 walking 预算，active 未收敛，`final_tracking_ratio=0.010537`。释放后低阻尼明显，`zeta_step=0.001932`，post_hold 约 2.56s 未收敛。 |
| 2026-05-11 | 触地复测 | `right_ankle_roll_joint` | 35 | 0.5 | 0.150 | 1 | 0.350572 | 0.429255 | 0.000000 | not_available | 0.478117 | `undershoot_soft` | true | 0.004262 | 10.400731 | 10.400825 | 0.315040 | not_settled_within_post_hold | 35 | 21 | 1.415988 | 9.184898 | 触地 `0.15 rad` 复测仍欠跟踪：`actual_step=0.052586`，约 35.1%；`peak_time=0.478117s` 更慢，active 未收敛，`final_tracking_ratio=-0.004195`。post_hold 约 3.35s 未收敛；ringdown 有 21 个有效递减峰对，`f_n=10.400825 Hz`，但 `zeta_step=0.004262` 仍极低。 |
| 2026-05-11 | 触地复测2 | `right_ankle_roll_joint` | 35 | 0.5 | 0.150 | 1 | 0.377993 | 0.472571 | 0.000000 | not_available | 0.345930 | `undershoot_soft` | true | 0.009147 | 3.841823 | 3.841984 | 0.315787 | not_settled_within_post_hold | 15 | 5 | 1.332265 | 9.609961 | 触地 `0.15 rad` 复测2 仍欠跟踪：`actual_step=0.056699`，约 37.8%；`peak_time=0.345930s` 超 walking 预算，active 未收敛，`final_tracking_ratio=0.004385`。post_hold 完整 4.0s 仍未收敛；ringdown 有 5 个有效递减峰对，`f_n=3.841984 Hz` 与前两次差异大，但 `zeta_step=0.009147` 仍极低。 |

#### `amp_rad = 0.200`

| 日期 | 工况 | joint | kp | kd | amp_rad | repeat | tracking_ratio | tail_tracking_ratio | active_overshoot_ratio | rise_time_sec | peak_time_sec | response_class | ringdown_valid | zeta_step | ringdown_freq_hz | f_n_closed_loop_hz | ringdown_overshoot_ratio | settling_time_ms | peak_count | valid_log_pairs | primary_peak_velocity | primary_peak_effort | 备注 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 2026-05-11 | 触地 | `right_ankle_roll_joint` | 35 | 0.5 | 0.200 | 1 | 0.530490 | 0.647368 | 0.000000 | not_available | 0.435793 | `undershoot_soft` | true | 0.021733 | 13.758044 | 13.761295 | 0.558890 | not_settled_within_post_hold | 13 | 8 | 1.863899 | 11.683039 | 触地 `0.2 rad` 幅值兑现继续提高：`actual_step=0.106098`，约 53.0%；但 `peak_time=0.435793s` 仍超 walking 预算，active 未收敛，`final_tracking_ratio=-0.019501`。释放后 `ringdown_overshoot_ratio=0.558890` 明显放大，post_hold 约 3.51s 未收敛，`primary_peak_effort=11.683039` 已高于 0.15。 |
| 2026-05-11 | 触地复测 | `right_ankle_roll_joint` | 35 | 0.5 | 0.200 | 1 | 0.537318 | 0.653583 | 0.000000 | not_available | 0.433008 | `undershoot_soft` | true | 0.012220 | 10.888401 | 10.889214 | 0.561810 | not_settled_within_post_hold | 14 | 5 | 1.942677 | 11.455220 | 触地 `0.2 rad` 复测与首测高度一致：`actual_step=0.107464`，约 53.7%；`peak_time=0.433008s` 仍超 walking 预算，active 未收敛，`final_tracking_ratio=-0.020838`。释放后 `ringdown_overshoot_ratio=0.561810` 与首测接近，post_hold 约 3.65s 未收敛，`primary_peak_effort=11.455220` 仍处高位。 |
| 2026-05-11 | 触地复测2 | `right_ankle_roll_joint` | 35 | 0.5 | 0.200 | 1 | 0.496858 | 0.624415 | 0.000000 | not_available | 0.488075 | `undershoot_soft` | true | 0.036784 | 16.833927 | 16.845327 | 0.553985 | not_settled_within_post_hold | 53 | 6 | 1.866330 | 11.701310 | 触地 `0.2 rad` 复测2 tracking 略低但仍接近前两次：`actual_step=0.099372`，约 49.7%；`peak_time=0.488075s` 更慢，active 未收敛，`final_tracking_ratio=-0.021659`。释放后 `ringdown_overshoot_ratio=0.553985` 仍与前两次一致偏高，post_hold 约 3.26s 未收敛，`primary_peak_effort=11.701310` 仍处高位。 |

#### `amp_rad = 0.250`

| 日期 | 工况 | joint | kp | kd | amp_rad | repeat | tracking_ratio | tail_tracking_ratio | active_overshoot_ratio | rise_time_sec | peak_time_sec | response_class | ringdown_valid | zeta_step | ringdown_freq_hz | f_n_closed_loop_hz | ringdown_overshoot_ratio | settling_time_ms | peak_count | valid_log_pairs | primary_peak_velocity | primary_peak_effort | 备注 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 2026-05-11 | 触地 | `right_ankle_roll_joint` | 35 | 0.5 | 0.250 | 1 | 0.679407 | 0.856651 | 0.000000 | 0.474332 | 0.498859 | `undershoot_soft` | true | 0.036954 | 14.994752 | 15.005001 | 0.740904 | not_settled_within_post_hold | 20 | 9 | 2.514251 | 15.330791 | 触地 `0.25 rad` 幅值兑现明显提高：`actual_step=0.169852`，约 67.9%，tail tracking 达 `0.856651`；但 `rise_time=0.474332s` 已被判为 too_slow_for_walking，`peak_time=0.498859s` 仍不可用于 walking，active 未收敛。释放后 `ringdown_overshoot_ratio=0.740904`、`max_abs_overshoot=0.185226`，post_hold 约 3.10s 未收敛；`primary_peak_effort=15.330791` 已明显高于 0.20，说明继续加幅值主要换来更大的释放冲击和力矩负担。 |

### 当前解读

- `0.050 rad`：悬空三次 tracking 在 `0.900629~0.998483`，active 超调在 `0.166179~0.264116`，均未在 post_hold 内稳定收敛；首次 `f_n=3.462991 Hz`，两次复测为 `18.936161 / 17.063499 Hz`。触地三次 tracking 只有 `0.115942 / 0.150808 / 0.148449`，`final_tracking_ratio=0.025269 / 0.082281 / 0.034815`，说明同幅值下接触约束造成可重复的严重欠跟踪。触地 peak_time 前两次超 walking 预算，第三次回到 `0.034049s` good，说明触地时序有状态依赖，但幅值兑现差是稳定复现的主问题。触地释放后均未在 post_hold 内收敛；第三次 ringdown 无有效同号递减峰对，`f_n` 不可用。
- `0.100 rad`：悬空三次 tracking 在 `0.948378~0.978835`，active 超调稳定偏高：`0.319234 / 0.368967 / 0.346982`，且均未在 post_hold 内稳定收敛。触地三次 tracking 为 `0.205020 / 0.170880 / 0.224421`，高于 `0.05 rad` 触地但仍严重欠跟踪；`peak_time=0.249939 / 0.237006 / 0.267927s` 均超 walking 预算，说明大一步长没有恢复可用触地跟踪。触地 ringdown 中首测和复测2 的 `f_n=11.187961 / 11.868555 Hz` 接近，复测1 的 `2.606496 Hz` 是离群；但三次 post_hold 都未收敛，且只有复测2 有 3 个有效递减峰对。
- `0.150 rad`：悬空三次 tracking 很接近：`0.918028 / 0.921648 / 0.922447`，active 超调也很接近：`0.354617 / 0.357078 / 0.357224`。触地三次 tracking 为 `0.401219 / 0.350572 / 0.377993`，明显高于 `0.05/0.10` 触地，但仍远低于悬空，且 `peak_time=0.322080 / 0.478117 / 0.345930s` 均超 walking 预算、`final_tracking_ratio=0.010537 / -0.004195 / 0.004385`。这说明增加幅值能提高触地幅值兑现，但没有解决触地可用性；释放段 `f_n=8.453806 / 10.400825 / 3.841984 Hz` 分散，post_hold 均未收敛，低阻尼风险稳定存在。
- `0.200 rad`：触地三次 tracking 为 `0.530490 / 0.537318 / 0.496858`，tail tracking 为 `0.647368 / 0.653583 / 0.624415`，幅值兑现高度一致且继续高于 0.15；但 `peak_time=0.435793 / 0.433008 / 0.488075s` 仍远超 walking 预算，`final_tracking_ratio=-0.019501 / -0.020838 / -0.021659`，active 后仍不保留。释放后 `ringdown_overshoot_ratio=0.558890 / 0.561810 / 0.553985` 高度一致，`primary_peak_effort=11.683039 / 11.455220 / 11.701310` 处于当前最高区间，说明继续加幅值会换来稳定的大释放冲击和高力矩负担。
- `0.250 rad`：触地首次 tracking 提高到 `0.679407`，tail tracking 达 `0.856651`，说明大幅值能进一步克服触地负载下的死区/静摩擦；但 `rise_time=0.474332s` 和 `peak_time=0.498859s` 已明显慢于 walking 预算，active 未收敛。释放段 `ringdown_overshoot_ratio=0.740904`、`primary_peak_effort=15.330791`，较 0.20 再次显著增大，说明 0.25 更像是冲击放大点，不应作为可行 walking 控制幅值候选。
- `0.003 rad` 小信号几乎不跟踪，而 `0.05/0.10/0.15 rad` 能接近目标，支持 `right_ankle_roll_joint` 存在小信号死区/静摩擦/间隙影响。
- 同一 `kp=35,kd=0.5` 下，悬空 active 段结论明确：幅值越大，active 超调越重，`0.10/0.15 rad` 已达到约 `0.32~0.37`。释放段结论应更谨慎：频率随幅值和复测状态变化大，不能把单次 `f_n_closed_loop_hz` 当作单一线性二阶模态。
- 后续触地工况必须按同一 `amp_rad` 小节追加，先与悬空同幅值横向比较，再判断接触约束是否改变阻尼、超调和收敛时间。

### 后续追加要求

后续专项实验继续追加到上方结果表，并尽量补齐：

```text
csv_path
side / axis / kp / kd / amp_rad
悬空或触地工况
repeat_count / iteration_count
zeta_step
ringdown_freq_hz
f_n_closed_loop_hz
settling_time_ms
primary_peak_effort
```

优先下一组：

```text
right_ankle_roll_joint
触地
amp_rad = 0.05, 0.10, 0.15, 0.20, 0.25
kp = 35
kd = 0.5
```

目标是先补齐同一 `kp/kd/amp_rad` 下的触地对照，判断接触约束是否改变 `tracking_ratio`、`active_overshoot_ratio`、`ringdown_overshoot_ratio`、`settling_time_ms` 和 `f_n_closed_loop_hz`。触地数据追加时直接写入对应 `amp_rad` 小节，工况填 `触地` 或 `触地复测`，不要与悬空结论混合收口。
