# Forward-X Failure First6 Step Metric Test Plan

状态：`active`

对应报告：`.oma/sim2real/results/forward_x_failure/28_forward_x_failure_first6_step_detailed_report.md`

生成日期：2026-05-13

## 目的

本文档把 `28_forward_x_failure_first6_step_detailed_report.md` 中的分析结论整理成可复现的测试指标方案。目标不是重新解释 forward-x failure，而是把报告里的现象固化为后续实机 / 仿真对比时必须输出的指标、判读规则和异常现象对应关系。

核心问题保持与报告一致：

```text
forward-x 失败主线 =
  real 踝关节低阻尼 / 欠阻尼
  + touchdown 冲击
  + target 高频换向
  + 传动弹性储能
  -> ankle roll / pitch 过冲、自激、锁死和步间误差累积
```

## 数据与窗口口径

### 输入数据

每个 case 至少需要以下字段：

| 字段 | 必需 | 用途 |
|---|---|---|
| `timestamp` / `timestamp_ns` | 是 | 时间对齐、频率估计 |
| `pos_des_raw_*` | 是 | 原始策略 target，计算 target 换向、target 幅值、target 速度 |
| `joint_pos_*` | 是 | 关节实际响应，计算 tracking、gain、姿态 |
| `joint_vel_*` 或由 `joint_pos` 差分 | 是 | 计算 vel RMS、自激点 |
| touchdown / foot contact 标记 | 是 | 切分 swing / touchdown 窗口 |
| 足端姿态或 FK 所需状态 | 推荐 | 计算 `sole_roll`，避免只看 `ank_roll` 的盲区 |
| Kp / Kd / case 配置 | 是 | 按参数归因低阻尼风险 |

### 统一窗口

| 窗口 | 定义 | 说明 |
|---|---|---|
| `swing` | 每步摆动相 | 观察 target 高频、跟踪质量、自激前兆 |
| `touchdown` | touchdown 前 50ms 到后 100ms | 观察冲击过冲、脚掌姿态、锁死和支撑失败 |

### 方法口径

| 项目 | 固定口径 |
|---|---|
| touchdown lag 搜索上限 | `50 ms` |
| swing lag 搜索上限 | `200 ms` |
| 有效增益周期门限 | `target_amp >= 10 mrad` |
| 足端速度 | 使用 `foot_rel_vz` 或等价相对速度，避免 base_z 漂移 |
| 触地倾斜 | 优先使用 `sole_roll`，不要只用 `ank_roll` |
| 重点关节 | `left/right_ankle_pitch`、`left/right_ankle_roll`，必要时联动 `knee_pitch` |

## 指标总览

| 编号 | 指标 | 首要用途 | 报告对应现象 |
|---|---|---|---|
| M1 | `lag_ms` + `corr` | 判断 target 到 joint 的线性传递是否仍可信 | real/sim 延迟量级相近，延迟不是主 gap |
| M2 | `aligned_track_err` | 判断相位补偿后的跟踪误差 | real touchdown pitch / roll 误差显著高于 sim |
| M3 | `amplitude_gain` | 判断欠跟踪、过跟踪和冲击过冲 | real touchdown ankle_pitch `2.84x`，sim `0.37x` |
| M4 | `target_direction_change_rate_hz` | 判断策略输出是否超过系统带宽 | real target 换向 `22-37 Hz`，超稳定带宽 `3-5x` |
| M5 | `joint_vel_rms / target_vel_rms` | 识别自激点 | real 出现 `ratio > 1`，sim 为 0 |
| M6 | `sole_roll_at_touchdown` | 判断真实脚掌倾斜和接触冲击 | 35/0.5 锁死后 `sole_roll=-35.8 deg` |
| M7 | `touchdown_ankle_pitch_mean/std` | 判断落地背屈不足和姿态一致性 | real 背屈比 sim 少 `4-10 deg` |
| M8 | `joint_lock_flag` | 识别硬件保护 / 执行器失效 | 35/0.5 右踝 step4 后 pitch/roll 锁死 |
| M9 | `step_accumulation_score` | 判断步间误差是否累积 | Kp35/40 的 sole_roll 和失稳逐步放大 |
| M10 | `hf_energy_5_15` / `peak_gain_at_freq` | 验证低阻尼 / 谐振风险 | right_ankle_roll touchdown 是高风险对象 |

