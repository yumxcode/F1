# Sim2Real Checklist

适用对象：`rl_walk_leg.onnx` 在本仓库控制栈上的真机部署与参数适配。

关联资料：
- 部署基线：[deploy_info.json](/Users/yumx/code/X1/agibot_x1_infer/.oma/deploy_info.json:1)
- RL 配置：[rl_x1.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/module/control_module/cfg/rl_x1.yaml:326)
- 控制逻辑：[rl_controller.cc](/Users/yumx/code/X1/agibot_x1_infer/src/module/control_module/src/rl_controller.cc:58)
- 辨识驱动配置：[x1_cfg_identifier.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/install/linux/bin/cfg/x1_cfg_identifier.yaml:1)
- 辨识启动脚本：[run_identifier.sh](/Users/yumx/code/X1/agibot_x1_infer/src/install/linux/bin/run_identifier.sh:1)
- 辨识模块源码配置：[ankle_identifier.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/module/ankle_identifier_module/cfg/ankle_identifier.yaml:1)
- 辨识模块运行时配置：`build/cfg/ankle_identifier.yaml`（仅在实验室电脑编译后生成，不纳入仓库）
- 辨识模块实现：[ankle_identifier_module.cc](/Users/yumx/code/X1/agibot_x1_infer/src/module/ankle_identifier_module/src/ankle_identifier_module.cc:1)

## 文档结构

- 总体 checklist：本文件，负责维护 sim2real 阶段总览、轮次状态、方案索引、结果索引。
- 具体方案：存放在 `.oma/sim2real/plans/`
- 每轮结果：存放在 `.oma/sim2real/results/`
- `forward_x_failure` standalone `$deploy` 最终归档：`sim2real/walk_data_analysis/`
- `forward_x_failure` OMA 中间过程归档：`.oma/sim2real/intermediate_process/forward_x_failure/`
- 踝关节阶跃响应 / `Kp/Kd` 辨识独立归档：`sim2real/ankle_step_response/`
- 当前问题总结：`.oma/sim2real/forward_x_failure_5.14/SUMMARY.md`

## 当前状态

| 项目 | 当前值 |
|---|---|
| OMA 阶段 | `deploy` |
| 当前 standalone deploy | `forward_x_failure` |
| 当前轮状态 | `ended` |
| 当前重点 | 已收尾；最终资料以 `sim2real/walk_data_analysis/` 和 `sim2real/ankle_step_response/` 为准 |
| 中间过程 | `.oma/sim2real/intermediate_process/forward_x_failure/` |
| 上一轮状态 | `Round 2 archived as intermediate process` |

## 阶段总览

| 阶段 | 状态 | 目标 | 方案 | 最近结果 |
|---|---|---|---|---|
| `sensor_and_sign_check` | completed | 确认传感器、关节顺序、符号、零位无硬错误 | 本阶段按现场基础检查执行 | [Round 1](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_01_field_test.md:1) |
| `zero -> stand -> hold` | completed | 确认基础 PD 站立稳定 | 本阶段按现场基础检查执行 | [Round 1](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_01_field_test.md:1) |
| `rl_idle_and_in_place_step` | completed | 确认 RL 零速/小速度下基础行为 | 本阶段按现场基础检查执行 | [Round 1](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_01_field_test.md:1) |
| `forward_x_failure_walk_data_analysis` | completed | 汇总 forward-x failure 的行走数据分析方案、脚本、报告和表格 | [walk_data_analysis](/Users/yumx/code/X1/agibot_x1_infer/sim2real/walk_data_analysis/README.md:1) | [walk_data_analysis](/Users/yumx/code/X1/agibot_x1_infer/sim2real/walk_data_analysis/README.md:1) |
| `ankle_step_response_archive` | completed | 从 `.oma/sim2real/` 提取踝关节阶跃响应方案、脚本和结果，作为独立资料集 | [ankle_step_response](/Users/yumx/code/X1/agibot_x1_infer/sim2real/ankle_step_response/README.md:1) | [result_5.14.md](/Users/yumx/code/X1/agibot_x1_infer/sim2real/ankle_step_response/results/result_5.14.md:1) |
| `sim2real_summary` | completed | 汇总当前 sim2real 状态、最终问题结论、解决方案和数据入口 | [SUMMARY.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/forward_x_failure_5.14/SUMMARY.md:1) | [SUMMARY.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/forward_x_failure_5.14/SUMMARY.md:1) |
| `ankle_kp_kd_identification` | archived_process | 原 `.oma` 过程材料；正式独立入口见 `ankle_step_response_archive` | [ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/ankle_kp_kd_identification.md:1) | [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md:1) |
| `low_speed_walk` | pending | 在候选踝关节参数下验证低速直行、连续性和抖动变化 | [round_03_low_speed_walk_with_ankle_candidates.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/round_03_low_speed_walk_with_ankle_candidates.md:1) | 已有草案，但必须等待 Round 2 关闭后才能执行 |
| `lateral_and_yaw` | pending | 验证横移与转向 | 待创建 | 待更新 |
| `disturbance_and_contact` | pending | 验证扰动和接触鲁棒性 | 待创建 | 待更新 |

