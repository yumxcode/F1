# 14_ankle_resonance_peak_validation

状态：`active`

## 进入背景

当前问题已经收敛到 real 踝关节低阻尼 / 欠阻尼导致的 touchdown 响应放大风险。尤其 `right_ankle_roll` 在部分窗口里出现 `joint_amp / target_amp > 1`，并且残差频谱在 `5~7 Hz` 附近有峰值。本计划用于把工程判断补成可复现数据链：确认阻尼水平、模态频率、控制频率对齐关系和幅值放大。

本文档定义数据验证方案。目标是把下面四件事分开，避免再把 target 谐波、接触冲击、延迟误差和闭环自激混成一个模糊结论：

1. 系统是否表现为欠阻尼。
2. 是否出现谐振幅值放大。
3. 固有频率或闭环模态频率是多少。
4. 控制输入频率是否接近该固有频率。

## 数据源

优先复用已有数据：

| 数据 | 用途 |
|---|---|
| `test_logs/data_csv/t27_tracking_lag_b1_diag_*.csv` | real 多组 Kp/Kd 的走路窗口数据 |
| `test_logs/data_csv/sim/t27_tracking_lag_b1_diag_*.csv` | sim 对照 |
| `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_joint_change_frequency_detail.csv` | swing/touchdown 小窗口 target/joint 频率、折返、幅值、路径长度 |
| `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_ankle_window_dir_gain_summary.csv` | 窗口级 amplitude gain 汇总 |
| `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_ankle_vibration_frequency_detail.csv` | 延迟补偿残差频谱、target 频谱、residual/target power ratio |
| `test_logs/data_csv/ankle_sim/left_roll_step_kp30_kd0.5.csv` | step 激励识别样例 |

需要新增或补充的数据：

| 数据 | 目的 |
|---|---|
| real ankle step test，按 `left/right × pitch/roll × Kp/Kd` | 从自由衰减提取阻尼比、阻尼振荡频率 |
| real ankle sine sweep，`1~15 Hz` 或 `1~20 Hz` | 从频响峰直接确认谐振峰与增益 |
| touchdown/swing 分窗口 residual PSD | 避免全日志把步态、接触和控制阶段混在一起 |

## 1. 判断是否是欠阻尼系统

### 核心判据

欠阻尼不是只看“有振动峰”，而要看 step 后是否存在衰减振荡，以及阻尼比是否小于 1。工程上重点关注：

```text
zeta < 1.0      欠阻尼
zeta < 0.7      可能存在明显谐振峰
zeta < 0.3      高风险低阻尼
```

### 推荐指标

| 指标 | 计算方式 | 数据要求 | 判读 |
|---|---|---|---|
| `peak_count_after_step` | step 后残差局部极值数量 | step test | 大于等于 2 才能可靠估阻尼 |
| `log_decrement_delta` | `ln(A_k / A_{k+1})` | step test | 峰值包络衰减速度 |
| `zeta_step` | `delta / sqrt((2*pi)^2 + delta^2)` | step test | 直接判断欠阻尼 |
| `settling_time_ms` | 残差进入并保持在阈值内的时间 | step test | 跨步残留风险 |
| `overshoot_ratio` | `(max_response - final) / step_amp` | step test | 大于 0 表示欠阻尼倾向 |
| `ringdown_freq_hz` | 相邻峰间隔倒数 | step test | 阻尼振荡频率 |

### 辅助指标

| 指标 | 用途 |
|---|---|
| `residual_local_extrema_rate_hz` | 走路窗口内是否存在过多折返 |
| `joint_direction_change_rate_hz / target_direction_change_rate_hz` | joint 是否比 target 更容易来回折返 |
| `residual_band_power_5_30hz` | 高频残差能量是否异常 |

### 注意事项

走路日志可以定位风险对象，但不能单独给出严格阻尼比。接触冲击、target 谐波、延迟补偿不充分都能产生残差峰。`zeta_step` 和 `f_n_closed_loop` 最终应来自 step 或 sine sweep 专项实验。