## 指标定义、解释和现象对应

### M1. 延迟与相关性：`lag_ms` + `corr`

定义：

```text
lag_ms = argmax_lag corr(diff(pos_des_raw), diff(joint_pos))
corr   = 对齐后的相关系数
```

解释：

| `corr` 范围 | 含义 | 对应现象 |
|---|---|---|
| `corr >= 0.4` | 延迟估计可信，target 到 joint 仍有线性传递 | sim swing / touchdown 多数窗口 |
| `0.1 <= corr < 0.4` | 弱相关，延迟只能作为参考 | real swing ankle_pitch / roll 常见 |
| `corr < 0.1` | target 与 joint 解耦 | touchdown 冲击、保护锁死、饱和或自由振荡 |

报告对应：

| 场景 | 报告数值 | 判读 |
|---|---:|---|
| real swing ankle_pitch | `76.0 ms`, corr `0.306` | 延迟与 sim 接近，但线性度较弱 |
| sim swing ankle_pitch | `80.2 ms`, corr `0.427` | 延迟接近 real，线性度更好 |
| real touchdown ankle_pitch | `21.0 ms`, corr `0.058` | 落地期基本解耦，不能把问题归为延迟 |
| sim touchdown ankle_pitch | `16.9 ms`, corr `0.425` | sim 落地仍保持较强线性传递 |

测试要求：

- 每个 case / step / side / joint / phase 都输出 `lag_ms` 和 `corr`。
- `corr < 0.1` 的窗口不得继续用 `lag_ms` 解释控制延迟，必须标记为 `decoupled_window`。

### M2. 相位补偿跟踪误差：`aligned_track_err`

定义：

```text
aligned_track_err = RMS(joint_pos(t + lag) - pos_des_raw(t))
```

解释：

| 指标状态 | 含义 | 可能现象 |
|---|---|---|
| real 与 sim 相近 | 该轴跟踪不是主差距 | swing ankle_pitch |
| real 明显高于 sim | 真机动态质量差，可能被冲击 / 柔性 / 噪声主导 | swing ankle_roll、touchdown ankle_pitch/roll |
| tracking err 高且 corr 低 | 不只是慢，而是关节与 target 解耦 | 锁死、冲击回弹、自激 |

报告对应：

| 阶段 | real | sim | 现象 |
|---|---:|---:|---|
| swing ankle_pitch | `0.245 rad` | `0.272 rad` | 两者相近，pitch 摆动跟踪不是主因 |
| swing ankle_roll | `0.212 rad` | `0.123 rad` | real 高 `73%`，roll 轴质量差 |
| touchdown ankle_pitch | `0.278 rad` | `0.164 rad` | real 高 `70%`，落地期被动运动明显 |
| touchdown ankle_roll | `0.200 rad` | `0.121 rad` | real 高 `65%`，接触期 roll 控制差 |

建议阈值：

| 等级 | 条件 |
|---|---|
| `watch` | `aligned_track_err >= 0.15 rad` |
| `risk` | `aligned_track_err >= 0.20 rad` |
| `fail` | `aligned_track_err >= 0.25 rad` 且 `corr < 0.2` |

### M3. 幅值增益：`amplitude_gain`

定义：

```text
amplitude_gain = joint_range_rad / target_range_rad
```

仅在 `target_range_rad >= 0.01 rad` 时计算。

解释：

| 范围 | 含义 | 对应现象 |
|---|---|---|
| `< 0.5` | 明显欠跟踪 | sim swing ankle_roll 严重欠建模 |
| `0.5 - 1.2` | 基本可接受 | swing 期正常响应 |
| `1.2 - 2.0` | 过跟踪 / 低阻尼放大 | real 低速 ankle_pitch 轻度过激 |
| `> 2.0` | 冲击过冲或自激风险 | touchdown ankle_pitch、knee_pitch |

报告对应：

| 指标 | real | sim | 现象 |
|---|---:|---:|---|
| swing ankle_pitch range ratio | `1.144` | `0.684` | real 微过跟踪，sim 欠跟踪 |
| swing ankle_roll range ratio | `0.765` | `0.202` | sim roll 摆动严重欠建模 |
| touchdown ankle_pitch range ratio | `2.843` | `0.365` | real 落地冲击过冲，sim 接触过刚 |
| touchdown knee_pitch range ratio | `2.401` | `0.404` | real 膝关节也被冲击放大 |

