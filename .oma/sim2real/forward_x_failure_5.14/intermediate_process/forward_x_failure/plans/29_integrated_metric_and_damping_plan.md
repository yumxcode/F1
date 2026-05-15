# Forward-X Failure Integrated Metric and Damping Plan

状态：`ended_intermediate`

生成日期：2026-05-13

关联子方案：

- `.oma/sim2real/plans/forward_x_failure/28_first6_step_metric_test_plan.md`
- `real2sim/ankle_damping_analysis/ankle_damping_analysis_methodology.md`

## 目的

本文档是 forward-x failure 的总体指标方案。它把两个已有子方案合并成一个分层工作流：

1. 先用 `28_first6_step_metric_test_plan.md` 做前 6 步故障定位，回答“哪一步、哪条腿、哪个关节、出现了什么异常”。
2. 再用 `ankle_damping_analysis_methodology.md` 做阻尼/谐振归因，回答“该异常是否由欠阻尼、谐振、触地阻尼崩溃或 sim/real 阻尼差异导致”。

两个子方案不互相替代。28 方案负责**故障事件检测**，阻尼方案负责**动力学原因判定**。

## 子方案边界

### A. 前 6 步故障事件方案

来源：

```text
.oma/sim2real/plans/forward_x_failure/28_first6_step_metric_test_plan.md
```

解决的问题：

| 问题 | 输出 |
|---|---|
| forward-x 失败从哪一步开始恶化 | `step_id`, `risk_tags`, `step_accumulation_score` |
| 哪侧 / 哪个关节最先异常 | `side`, `joint`, `max_vel_ratio`, `joint_lock_flag` |
| 是 tracking 差、过冲、自激、脚掌倾斜还是锁死 | `tracking_error_rms_aligned`, `range_gain_phase`, `velocity_self_excitation_ratio`, `sole_roll_td_deg`, `joint_lock_flag` |
| real 与 sim 的现象差异在哪里 | case 级 `overall_status`, `primary_failure_mode` |

适用数据：

- walking / forward-x 日志
- 前 6 步或指定步态窗口
- 需要 touchdown / swing 分相位
- 需要 target 和 joint 时序
- 如要判断脚掌倾斜，需要 FK 或足端姿态

不负责的问题：

- 不单独给出严格阻尼比。
- 不用 `range_gain_phase > 1` 直接宣称系统欠阻尼。
- 不替代 step / sine sweep 的模态确认。

### B. 踝关节阻尼 / 谐振方法论

来源：

```text
real2sim/ankle_damping_analysis/ankle_damping_analysis_methodology.md
```

解决的问题：

| 问题 | 输出 |
|---|---|
| ankle 系统是欠阻尼、临界、过阻尼还是 FRF 不可信 | `frf_gain_at_fn_swing`, `zeta_frf_swing`, `frf_coherence_swing` |
| 行走 FRF 不可信时如何兜底判断 | `range_gain_abs_step`, `self_excitation_count` |
| 受控条件下真实阻尼是多少 | `zeta_step`, `ringdown_freq_hz`, `settling_time_ms` |
| Kp/Kd 应该往哪个方向调 | `zeta_target`, `kd_recommendation`, `stance/swing Kd split` |
| sim/real 阻尼建模是否一致 | `real_vs_sim_frf_gain_delta`, `real_vs_sim_zeta_delta` |

适用数据：

- swing 分离 FRF 所需 walking 日志
- 悬空 / 触地 step test
- sine sweep 或频域激励
- Kp/Kd 已知的关节级数据

不负责的问题：

- 不完整判断 forward-x 是否已经跌倒、锁死或脚掌严重倾斜。
- 不用全步态 `G_fn` 单独判定过阻尼。
- 不把 walking 残差 PSD 主峰直接当作固有频率。

## 统一指标命名

以下命名作为后续脚本、CSV 和报告的统一字段名。旧名可以在局部报告中保留，但新增产物应优先使用统一名。

### 时间与分相位

| 统一名 | 旧名 / 来源 | 定义 | 归属 |
|---|---|---|---|
| `phase` | `swing`, `touchdown`, `stance` | 分析窗口类型 | 两者共用 |
| `step_id` | step | 步编号 | 28 方案 |
| `side` | left/right | 左右侧 | 两者共用 |
| `joint` | ankle_pitch/ankle_roll | 关节轴 | 两者共用 |
| `kp` | Kp | 位置增益 | 两者共用 |
| `kd` | Kd | 速度阻尼 | 两者共用 |

