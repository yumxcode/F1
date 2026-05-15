# 并联踝关节 Kp/Kd 辨识方案

目标：在正式修改 `rl_walk_leg` 的踝关节 `stiffness/damping` 前，得到并联踝关节末端自由度在悬空和触地两类工况下的等效闭环响应特性，并用“跟踪能力 + 阻尼质量”联合判据收敛 `kp/kd`，避免把低跟踪率误判成“无超调最优”。

适用关节：
- `left_ankle_pitch_joint`
- `left_ankle_roll_joint`
- `right_ankle_pitch_joint`
- `right_ankle_roll_joint`

说明：
- 真机踝关节为并联结构，不按“单电机单关节”思路做辨识。
- 本方案辨识对象是踝关节末端等效自由度响应：
  - `ankle_pitch`
  - `ankle_roll`
- 重点观察主方向跟踪、交叉耦合、接触条件下的振动放大，而不是内部单执行器本体响应。

相关文件：
- 驱动-only 配置：[x1_cfg_identifier.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/install/linux/bin/cfg/x1_cfg_identifier.yaml:1)
- 驱动-only 启动脚本：[run_identifier.sh](/Users/yumx/code/X1/agibot_x1_infer/src/install/linux/bin/run_identifier.sh:1)
- 辨识节点：[native_ros2_ankle_identifier](/Users/yumx/code/X1/agibot_x1_infer/src/assistant/native_ros2_ankle_identifier/main.cc:1)
- CSV 分析脚本：[analyze_ankle_identifier_csv.py](/Users/yumx/code/X1/agibot_x1_infer/sim2real/ankle_step_response/scripts/analyze_ankle_identifier_csv.py:1)

## Round 2 当前状态

> **✅ Round 2A 已正式结束。当前处于 Round 2B。**

- `Round 2A` 悬空闭环收敛已完成，四个踝关节均已产出 `best_air_candidate`：
  - `left pitch`: `kp=80, kd=0.8`
  - `left roll`: `kp=80, kd=1.0`
  - `right roll`: `kp=50, kd=0.8`
  - `right pitch`: `kp=40, kd=0.8`
- `Round 2B` 触地退化测量正在进行，执行单见 [`02_round_02b_ground_degradation_test.md`](/Users/yumx/code/X1/agibot_x1_infer/sim2real/ankle_step_response/plans/round_02/02_round_02b_ground_degradation_test.md)
- 完全触地首轮历史数据已废除（存在测试口径误差），不参与任何排序或退化量判断
- 后续所有排序都必须使用同一判据：
  - `tracking_ratio = actual_step / command_step`
  - 是否过零
  - 是否振荡
  - `peak_time_sec`
  - `settling_time_sec`
  - `coupled_motion`

## 辨识原则

- 一次只测一个末端自由度，其余姿态尽量锁定在稳定站姿。
- 悬空和触地都要测，缺一不可。
- 先小阶跃，再低频扫频。
- `no_overshoot + no_zero_crossing` 不是充分条件，必须同时看 `tracking_ratio`。
- 如果空载不抖、接地抖，优先怀疑并联耦合、接触耦合和滤波相位滞后，不要直接大幅加 `kp`。
- 任何测试都先从最小激励开始，不直接使用大幅位置阶跃。

## 优选判据

真正好的“无超调”应同时满足：

- `tracking_ratio` 接近 `1.0`
- 无持续振荡
- 无明显过零
- `peak_time_sec` 和 `settling_time_sec` 不异常变长
- `coupled_motion` 不明显放大

需要明确排除的情形：

- `actual_step ≈ 0.6 x command_step`
- 主轴没有冲到目标，只是因为系统太软所以看起来“不超调”
- 末段平滑，但跟踪严重不足

推荐排序顺序：

1. 先剔除有明显振荡、过零或耦合放大的配置
2. 在剩余配置中优先保留 `tracking_ratio` 更接近 `1.0` 的配置
3. 再比较 `peak_time_sec`、`settling_time_sec` 和 effort 代价

## 测试前固定项

| 项目 | 建议值 | 备注 |
|---|---|---|
| 机器人状态 | 吊保护或可靠支撑 | 避免跌倒 |
| 其他关节 | 锁定在稳定站姿 | 减少耦合 |
| 被测自由度模式 | 单自由度末端小扰动 | 不做大幅动作 |
| 记录频率 | `>= 500 Hz`，建议 `1000 Hz` | 尽量与控制频率一致 |
| 每次改动 | 只改一个变量 | 便于归因 |
| 阶跃基线 | `step_amplitude_rad = 0.015` | 悬空和触地保持同口径 |

## 启动流程

1. 编译工程

```bash
./build.sh
```

2. 启动驱动-only 配置

```bash
cd build
./run_identifier.sh
```

3. 确认基础 topic 正常

```bash
ros2 topic echo /joint_states --once
ros2 topic echo /imu/data --once
ros2 topic info /joint_cmd
```

要求：
- `/joint_states` 正常输出
- `/imu/data` 正常输出
- 辨识时不能有其他控制节点同时占用 `/joint_cmd`

4. 启动辨识节点

示例：