测试要求：

- 输出 `target_range_rad`、`joint_range_rad`、`amplitude_gain`。
- `amplitude_gain > 1` 的窗口要继续检查 M5 / M10，确认是跟踪过激、接触冲击还是闭环自激。

### M4. Target 换向频率：`target_direction_change_rate_hz`

定义：

```text
direction_change_rate_hz = 每秒速度符号反转次数
target_oscillation_hz    = direction_change_rate_hz / 2
```

解释：

该指标直接衡量策略输出是否在执行器可达带宽之外频繁抖动。报告中用 `76 ms` 延迟估计得到稳定带宽上限：

```text
f_stable_max ~= 1 / (4 * 0.076) ~= 3.28 Hz
```

报告对应：

| 数据集 | 阶段 | 关节 | target dir_chg | 对应振荡频率 | 现象 |
|---|---|---|---:|---:|---|
| real | swing | ankle_pitch | `22.3 Hz` | `11.2 Hz` | 超带宽约 `3.4x` |
| real | swing | ankle_roll | `32.4 Hz` | `16.2 Hz` | 超带宽约 `4.9x` |
| real | touchdown | ankle_roll | `36.6 Hz` | `18.3 Hz` | 接触期高频 target 最严重 |
| sim | swing | ankle_roll | `24.6 Hz` | `12.3 Hz` | sim 也超带宽，但弱于 real |

判读：

| 等级 | 条件 |
|---|---|
| `pass` | `target_oscillation_hz <= 3.3 Hz` |
| `watch` | `3.3 < target_oscillation_hz <= 6 Hz` |
| `risk` | `6 < target_oscillation_hz <= 10 Hz` |
| `fail` | `target_oscillation_hz > 10 Hz` |

对应现象：

- `fail` 通常表现为关节无法跟随、joint 变成机械低通输出。
- real 比 sim 高 `30%` 左右时，优先怀疑观测噪声放大策略输出。
- touchdown 中 `target_direction_change_rate_hz` 高时，会持续激励已经接地的关节，放大接触不稳定。

### M5. 速度自激比：`joint_vel_rms / target_vel_rms`

定义：

```text
vel_ratio = RMS(d joint_pos / dt) / RMS(d pos_des_raw / dt)
```

解释：

| 范围 | 含义 | 对应现象 |
|---|---|---|
| `< 0.5` | joint 作为低通响应，正常衰减高频 target | 多数 sim 窗口 |
| `0.5 - 1.0` | 响应偏强，需要结合 gain 判断 | real step3-step4 前兆 |
| `> 1.0` | joint 速度超过 target，存在额外能量输入 | 自激、弹性释放、冲击诱发振荡 |

报告对应：

| Case | Step | Side | vel_ratio | 现象 |
|---|---:|---|---:|---|
| real 25/0.4 | 5 | left | `1.56` | target 减小后关节仍高速振荡 |
| real 35/0.5 | 3 | left | `2.17` | 右踝锁死前的失控前兆 |
| real 40/0.8 | 4 | right | `2.92` | 严重过激 |
| real 40/0.8 | 6 | right | `10.35` | 极端失控，jnt 达 `11.63 rad/s` |

测试要求：

- 每个 step / side / joint 输出 `target_vel_rms`、`joint_vel_rms`、`vel_ratio`。
- `vel_ratio > 1` 必须标记为 `self_excitation_candidate`。
- 同一个 case 出现 2 个以上 `self_excitation_candidate`，判为该配置 `unstable_for_forward_x`。

### M6. 触地脚掌倾斜：`sole_roll_at_touchdown`

定义：

```text
sole_roll_at_touchdown = touchdown 时刻脚掌世界系 roll 角
```

优先通过 FK / 足体 `xmat` 计算，不用 `ank_roll` 直接替代。

解释：