## 轮次索引

| 轮次 | 状态 | 目标 | 结果文件 |
|---|---|---|---|
| `Round 1` | completed | 基础链路、站立、RL 小速度初测 | [round_01_field_test.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_01_field_test.md:1) |
| `forward_x_failure standalone` | ended | 行走数据分析最终整理 | [walk_data_analysis](/Users/yumx/code/X1/agibot_x1_infer/sim2real/walk_data_analysis/README.md:1) |
| `Round 2` | archived_process | 踝关节 `kp/kd` 阶跃辨识；正式独立结果见 `sim2real/ankle_step_response/results/result_5.14.md` | [result_5.14.md](/Users/yumx/code/X1/agibot_x1_infer/sim2real/ankle_step_response/results/result_5.14.md:1) |
| `Round 3` | pending | 分轴踝关节参数下的低速步态验证 | 待生成 |

## 当前结论

- 本次 standalone `$deploy` 的 `forward_x_failure` 专项分析已结束。
- 最终整理后的整体行走和欠阻尼分析位于 `sim2real/walk_data_analysis/`。
- 踝关节阶跃响应试验、`Kp/Kd` 辨识方案、脚本和结果位于 `sim2real/ankle_step_response/`。
- `.oma/sim2real/intermediate_process/forward_x_failure/` 仅保留中间过程、历史分支、探索脚本和阶段性结果，用于追溯，不作为最终交付入口。
- 当前最终问题结论：
  - 踝关节机械标零后仍存在 `ankle pitch` 约 `1.3~1.8 deg` 偏差。
  - 踝关节小腿硬件支撑件发生明显弯曲。
  - 踝关节闭环为严重欠阻尼系统。
- 已执行解决方案：
  - 配置文件 `offset` 标零对齐。
  - 更换踝关节小腿支撑件。
  - 提升 `kd`、降低 `kp`，当前阶段 `kp/kd = 30/1.5`。
- 基础部署链路已跑通。
- `sensor_and_sign_check` 已通过。
- `zero -> stand -> hold` 已通过。
- `rl_idle_and_in_place_step` 已通过基础可用性验证，但仍存在：
  - 行走连续性不足，约 `10 s`
  - 行走形态偏踏步前进
  - 踝关节轻微抖动
- 当前不优先修改：
  - `action_scale`
  - `pd_zero/pd_stand`
- `Round 2` 当前进展：
  - 辨识链路已切换为 `run_identifier.sh -> DcuDriverModule + AnkleIdentifierModule`
  - 不再依赖外部 `native_ros2_ankle_identifier` ROS2 topic bridge
  - 四个自由度都已完成“完全着地”工况首轮阶跃辨识
  - `right roll` 已补悬空 `kp=35, kd=0.5/0.8/1.0`
  - `right pitch` 已补悬空 `kp=35, kd=0.5`，并补完完全触地 `kd=0.5` 支路
  - `left pitch` 与 `left roll` 仍缺悬空数据，`right pitch 100/0.8` 也仍缺悬空对照，因此 `Round 2` 不能关闭
  - 数据分析判据已从“无超调优先”修正为“`tracking_ratio` 接近 `1.0` 且无振荡优先”
- 当前判断：
  - 仅凭 `no_overshoot + no_zero_crossing` 不能证明参数好
  - 触地首轮里多个配置存在明显欠跟踪，属于“系统偏软”而非“阻尼优良”
  - `right pitch 100/0.8` 与 `right roll 60/0.8` 目前只是触地下的相对较优点，不是最终收敛结论
  - `right roll` 触地下 `35/0.5` 可作为相对最好对照点，但不能当成最终候选
  - `right roll` 悬空工况下，`kp=35` 配合 `kd=0.5/0.8/1.0` 都不是可收口点：
    - `0.5` 为持续振荡
    - `0.8/1.0` 改善为单次过冲，但仍是过冲后回落
  - 这说明 `right roll` 对接触条件高度敏感，当前更应关注悬空/触地等效动力学差异，而不是把 `kp/kd` 看成单调可调
  - `right pitch` 悬空工况下，`kp=35, kd=0.5` 已接近可用区间：
    - `peak/tail tracking` 接近 `1`
    - 时间响应满足 walking 预算
    - 但仍有轻度振荡和轮次分裂，属于接近可用但未收口
  - `right pitch` 完全触地 `kd=0.5` 支路已可判定为无效方向，不应继续沿这条线加 `kp`
  - `left pitch` 与 `left roll` 仍需要继续扫描或复核工况一致性