## 2. 验证是否出现谐振幅值现象

### 核心定义

谐振幅值现象需要同时满足：

```text
输入频率接近系统模态频率
输出幅值相对输入被放大
残差或响应峰不能完全由 target 频谱解释
```

### 推荐指标

| 指标 | 计算方式 | 数据源 | 判读 |
|---|---|---|---|
| `amplitude_gain` | `joint_range_rad / target_range_rad` | 小窗口统计 | `> 1` 表示输出幅值大于输入幅值 |
| `rms_gain` | `rms(joint_aligned) / rms(target)` | 小窗口统计 | 比 range gain 更稳健 |
| `peak_gain_at_freq` | `|Q(f_control)| / |Target(f_control)|` | 频域 | 直接验证频点放大 |
| `residual_target_power_ratio` | `PSD_residual(f_peak) / PSD_target(f_peak)` | 现有 vibration detail | `>= 3x` 表示 residual 峰不是 target 同频成分直接解释 |
| `residual_target_power_ratio_db` | `10*log10(ratio)` | 现有 vibration detail | `>= 4.8 dB` 对应 `3x` |
| `closed_loop_dominant` | `residual_target_power_ratio >= 3` | 现有 vibration detail | 闭环自身峰候选 |
| `gain_real_minus_sim` | `gain_real - gain_sim` | real/sim 配对 | real 特有放大更支持真实机构谐振 |

### 候选判据

窗口级谐振候选先用保守规则：

```text
amplitude_gain > 1.0
abs(target_dominant_freq_hz - modal_freq_hz) <= 1.0
residual_target_power_ratio >= 3.0
```

如果使用频域响应：

```text
peak_gain_at_freq > 1.0
target_power_at_freq is not tiny
residual_target_power_ratio >= 3.0
```

### 当前已有迹象

现有全日志 residual/target PSD 检查显示：

```text
real ankle_pitch: closed_loop_dominant 0/8
real ankle_roll : closed_loop_dominant 2/8
sim  ankle_pitch: closed_loop_dominant 0/8
sim  ankle_roll : closed_loop_dominant 0/8
```

这说明大多数 `5~7 Hz` 残差峰在 target 里也有同频能量，不应直接判为谐振。更像谐振候选的是 `real ankle_roll` 的少数 case，需要用窗口级对齐继续缩小范围。

## 3. 确定固有频率或闭环模态频率

### 需要区分的频率

| 名称 | 含义 | 推荐用途 |
|---|---|---|
| `f_target` | 控制目标主频 | 判断输入激励 |
| `f_residual_peak` | 跟踪残差峰值频率 | 查异常频段 |
| `f_ringdown` | step 后自由衰减频率 | 估闭环阻尼振荡频率 |
| `f_n_closed_loop` | 闭环等效固有频率 | 谐振判据核心 |
| `f_mech_open_loop` | 裸机械固有频率 | 需要低 Kp 或力矩模式，当前走路数据不直接给出 |

本阶段主要求 `f_n_closed_loop`，即当前 Kp/Kd、执行器、传动、接触状态下的闭环等效模态频率。

### 从 step test 提取

对 step 后的残差：

```text
e(t) = q(t) - q_target(t)
```

取相邻同向峰的时间间隔：

```text
T_d = mean(t_peak[k+1] - t_peak[k])
f_d = 1 / T_d
omega_d = 2*pi*f_d
```

由峰值衰减求阻尼比：

```text
delta = mean(ln(A_k / A_{k+1}))
zeta = delta / sqrt((2*pi)^2 + delta^2)
```

再得到闭环固有频率：

```text
omega_n = omega_d / sqrt(1 - zeta^2)
f_n = omega_n / (2*pi)
```

### 从 sine sweep 提取

对每个频点计算：

```text
H(f) = FFT(q_aligned) / FFT(target)
```

或更理想：