| `abs(sole_roll)` | 等级 | 现象 |
|---:|---|---|
| `< 5 deg` | 正常 | 脚掌接近水平 |
| `5 - 8 deg` | watch | 轻度倾斜，需看下一步是否消除 |
| `8 - 15 deg` | risk | 触地倾斜明显，可能产生侧向冲击 |
| `> 15 deg` | fail | 严重内翻 / 外翻，步态稳定性已受破坏 |
| `> 25 deg` | critical | 跌倒或锁死后的结构性失稳 |

报告对应：

| Case / step | `ank_roll` | `sole_roll` | 现象 |
|---|---:|---:|---|
| real 35/0.5 step4 TD(R) | `0.0 deg lock` | `-17.5 deg` | 关节锁死掩盖脚掌严重内翻 |
| real 35/0.5 step5 SP(R) | `0.0 deg lock` | `-35.8 deg` | 锁死支撑踝极度内翻 |
| real 35/0.5 step6 SP(L) | `+1.4 deg` | `+31.2 deg` | 支撑腿极度外翻，跌倒姿态 |
| real 40/0.8 step6 TD(R) | `+23.6 deg` | `+12.6 deg` | 右踝剧烈外翻，目视翻机吻合 |

测试要求：

- `sole_roll` 是 touchdown 姿态的主指标。
- 当 `abs(sole_roll) - abs(ank_roll) > 8 deg` 时，标记 `ankle_joint_angle_blind_spot`。

### M7. 触地背屈与姿态一致性：`touchdown_ankle_pitch_mean/std`

定义：

```text
touchdown_ankle_pitch_mean = 前 6 步 touchdown leg ankle_pitch 均值
touchdown_joint_std        = 前 6 步 touchdown 关节角标准差
```

解释：

| 指标 | 含义 | 对应现象 |
|---|---|---|
| `ankle_pitch_mean` 不够负 | 背屈不足，落地缓冲差 | real 比 sim 少 `4-10 deg` |
| `ankle_pitch_std` 高 | 触地踝姿态不一致 | real 0.070-0.161 rad |
| `knee_pitch_std` 高 | 落地膝角离散，支撑策略不稳定 | real 0.071-0.233 rad，sim 0.017-0.054 rad |

报告对应：

| Case | real ankle_pitch mean | sim 参考 | 现象 |
|---|---:|---:|---|
| real 25/0.4 | `-0.066 rad` | `-0.216~-0.241 rad` | 背屈不足约 `9-10 deg` |
| real 30/0.4 | `-0.074 rad` | 同上 | 背屈不足 |
| real 35/0.5 | `-0.139 rad` | 同上 | 背屈仍不足，且伴随锁死 |
| real 40/0.8 | `-0.196 rad` | 同上 | 接近 sim，但 roll 失稳更严重 |

建议阈值：

| 指标 | watch | fail |
|---|---:|---:|
| `touchdown_ankle_pitch_mean` | `> -0.18 rad` | `> -0.10 rad` |
| `touchdown_ankle_pitch_std` | `> 0.08 rad` | `> 0.12 rad` |
| `touchdown_knee_pitch_std` | `> 0.08 rad` | `> 0.15 rad` |

### M8. 关节锁死 / 保护触发：`joint_lock_flag`

定义：

```text
joint_lock_flag =
  joint_range_rad < 0.02
  AND target_range_rad > 0.10
  AND aligned_track_err > 0.25
```

解释：

该指标识别“目标仍在变化，但实际关节几乎不动”的执行器失效状态。它和普通欠跟踪不同：普通欠跟踪仍有小幅响应，锁死窗口 `joint_range` 接近 0。

报告对应：

| Case | Step | 现象 |
|---|---:|---|
| real 35/0.5 | step4 touchdown | 右踝 pitch/roll `joint_range=0`，目标仍有信号 |
| real 35/0.5 | step5-6 | 右踝 pitch/roll 持续 `0.0 deg lock` |
| real 35/0.5 | step5 SP(R) | `sole_roll=-35.8 deg`，锁死后支撑稳定性完全失效 |

测试要求：

- 任一 ankle 出现 `joint_lock_flag`，本 case 直接判为 `hardware_protection_failure`。
- 如果锁死后控制仍继续行走，额外标记 `missing_degradation_behavior`。

### M9. 步间累积：`step_accumulation_score`

定义：

```text
step_accumulation_score =
  count of monotonic risk increase over consecutive steps
```

推荐同时跟踪：