```bash
cd build
./native_ros2_ankle_identifier \
  --ros-args \
  -p mode:=step \
  -p test_side:=left \
  -p test_axis:=pitch \
  -p publish_rate_hz:=1000.0 \
  -p step_amplitude_rad:=0.015 \
  -p pre_hold_sec:=2.0 \
  -p active_sec:=1.0 \
  -p post_hold_sec:=2.0 \
  -p repeat_count:=3 \
  -p test_kp:=100.0 \
  -p test_kd:=0.8 \
  -p csv_path:=/tmp/left_pitch_step.csv
```

5. 结束条件

- 节点按设定轮次完成后自动退出
- CSV 自动写入指定路径
- 出现明显异响、持续振荡、明显耦合摆动时立即停止

6. 分析 CSV

```bash
python3 sim2real/ankle_step_response/scripts/analyze_ankle_identifier_csv.py /tmp/left_pitch_step.csv
```

脚本重点输出：
- `command_step`
- `actual_step`
- `tracking_ratio`
- `peak_overshoot`
- `zero_crossing_count`
- `peak_time_sec`
- `settling_time_sec`
- `response_class`

## 需要记录的数据

| 字段 | 必需 | 用途 |
|---|---|---|
| 时间戳 `t` | 是 | 对齐分析 |
| 末端自由度名 | 是 | 区分左右脚、pitch/roll |
| 主方向目标位置 `q_des` | 是 | 阶跃/正弦输入参考 |
| 主方向实际位置 `q` | 是 | 跟踪误差分析 |
| 主方向实际速度 `dq` | 是 | 阻尼和振荡判断 |
| 交叉方向位置 | 推荐 | 观察 pitch-roll 耦合 |
| 交叉方向速度 | 推荐 | 观察 pitch-roll 耦合 |
| 输出 effort / torque command | 是 | 判断是否饱和 |
| 当前 `kp` | 是 | 记录配置 |
| 当前 `kd` | 是 | 记录配置 |
| 接触状态 | 是 | 必须明确写明悬空或触地 |

## 实验 1：悬空小阶跃

目的：先在较少接触耦合的条件下看主方向跟踪率、超调、振荡和左右一致性。

| 项目 | 建议值 |
|---|---|
| 输入类型 | 末端自由度位置阶跃 |
| 幅值 | `0.015 rad` |
| 保持时间 | `1 s` |
| 重复次数 | 正向 3 次，反向 3 次 |
| 被测对象 | 左右踝 `pitch` 与 `roll` 逐个测试 |

记录指标：

| 指标 | 记录内容 |
|---|---|
| 跟踪率 | `tracking_ratio = actual_step / command_step` |
| 上升时间 | `10% -> 90%` |
| 超调量 | 峰值偏离目标百分比 |
| 稳定时间 | 进入并保持在误差带内的时间 |
| 稳态误差 | 最终误差 |
| 主方向是否振荡 | 无 / 轻微 / 明显 |
| 交叉方向响应 | 无 / 轻微 / 明显 |

## 实验 2：悬空正弦扫频

目的：识别容易激发并联踝抖动的频段，判断末端闭环带宽、耦合和相位滞后趋势。

| 项目 | 建议值 |
|---|---|
| 输入类型 | 末端自由度正弦位置命令 |
| 幅值 | `0.003 ~ 0.008 rad` |
| 频率点 | `0.5, 1, 2, 3 Hz` |
| 每个频点时长 | `8 ~ 10 s` |
| 被测对象 | 左右踝 `pitch` 与 `roll` 逐个测试 |

## 实验 3：触地小阶跃

目的：验证接触条件下并联踝末端是否比悬空更容易抖，以及是否出现“无超调但欠跟踪”的软响应。

| 项目 | 建议值 |
|---|---|
| 输入类型 | 末端自由度位置阶跃 |
| 幅值 | `0.015 rad` |
| 工况 | 吊保护，脚掌稳定触地 |
| 保持时间 | `1 s` |
| 重复次数 | 正反各 3 次 |

重点观察：

| 现象 | 含义 |
|---|---|
| 悬空跟踪正常，触地下 `tracking_ratio` 明显掉到 `< 0.8` | 接触下等效刚度不足，不能因无超调而判优 |
| 悬空稳定、接地抖 | 接触耦合问题明显，优先看 `kd` 和 `lpf_conf.wc` |
| 接地后交叉方向响应明显增大 | 并联耦合在接触状态下被放大 |
| 接地后 effort 明显放大 | 接触刚度放大了控制环响应 |

## 实验 4：触地低频扫频

目的：验证实际接触工况下容易触发并联踝抖动和耦合的频段。

| 项目 | 建议值 |
|---|---|
| 输入类型 | 末端自由度正弦位置命令 |
| 幅值 | `0.003 ~ 0.006 rad` |
| 频率点 | `0.5, 1, 2, 3 Hz` |
| 每个频点时长 | `8 s` |
| 工况 | 脚掌稳定触地 |

## 调参决策表

| 辨识结果 | 优先动作 |
|---|---|
| 阶跃超调大，存在衰减振荡 | 先增加 `kd` |
| `tracking_ratio < 0.8`，响应偏软、跟踪不足、无明显抖动 | 先增加 `kp`，不要把它记成“好阻尼” |
| 悬空正常，接地才抖 | 先小幅增加 `kd`，再看是否降低 `lpf_conf.wc` |
| 悬空和触地都持续欠跟踪 | 继续向上扫描 `kp`，并检查阶跃幅值与接触一致性 |