```text
H_tau(f) = FFT(q) / FFT(torque)
```

取 `|H(f)|` 的局部峰值：

```text
f_peak_response = argmax |H(f)|
```

若 `zeta < 0.7`，该峰通常接近固有频率，但应修正：

```text
f_peak = f_n * sqrt(1 - 2*zeta^2)
```

### 从走路窗口提取

走路数据只能给候选：

```text
f_modal_candidate = residual peak that satisfies:
  residual_target_power_ratio >= 3
  target power at that frequency is not dominant explanation
  same side/joint/Kp appears repeatedly
```

若 residual peak 与 target peak 基本重合，且 ratio 约 `1x`，则该频率更可能是 target/步态谐波，不应直接作为固有频率。

## 4. 对齐控制频率和固有频率

### 控制频率定义

不要用单一指标代表控制频率。按用途分三类：

| 指标 | 含义 | 用途 |
|---|---|---|
| `target_dominant_freq_hz` | target 频谱主频 | 最适合与固有频率对齐 |
| `target_direction_change_rate_hz / 2` | 折返频率近似周期频率 | 用于识别快速反复修正，但不是严格频率 |
| `target_path_rate_radps` | 单位时间累计 target 运动量 | 表示控制强度，不表示频率 |

### 对齐指标

对每个窗口输出：

```text
freq_gap_hz = abs(target_dominant_freq_hz - f_n_closed_loop_hz)
freq_ratio  = target_dominant_freq_hz / f_n_closed_loop_hz
```

判据：

```text
freq_gap_hz <= 1.0
0.8 <= freq_ratio <= 1.2
```

如果使用 `target_dir_chg_hz / 2`：

```text
dir_freq_gap_hz = abs(target_direction_change_rate_hz / 2 - f_n_closed_loop_hz)
```

但该指标只作为辅助，因为折返次数容易被噪声、非正弦轨迹和接触瞬间修正放大。

### 最终窗口级判据

每个窗口输出一行：

```text
dataset
case_label
kp_case
window
step_index
side
joint
target_dominant_freq_hz
target_direction_change_rate_hz
target_dir_chg_half_hz
f_n_closed_loop_hz
f_residual_peak_hz
freq_gap_hz
freq_ratio
amplitude_gain
rms_gain
residual_target_power_ratio
alignment_lag_ms
alignment_corr
resonance_candidate
```

候选规则：

```text
resonance_candidate =
  freq_gap_hz <= 1.0
  and amplitude_gain > 1.0
  and residual_target_power_ratio >= 3.0
```

可选增强规则：

```text
real_resonance_candidate =
  resonance_candidate
  and real amplitude_gain - matched_sim amplitude_gain > 0.3
```

## 实施步骤

1. 扩展现有 `analyze_forward_x_ankle_vibration_dir_gain.py` 或新增脚本，生成窗口级 resonance candidate 表。
2. 对 `swing` 和 `touchdown` 分开计算 residual/target PSD，不再只用全日志。
3. 对每个窗口先估 lag，再计算 aligned residual。
4. 计算 `target_dominant_freq_hz`、`target_dir_chg_half_hz`、`amplitude_gain`、`rms_gain`。
5. 从 step/sine test 读取或估计 `f_n_closed_loop_hz`；没有专项实验时，只能使用 `f_modal_candidate`，并在表中标记 `frequency_source=walking_residual_candidate`。
6. 生成 `resonance_candidate` 表，并按 `dataset × joint × window × kp_case` 汇总。

## 专项实验详细步骤

### 实验目标

专项实验只回答四个问题：

1. `right_ankle_roll` 是否在 real 上表现为低阻尼或欠阻尼。
2. `5~7 Hz` 是否是闭环模态频率或谐振峰，而不是 target 或步态谐波。
3. touchdown 窗口里的 target 主频是否接近该模态频率。
4. 提高 `Kd` 或降低 `Kp` 后，阻尼、峰值增益和走路窗口风险是否按预期下降。