### 线性传递与延迟

| 统一名 | 旧名 / 来源 | 定义 | 判读 |
|---|---|---|---|
| `tracking_lag_ms` | `lag_ms`, `delay_ms`, `tau_d` | target 到 joint 的时延估计 | 事件定位和相位裕度分析共用 |
| `xcorr_coeff` | `corr` | 差分互相关系数 | 只表示时域 lag 估计可信度 |
| `frf_coherence_swing` | `coh_sw` | swing FRF 在 `fn_th` 附近的相干函数 | 只表示频域 FRF 可信度 |

注意：

```text
xcorr_coeff != frf_coherence_swing
```

两者阈值都可能在 0.4 附近，但含义不同。`xcorr_coeff` 用于判断 lag 和 target/joint 线性传递，`frf_coherence_swing` 用于判断 FRF 阻尼结论是否可信。

### 跟踪误差与幅值增益

| 统一名 | 旧名 / 来源 | 定义 | 用途 |
|---|---|---|---|
| `tracking_error_rms_aligned` | `aligned_track_err`, `e_RMS` | lag 对齐后的 RMS(pos - des) | 事件检测，sim/real tracking gap |
| `tracking_error_rms_swing` | `e_RMS_sw` | swing phase RMS(pos - des) | 阻尼方案一级指标辅助项 |
| `tracking_error_rms_stance` | `e_RMS_st` | stance/contact phase RMS(pos - des) | 接地冲击稳定性 |
| `range_gain_phase` | `amplitude_gain` | phase 内 `joint_range / target_range` | 28 方案，用于过冲/自激事件检测 |
| `range_gain_abs_step` | `G_amp` | 每步 `max(abs(joint)) / max(abs(target))` | 阻尼方案，在 FRF 不可信时兜底判断局部欠阻尼行为 |
| `touchdown_overshoot_ratio` | `A_peak` | 接地后峰值 / 稳态均值 | 接地冲击响应，独立于 `range_gain_phase` |

关键约束：

```text
range_gain_phase > 1
  => 只能说明该窗口输出幅值大于输入
  => 不能单独得出“欠阻尼”

欠阻尼结论必须来自：
  frf_gain_at_fn_swing / zeta_frf_swing / zeta_step
  或 FRF 不可信时由 range_gain_abs_step + self_excitation_count 作为行为证据
```

### 高频、自激与频域

| 统一名 | 旧名 / 来源 | 定义 | 用途 |
|---|---|---|---|
| `target_direction_change_rate_hz` | target dir_chg | target 速度符号反转次数/秒 | 判断策略输出高频换向 |
| `target_oscillation_freq_hz` | target dir_chg / 2 | target 等效振荡频率 | 与稳定带宽比较 |
| `joint_direction_change_rate_hz` | joint dir_chg | joint 速度符号反转次数/秒 | 判断 joint 高频响应 |
| `velocity_self_excitation_ratio` | `vel_ratio`, `joint_vel_rms / target_vel_rms` | `RMS(joint_vel) / RMS(target_vel)` | `>1` 为自激候选 |
| `self_excitation_count` | 自激点数量 | `velocity_self_excitation_ratio > 1` 的窗口数 | case 级风险聚合 |
| `hf_energy_5_15_rad2` | `hf_energy_5_15` | 5-15Hz PSD 积分 | 高频振荡能量 |
| `hf_energy_ratio_5_15` | `hf_over_total` | 5-15Hz 能量 / 0.5-20Hz 能量 | 高频占比 |
| `peak_freq_hz` | `peak_hz` | 主频 | 频域描述，不直接等于固有频率 |
| `frf_gain_at_fn_swing` | `G_fn_sw` | swing FRF 在理论固有频率处的幅值 | 阻尼判定一级指标 |
| `zeta_frf_swing` | `ζ_frf_sw` | `1/(2*frf_gain_at_fn_swing)`，需相干可信 | 阻尼判定 |
| `zeta_step` | `ζ_step` | step ringdown 阻尼比 | 最可信阻尼证据 |
| `ringdown_freq_hz` | `f_ringdown` | step 后自由衰减频率 | 闭环模态确认 |
| `closed_loop_natural_freq_hz` | `f_n_closed_loop` | 闭环等效固有频率 | step/sine 结论 |
| `settling_time_ms` | settling time | 进入并保持阈值内的时间 | 跨步残留风险 |

