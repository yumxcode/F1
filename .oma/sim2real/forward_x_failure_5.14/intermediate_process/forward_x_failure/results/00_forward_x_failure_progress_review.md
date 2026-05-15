# Forward X Failure Current Result

状态：`ended_intermediate`

说明：本文件已归档为中间过程。最终整理后的方案、脚本、报告和表格以 `sim2real/walk_data_analysis/` 为准。

## 当前总判断

`forward_x_failure` 的主因当前收敛为：

```text
真机踝关节闭环低阻尼 / 欠阻尼
  + touchdown 冲击
  + target 中接近模态的频率成分
  -> 关节响应幅值放大、过冲、自激点
  -> 前向推进失败
```

最重要对象：

```text
real right_ankle_roll
touchdown
Kp40/Kd0.8 及相近低阻尼配置
```

## 已删除的旧结论

以下方向不再作为当前问题主线：

| 旧方向 | 当前处理 |
|---|---|
| FK foot-frame / contact-frame 主导 | 删除。旧结论依赖过多 frame / detector 假设，无法作为确定主因 |
| coupled geometry 主导 | 删除。证据链分散，不能解释 Kd 改善和过冲/自激现象 |
| dead-zone 主导 | 删除。可解释小信号兑现，但不是 forward failure 主因 |
| policy output 延迟主导 | 删除。real/sim 延迟量级相近，不能解释 real-only 放大 |
| raw touchdown detector / old contact proxy | 删除。历史方法论污染，不能继续作为主证据 |

## 保留数据结论

### 1. real 的 touchdown 响应比 sim 更重

来自 `20_real_vs_sim_joint_jitter_compare.md`：

```text
roll touchdown:
  real/sim joint hp    ~= 1.76x
  real/sim joint range ~= 2.08x
  real/sim joint path  ~= 2.26x
```

这说明主要差异不是 policy target 本身，而是真机 joint 层在 touchdown 的响应更重。

### 2. real 存在过冲和自激点

来自 `28_forward_x_failure_first6_step_detailed_report.md`：

```text
real touchdown ankle_pitch gain 可高到 2.84x 量级
real ankle_roll 出现 joint velocity > target velocity 的自激点
35/0.5 右踝 step4 起出现锁死风险
40/0.8 右踝出现极端过激窗口
```

关键解释：

```text
target 小，但 joint 仍高速运动
=> 关节响应不再只是跟随 target
=> 需要机械弹性、接触冲击、低阻尼闭环共同解释
```

### 3. 低阻尼理论能解释 Kd 敏感性

来自 `33_kp_kd_stability_theory_plan.md`：

```text
Kp35/Kd0.5:
  zeta ~= 0.136
  M_r  ~= 3.7x

Kp40/Kd0.8:
  zeta ~= 0.202
  M_r  ~= 2.5x

Kp35/Kd1.5:
  zeta ~= 0.408
  M_r  ~= 1.3x
```

因此，低 `Kd` 配置天然容易在模态附近放大扰动；提高 `Kd` 会同时降低谐振峰、缩短衰减时间、改善相位补偿。

### 4. 现有 walking data 的谐振验证结果

来自 `34_ankle_resonance_peak_validation.md`：

严格窗口判据：

```text
freq_gap_hz <= 1.0
amplitude_gain > 1.0
residual_target_power_ratio >= 3.0
```

当前：

```text
strict resonance_candidate = 0 / 384
```

但放宽频率接近阈值后：

```text
freq_gap <= 1.5 Hz -> 1 个候选
freq_gap <= 2.0 Hz -> 6 个候选
```

全部集中在：

```text
real right_ankle_roll
```

最强候选：

```text
real kp40_kd0.8 touchdown step 5 right_ankle_roll
target_dominant_freq_hz = 6.25
f_modal_candidate_hz   = 5.00
freq_gap_hz            = 1.25
amplitude_gain         = 4.09
residual_target_ratio  = 21.11
```

解释：walking data 已经足够把风险对象收敛到 `right_ankle_roll touchdown`，但严格 `zeta_step` 仍需 step/sine 专项实验确认。

## 当前唯一有效逻辑链

```text
1. forward x 失败时，real 踝关节在 touchdown 出现更大 joint range/path/tracking error。
2. sim 没有同等 real-only 放大，延迟量级也不能解释差异。
3. low Kd 的二阶闭环模型给出低阻尼和高谐振峰。
4. walking data 中 real right_ankle_roll 存在 residual/target 额外功率放大。
5. 因此当前主因收敛为真机踝关节低阻尼导致的 touchdown 过冲/自激风险。
```

## 当前不可再使用的说法

不要再写：

```text
主因是 coupled geometry
主因是 dead-zone
主因是 policy output late
主因是 FK foot-frame residual
所有 5~7 Hz 峰都是固有频率
```

可以写：

```text
现有 walking data 支持 right_ankle_roll touchdown 的低阻尼放大风险。
Kp/Kd 理论与 real/sim 差异共同支持欠阻尼主线。
下一步用 step/sine 补充 zeta_step 和 f_n_closed_loop。
```

## 下一步

只做一个验证：

```text
right_ankle_roll
Kp40/Kd0.8 vs Kp35/Kd1.5
step + sine sweep
```

必须输出：

```text
zeta_step
ringdown_freq_hz
f_n_closed_loop_hz
peak_gain_at_freq
settling_time_ms
```

如果 `Kp35/Kd1.5` 显著降低 `peak_gain_at_freq`、`settling_time_ms` 和 walking touchdown 的 `amplitude_gain`，则当前问题可以正式关闭为“低阻尼配置导致的踝关节闭环放大问题”。