本阶段优先识别闭环等效模态 `f_n_closed_loop`，不是裸机械开环固有频率。裸机械 `f_mech_open_loop` 需要低 Kp 或力矩模式，当前辨识链路不能直接给出。

### 实验矩阵

优先级从高到低：

| 组别 | 关节 | Kp/Kd | 目的 |
|---|---|---|---|
| A | `right_ankle_roll` | `40/0.8` | 当前最强风险对象，验证低阻尼和谐振峰 |
| B | `right_ankle_roll` | `35/1.5` 或当前候选稳定参数 | 验证提高阻尼后峰值是否下降 |
| C | `left_ankle_roll` | 与 A/B 相同 | real 左右差异对照 |
| D | `right_ankle_pitch` | 与 A/B 相同 | 轴向对照，避免把所有踝关节都归因到 roll |
| E | sim `right_ankle_roll` | 与 A/B 相同 | sim 对照，判断是否 real 特有 |

每个实验至少保留 `run01/run02/run03` 三次重复。real 首轮可先做 `run01` 安全探测，确认无异常后再补齐三次重复。

### Step Ringdown 实验

目的：从 step 响应提取 `zeta_step`、`log_decrement_delta`、`ringdown_freq_hz`、`settling_time_ms`、`overshoot_ratio` 和 `f_n_closed_loop_hz`。

推荐配置：

```yaml
mode: step
startup_pose_mode: stand
test_side: right
test_axis: roll
publish_rate_hz: 1000.0
pre_hold_sec: 3.0
active_sec: 0.5
post_hold_sec: 4.0
repeat_count: 1
hold_target_after_active: false
step_amplitude_rad: 0.003   # real 首次试验
test_kp: 40
test_kd: 0.8
```

执行顺序：

1. sim dry-run：先用同一配置在 sim 中确认日志字段、相位标记和幅值方向正确。
2. real 空载或支撑：机器人固定或悬挂，确认 `/joint_states`、IMU、急停和日志写入正常。
3. real 小幅 step：从 `0.003 rad` 开始；若响应平稳，再做 `0.005 rad`；不直接使用现有默认 `0.015 rad` 作为 real 首次试验。
4. 每次只测一个轴和一个侧；`right_ankle_roll` 完成后再做对照关节。
5. 每条 CSV 离线检测 step 释放后的残差峰值序列，若同向峰少于 2 个，则该条不用于 `zeta_step`。

离线计算：

```text
e(t) = actual_primary(t) - target_primary(t)
delta = mean(ln(A_k / A_{k+1}))
zeta_step = delta / sqrt((2*pi)^2 + delta^2)
ringdown_freq_hz = 1 / mean(t_peak[k+1] - t_peak[k])
f_n_closed_loop_hz = ringdown_freq_hz / sqrt(1 - zeta_step^2)
overshoot_ratio = max_abs_overshoot / step_amplitude_rad
settling_time_ms = first time after step where |e| stays below threshold
```

判据：

```text
zeta_step < 1.0     欠阻尼成立
zeta_step < 0.7     可能存在明显谐振峰
zeta_step < 0.3     低阻尼高风险
ringdown_freq_hz in 5~7 Hz 且反复出现  支持 walking residual 的 5~7 Hz 是闭环模态候选
```

### Sine Frequency Response 实验

目的：直接测量输入 target 到输出 joint 的幅频响应，验证是否在 `5~7 Hz` 附近出现 `peak_gain_at_freq > 1`。

当前代码只支持单频 sine，因此扫频需要逐频点修改配置或由外部脚本生成配置并重复运行。推荐频点：

```text
2, 3, 4, 5, 5.5, 6, 6.5, 7, 8, 10, 12 Hz
```

推荐配置模板：

