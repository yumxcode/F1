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
