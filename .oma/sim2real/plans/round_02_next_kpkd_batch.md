# Round 2 下一批 Kp/Kd 测试执行单

状态：`ready to run`。本批次仍属于 `Round 2`，目标是补齐悬空证据，不进入步态验证。

当前源码配置已切到第 1 条待测点：
- `left pitch`
- `air`
- `kp=100, kd=0.8`
- `csv_path=./log/left_pitch_step_air_kp100_kd0.8_r2a.csv`

## 本批目标

- 补齐左脚两轴的悬空对照，判断左脚触地下的“偏软欠跟踪”到底是单纯 `kp` 偏低，还是悬空下已经存在阻尼问题。
- 为 `right_ankle_pitch_joint` 补 `kp=100, kd=0.8` 的悬空对照，验证它是否真的是“触地下暂时最接近可用”的候选。
- 所有结论继续使用同一判据：
  - `tracking_ratio`
  - `response_class`
  - `peak_time_sec`
  - `zero_crossing_count`
  - `coupled_motion`

## 执行顺序

1. `left_ankle_pitch_joint` 悬空：`kp=100, kd=0.8`
2. `left_ankle_pitch_joint` 悬空：`kp=105, kd=0.8`
3. `left_ankle_roll_joint` 悬空：`kp=80, kd=0.8`
4. `left_ankle_roll_joint` 悬空：`kp=70, kd=0.8`
5. `right_ankle_pitch_joint` 悬空：`kp=100, kd=0.8`

说明：
- 先测每个自由度在触地下相对较优或接近相对较优的点，不在这一批里继续扩展新的大扫。
- 若前一条就出现明显持续振荡、强过零或异常耦合，立即停止该自由度后续点位，并在结果里记录为“该支路需改 `kd` 或看接触耦合”。
- 每跑完一条，立即分析 CSV，再决定是否继续同一自由度的下一条，避免把明显错误支路整批跑完。

## 现场单条执行模板

每条测试都按以下顺序执行：

1. 本地或实验室电脑切配置
2. 确认 `ankle_identifier.yaml` 的 `test_side / test_axis / test_kp / test_kd / csv_path` 与目标一致
3. 实验室电脑执行 `./build.sh`
4. 进入 `build/` 执行 `./run_identifier.sh`
5. 等待测试自动结束并生成 CSV
6. 立刻运行分析脚本
7. 记录是否满足继续条件

继续条件：
- `signal_path_status = ok`
- 没有明显异响、持续振荡、异常耦合
- `tracking_ratio` 至少能支持当前自由度继续比较

立即停该支路条件：
- `response_class = sustained_oscillation`
- 或 `zero_crossing_count > 1`
- 或人工观察到明显异响、抖动放大、姿态不可控

## 每条测试的推荐命名

| 序号 | 测试项 | 推荐 CSV 文件名 |
|---|---|---|
| 1 | `left pitch air 100/0.8` | `./log/left_pitch_step_air_kp100_kd0.8_r2a.csv` |
| 2 | `left pitch air 105/0.8` | `./log/left_pitch_step_air_kp105_kd0.8_r2a.csv` |
| 3 | `left roll air 80/0.8` | `./log/left_roll_step_air_kp80_kd0.8_r2a.csv` |
| 4 | `left roll air 70/0.8` | `./log/left_roll_step_air_kp70_kd0.8_r2a.csv` |
| 5 | `right pitch air 100/0.8` | `./log/right_pitch_step_air_kp100_kd0.8_r2a.csv` |

## 本地切配置命令

```bash
python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact air --tag r2a --kp 100 --kd 0.8
python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact air --tag r2a --kp 105 --kd 0.8
python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis roll --mode step --contact air --tag r2a --kp 80 --kd 0.8
python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis roll --mode step --contact air --tag r2a --kp 70 --kd 0.8
python3 .oma/sim2real/set_ankle_identifier_config.py --side right --axis pitch --mode step --contact air --tag r2a --kp 100 --kd 0.8
```

推荐实际执行顺序：

```bash
python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact air --tag r2a --kp 100 --kd 0.8
# build && run_identifier.sh && analyze CSV
python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact air --tag r2a --kp 105 --kd 0.8
# build && run_identifier.sh && analyze CSV
python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis roll --mode step --contact air --tag r2a --kp 80 --kd 0.8
# build && run_identifier.sh && analyze CSV
python3 .oma/sim2real/set_ankle_identifier_config.py --side left --axis roll --mode step --contact air --tag r2a --kp 70 --kd 0.8
# build && run_identifier.sh && analyze CSV
python3 .oma/sim2real/set_ankle_identifier_config.py --side right --axis pitch --mode step --contact air --tag r2a --kp 100 --kd 0.8
# build && run_identifier.sh && analyze CSV
```

## 实验室执行模板

每切一次参数，重复以下流程：

1. 实验室电脑 `git pull`
2. 如配置文件已改动且需要重编译，则执行 `./build.sh`
3. 进入 `build/` 执行 `./run_identifier.sh`
4. 确认只有辨识链路在发布 `/joint_cmd`
5. 完成该点测试并保存 CSV
6. 用分析脚本输出汇总指标

分析命令模板：

```bash
python3 .oma/sim2real/analyze_ankle_identifier_csv.py build/log/<csv_name>.csv
```

## 这批的判定规则

- `left pitch`
  - 若 `100/0.8` 与 `105/0.8` 在悬空下都仍 `tracking_ratio < 0.8`，优先判断为“左 pitch 不只是接触问题，还需要继续上扫 `kp`”
  - 若 `100/0.8` 已出现明显过冲或振荡，不继续直接上 `105/0.8`，先转 `kd` 支路
  - 若悬空接近 `1.0` 而触地下仅 `0.6` 左右，优先判断为“接触下等效刚度/耦合问题”
- `left roll`
  - 若悬空下已过冲或振荡，而触地下偏软，说明与 `right roll` 一样存在工况分裂，应优先转向 `kd` 或耦合分析
  - 若悬空和触地都持续偏软，则下一批优先上扫 `kp`
- `right pitch`
  - 若 `100/0.8` 悬空下 `tracking_ratio` 接近 `1.0` 且无明显振荡，它才有资格保留为部署候选
- 若 `100/0.8` 悬空下仍显著偏软或振荡，则 `right pitch` 触地侧的“相对较优”判断要降级

## 本批结束后的收口动作

- 将 5 条 CSV 分析结果增补到 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_02_ankle_kp_kd_identification.md:1)
- 在 [sim2real_checklist.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real_checklist.md:1) 更新 `Round 2` 是否仍 `in progress`
- 为四个自由度分别写出下一动作：
  - `continue_kp_scan`
  - `switch_kd_scan`
  - `investigate_contact_or_lpf`
- 只有这三项都完成，才允许判断 `Round 2` 是否可以关闭

## 本批结束后必须更新

- 更新 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_02_ankle_kp_kd_identification.md:1)
- 更新 [sim2real_checklist.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real_checklist.md:1)
- 若左脚或 `right pitch 100/0.8` 已形成明确方向，再决定下一批是：
  - 继续扫 `kp`
  - 小步调 `kd`
  - 转入接触耦合 / `lpf_conf.wc`