关键约束：

```text
peak_freq_hz != closed_loop_natural_freq_hz
```

walking 数据中的 PSD 主峰可能来自 target 谐波、步态基频、接触冲击或误差灵敏度峰。只有 step/sine 或可信 FRF 才能用于闭环模态确认。

### 触地姿态、锁死与步间累积

| 统一名 | 旧名 / 来源 | 定义 | 用途 |
|---|---|---|---|
| `sole_roll_td_deg` | `sole_roll_at_touchdown` | touchdown 时脚掌世界系 roll 角 | 真实脚掌倾斜主指标 |
| `ankle_roll_td_deg` | `ank_roll` | touchdown 时 ankle roll 关节角 | 辅助指标，不可替代 `sole_roll_td_deg` |
| `ankle_joint_angle_blind_spot` | blind spot | `abs(sole_roll) - abs(ank_roll) > 8deg` | 关节角低估脚掌倾斜 |
| `touchdown_ankle_pitch_mean_rad` | ankle_pitch mean | 前 6 步触地腿 ankle pitch 均值 | 判断背屈不足 |
| `touchdown_ankle_pitch_std_rad` | ankle_pitch std | 前 6 步触地腿 ankle pitch 标准差 | 判断触地一致性 |
| `touchdown_knee_pitch_std_rad` | knee_pitch std | 前 6 步触地腿 knee pitch 标准差 | 判断支撑姿态离散 |
| `joint_lock_flag` | lock flag | `joint_range < 0.02` 且 target/err 仍大 | 硬件保护 / 执行器失效 |
| `lock_step_id` | lock step | 首次锁死步编号 | case 级失败定位 |
| `step_accumulation_score` | accumulation score | 连续步风险增长计数 | 判断步间误差累积 |

## 分层使用流程

### Phase 1: 事件定位

执行 `28_first6_step_metric_test_plan.md` 的 M1-M9。

输出：

```text
forward_x_failure_first6_metric_detail.csv
forward_x_failure_first6_metric_summary.csv
```

必需字段：

```text
case_id, source, kp, kd, step_id, phase, side, joint,
tracking_lag_ms, xcorr_coeff,
tracking_error_rms_aligned,
range_gain_phase,
target_direction_change_rate_hz,
target_oscillation_freq_hz,
velocity_self_excitation_ratio,
sole_roll_td_deg,
joint_lock_flag,
risk_tags
```

Phase 1 的结论只写事件：

- `touchdown_overshoot`
- `target_high_frequency`
- `self_excitation_candidate`
- `sole_roll_failure`
- `joint_lock`
- `step_accumulation`
- `sim_model_gap`

不要在 Phase 1 直接写：

```text
系统欠阻尼已确认
固有频率是 X Hz
Kd 必须改到某个值
```

### Phase 2: 阻尼归因

对 Phase 1 标记为 `risk/fail` 的对象进入阻尼方案。

优先级：

1. 若有 step/sine 数据，用 `zeta_step`、`ringdown_freq_hz`、`closed_loop_natural_freq_hz`。
2. 若只有 walking 数据，先看 `frf_coherence_swing`。
3. 若 `frf_coherence_swing >= 0.40`，用 `frf_gain_at_fn_swing` 和 `zeta_frf_swing`。
4. 若 `frf_coherence_swing < 0.40`，FRF 不下阻尼结论，只用 `range_gain_abs_step + self_excitation_count` 描述局部欠阻尼行为。

Phase 2 的结论写原因：

- `confirmed_under_damped_by_step`
- `confirmed_under_damped_by_frf`
- `frf_inconclusive_time_domain_instability`
- `touchdown_damping_collapse`
- `sim_over_damped_model_gap`
- `delay_phase_margin_risk`

### Phase 3: 综合判定

综合判定必须同时包含“现象”和“原因”：

```text
现象: real 40/0.8 right_ankle_roll step6 出现 velocity_self_excitation_ratio > 1、
      sole_roll_td_deg 超限、forward-x fail。

原因: walking FRF / step test 指向低阻尼或触地阻尼崩溃；
      若 FRF coh 不足，则写为“局部欠阻尼行为，需 step/sine 确认”。
```

## 统一判定规则

### 事件风险等级