- `abs(sole_roll_at_touchdown)`
- `amplitude_gain`
- `vel_ratio`
- `aligned_track_err`
- `knee_pitch` 极值

解释：

forward-x 失败不是单个瞬间异常，而是多步误差没有消除，逐步进入不可恢复状态。

报告对应：

| 现象 | 报告证据 |
|---|---|
| Kp35/40 touchdown `sole_roll` 逐步放大 | Kp35 step6 `26.6 deg`，Kp40 step6 右踝外翻 |
| Kp40 `joint_path / target_path` step6 到 `4.36x` | 控制器完全失去主动控制 |
| 35/0.5 锁死后左侧代偿失败 | step5-6 左踝目标增大但 joint 响应不足 |

建议判据：

| 等级 | 条件 |
|---|---|
| `watch` | 任一风险指标连续 2 步上升 |
| `risk` | 任一风险指标连续 3 步上升 |
| `fail` | `abs(sole_roll) > 15 deg` 或 `vel_ratio > 1` 后下一步未恢复 |

### M10. 频域低阻尼风险：`hf_energy_5_15` / `peak_gain_at_freq`

定义：

```text
hf_energy_5_15 = integral(PSD(joint_pos_ac), 5..15 Hz)
peak_gain_at_freq = |Q(f)| / |Target(f)|
residual_target_power_ratio = PSD(residual_peak) / PSD(target_peak)
```

解释：

该指标用于把 walking 数据中的“看起来抖”转成频域风险。它不能单独证明固有频率，必须和 step / sine sweep 的 `zeta_step`、`ringdown_freq_hz` 联合使用。

报告对应：

| 现象 | 对应后续验证 |
|---|---|
| real right_ankle_roll 自激点集中 | 优先检查 right_ankle_roll |
| Kp40/Kd0.8 高风险 | step + sine sweep 对比 Kp35/Kd1.5 |
| walking data 中严格 resonance candidate 不足 | 用专项激励补充 `zeta_step` 和 `f_n_closed_loop` |

建议输出：

| 指标 | 用途 |
|---|---|
| `peak_hz` | 主导振荡频率 |
| `hf_energy_5_15` | 高频振荡能量 |
| `hf_over_total` | 高频能量占比 |
| `peak_gain_at_freq` | 频点放大 |
| `residual_target_power_ratio` | 判断 residual 峰是否不能由 target 解释 |
| `zeta_step` | 最终判断阻尼水平 |
| `settling_time_ms` | 判断跨步残留风险 |

## 方案-报告对应表

| 报告章节 / 结论 | 测试指标 | 方案动作 | 通过 / 失败现象 |
|---|---|---|---|
| 2.2 延迟汇总：real/sim 延迟量级接近 | M1 `lag_ms`, `corr` | 每窗口输出延迟和相关性 | 延迟接近但 corr 低时，不再归因为延迟 |
| 3.3 Tracking Error：real touchdown 误差高 | M2 `aligned_track_err` | 对 swing/touchdown 分阶段对齐比较 | touchdown err `>=0.25 rad` 且 corr 低为失败窗口 |
| 6.1 range ratio：real touchdown pitch `2.84x` | M3 `amplitude_gain` | 输出 target/joint range 和 gain | `gain > 2` 为冲击过冲 / 自激风险 |
| 3.5 target 换向：22-37Hz | M4 `target_direction_change_rate_hz` | 计算 target 振荡频率并和 3.28Hz 带宽比较 | `target_oscillation_hz > 10Hz` 为 fail |
| 3.4 自激点：`joint_vel > target_vel` | M5 `vel_ratio` | 每 step/side 检测 `vel_ratio > 1` | 出现 2 个以上自激点则该配置不适合 forward-x |
| 5.4 sole_roll 修正：关节角盲区 | M6 `sole_roll_at_touchdown` | FK 计算脚掌 roll，不用 ank_roll 替代 | `abs(sole_roll)>15deg` fail，`>25deg` critical |
| 5.2 真机触地背屈不足 | M7 `touchdown_ankle_pitch_mean/std` | 统计前6步 touchdown leg 姿态 | mean `>-0.10rad` 或 std `>0.12rad` fail |
| 4.1 35/0.5 右踝锁死 | M8 `joint_lock_flag` | 检查 target 有信号但 joint range 近零 | 任一 ankle 锁死即硬件保护失败 |
| 3.6 Kp35/40 步间放大 | M9 `step_accumulation_score` | 对前6步风险指标做趋势检查 | 连续 3 步恶化或自激后不恢复为 fail |
| 8.1 低阻尼 + touchdown 主线 | M10 频域 + step/sine 指标 | 对 right_ankle_roll 做频谱和专项辨识 | `zeta_step < 0.3` 或 `peak_gain > 1` 为高风险 |

