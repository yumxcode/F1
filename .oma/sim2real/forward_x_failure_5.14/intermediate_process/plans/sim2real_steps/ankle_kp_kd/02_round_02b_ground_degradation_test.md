# Round 2B 完全触地退化测量执行单

状态：✅ `completed`。四个关节的双口径触地退化测量已全部完成。详细结论与 Round 2C 动作见本文档下方，汇总见 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md)。

## 背景与目标

- `Round 2A` 已正式结束，各关节当前最佳 air 点已确认（见下表）。
- 此前历史 `ground` 数据已全部废除，原因是测试口径存在误差，不能作为退化量基线。
- 本轮目标：对四个关节统一做完全触地阶跃测试，输出 `ground_tracking_ratio`、`degradation_ratio`、`ground_response_class`，判断触地是否引入显著退化。
- 本轮不引入任何新 `kp/kd` 参数，只测当前 best_air_candidate 在触地工况下的响应。

## 测试对象

| 关节 | best_air_candidate | air 指标（参考） |
|---|---|---|
| `left_ankle_pitch_joint` | `kp=80, kd=0.8` | `tracking_ratio ≈ 1.025`，`response_class = single_overshoot` |
| `left_ankle_roll_joint` | `kp=80, kd=1.0` | `tracking_ratio ≈ 1.067`，`response_class = single_overshoot` |
| `right_ankle_roll_joint` | `kp=50, kd=0.8` | `tracking_ratio ≈ 0.845`，`response_class = well_damped_tracking` |
| `right_ankle_pitch_joint` | `kp=40, kd=0.8` | `tracking_ratio ≈ 0.931`，`response_class = well_damped/single_overshoot` |

## 固定测试口径

与 Round 2A 完全一致，避免引入口径误差：

- `mode = step`
- `step_amplitude_rad = 0.015`
- `active_sec = 1.0`
- `repeat_count = 3`
- `publish_rate_hz = 1000`
- 工况：完全触地（脚掌稳定接地，吊保护）

## 推荐执行顺序

| 序号 | 关节 | kp/kd | 推荐 CSV 文件名 |
|---|---|---|---|
| 1 | `right_ankle_roll_joint` | `50/0.8` | `./log/right_roll_step_ground_kp50_kd0.8_r2b.csv` |
| 2 | `right_ankle_pitch_joint` | `40/0.8` | `./log/right_pitch_step_ground_kp40_kd0.8_r2b.csv` |
| 3 | `left_ankle_pitch_joint` | `80/0.8` | `./log/left_pitch_step_ground_kp80_kd0.8_r2b.csv` |
| 4 | `left_ankle_roll_joint` | `80/1.0` | `./log/left_roll_step_ground_kp80_kd1.0_r2b.csv` |

排序理由：
- 右侧 right roll `50/0.8` 在 air 下已是 `well_damped_tracking`，先测可快速建立退化量参考基线。
- left 两轴幅值/阻尼更复杂，放后面便于根据前两条及时修正判因预期。

## 配置切换命令

```bash
python3 .oma/sim2real/set_ankle_identifier_config.py --side right --axis roll --mode step --contact ground --tag r2b --kp 50 --kd 0.8
# build && run_identifier.sh && analyze CSV

python3 .oma/sim2real/set_ankle_identifier_config.py --side right --axis pitch --mode step --contact ground --tag r2b --kp 40 --kd 0.8
# build && run_identifier.sh && analyze CSV

python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact ground --tag r2b --kp 80 --kd 0.8
# build && run_identifier.sh && analyze CSV

python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis roll --mode step --contact ground --tag r2b --kp 80 --kd 1.0
# build && run_identifier.sh && analyze CSV
```

## 每条测试执行模板

每跑完一条，立即分析，再执行下一条：

1. 确认 `ankle_identifier.yaml` 的 `test_side / test_axis / test_kp / test_kd / csv_path / contact = ground` 与目标一致
2. 实验室电脑执行 `./build.sh`（若已编译可跳过，只需确认配置已同步）
3. 进入 `build/` 执行 `./run_identifier.sh`
4. 确认只有辨识链路在发布 `/joint_cmd`，无其他控制节点干扰
5. 完成 3 次 step，等待 CSV 生成
6. 立即运行分析脚本

```bash
python3 .oma/sim2real/analyze_ankle_identifier_csv.py build/log/<csv_name>.csv
```

立即终止该关节 ground 测试的条件：
- 出现明显异响或高频抖动放大
- `response_class = sustained_oscillation` 且振荡明显
- 人工观察姿态不可控或脚掌明显拍打地面

## 必须输出的指标

每个 CSV 都需要记录以下指标，用于计算退化量：

| 指标 | 用途 |
|---|---|
| `tracking_ratio` | 触地跟踪率主指标 |
| `tail_tracking_ratio` | 尾段跟踪质量 |
| `peak_tracking_ratio` | 峰值评估 |
| `peak_time_sec` | 时间响应对比 |
| `zero_crossing_count` | 触地是否新增振荡 |
| `response_class` | 整体响应类型 |
| `coupled_motion` | 触地是否放大耦合 |

## 退化量计算

> **Round 2B 已完成，全部退化量数据已记录到**：
> [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md) — Round 2B 横向总结一节。
>
> 本执行单不再重复内嵌测量数值，以防与结果文件不一致。

`degradation_ratio = ground_tracking_ratio / air_tracking_ratio`

## 判断规则

### 退化可接受 → 进入 Round 3

满足全部：
- `degradation_ratio ≥ 0.85`（ground 跟踪率不低于 air 的 85%）
- `ground_response_class` 未出现新的持续振荡（`sustained_oscillation`）
- `coupled_motion` 未显著放大

下一步：直接进入 `Round 3 low_speed_walk`，使用当前 best_air_candidate 参数。

### 退化较大但可控 → 进入 Round 2C

满足任一：
- `degradation_ratio` 在 `0.70 ~ 0.85` 之间
- `ground_response_class` 新出现轻度振荡但仍可收敛

下一步：进入 `Round 2C`，优先查接触耦合、`kd` 邻域微调、`lpf_conf.wc`。

### 退化严重或新增不稳定 → 返回调参

满足任一：
- `degradation_ratio < 0.70`
- `ground` 下出现 `sustained_oscillation`
- 触地后出现明显异响、耦合放大、拍地

下一步：暂停该关节进入步态，回到 `kd` 或接触耦合分析，不进入 `Round 3`。

## 本轮结束条件

- 四个关节都完成完全触地阶跃测试（各 3 次 repeat）
- 每个关节都输出 `degradation_ratio` 和 `ground_response_class`
- 每个关节都写出 `next_action`
- 结果补录到 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md) 的各关节测试表
- 更新 [sim2real_checklist.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real_checklist.md) 的 `Round 2` 状态
- 若所有关节退化均可接受，将 `Round 2` 标记为 `completed`，允许进入 `Round 3`
