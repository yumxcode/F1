 # Round 2 踝关节 Kp/Kd 辨识结果

## 阶段状态

> **✅ Round 2A 已正式结束**；**✅ Round 2B 已正式结束**
>
> 四个踝关节的悬空收敛与双口径触地退化测量均已完成。
> 当前进入 **Round 2C**：基于 Round 2B 各关节退化根因，执行定向参数修复。

轮次目标：
- `Round 2A`: 悬空工况 `best_air_candidate` 收口 ✅
- `Round 2B`: 触地退化测量 ✅
- `Round 2C`: 定向修复（提升 kp / kd，消除 timing 退化与振荡分裂）← **当前阶段**（执行单：[03_round_02c_contact_degradation_fix.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/sim2real_steps/ankle_kp_kd/03_round_02c_contact_degradation_fix.md)）

---

## Round 2A 最终结论汇总

| 关节 | 最佳 `kp/kd` | 状态 | 选择原因 |
|---|---|---|---|
| `left_ankle_pitch_joint` | `80 / 0.8` | `best_air_candidate` | 主口径 `0.015 rad` 下 3 次重复高度一致；`tracking_ratio ≈ 1.025`，幅值最到位；`kd: 0.5→0.8` 已将持续振荡压至单次过冲（`zero_crossing_count: 3→1`）；`kd: 0.8→1.0` 无额外收益 |
| `left_ankle_roll_joint` | `80 / 1.0` | `best_air_candidate` | 沿 `kd` 支路在标准口径与大步长口径下均持续优于 `80/0.5` 和 `80/0.8`；`overshoot_ratio` 逐步从 `0.197→0.158→0.122`；当前阶段在已测点位中过冲最小，为局部最优 |
| `right_ankle_roll_joint` | `50 / 0.8` | `best_air_candidate` | 当前唯一稳定进入 `well_damped_tracking` 的点；`overshoot_ratio = 0`，`zero_crossing_count = 0`，3 次重复完全一致；时间响应满足 walking 预算 |
| `right_ankle_pitch_joint` | `40 / 0.8` | `best_air_candidate` | 相比 `kd=0.5` 支路，主口径与大步长口径均更稳定；`40/0.8 @ 0.100` 相比 `40/0.5 @ 0.100` 过冲从 `0.401` 降至 `0.202`；确认高 `kd` 为正确方向 |

> **说明**：各关节测试数据表中，`ground` 历史数据已全部移除。原因是此前完全触地测试口径存在误差，不能继续作为退化量判断基线。**Round 2B 将对四个关节当前最佳 air 点统一重新做完全触地测试。**

---

## Round 2B 执行情况