## 推荐产物

### 1. 指标明细 CSV

建议路径：

```text
real2sim/table/forward_x_failure_first6/forward_x_failure_first6_metric_detail.csv
```

每行一个 `case / step / phase / side / joint`：

| 字段 |
|---|
| `source` |
| `case_id` |
| `kp` |
| `kd` |
| `step_id` |
| `phase` |
| `side` |
| `joint` |
| `lag_ms` |
| `corr` |
| `target_range_rad` |
| `joint_range_rad` |
| `amplitude_gain` |
| `aligned_track_err_rad` |
| `target_dir_chg_hz` |
| `joint_dir_chg_hz` |
| `target_vel_rms` |
| `joint_vel_rms` |
| `vel_ratio` |
| `sole_roll_deg` |
| `joint_lock_flag` |
| `risk_tags` |

### 2. Case 级结论 CSV

建议路径：

```text
real2sim/table/forward_x_failure_first6/forward_x_failure_first6_metric_summary.csv
```

每行一个 case：

| 字段 |
|---|
| `source` |
| `case_id` |
| `kp` |
| `kd` |
| `max_touchdown_gain` |
| `max_vel_ratio` |
| `self_excitation_count` |
| `max_abs_sole_roll_deg` |
| `lock_step` |
| `target_oscillation_fail_count` |
| `tracking_fail_count` |
| `overall_status` |
| `primary_failure_mode` |

### 3. 方案-report 对应 Markdown

本文档就是 `28_forward_x_failure_first6_step_detailed_report.md` 的方案对应文件。后续如果生成自动化分析脚本，建议在脚本输出末尾同步写入：

```text
.oma/sim2real/results/forward_x_failure/28_first6_step_metric_test_result.md
```

该结果文件只写指标输出和 pass/fail，不重复本文档中的指标定义。

## Overall 判定规则

按 case 给出最终状态：

| 状态 | 条件 |
|---|---|
| `pass` | 无 lock；`self_excitation_count=0`；`abs(sole_roll)<=8deg`；主要 tracking err 未进入 fail |
| `watch` | 有轻度 sole_roll 或 target 高频，但无自激、无锁死 |
| `risk` | 出现 `vel_ratio>1`、`gain>2`、`abs(sole_roll)>15deg` 任一项 |
| `fail` | 出现 `joint_lock_flag`、`abs(sole_roll)>25deg`、或连续步间恶化且未恢复 |

基于当前报告，已有 case 的预期归类：

| Case | 预期状态 | 主要依据 |
|---|---|---|
| real 25/0.4 | `watch/risk` | 可稳定原地踏步，但 forward-x 存在支撑侧深屈曲和局部自激点 |
| real 30/0.4 | `risk` | 支撑膝极端屈曲、touchdown 姿态离散、前向稳定不足 |
| real 35/0.5 | `fail` | step4 起右踝锁死，step5/6 sole_roll 进入 critical |
| real 40/0.8 | `fail` | step6 右踝严重外翻，自激倍数极高 |
| sim 2504/3505/4005/5008 | `model_gap` | 无 real-like 自激和锁死，但 swing ankle_roll 严重欠响应、左脚 sole_roll 系统性异常 |

## 下一步执行建议

1. 先把 M1-M9 做成前 6 步批量表，复现当前报告中的关键数值。
2. 对所有 `risk/fail` 窗口生成事件表，按 `case -> step -> side -> joint -> risk_tags` 排序。
3. 对 `real right_ankle_roll touchdown` 执行 M10 频域验证。
4. 用 step + sine sweep 输出 `zeta_step`、`ringdown_freq_hz`、`f_n_closed_loop_hz`、`peak_gain_at_freq`、`settling_time_ms`，最终关闭或修正“低阻尼配置导致闭环放大”的判断。