```yaml
mode: sine
startup_pose_mode: stand
test_side: right
test_axis: roll
publish_rate_hz: 1000.0
pre_hold_sec: 3.0
active_sec: 4.0
post_hold_sec: 1.0
repeat_count: 1
sine_amplitude_rad: 0.002   # real 首次试验
sine_frequency_hz: 6.0
test_kp: 40
test_kd: 0.8
```

执行顺序：

1. 先跑 sim 的完整频点表，确认分析脚本能从 CSV 生成幅频曲线。
2. real 从低频低幅开始，逐步接近 `5~7 Hz`；如果 `5 Hz` 已出现异常放大，则不继续加频率或幅值。
3. 每个频点至少保留 2 秒以上稳态周期；分析时丢弃第一个周期，避免启动瞬态污染频响。
4. 对同一频点计算 `actual_primary` 相对 `target_primary` 的基波幅值比和相位滞后。
5. 对 `Kp40/Kd0.8` 与提高 `Kd` 的对照组画同一幅 Bode-like 曲线。

离线计算：

```text
target_amp_f = amplitude(target_primary, f)
joint_amp_f = amplitude(actual_primary, f)
peak_gain_at_freq = joint_amp_f / target_amp_f
phase_lag_deg = phase(actual_primary, f) - phase(target_primary, f)
f_peak_response = argmax_f peak_gain_at_freq(f)
```

判据：

```text
peak_gain_at_freq > 1.0
f_peak_response in 5~7 Hz
提高 Kd 后 peak_gain_at_freq 下降
real peak_gain_at_freq 明显高于 sim
```

### 走路窗口回填验证

step/sine 得到 `f_n_closed_loop_hz` 后，回填到已有走路窗口表：

1. 只对 touchdown 与 swing 分开判断，不再混用全日志频谱。
2. 对每个窗口使用延迟补偿后的 residual：`joint[k+lag] - target[k]`。
3. 用 `target_dominant_freq_hz` 对齐 `f_n_closed_loop_hz`，计算 `freq_gap_hz` 和 `freq_ratio`。
4. 用 `amplitude_gain`、`rms_gain` 和 `residual_target_power_ratio` 判断是否出现幅值放大。
5. 对比 `Kp40/Kd0.8` 与提高 `Kd` 后的窗口级候选数量是否下降。

最终只接受同时满足下面条件的窗口作为强谐振候选：

```text
frequency_source = step_or_sine
freq_gap_hz <= 1.0
0.8 <= freq_ratio <= 1.2
amplitude_gain > 1.0
residual_target_power_ratio >= 3.0
real candidate count > sim candidate count
```

### 数据命名

CSV 文件命名应包含数据域、关节、激励、Kp/Kd、幅值、频率和重复号：

```text
test_logs/data_csv/ankle_real/resonance/YYYYMMDD/
  right_roll_step_kp40_kd0.8_amp003_run01.csv
  right_roll_sine_kp40_kd0.8_amp002_f6.0_run01.csv

test_logs/data_csv/ankle_sim/resonance/YYYYMMDD/
  right_roll_step_kp40_kd0.8_amp003_run01.csv
  right_roll_sine_kp40_kd0.8_amp002_f6.0_run01.csv
```

每组实验同步记录：

```text
robot_id
date
surface/contact condition
startup_pose_mode
test_side/test_axis
Kp/Kd
amplitude
frequency
csv_path
operator note
abort reason, if any
```

## 现有代码审核

审核对象：`src/module/ankle_identifier_module` 及现有 sim identifier 启动配置。

### 已具备能力

| 能力 | 状态 | 依据 |
|---|---|---|
| 单关节/单轴选择 | 可用 | `test_side` 支持 left/right，`test_axis` 支持 pitch/roll |
| step 激励 | 可用 | `mode: step` 下给 primary joint 添加 `step_amplitude_rad` |
| sine 激励 | 可用 | `mode: sine` 下给 primary joint 添加单频正弦 target |
| Kp/Kd 扫点 | 手动可用 | `test_kp`、`test_kd` 可配置 |
| target/actual/velocity/effort/IMU CSV | 可用 | CSV 已记录 primary/coupled target、actual、vel、effort、gyro |
| sim dry-run | 可用 | 已有 `x1_cfg_sim_identifier.yaml` 和 `run_sim_identifier.sh` |
| baseline 稳定等待 | 可用 | 进入测试前检查关节速度和 IMU gyro |

