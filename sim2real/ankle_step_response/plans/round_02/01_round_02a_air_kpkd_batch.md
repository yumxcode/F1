# Round 2 下一批 Kp/Kd 测试执行单

状态：✅ `completed`。本批次属于 `Round 2A`，目标是先完成悬空闭环收敛。**Round 2A 已正式结束，本执行单内容已全部过时，保留仅作历史参考。**

> 本批次列出的扫描点位（kp=100/105 等）在后续测试中已被超越或否定，最终 best_air_candidate 见
> [result_5.14.md](/Users/yumx/code/X1/agibot_x1_infer/sim2real/ankle_step_response/results/result_5.14.md) 的 Round 2A 最终结论汇总表。

## 本批目标

- 为每个自由度先找出 `best_air_candidate`，建立无接触基线。
- 用悬空工况区分“本体闭环就不行”与“接触一进来才退化”。
- 为 `Round 2B` 的触地退化测量准备候选点，而不是在完全触地工况下直接收敛最终参数。
- 所有结论继续使用同一判据：
  - `tracking_ratio`
  - `response_class`
  - `peak_time_sec`
  - `zero_crossing_count`
  - `coupled_motion`

## 新的 Round 2 结构

- `Round 2A`: 悬空闭环收敛
- `Round 2B`: 基于 `best_air_candidate` 的触地退化测量
- `Round 2C`: 若触地退化过大，再转接触耦合 / `kd` / `lpf_conf.wc`

本执行单只覆盖 `Round 2A`。

## 执行顺序

1. `left_ankle_pitch_joint` 悬空：`kp=100, kd=0.8`
2. `left_ankle_pitch_joint` 悬空：`kp=105, kd=0.8`
3. `left_ankle_roll_joint` 悬空：`kp=80, kd=0.8`
4. `left_ankle_roll_joint` 悬空：`kp=70, kd=0.8`
5. `right_ankle_pitch_joint` 悬空：`kp=100, kd=0.8`

说明：
- 先测各自由度在悬空工况下最有希望收敛的点，不在这一批里继续扩展完全触地工况。
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
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact air --tag r2a --kp 100 --kd 0.8
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact air --tag r2a --kp 105 --kd 0.8
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side left --axis roll --mode step --contact air --tag r2a --kp 80 --kd 0.8
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side left --axis roll --mode step --contact air --tag r2a --kp 70 --kd 0.8
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side right --axis pitch --mode step --contact air --tag r2a --kp 100 --kd 0.8
```

推荐实际执行顺序：

```bash
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact air --tag r2a --kp 100 --kd 0.8
# build && run_identifier.sh && analyze CSV
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side left --axis pitch --mode step --contact air --tag r2a --kp 105 --kd 0.8
# build && run_identifier.sh && analyze CSV
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side left --axis roll --mode step --contact air --tag r2a --kp 80 --kd 0.8
# build && run_identifier.sh && analyze CSV
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side left --axis roll --mode step --contact air --tag r2a --kp 70 --kd 0.8
# build && run_identifier.sh && analyze CSV
python3 sim2real/ankle_step_response/scripts/set_ankle_identifier_config.py --side right --axis pitch --mode step --contact air --tag r2a --kp 100 --kd 0.8
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
python3 sim2real/ankle_step_response/scripts/analyze_ankle_identifier_csv.py build/log/<csv_name>.csv
```

## 这批的判定规则

- `left pitch`
  - 若 `100/0.8` 与 `105/0.8` 在悬空下都仍 `tracking_ratio < 0.8`，优先判断为“左 pitch 不只是接触问题，还需要继续上扫 `kp`”
  - 若 `100/0.8` 已出现明显过冲或振荡，不继续直接上 `105/0.8`，先转 `kd` 支路
  - 若悬空接近 `1.0` 且响应时间可接受，则记为 `best_air_candidate`
- `left roll`
  - 若悬空下已过冲或振荡，而触地下偏软，说明与 `right roll` 一样存在工况分裂，应优先转向 `kd` 或耦合分析
  - 若悬空和触地都持续偏软，则下一批优先上扫 `kp`
- `right pitch`
  - 若 `100/0.8` 悬空下 `tracking_ratio` 接近 `1.0` 且无明显振荡，它才有资格保留为部署候选
- 若 `100/0.8` 悬空下仍显著偏软或振荡，则 `right pitch` 触地侧的“相对较优”判断要降级

## 本批结束后的收口动作

- 将 5 条 CSV 分析结果增补到 [result_5.14.md](/Users/yumx/code/X1/agibot_x1_infer/sim2real/ankle_step_response/results/result_5.14.md:1)
- 在 [sim2real_checklist.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real_checklist.md:1) 更新 `Round 2` 是否仍 `in progress`
- 为已测自由度写出：
  - `best_air_candidate` 或 `continue_air_scan`
  - `air_tracking_ratio`
  - `air_response_class`
  - `next_action`
- 只有 `Round 2A` 的 air 结论清楚后，才允许进入 `Round 2B`

## 本批结束后必须更新

- 更新 [result_5.14.md](/Users/yumx/code/X1/agibot_x1_infer/sim2real/ankle_step_response/results/result_5.14.md:1)
- 更新 [sim2real_checklist.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real_checklist.md:1)
- 若某个自由度已形成 `best_air_candidate`，下一轮只拿这个点进入 `Round 2B`
- 若 air 仍未收口，再决定下一批是：
  - 继续扫 `kp`
  - 小步调 `kd`
  - 暂不进入 ground
