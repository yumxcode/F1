# Round 2C 触地退化修复执行单

状态：`ready to run`。本轮基于 Round 2B 完整结论，针对各关节触地退化的不同根因，执行定向修复测试。

## 背景说明

Round 2B 测试条件为**双脚同时触地、机器人静止站立**，是比实际动态任务更保守的约束工况：
- 实际动态任务以单脚支撑为主，双脚触地仅在换步瞬间（约占动态任务周期 20%）
- 单脚支撑时接触约束减半，动态惯性可辅助踝关节运动
- 因此 Round 2B 的退化量是上界估计，不代表动态任务时的真实退化

并联踝结构使得 pitch/roll 接触反力路径耦合，需要在修复时分别评估主轴和耦合轴的力矩分配。

## 四关节退化分类与本轮目标

| 关节 | 退化类型 | 本轮目标 | 对后续控制验证影响 |
|---|---|---|---|
| `right_ankle_roll_joint` | 接触阈值型，大步长完全恢复 | 补测中间幅值，确认可用范围 | **否**，当前参数在阶跃辨识中不构成继续修复阻塞 |
| `right_ankle_pitch_joint` | 接触阈值 + timing 退化 | 提升 kp，修复 timing | **是**，timing 未满足目标响应时序 |
| `left_ankle_pitch_joint` | 接触阈值 + 振荡分裂 | 提升 kd（ground 侧），消除分裂 | **条件是**，mild split 可进行，需确认 |
| `left_ankle_roll_joint` | 非纯阈值，结构性约束 | 排查硬件，评估是否能改善 | **否**，需结合硬件复核后判断 |

---

## 本轮边界

Round 2C 只负责阶跃辨识内的单轴问题修复：

- `right pitch`：触地 timing 退化。
- `left pitch`：触地大步长振荡分裂。
- `right roll`：接触阈值 / 小幅值欠跟踪。
- `left roll`：硬件或几何约束导致的持续欠跟踪。

本文件不讨论任何具体动态任务故障，也不把是否进入后续控制验证作为本轮完成条件。Round 2C 的输出只包括：新增测试点、阶跃响应指标、参数是否在 air/ground 两类工况下满足辨识判据。

---

## 任务 A：right roll 中间幅值阈值确认

**目标**：确认 `kp=50, kd=0.8` 在 ground 下的临界幅值（从 0.015 rad 严重退化到 0.100 rad 完全恢复之间的转折点）

**背景**：0.100 rad ground 已是 `well_damped_tracking`（tracking=0.832），说明大幅值无问题；关键是中间幅值是否已经越过接触阈值。

**测试序列**（ground，kp=50，kd=0.8）：

| 序号 | 幅值 | CSV 文件名 | 目标 |
|---|---|---|---|
| A-1 | `0.030 rad` | `./log/right_roll_step_ground_kp50_kd0.8_r2c_0030.csv` | 是否已脱离 undershoot |
| A-2 | `0.050 rad` | `./log/right_roll_step_ground_kp50_kd0.8_r2c_0050.csv` | 进一步确认恢复趋势 |

```bash
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side right --axis roll --mode step --contact ground --tag r2c --kp 50 --kd 0.8
# 手动改 step_amplitude_rad = 0.030 测一次，再改 0.050 测一次
```

**判断规则**：
- 若 `0.030 rad ground` 已达 `tracking > 0.70`：临界幅值在 0.015~0.030 之间
- 若 `0.030 rad ground` 仍严重欠跟踪（`< 0.60`）：临界幅值更高，需重新评估或提升 kp

**完成后**：记录 right roll 的触地临界幅值区间，并决定是否需要继续提升 `kp`。

---

## 任务 B：right pitch 提升 kp（timing 修复）

**目标**：找到 ground 工况下 `peak_time_status` 全部 good 的新参数点

**背景**：kp=40 在 0.100 rad ground 下 iter2/3 的 `peak_time = 0.285~0.291 sec`（`unusable_for_dynamic_response`），根因是 pitch 方向触地阻力大（`17.73 Nm`），kp=40 驱动力不足以在目标响应时序内完成响应。

**步骤 1：air 下确认新 kp 稳定性**

| 序号 | 参数 | CSV | 判据 |
|---|---|---|---|
| B-1 | `kp=50, kd=1.0`（air） | `./log/right_pitch_step_air_kp50_kd1.0_r2c.csv` | tracking > 0.85，peak_time good，无 sustained_oscillation |
| B-2 | `kp=60, kd=1.0`（air） | `./log/right_pitch_step_air_kp60_kd1.0_r2c.csv` | 同上，若 B-1 幅值仍偏软 |
| B-3 | `kp=50, kd=1.2`（air） | `./log/right_pitch_step_air_kp50_kd1.2_r2c.csv` | 若 B-1 出现过冲偏大 |