### 不能直接完成的部分

| 缺口 | 影响 | 处理建议 |
|---|---|---|
| 无自动多频 sine sweep | 不能一次运行完整频响曲线 | 先用外部脚本批量改 `sine_frequency_hz`；后续再加 `sine_frequency_list` |
| 无 real identifier 专用启动配置 | real 上容易误开 `ControlModule`，与辨识模块同时发布 `/joint_cmd` | 新增只包含 `DcuDriverModule + AnkleIdentifierModule` 的 real cfg，并明确禁用 `ControlModule` |
| active 阶段无安全中止阈值 | real 谐振放大时只能依赖人工急停 | 增加 `max_abs_error_rad`、`max_abs_velocity_radps`、`max_abs_effort`、`max_gyro_norm`，超过即回到 hold 并停测 |
| 无在线/离线指标脚本 | CSV 能采集，但不能自动产出 `zeta_step`、`peak_gain_at_freq` 等结果 | 新增离线 analyzer，输出 step/sine summary CSV 和图 |
| 只能做位置 PD target 响应 | 不能直接得到裸机械开环固有频率 | 本阶段结论限定为闭环等效模态 `f_n_closed_loop` |
| 只打印多 publisher 警告 | 无法程序化防止多个 `/joint_cmd` publisher | real 试验前必须人工或脚本检查 `ros2 topic info /joint_cmd` |

### 代码能否支撑本专项实验

结论：现有代码可以完成“采集 step ringdown 和单频 sine 响应”的核心数据，因此足够支撑 sim dry-run 和小规模 real 探测；但还不能安全、自动、完整地完成 real 专项实验。

最低补齐项：

1. real 专用 identifier 启动配置，确保只有辨识链路发布 `/joint_cmd`。
2. active 阶段安全中止阈值。
3. 离线分析脚本，自动从 CSV 输出 `zeta_step`、`ringdown_freq_hz`、`f_n_closed_loop_hz`、`peak_gain_at_freq`、`phase_lag_deg`。
4. 批量扫频执行脚本或配置生成脚本。

在补齐前，可以先执行 sim 全流程和 real 单点低幅试验；不建议直接在 real 上做完整 `5~7 Hz` 扫频。

## 输出文件建议

| 文件 | 内容 |
|---|---|
| `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_ankle_resonance_window_detail.csv` | 每个窗口的完整判据 |
| `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_ankle_resonance_summary.csv` | 按 dataset/joint/window/kp_case 汇总 |
| `.oma/sim2real/results/forward_x_failure/34_ankle_resonance_peak_validation.md` | 结果解释与结论 |

## 成功标准

本验证完成后，必须能回答：

1. 哪些 joint/side/window/Kp/Kd 是欠阻尼高风险。
2. 哪些窗口同时满足频率接近、幅值放大、residual 强于 target。
3. 固有频率来自 step/sine 还是 walking residual candidate。
4. 谐振候选是否是 real 特有，还是 sim 同样存在。
5. 如果只在 real 存在，下一步应优先调 `Kd`、降低 `Kp`、改 target smoothing，还是排查并联踝/接触几何。

## 当前预期

基于已有统计，最可能成立的路径是：

```text
real ankle_roll touchdown
target_dominant_freq_hz ~= 6~7 Hz
residual peak ~= 5~7 Hz
部分窗口 amplitude_gain > 1
少数 case residual_target_power_ratio >= 3
```

因此下一轮验证应优先聚焦：

```text
real ankle_roll × touchdown × high Kp/Kd case
```

而不是把所有 `5~7 Hz` 残差峰统一解释为踝关节固有频率。
