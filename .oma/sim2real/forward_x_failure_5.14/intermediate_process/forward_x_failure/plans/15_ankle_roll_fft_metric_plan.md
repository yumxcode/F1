# 15_ankle_roll_fft_metric_plan

状态：`ended_intermediate`

## 目的

本文档定义 `test_logs/data_csv/sim_vs_real_ankle_fft(1).py` 的主要测试指标和产物位置。目标是把 ankle roll 的 sim/real 差异从“看图判断”变成可复现、可横向比较的频域指标。

当前脚本用于回答：

1. real ankle roll 的主频是否与 sim 一致。
2. real ankle roll 是否存在额外的 `5~15 Hz` 高频振荡。
3. real 相对 sim 的高频能量放大倍数是多少。
4. 左右 ankle roll 哪一侧更接近异常振荡源。

## 当前分析数据

脚本内部保留 Windows 绝对路径；在本仓库执行时，如果原路径不存在，会自动 fallback 到脚本同目录同名 CSV。

| 类型 | 实际使用文件 | 帧数 | 时长 |
|---|---|---:|---:|
| sim | `test_logs/data_csv/t23_joint_sim.csv` | 1725 | 17.24 s |
| real | `test_logs/data_csv/round_kp40_kd3_ff0_20260507_134731.csv` | 761 | 7.60 s |

real 数据载入时会跳过前 5 帧，并基于 `pos_left_knee_pitch_joint` 或 `pos_left_hip_roll_joint` 的 rolling std 截到有效运动末尾。

## 产物位置

| 产物 | 路径 | 用途 |
|---|---|---|
| FFT/PSD 图 | `test_logs/data_csv/sim_vs_real_ankle_fft.png` | 观察 sim/real 在左右 ankle roll 上的频谱差异 |
| 时域图 | `test_logs/data_csv/sim_vs_real_ankle_timeseries.png` | 对比 actual/target 时域轨迹 |
| 指标 CSV | `test_logs/data_csv/sim_vs_real_ankle_spectral_metrics.csv` | 机器可读表格，适合后续汇总 |
| 指标 JSON | `test_logs/data_csv/sim_vs_real_ankle_spectral_metrics.json` | 保留结构化记录，适合脚本读取 |

## 预处理定义

频谱指标使用 actual ankle roll position：

```text
pos_left_ankle_roll_joint
pos_right_ankle_roll_joint
```

FFT 和 Welch PSD 计算前都先去均值：

```text
q_ac(t) = q(t) - mean(q)
```

去均值的原因是本测试关注振荡能量，不让 ankle roll 静态偏置污染 `0 Hz` 和总能量比例。

## 主要测试指标

### 1. `peak_hz`

定义：`0.5~20 Hz` 范围内 FFT 幅值最大的频率。

用途：

- 判断主导运动频率。
- 检查 real 主峰是否从步态基频漂移到高频振荡频率。

判读：

```text
sim 与 real 都在 ~1~2 Hz：主频仍主要是步态。
real 主峰进入 5~15 Hz：高频振荡成为主导响应。
```

### 2. `peak_amp_rad`

定义：`peak_hz` 对应的 FFT 幅值，单位 rad。

用途：

- 衡量主峰振荡幅值。
- 通过 `real/sim peak_amp_x` 估计 real 主峰响应放大。

注意：该指标来自窗函数 FFT 幅值，适合同脚本、同流程下做相对比较；跨脚本比较时需保持采样率、窗函数和频段一致。

### 3. `hf_energy_5_15_rad2`

定义：Welch PSD 在 `5~15 Hz` 上的积分：

```text
hf_energy_5_15 = integral(PSD(q_ac), f=5..15 Hz)
```

用途：

- 量化 ankle roll 高频振荡能量。
- 是本脚本最重要的振荡风险指标。

判读：

```text
real/sim hf_energy_5_15_x >> 1：real 高频振荡显著强于 sim。
real/sim hf_energy_5_15_x 接近 1：sim 已较好覆盖该频段响应。
```

### 4. `total_energy_0p5_20_rad2`

定义：Welch PSD 在 `0.5~20 Hz` 上的积分：

```text
total_energy_0p5_20 = integral(PSD(q_ac), f=0.5..20 Hz)
```

用途：

- 作为 AC 运动总能量基准。
- 排除 DC 偏置，保留步态基频和高频振荡。

### 5. `hf_over_total`

定义：

```text
hf_over_total = hf_energy_5_15 / total_energy_0p5_20
```

用途：

- 判断高频振荡在总 AC 运动中的占比。
- 可避免只看绝对能量时被大幅步态动作掩盖。

判读：

```text
比例上升：高频成分在 real 中更突出。
比例很高且 peak_hz 在 5~15 Hz：高频振荡已接近或成为主导模式。
```

### 6. Real/Sim 倍率

脚本输出三个倍率：

```text
hf_energy_5_15_x       = real hf_energy_5_15 / sim hf_energy_5_15
total_energy_0p5_20_x  = real total_energy_0p5_20 / sim total_energy_0p5_20
peak_amp_x             = real peak_amp / sim peak_amp
```

推荐优先级：

1. `hf_energy_5_15_x`
2. `hf_over_total`
3. `peak_hz`
4. `peak_amp_x`
5. `total_energy_0p5_20_x`

## 当前结果快照