- 专项实验 14/34 的下一步统计已按 `t27` 口径重做：
  - sim 数据来自 `test_logs/data_csv/sim/t27*.csv`，共 4 个文件
  - real 数据来自 `test_logs/data_csv/t27*.csv`，共 12 个文件
  - 该统计是 walking-data 的频域半功率近似，输出 `zeta_bandwidth` / `f_modal_candidate_hz` / `f_n_equiv_hz`，不再混用 step 实验的 `zeta_step`
  - `40/0.8 all_ankles` real roll 组：`f_modal_candidate_hz≈2.83 Hz`，`zeta_bandwidth≈0.0517`，`f_n_equiv≈2.84 Hz`
  - sim roll 组在 25/0.4、35/0.5、40/0.5、50/0.8 下主峰约 `2.83~2.88 Hz`，`zeta_bandwidth≈0.0254~0.0259`
  - 后续参数判断应基于 `forward_x_failure_first6_t27_ankle_zeta_fn_detail.csv` 的 per-joint 差异，尤其 `right_ankle_roll_joint` 的 `residual_target_power_ratio` 和峰值 gain
- `Round 3` 当前策略：
  - 已形成草案，但继续暂缓
  - 待 `Round 2` 在悬空和触地两类工况下都形成闭环结论后，再决定是否进入低速步态验证

## 当前实机辨识启动方式

- 工作流约束：
  - 本地电脑只负责修改源码、配置、分析脚本和部署文档。
  - 真正的编译与 `run_identifier.sh` 在实验室电脑执行。
  - 推荐流程：本地改完后 `git push`，实验室电脑 `git pull` 后再编译和测试。

- 编译：
  - 在实验室电脑执行 `./build.sh`
- 启动辨识进程：
  - 在实验室电脑执行 `cd build && ./run_identifier.sh`
- 参数入口：
  - 本地修改 [ankle_identifier.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/module/ankle_identifier_module/cfg/ankle_identifier.yaml:1) 中的 `test_side`、`test_axis`、`test_kp`、`test_kd`、`step_amplitude_rad`、`csv_path`
  - 或使用 [set_ankle_identifier_config.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/set_ankle_identifier_config.py:1) 一次性切换源码配置，并在本地已有 `build/` 时同步切换运行时配置
- 结果分析：
  - 实验室电脑产出 CSV 后，可在实验室电脑或同步回本地后执行 `python3 .oma/sim2real/analyze_ankle_identifier_csv.py build/log/<csv_name>.csv`
- 约束：
  - 辨识时不运行 `run.sh`
  - 辨识时不能有其他模块或节点同时发布 `/joint_cmd`

## Round 2 下一步执行顺序

- 当前源码配置已预置到第 1 条待测点：
  - `left_ankle_pitch_joint`
  - 悬空 `step`
  - `kp=100, kd=0.8`
  - `csv_path=./log/left_pitch_step_air_kp100_kd0.8_r2a.csv`
- 先补 `left_ankle_pitch_joint` 与 `left_ankle_roll_joint` 的悬空阶跃测试，沿用当前 `step_amplitude_rad = 0.015`
- `right_ankle_pitch_joint` 再补悬空对照，首个参数用 `kp=100, kd=0.8`
- 对每个 CSV 用 [analyze_ankle_identifier_csv.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/analyze_ankle_identifier_csv.py:1) 输出：
  - `command_step`
  - `actual_step`
  - `tracking_ratio`
  - `peak_overshoot`
  - `zero_crossing_count`
  - `response_class`
- 用同口径复查已有触地数据，按“先剔除振荡，再比较 tracking_ratio”重排
- 若悬空跟踪已接近 `1.0` 而触地下明显变软或振荡：
  - 转入接触耦合方向，重点看 `kd` 和 `lpf_conf.wc`
- 若悬空和触地都持续欠跟踪：
  - 继续向上扫描 `kp`
  - 不提前进入 `Round 3`
- `Round 2` 关闭条件：
  - 左脚两轴悬空数据补齐
  - `right pitch 100/0.8` 悬空对照补齐
  - 触地与悬空结果按统一判据完成重排
  - 至少为四个自由度分别写出“继续扫 `kp` / 改 `kd` / 转接触耦合`”三选一结论

## 维护规则

- 本文件只维护总览，不写大段实验细节。
- 新的具体实验方案写到 `.oma/sim2real/plans/`
- 每轮真机实验结果单独写到 `.oma/sim2real/results/round_xx_*.md`
- 每完成一轮实验，只更新：
  - 当前 sim2real 轮次
  - 当前轮状态
  - 阶段总览表
  - 轮次索引表
  - 当前结论