> **✅ Round 2B 已完成**，四关节双口径（0.015 rad + 0.100 rad）触地退化测量全部完成。
>
> 执行单：[02_round_02b_ground_degradation_test.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/sim2real_steps/ankle_kp_kd/02_round_02b_ground_degradation_test.md)（含测试程序和通过/失败判据）
>
> 详细结论见本文档下方：[Round 2B 横向总结](#round-2b-横向总结)、各关节详细结论节。

---

## 当前测试方法

- 统一按以下顺序推进：
  - `Round 2A` 先在悬空工况建立本体闭环上界 ✅
  - `Round 2B` 再测触地退化量 ✅
  - `Round 2C` 针对各关节退化根因定向修复 ← 当前
- **关于 ground 数据**：
  - 本文档中所有历史 `ground` 数据已全部清除
  - 原因：此前完全触地测试口径存在误差，不能参与当前退化量排序与判断
  - 从 Round 2B 起，将对四个关节重新统一做完全触地测试，结果另行记录

---

## 每关节测试记录表（air 数据）

说明：
- 下表只记录当前已测过并在文档中留有数值证据的 air 点位。
- 所有历史 `ground` 数据已从表中删除；后续完全触地结果将在 `Round 2B` 重新统一记录。
- `—` 表示该字段在当前文档或历史结果页中没有保留，不做推断补值。
- `状态` 标记当前点位在 `Round 2` 中的角色。

### Left Pitch 测试表

| `kp/kd` | 工况 | `tracking_ratio` | `peak_tracking_ratio` | `tail_tracking_ratio` | `peak_time_sec` | `response_class` | 备注 | 状态 |
|---|---|---:|---:|---:|---:|---|---|---|
| `30/0.5` | `air` | `0.462 ± 0.143` | `0.486 ± 0.153` | `0.486 ± 0.153` | `0.079 ± 0.010` | `undershoot_soft` | `Round 2D` 补测。1 次约 `0.627`，2 次约 `0.380`；无过冲、无过零，但主轴明显偏软，且 `coupled_motion ≈ -0.004 ± 0.002` 偏大 | `rejected_soft_split` |
| `30/0.5` | `air` | `0.988 ± 0.011` | `1.215 ± 0.012` | `1.027 ± 0.012` | `0.107 ± 0.001` | `oscillatory_but_settling` | `step_amplitude_rad = 0.100`。补录大步长对照；`overshoot_ratio ≈ 0.215`，`zero_crossing_count = 3`，`settling_time_sec ≈ 0.163 ± 0.001`，说明该点存在明显幅值依赖 | `supplementary_large_step` |
| `80/0.5` | `air` | `1.028 ± 0.001` | `1.324 ± 0.000` | `1.060 ± 0.000` | `0.059 ± 0.001` | `sustained_oscillation` | `Round 2D` 复测确认 3 次高度一致；`overshoot_ratio ≈ 0.324`，`zero_crossing_count = 3`，`decay_ratio ≈ 0.999`，稳定欠阻尼点 | `retested_consistent_but_unstable` |
| `80/0.8` | `air` | `1.025 ± 0.001` | `1.060 ± 0.000` | `1.060 ± 0.000` | `0.049 ± 0.001` | `single_overshoot` | `Round 2D` 补测。3 次高度一致；`overshoot_ratio ≈ 0.060`，`zero_crossing_count = 1`，相较 `80/0.5` 明显收口，主轴幅值仍基本到位 | **`best_air_candidate`** |
| `80/0.8` | `air` | `0.975 ± 0.001` | `1.314 ± 0.000` | `0.994 ± 0.000` | `0.067 ± 0.001` | `oscillatory_but_settling` | `step_amplitude_rad = 0.100`。补录大步长对照；`overshoot_ratio ≈ 0.314`，`zero_crossing_count = 4`，`settling_time_sec ≈ 0.179 ± 0.002`，大步长下仍明显欠阻尼但可回收 | `supplementary_large_step` |
| `80/0.8` | `ground` | `0.641 ± 0.002` | `0.664 ± 0.001` | `0.664 ± 0.001` | `0.055 ± 0.001` | `undershoot_soft` | `Round 2B`，`step_amplitude_rad = 0.015`。3 次全部 `undershoot_soft`；`degradation_ratio ≈ 0.625`；无振荡无过零，纯欠跟踪；**3 次极度一致（std=0.002）**；`primary_peak_effort ≈ 7.03 Nm`；`peak_time` 全部 good；`coupled_motion ≈ 0.003` | `ground_severe_degradation_small_step` |
| `80/0.8` | `ground` | `0.880 ± 0.003` | `1.015 ± 0.019` | `0.900 ± 0.000` | `0.089 ± 0.001` | `sustained_oscillation / single_overshoot / well_damped_tracking` | `Round 2B`，`step_amplitude_rad = 0.100`。tracking 大幅恢复（`degradation_ratio ≈ 0.859`），确认接触阈值效应；**响应类型改善型分裂**：iter1 `sustained_oscillation`（zero_crossing=2）→ iter2 `single_overshoot` → iter3 `well_damped_tracking`，随迭代逐步收敛；`decay_ratio = 1.000`（iter1 振荡不衰减）；timing 全部 good（`peak_time = 0.089 ± 0.001`），与 right pitch 的 timing 退化形成对比；`primary_peak_effort ≈ 37.13 Nm`（为四关节最高）；`actual_span = 0.127`，实际位移超过命令幅值，需注意安全边界；`coupled_motion ≈ -0.001 ± 0.003`，方向不稳定（iter1 正，iter2/3 负） | `ground_large_step_tracking_ok_oscillation_split` |
| `80/1.0` | `air` | `1.023 ± 0.001` | `1.060 ± 0.000` | `1.060 ± 0.000` | `0.053 ± 0.001` | `single_overshoot` | `Round 2D` 补测。与 `80/0.8` 相比未继续减小过冲，且 `rise/peak_time` 略慢 | `rejected_no_gain_vs_80_0.8` |

### Left Roll 测试表

| `kp/kd` | 工况 | `tracking_ratio` | `peak_tracking_ratio` | `tail_tracking_ratio` | `peak_time_sec` | `response_class` | 备注 | 状态 |
|---|---|---:|---:|---:|---:|---|---|---|
| `30/0.5` | `air` | `0.119 ± 0.297` | `0.164 ± 0.284` | `0.130 ± 0.313` | `0.031 ± 0.053` | `undershoot_soft` | 标准口径 `0.015`。3 次 repeat：`0.462 / -0.052 / -0.052`，两次 `peak_time_status = too_fast`，严重分裂 | `rejected_post_fix_standard` |
| `30/0.5` | `air` | `0.991 ± 0.044` | `1.186 ± 0.019` | `1.033 ± 0.049` | `0.106 ± 0.008` | `sustained_oscillation / single_overshoot` | `step_amplitude_rad = 0.100`。补录大步长对照；幅值接近目标，但仍有轻度欠阻尼 | `supplementary_large_step` |
| `80/0.5` | `air` | `1.073 ± 0.001` | `1.197 ± 0.000` | `1.114 ± 0.000` | `0.061 ± 0.001` | `sustained_oscillation` | 复紧后标准口径 `0.015`。`overshoot_ratio ≈ 0.197`，`zero_crossing_count ≈ 3.67 ± 1.15` | `provisional_post_fix_standard` |
| `80/0.5` | `air` | `0.998 ± 0.002` | `1.460 ± 0.012` | `1.022 ± 0.002` | `0.062 ± 0.002` | `sustained_oscillation` | `step_amplitude_rad = 0.100`。补录大步长对照；`overshoot_ratio ≈ 0.460`，`zero_crossing_count = 5`，大步长下振荡显著放大 | `supplementary_large_step` |
| `80/0.8` | `air` | `1.072 ± 0.000` | `1.158 ± 0.007` | `1.114 ± 0.000` | `0.065 ± 0.001` | `single_overshoot` | 标准口径 `0.015`；`overshoot_ratio ≈ 0.158`，`zero_crossing_count = 1`，较 `80/0.5` 明显更稳 | `provisional_best_air_point` |
| `80/0.8` | `air` | `0.984 ± 0.000` | `1.321 ± 0.006` | `1.008 ± 0.000` | `0.062 ± 0.003` | `oscillatory_but_settling` | `step_amplitude_rad = 0.100`。补录大步长对照；`overshoot_ratio ≈ 0.321`，`settling_time_sec ≈ 0.174 ± 0.036`，较 `80/0.5` 明显改善 | `supplementary_large_step` |
| `80/1.0` | `air` | `1.067 ± 0.007` | `1.122 ± 0.007` | `1.110 ± 0.007` | `0.068 ± 0.001` | `single_overshoot` | 标准口径 `0.015`；`overshoot_ratio ≈ 0.122`，`zero_crossing_count = 1`，较 `80/0.8` 进一步减小过冲 | **`best_air_candidate`** |
| `80/1.0` | `air` | `0.957 ± 0.002` | `1.226 ± 0.000` | `0.977 ± 0.002` | `0.063 ± 0.001` | `sustained_oscillation` | `step_amplitude_rad = 0.100`。补录大步长对照；`overshoot_ratio ≈ 0.226`，`zero_crossing_count = 2`，大步长下继续改善但仍未在 active 窗口内收敛 | `supplementary_large_step` |
| `80/1.0` | `ground` | `0.567 ± 0.164` | `0.624 ± 0.181` | `0.581 ± 0.170` | `0.047 ± 0.007` | `undershoot_soft` | `Round 2B`，`step_amplitude_rad = 0.015`。3 次全部 `undershoot_soft`；`degradation_ratio ≈ 0.531`；首次效应：iter1=0.756，iter2/3≈0.472；`zero_crossing_count=1` 但 `overshoot=0`（初始反向偏移，`actual_span=0.022760 > 0.015`）；`steady_error ≈ 0.01163`；`primary_peak_effort ≈ 2.37 Nm`；`coupled_peak_effort ≈ 3.02 Nm > primary`（四关节唯一） | `ground_severe_degradation_small_step` |
| `80/1.0` | `ground` | `0.757 ± 0.012` | `0.809 ± 0.018` | `0.777 ± 0.013` | `0.070 ± 0.004` | `undershoot_soft` | `Round 2B`，`step_amplitude_rad = 0.100`。**3 次全部仍为 `undershoot_soft`**——四关节中唯一在大步长下未恢复到 `well_damped_tracking`；`degradation_ratio ≈ 0.709`（仅恢复至 air 的 71%）；`zero_crossing_count=0`（0.015 rad 下的初始反向偏移在大幅值下消失）；`actual_span=0.091373 < 0.100`（关节峰值未超过命令幅值，其他三关节均超过）；timing 全部 good；`primary_peak_effort ≈ 11.74 Nm`，`coupled_peak_effort ≈ 6.12 ± 1.80 Nm`（方差大：iter2=8.19，iter1/3≈5 Nm），pitch 驱动器受力不稳定；large-step ground 仍持续欠跟踪，与其他三关节的接触阈值型恢复模式根本不同 | `ground_large_step_still_undershoot` |

### Right Roll 测试表

| `kp/kd` | 工况 | `tracking_ratio` | `peak_tracking_ratio` | `tail_tracking_ratio` | `peak_time_sec` | `response_class` | 备注 | 状态 |
|---|---|---:|---:|---:|---:|---|---|---|
| `35/0.5` | `air` | `1.106` | `1.184` | `1.146` | `—` | `sustained_oscillation` | `final_tracking_ratio ≈ 0.000`，明显欠阻尼 | `rejected` |
| `35/0.8` | `air` | `1.191` | `1.251` | `1.239` | `—` | `single_overshoot` | `final_tracking_ratio ≈ 0.010`，过冲后回落 | `rejected` |
| `35/1.0` | `air` | `1.190` | `1.255` | `1.236` | `—` | `single_overshoot` | `final_tracking_ratio ≈ 0.012`，不优于 `35/0.8` | `rejected` |
| `50/0.8` | `air` | `0.845` | `0.971` | `0.879` | `0.077` | `well_damped_tracking` | `rise_time_sec ≈ 0.047`，3 次重复一致；`overshoot_ratio = 0`，`zero_crossing_count = 0` | **`best_air_candidate`** |
| `50/0.8` | `ground` | `0.415 ± 0.111` | `0.617 ± 0.118` | `0.428 ± 0.114` | `0.061 ± 0.003` | `undershoot_soft` | `Round 2B`，`step_amplitude_rad = 0.015`。3 次全部 `undershoot_soft`；`degradation_ratio ≈ 0.49`；无振荡无过零，纯欠跟踪；`final_tracking_ratio ≈ 0.074`，active 窗口结束后关节几乎全部回弹；`primary_peak_effort ≈ 1.52 Nm`，力矩偏低；第 1 次 `0.543`，第 2/3 次降至 `~0.35`，存在首次效应；`coupled_motion ≈ -0.002`，耦合未放大 | `ground_severe_degradation_small_step` |
| `50/0.8` | `ground` | `0.832 ± 0.015` | `0.936 ± 0.013` | `0.856 ± 0.010` | `0.087 ± 0.012` | `well_damped_tracking` | `Round 2B`，`step_amplitude_rad = 0.100`。3 次全部 `well_damped_tracking`；无过冲无过零；3 次高度一致（无首次效应）；`primary_peak_effort ≈ 7.84 Nm`，力矩充足；`coupled_motion ≈ -0.002`，耦合未放大；与 0.015 rad ground 形成鲜明对比，揭示明显幅值依赖 | `ground_large_step_well_damped` |

### Right Pitch 测试表

| `kp/kd` | 工况 | `tracking_ratio` | `peak_tracking_ratio` | `tail_tracking_ratio` | `peak_time_sec` | `response_class` | 备注 | 状态 |
|---|---|---:|---:|---:|---:|---|---|---|
| `35/0.5` | `air` | `0.921` | `1.053` | `0.965` | `0.088` | `—` | `overshoot_ratio ≈ 0.053`，`rise_time_sec ≈ 0.048` | `pending_compare` |
| `30/0.5` | `air` | `0.879 ± 0.131` | `0.928 ± 0.133` | `0.928 ± 0.133` | `0.098 ± 0.013` | `well_damped_tracking / undershoot_soft / single_overshoot` | `Round 2D` 复测。3 次明显分裂：`0.876 / 0.750 / 1.012`；其中 1 次 `rise_time_status = too_slow_for_walking`，不再是稳定可用点 | `pending_recheck_split` |
| `40/0.5` | `air` | `1.098` | `1.149` | `—` | `—` | `single_overshoot` | 更接近目标幅值，但已进入轻度过冲区 | `reference` |
| `40/0.5` | `air` | `1.013 ± 0.011` | `1.401 ± 0.012` | `1.046 ± 0.012` | `0.078 ± 0.001` | `sustained_oscillation` | `step_amplitude_rad = 0.100`。补录大步长对照；`overshoot_ratio ≈ 0.401`，`zero_crossing_count = 3`，大步长下直接进入持续振荡 | `supplementary_large_step` |
| `40/0.8` | `air` | `0.931 ± 0.075` | `0.972 ± 0.077` | `0.972 ± 0.077` | `0.068 ± 0.000` | `well_damped_tracking / single_overshoot` | `Round 2D` 补测。3 次中 2 次 `well_damped_tracking`、1 次 `single_overshoot`；较 `40/0.5` 明显减小过冲，时间响应稳定 | **`best_air_candidate`** |
| `40/0.8` | `air` | `0.967 ± 0.000` | `1.202 ± 0.000` | `0.994 ± 0.000` | `0.082 ± 0.001` | `oscillatory_but_settling` | `step_amplitude_rad = 0.100`。补录大步长对照；`overshoot_ratio ≈ 0.202`，`zero_crossing_count = 2`，`settling_time_sec ≈ 0.206 ± 0.005`，相比 `40/0.5 @ 0.100` 明显更稳 | `supplementary_large_step` |
| `80/0.5` | `air` | `0.964 ± 0.075` | `1.500 ± 0.077` | `0.972 ± 0.077` | `0.058 ± 0.000` | `sustained_oscillation` | `Round 2D` 补测。`overshoot_ratio ≈ 0.500`，`zero_crossing_count = 2`；明确说明 `kd=0.5` 下继续抬 `kp` 会直接进欠阻尼区 | `rejected_oscillatory_high_kp` |
| `40/0.8` | `ground` | `0.554 ± 0.076` | `0.575 ± 0.077` | `0.575 ± 0.077` | `0.054 ± 0.001` | `undershoot_soft` | `Round 2B`，`step_amplitude_rad = 0.015`。3 次全部 `undershoot_soft`；`degradation_ratio ≈ 0.595`；无振荡无过零，纯欠跟踪；`primary_peak_effort ≈ 2.99 Nm`；iter1/2 约 `0.510`，iter3 升至 `0.641`（热身型）；`coupled_motion ≈ 0.003`，偏正方向小幅耦合 | `ground_severe_degradation_small_step` |
| `40/0.8` | `ground` | `0.815 ± 0.011` | `0.868 ± 0.012` | `0.848 ± 0.012` | `0.228 ± 0.105` | `well_damped_tracking` | `Round 2B`，`step_amplitude_rad = 0.100`。3 次全部 `well_damped_tracking`，无过冲无过零；`degradation_ratio ≈ 0.875`，tracking 大幅恢复，确认接触阈值效应；**但 `peak_time_status`：iter1 `good (0.107s)`，iter2/3 `unusable_for_walking (0.291/0.285s)`**，iter2/3 远超 walking 预算上限 `0.147s`，时序严重退化；`primary_peak_effort ≈ 17.73 Nm`，远高于 roll 方向的 `7.84 Nm`，说明 pitch 触地阻力更大；`coupled_motion ≈ 0.002`，耦合稳定；时序退化在 right roll `0.100 rad ground` 中未出现，属于 pitch 方向特有问题 | `ground_large_step_tracking_ok_but_timing_degraded` |

---

## 各关节 Round 2A 详细结论

### Left Pitch

- **air 最佳点**：`kp=80, kd=0.8`（`best_air_candidate`，air 结论不变）
- **air 选择原因**：
  - 主口径 `0.015 rad` 下，`tracking_ratio ≈ 1.025`，幅值最接近目标，3 次重复高度一致
  - 时间响应满足 walking 预算：`rise_time_sec ≈ 0.030`，`peak_time_sec ≈ 0.049`
  - `kd: 0.5→0.8` 显著改善，`kd: 0.8→1.0` 无额外收益
- **Round 2B ground 结果（0.015 rad）**：`tracking_ratio ≈ 0.641 ± 0.002`，`degradation_ratio ≈ 0.625` → 严重退化
- **与其他关节对比**：
  - 退化模式和 right roll / right pitch 完全一致：纯欠跟踪，无振荡，无过零
  - **关键差异：极度一致**——3 次 std 仅 `0.002`，是四关节中最低（right pitch `0.076`，right roll `0.111`），说明 left pitch 触地接触状态高度稳定，无首次效应或热身型分裂
  - `primary_peak_effort ≈ 7.03 Nm`（`kp=80` 驱动，但在 0.015 rad 小步长下仍不够克服触地阻力），对比 right pitch `2.99 Nm`（`kp=40`）
  - `peak_time_sec = 0.055 ± 0.001`，timing 全部 good——说明触地对响应速度没有明显影响，只是压制了幅值
- **Round 2B 完整结论（两条口径）**：
  - `0.015 rad ground`：严重欠跟踪（`0.641`），接触阈值效应，3 次极度一致
  - `0.100 rad ground`：tracking 恢复（`0.880`），timing 全部 good，但**响应类型改善型分裂**（iter1 sustained → iter2 single → iter3 well_damped）
- **与其他关节的横向对比**：
  - right roll（kp=50）：大步长下干净恢复，无振荡分裂，`effort ≈ 7.84 Nm` → Round 2C 找临界幅值
  - right pitch（kp=40）：大步长下 timing 退化（peak_time unusable×2），`effort ≈ 17.73 Nm` → Round 2C 提升 kp
  - left pitch（kp=80）：大步长下 timing good，但振荡分裂，`effort ≈ 37.13 Nm` → Round 2C 方向特殊
- **振荡分裂的机制**：
  - iter1 → iter3 的改善型分裂，说明接触面在多次激励后状态变化（可能是接触点沉降、等效刚度改变）
  - `kp=80` 在 0.100 rad 触地下产生 37 Nm，已经是相当大的力矩，略高于临界阻尼需要的 `kd`
  - air 下 80/0.8 @ 0.100 rad 已是 `oscillatory_but_settling`，触地后等效刚度改变进一步压低了阻尼比
  - **在 air 下提升 kd（0.8→1.0）没有改善 0.015 rad 的空载响应，但触地大步长下可能有效**
- **Round 2C 方向（left pitch 特有）**：
  - kp=80 不变（timing 已经 good，不需要提升速度）
  - 需要在 ground 下测试更高 kd（`1.0`、`1.2`），看能否消除大步长振荡分裂
  - 注意 `actual_span = 0.127` 超过命令幅值，测试时需监控机构安全边界
  - 若 ground @ 0.100 rad + kd=1.0 改善为稳定 single_overshoot 或 well_damped，则 left pitch Round 2C 收口
  - 若不改善，再考虑查接触耦合或 lpf_conf.wc

### Left Roll

- **air 最佳点**：`kp=80, kd=1.0`（`best_air_candidate`，air 结论不变）
- **air 选择原因**：标准口径与大步长口径下沿 `kd` 支路均持续优于 `80/0.5` 和 `80/0.8`，`overshoot_ratio` 逐步从 `0.197→0.158→0.122`；螺栓松动污染已排除
- **Round 2B ground 结果（0.015 rad）**：`tracking_ratio ≈ 0.567 ± 0.164`，`degradation_ratio ≈ 0.531` → 严重退化
- **独有特征（与其他三关节的差异）**：
  - **`zero_crossing=1` 但 `overshoot=0`**：关节在触地激励下先向命令反方向偏移再正向运动，`actual_span=0.022760 > 0.015`。可能是并联机构触地接触几何导致：触地反力先把 roll 关节向反方向顶出
  - **`coupled_peak_effort (3.02 Nm) > primary_peak_effort (2.37 Nm)`**：四关节中唯一。left roll 被激励时反力路径主要经由 pitch 执行器，说明触地时接触力矩主要由 pitch 驱动器承担，存在 pitch 驱动器过载风险
  - **首次效应**：iter1 tracking=0.756，iter2/3≈0.472，分裂明显
  - **`steady_error ≈ 0.01163`（3 次几乎完全相同）**：系统性触地跟踪偏置，与 left pitch 的 steady_error 高度一致性一样，触地工况下存在稳定的偏差
- **Round 2B 完整结论（两条口径）**：
  - `0.015 rad ground`：`tracking=0.567`，`degradation=0.531`，初始反向偏移，`coupled_effort > primary`
  - `0.100 rad ground`：`tracking=0.757`，仍为 `undershoot_soft` ×3，仅部分恢复——**四关节中唯一大步长下未恢复到 `well_damped_tracking` 的关节**
- **与其他三关节的本质区别**：
  - right roll / right pitch / left pitch 在 0.100 rad ground 下均恢复到 `well_damped_tracking`，属于接触阈值效应（越过阈值后正常）
  - left roll 大步长下仍持续欠跟踪，说明存在更根本的限制，不是纯阈值效应
- **可能的根本原因**：
  - `actual_span=0.091 < 0.100`：其他三关节大步长 actual_span 均超过命令，left roll 连峰值都没达到命令幅值——接触约束对 roll 方向的等效阻力在全幅值范围内持续存在
  - kp=80 已是 right roll kp=50 的 1.6 倍，但触地跟踪（`0.757`）仍低于 right roll（`0.832`）——kp 并非制约主因，更可能是左踝 roll 方向接触几何或硬件特性
  - 0.015 rad 时 `coupled > primary`，0.100 rad 时 `primary > coupled`（`11.74 vs 6.12`），两条口径力矩比例反转——接触几何在不同幅值下非线性变化
  - `coupled_peak_effort` 方差大（iter2=8.19，iter1/3≈5 Nm）：pitch 驱动器受力不稳定，接触条件不一致
- **Round 2C 方向（left roll 最复杂）**：
  - **不建议盲目提升 kp**：kp=80 下已达 11.74 Nm，继续上调可能引入振荡且不一定改善跟踪
  - **优先排查硬件/接触几何**：检查左踝并联机构的杆长、预紧状态；检查左脚接触面几何是否与右脚存在明显差异
  - **备选参数方向**：若硬件确认无异常，可尝试 `kp=90~100, kd=1.2` 在 air 下验证稳定性，再测 ground
  - **可接受性评估**：walking 中 roll 方向实际命令幅值若主要在 `0.030~0.050 rad`，`tracking ≈ 0.757` 是否已足够——最终需要 Round 3 步态验证

### Right Roll

- **air 最佳点**：`kp=50, kd=0.8`（`best_air_candidate`，air 结论不变）
- **Round 2B ground 结果（两条口径）**：
  - `0.015 rad ground`：`tracking_ratio ≈ 0.415 ± 0.111`，`degradation_ratio ≈ 0.49`，`undershoot_soft`
  - `0.100 rad ground`：`tracking_ratio ≈ 0.832 ± 0.015`，`degradation_ratio ≈ 0.984`，`well_damped_tracking`
- **关键现象：强幅值依赖**
  - 小步长（`0.015 rad`）触地时：`primary_peak_effort ≈ 1.52 Nm`，跟踪率掉至 `0.415`，且有首次效应（iter1 `0.543`，iter2/3 `~0.35`）
  - 大步长（`0.100 rad`）触地时：`primary_peak_effort ≈ 7.84 Nm`，跟踪率 `0.832`，3 次高度一致，无首次效应
  - 力矩比例：`7.84 / 1.52 ≈ 5.2x`；幅值比例：`0.100 / 0.015 ≈ 6.7x`——力矩增长略低于线性，说明接触存在非线性阈值
- **退化根因修正：接触阈值 / 静摩擦效应，而非 kp 整体不足**
  - `kp=50` 在 `0.015 rad` 下产生的力矩（`~1.5 Nm`）不足以克服接触约束的静摩擦/初始阈值
  - 一旦幅值足以产生足够力矩（`~7.8 Nm`），响应恢复为 `well_damped_tracking`，与 air 几乎一致
  - 问题的本质是**接触非线性阈值**，而不是 `kp` 全局偏小
- **Round 2C 方向修正**：
  - 不应立即跳到"大幅提升 kp"——大步长下 `kp=50` 已经足够
  - 核心问题是：**walking 期间 right roll 的实际命令幅值是否能持续超过接触阈值？**
  - 若 RL walking 策略对 right roll 的命令幅值主要集中在 `≥ 0.03~0.05 rad`，则 `kp=50` 可能直接可用
  - 若 walking 中 right roll 主要做小幅修正（`< 0.02 rad`），则仍需要提升 kp
  - **建议下一步**：先补测 `0.030 rad` 和 `0.050 rad` 的触地阶跃，找到接触阈值的临界幅值，再决定是否提升 kp
- **保留问题**：
  - 小幅值触地跟踪不足，行走中小幅修正能力存疑
  - 大幅值触地表现良好，结构上没有根本性问题
  - `final_tracking_ratio ≈ 0.012`（0.100 rad 工况），active 窗口结束后关节仍会回弹（接触下无持续保持力矩），走路时持续命令可覆盖此现象

### Right Pitch

- **air 最佳点**：`kp=40, kd=0.8`（`best_air_candidate`，air 结论不变）
- **Round 2B ground 结果（0.015 rad）**：`tracking_ratio ≈ 0.554 ± 0.076`，`degradation_ratio ≈ 0.595` → 严重退化
- **与 right roll 的对比**：
  - 退化模式高度相似：小步长 ground 下纯欠跟踪，无振荡，无过零
  - `primary_peak_effort ≈ 2.99 Nm`（right roll 是 `1.52 Nm`），pitch 产生的力矩更高，但仍有严重欠跟踪
  - right roll 在 `0.100 rad ground` 下完全恢复（`tracking ≈ 0.832`），表明该类退化可能是接触阈值效应
  - right pitch 此前 `40/0.8 @ 0.100 rad air` 已测（`tracking ≈ 0.967`，`oscillatory_but_settling`）；**缺少 `0.100 rad ground` 数据**，需要补测才能确认是否同为接触阈值型
- **两者关键差异**：
  - right pitch 的 iter3 反而最好（`0.641`，热身型），right roll 是 iter1 最好（首次效应型）
  - 热身型可能说明 pitch 方向的接触界面在多次激励后逐渐"磨开"，与 roll 方向的接触界面沉降机制不同
  - `coupled_motion ≈ +0.003`（pitch 激励时 roll 有正方向运动），与 roll 激励时 pitch 耦合方向（负）相反——并联踝两方向的耦合方向不对称，符合预期
- **Round 2B 完整结论（两条口径）**：
  - `0.015 rad ground`：严重欠跟踪（`0.554`），接触阈值效应确认（与 right roll 同类）
  - `0.100 rad ground`：tracking 恢复（`0.815`），但出现**时序退化**——iter2/3 的 `peak_time = 0.285~0.291 sec`（`unusable_for_walking`），超出 walking 预算近一倍
- **与 right roll 的本质区别**：
  - right roll：接触阈值效应，大步长下 tracking 和 timing 都恢复正常 → Round 2C 只需找临界幅值
  - right pitch：接触阈值效应相同，但大步长下 **timing 没有恢复**，iter2/3 严重偏慢 → kp=40 在 pitch 触地工况下驱动力不足，不只是跨阈值问题
- **`peak_time` 分裂机制分析**：
  - iter1 `peak_time = 0.107 sec`（good）：第一次激励时地面接触状态"新鲜"，响应尚快
  - iter2/3 `peak_time = 0.285~0.291 sec`（unusable）：多次激励后接触面状态改变（压实/变形），pitch 方向等效接触刚度升高，`kp=40` 已无法在 walking 时序内驱动关节到达目标
  - `primary_peak_effort ≈ 17.73 Nm`（pitch）vs `7.84 Nm`（roll）：pitch 触地时关节承受的等效阻力是 roll 的 2.3 倍，说明接触几何对 pitch 方向的约束更强
- **Round 2C 方向（pitch 比 roll 更复杂）**：
  - 不能只靠找临界幅值解决，需要提升 kp 来同时改善 tracking rate 和响应速度
  - 在 air 下探索更高 kp（`kp=50~60`）配合更高 kd（`1.0~1.2`），找到 air 稳定且响应更快的新基准点
  - 再测 ground，观察 `peak_time` 是否能恢复至 `good` 状态
  - 目标：ground 工况下 `peak_time_status` 至少 iter1/2/3 中有 2 次 `good`

---

## Round 2B 横向总结

### 测试背景：双脚触地 + 并联踝结构

当前 Round 2B 的所有 ground 测试均在**双脚同时触地、机器人静止站立**工况下进行。这比实际行走工况更保守：

| 测试工况 | 接触状态 | 约束强度 | 对应场景 |
|---|---|---|---|
| Round 2B（当前）| 双脚触地，静止 | **最高**：双侧约束，全重压脚，无惯性辅助 | 静态辨识 |
| 实际行走（目标） | 主要单脚支撑，动态 | **较低**：单侧约束，动态接触，惯性可辅助 | 步态运行 |

此外，并联踝结构使得 pitch 和 roll 两个自由度的接触反力路径相互耦合。Round 2B 数据中可以观察到：
- 激励 roll 时，pitch 执行器的反力（`coupled_peak_effort`）有时超过主轴（left roll @ 0.015 rad ground 唯一出现）
- 各关节的 `steady_error` 在触地工况下呈现高度一致的系统性偏置（并非随机误差，而是接触力与 PD 控制的稳态博弈）
- 双脚静态接触下的"接触阈值"在单脚动态行走中将因单侧负载减半和惯性助力而显著降低

**实践意义：Round 2B 数据揭示的退化量，是触地工况下的上界估计。实际行走中的退化将明显小于 Round 2B 测试结果。**

### 四关节 Round 2B 完整汇总

| 关节 | `kp/kd` | `0.015rad ground` | `0.100rad ground` | 退化类型 | Round 2C 优先动作 |
|---|---|---|---|---|---|
| `right_ankle_roll_joint` | `50/0.8` | `0.415`，severe | `0.832`，well_damped ✓ | 接触阈值型，完全恢复 | 补测中间幅值（0.030/0.050 rad），评估 walking 可用性 |
| `right_ankle_pitch_joint` | `40/0.8` | `0.554`，severe | `0.815`，tracking ok 但 timing ×2 unusable | 接触阈值 + timing 退化 | **提升 kp（50→60），修复 timing** |
| `left_ankle_pitch_joint` | `80/0.8` | `0.641`，severe | `0.880`，振荡分裂（sustained→single→well） | 接触阈值 + 振荡分裂 | ground 下提升 kd（0.8→1.0/1.2），消除分裂 |
| `left_ankle_roll_joint` | `80/1.0` | `0.567`，severe | `0.757`，仍 undershoot ✗ | 非纯阈值，结构性约束 | 排查硬件/接触几何，再决定参数方向 |

### 各关节 Round 2C 进入优先级

1. **right pitch**（最高）：timing 退化是走路时序的直接威胁，必须修复后才能安全进入 Round 3
2. **left pitch**（高）：振荡分裂在 kd=0.8 下出现，kd=1.0 的 ground 验证是一次测试的事
3. **right roll**（中）：技术上已可接受，补测中间幅值确认阈值后可直接进 Round 3
4. **left roll**（观察）：先排查硬件，但不应作为 Round 3 的硬性阻塞条件——walking 中的单脚支撑可能使 0.757 的跟踪率已足够