```bash
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side right --axis pitch --mode step --contact air --tag r2c --kp 50 --kd 1.0
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side right --axis pitch --mode step --contact air --tag r2c --kp 60 --kd 1.0
```

**步骤 2：ground 验证（0.100 rad）**

air 稳定后，立即测同点 ground @ 0.100 rad，重点看 `peak_time_status`：
- 目标：3 次中至少 2 次 `peak_time_status = good`
- 若只有 1 次 good：换更高 kp 或 kd 继续

```bash
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side right --axis pitch --mode step --contact ground --tag r2c --kp 50 --kd 1.0
# step_amplitude_rad = 0.100
```

**收口条件**：ground @ 0.100 rad 下 `peak_time_status` 至少 2/3 次 good，`tracking > 0.80`，无 sustained_oscillation。

---

## 任务 C：left pitch 提升 kd（振荡分裂修复）

**目标**：在 ground 大步长下消除振荡分裂（iter1 sustained → 全部 single_overshoot 或 well_damped）

**背景**：kp=80, kd=0.8 在 0.100 rad ground 下出现振荡分裂（iter1 sustained_oscillation，decay_ratio=1），根因是触地等效刚度使系统略低于临界阻尼，kd=0.8 不够。air 下 kd=1.0 没有改善空载 0.015 rad，但触地大步长下可能有效。

**注意**：`actual_span = 0.127`（超过命令 0.100 rad），测试时严格监控机构行程安全。

| 序号 | 参数 | 工况 | CSV | 判据 |
|---|---|---|---|---|
| C-1 | `kp=80, kd=1.0` | ground @ 0.100 rad | `./log/left_pitch_step_ground_kp80_kd1.0_r2c.csv` | 3 次 response_class 不含 sustained_oscillation |
| C-2 | `kp=80, kd=1.2` | ground @ 0.100 rad | `./log/left_pitch_step_ground_kp80_kd1.2_r2c.csv` | 若 C-1 仍有分裂 |

```bash
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact ground --tag r2c --kp 80 --kd 1.0
# step_amplitude_rad = 0.100，严格观察实际位移是否超限
```

**收口条件**：3 次 response_class 均为 `single_overshoot` 或 `well_damped_tracking`，tracking > 0.85，timing good。

---

## 任务 D：left roll 硬件排查 + 参数评估

**目标**：判断 left roll 大步长 ground 仍为 undershoot（tracking=0.757）的根因是硬件/几何问题还是参数问题

**背景**：kp=80（高于 right roll 的 kp=50），但触地跟踪反而更差（0.757 vs 0.832）；并且大步长下 0.100 rad actual_span=0.091 < command（其余三关节均超过命令）；coupled_peak_effort 方差大。

**步骤 1：硬件检查（优先）**

- 对比左右踝并联机构：杆长是否等长、预紧力是否对称、接触面是否一致
- 检查左踝 roll 方向有无明显卡滞、磨损或装配偏差
- 若发现异常：处理后重新测 air baseline（kp=80, kd=1.0 @ 0.015 rad air），与历史数据对比

**步骤 2：若硬件正常，测 air 更高 kp**

| 序号 | 参数 | 工况 | 判据 |
|---|---|---|---|
| D-1 | `kp=90, kd=1.2`（air） | air @ 0.015 rad | tracking > 0.90，无 sustained_oscillation |
| D-2 | `kp=100, kd=1.2`（air） | air @ 0.015 rad | 若 D-1 幅值仍偏软 |

若 air 新点稳定，做同点 ground @ 0.100 rad，观察 tracking 是否突破 0.80。

**步骤 3：可接受性评估**

若 D 任务无法改善到 tracking > 0.80，则记录 `kp=80, kd=1.0` 为“触地约束下仍欠跟踪”的当前边界点，并停止在无硬件复核的情况下继续盲目加 `kp`。

---

## 执行顺序建议

```
任务 A（right roll 中间幅值）→ 确认触地临界幅值
任务 C（left pitch kd 提升）→ 一次测试即可收口
任务 B（right pitch kp 提升）→ 需要 air + ground 两步，较关键
任务 D（left roll 硬件排查）→ 最后或并行处理
```

**Round 2C 收口条件**：

- 任务 A 得到 right roll 的触地临界幅值区间。
- 任务 B 得到 right pitch 的可用 air 点，并在 ground @ 0.100 rad 下至少 2/3 次 `peak_time_status = good`。
- 任务 C 将 left pitch 的 ground 大步长响应收敛到无 sustained oscillation。
- 任务 D 完成硬件/几何排查结论，或明确记录 left roll 当前参数边界。

## 本轮结束后必须更新

- 将各任务结果补录到 [result_5.14.md](/Users/yumx/code/X1/agibot_x1_infer/sim2real/ankle_step_response/results/result_5.14.md) 的各关节测试表
- 更新本目录 README 的当前结果说明