| side | sim peak Hz | real peak Hz | sim HF/total | real HF/total | real/sim HF energy |
|---|---:|---:|---:|---:|---:|
| left | 1.449 | 1.445 | 3.40% | 16.86% | 10.74x |
| right | 1.449 | 4.993 | 13.46% | 34.36% | 313.92x |

初步判读：

- `left_ankle_roll`：real 主峰仍在 `~1.45 Hz`，但 `5~15 Hz` 高频能量相对 sim 放大 `10.74x`，说明高频振荡明显增加但尚未成为主频。
- `right_ankle_roll`：real 主峰变为 `~4.99 Hz`，`5~15 Hz` 高频能量相对 sim 放大 `313.92x`，是当前更强的异常振荡候选。

## 使用方式

在 `x1` conda 环境运行：

```bash
MPLCONFIGDIR=/private/tmp/matplotlib-x1 conda run -n x1 python 'test_logs/data_csv/sim_vs_real_ankle_fft(1).py'
```

对 `t27` 批量 real/sim 数据运行：

```bash
MPLCONFIGDIR=/private/tmp/matplotlib-x1 conda run -n x1 python 'test_logs/data_csv/sim_vs_real_ankle_fft(1).py' \
  --tag t27 \
  --sim 'sim/t27_tracking_lag_b1_diag_*.csv' \
  --real 't27_tracking_lag_b1_diag_*.csv' \
  --max-plot-files 6
```

脚本兼容性：

- `--sim` 和 `--real` 支持单个 CSV、多个 CSV、相对路径 glob、绝对路径 glob。
- actual 列优先匹配 `pos_{left/right}_ankle_roll_joint`。
- target 列按 `pos_des_raw_*`、`pos_des_lpf_*`、`target_*`、`action_*` 顺序自动匹配。
- 如果存在 `timestamp_ns`，使用日志时间戳；否则退化为 `fs` 推算时间。
- 多个 sim 文件时，real/sim 倍率使用同侧 sim 指标中位数作为参考，输出为 `real_over_sim_median`。

每次运行后检查：

1. 终端输出的 sim/real 数据源是否符合预期。
2. `sim_vs_real_ankle_spectral_metrics.csv` 是否更新。
3. `right_ankle_roll` 的 `hf_energy_5_15_x` 和 `peak_hz` 是否仍指向 `~5 Hz` 高频主导。

## t27 批量测试结果

本次 `t27` 测试使用：

| 类型 | 文件 |
|---|---|
| sim | `test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_*.csv`，共 4 个 |
| real | `test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_*.csv`、`20260429_*.csv`、`20260430_*.csv`，共 12 个 |

产物：

| 产物 | 路径 |
|---|---|
| 指标 CSV | `test_logs/data_csv/sim_vs_real_ankle_t27_spectral_metrics.csv` |
| 指标 JSON | `test_logs/data_csv/sim_vs_real_ankle_t27_spectral_metrics.json` |
| FFT/PSD 图 | `test_logs/data_csv/sim_vs_real_ankle_t27_fft.png` |
| 时域图 | `test_logs/data_csv/sim_vs_real_ankle_t27_timeseries.png` |

右 ankle roll 高频能量倍率最高的 real 日志：

| run_id | right `hf_energy_5_15_x` | right `total_energy_0p5_20_x` | right `peak_amp_x` |
|---|---:|---:|---:|
| `t27_tracking_lag_b1_diag_20260430_101404` | 441.72x | 76.50x | 7.53x |
| `t27_tracking_lag_b1_diag_20260428_162312` | 375.51x | 72.05x | 6.40x |
| `t27_tracking_lag_b1_diag_20260428_161322` | 316.12x | 94.87x | 11.16x |
| `t27_tracking_lag_b1_diag_20260430_100024` | 70.87x | 31.29x | 3.23x |
| `t27_tracking_lag_b1_diag_20260428_152240` | 51.81x | 32.90x | 4.27x |

左 ankle roll 高频能量倍率最高的 real 日志：

| run_id | left `hf_energy_5_15_x` | left `total_energy_0p5_20_x` | left `peak_amp_x` |
|---|---:|---:|---:|
| `t27_tracking_lag_b1_diag_20260430_101404` | 11.10x | 1.79x | 1.00x |
| `t27_tracking_lag_b1_diag_20260428_152240` | 6.83x | 2.46x | 1.08x |
| `t27_tracking_lag_b1_diag_20260430_100705` | 4.92x | 1.98x | 0.83x |
| `t27_tracking_lag_b1_diag_20260428_162312` | 4.78x | 0.77x | 0.74x |
| `t27_tracking_lag_b1_diag_20260428_163825` | 4.74x | 1.26x | 0.65x |

注意：`t27_tracking_lag_b1_diag_20260428_155015` 和 `t27_tracking_lag_b1_diag_20260428_155055` 的 ankle roll 频谱指标为 0，说明该段 ankle roll actual 序列近似常量或不适合作为 ankle roll 振动样本；后续聚合时应单独标注或剔除。

## 后续扩展

下一步建议把该指标扩展到多组 Kp/Kd real 日志和对应 sim 日志：

1. 每个日志输出一行 `source/run_id/side/kp/kd/ff/peak_hz/hf_energy/hf_ratio`。
2. 按 side 和 Kp/Kd 聚合，统计均值、最大值和排序。
3. 将 `right_ankle_roll hf_energy_5_15_x` 作为快速筛选指标，优先排查高倍率配置。
4. 对高倍率配置再进入 step test 或 sine sweep，提取阻尼比和闭环模态频率。