| 等级 | 条件 |
|---|---|
| `event_pass` | 无锁死；`self_excitation_count=0`；`abs(sole_roll_td_deg)<=8`；tracking 未超 fail |
| `event_watch` | target 高频或轻度 sole roll，但未出现自激 / 锁死 |
| `event_risk` | `velocity_self_excitation_ratio>1`、`range_gain_phase>2`、`abs(sole_roll_td_deg)>15` 任一项 |
| `event_fail` | `joint_lock_flag=true`、`abs(sole_roll_td_deg)>25`、或连续步间恶化且未恢复 |

### 阻尼可信等级

| 等级 | 条件 |
|---|---|
| `damping_confirmed_step` | 有 step/sine，`zeta_step` 或频响峰明确 |
| `damping_confirmed_frf` | `frf_coherence_swing>=0.40` 且 `zeta_frf_swing` 可判读 |
| `damping_behavior_only` | FRF 不可信，但 `range_gain_abs_step>1` 或 `self_excitation_count>0` |
| `damping_inconclusive` | FRF 不可信，且无明显时域自激证据 |

### 总体状态

| 总体状态 | 条件 |
|---|---|
| `pass` | `event_pass` 且无欠阻尼证据 |
| `watch` | `event_watch` 或 `damping_behavior_only`，但无 fail 事件 |
| `risk` | `event_risk` 且阻尼证据至少为 `damping_behavior_only` |
| `fail` | `event_fail`，或 `event_risk + damping_confirmed_step/frf` |
| `model_gap` | sim 无对应 real-like fail，但 sim 阻尼/roll 响应与 real 系统性不一致 |

## 典型使用示例

### 示例 1: `range_gain_phase > 2`

正确写法：

```text
该 touchdown 窗口存在过冲/放大事件，需检查 velocity_self_excitation_ratio、
sole_roll_td_deg 和阻尼指标。
```

错误写法：

```text
range_gain_phase > 2，所以系统欠阻尼已确认。
```

### 示例 2: `frf_coherence_swing < 0.40`

正确写法：

```text
FRF 阻尼结论不可信，降级使用 range_gain_abs_step 和 self_excitation_count
描述局部欠阻尼行为，并安排 step/sine 确认。
```

错误写法：

```text
G_fn_sw 数值很低，所以系统过阻尼。
```

### 示例 3: `sole_roll_td_deg` 超限

正确写法：

```text
这是 forward-x 失败事件证据，说明触地脚掌姿态已破坏；
它本身不直接给出阻尼比，但可作为触地冲击/锁死/低阻尼放大的结果证据。
```

错误写法：

```text
sole_roll 超限，所以阻尼比是多少。
```

## 推荐报告结构

后续综合报告统一按以下结构写：

```text
1. Case 级总体状态
   - event_status
   - damping_status
   - overall_status

2. 故障事件证据
   - first_failed_step
   - side/joint
   - risk_tags
   - key metrics: range_gain_phase, velocity_self_excitation_ratio,
     sole_roll_td_deg, joint_lock_flag

3. 阻尼/谐振归因
   - frf_coherence_swing
   - frf_gain_at_fn_swing
   - zeta_frf_swing
   - zeta_step / ringdown_freq_hz / settling_time_ms when available

4. Sim2Real gap
   - real event not reproduced in sim
   - sim over-damped or roll response under-modeled
   - contact/touchdown response gap

5. 参数建议
   - only if damping_status is confirmed_step or confirmed_frf
   - otherwise write required next experiment instead of Kd conclusion
```

## 与当前结论的关系

当前 forward-x 主线保持不变：

```text
real 踝关节低阻尼 / 欠阻尼
  + touchdown 冲击
  + target 高频换向
  + 传动弹性储能
  -> ankle roll / pitch 过冲、自激、锁死和步间误差累积
```

但后续表达必须分层：

- “过冲、自激、锁死、sole_roll 超限”属于事件层，由 28 方案负责。
- “欠阻尼、触地阻尼崩溃、sim 过阻尼、Kd 不足”属于归因层，由阻尼方案负责。
- 只有当事件层和归因层同时成立，才写成“低阻尼导致 forward-x failure 的强证据链”。

## 下一步

1. 在后续脚本输出中采用本文档的统一字段名。
2. 保留旧字段兼容，但在 CSV 中增加统一字段别名。
3. 对 `real right_ankle_roll touchdown` 先跑事件层表，再用 step/sine 或可信 FRF 补齐归因层。
4. 对 `Kp40/Kd0.8` 和 `Kp35/Kd1.5` 做统一字段对照，验证提高 Kd 是否同时降低事件风险和改善阻尼状态。
