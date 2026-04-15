# 并联踝关节 Kp/Kd 辨识方案

目标：在正式修改 `rl_walk_leg` 的踝关节 `stiffness/damping` 前，先得到并联踝关节末端自由度在空载和轻接触下的等效闭环响应特性，判断应优先调 `kp`、`kd` 还是 `lpf_conf.wc`。

适用关节：
- `left_ankle_pitch_joint`
- `left_ankle_roll_joint`
- `right_ankle_pitch_joint`
- `right_ankle_roll_joint`

说明：
- 真机踝关节为并联结构，不按“单电机单关节”思路做辨识。
- 本方案辨识对象改为踝关节末端等效自由度响应：
  - `ankle_pitch` 末端等效响应
  - `ankle_roll` 末端等效响应
- 重点观察主方向响应、交叉耦合响应、接触条件下的振动放大，而不是内部单执行器本体响应。

相关文件：
- 驱动-only 配置：[x1_cfg_identifier.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/install/linux/bin/cfg/x1_cfg_identifier.yaml:1)
- 驱动-only 启动脚本：[run_identifier.sh](/Users/yumx/code/X1/agibot_x1_infer/src/install/linux/bin/run_identifier.sh:1)
- 辨识节点：[native_ros2_ankle_identifier](/Users/yumx/code/X1/agibot_x1_infer/src/assistant/native_ros2_ankle_identifier/main.cc:1)

## 辨识原则

- 一次只测一个末端自由度，其余姿态尽量锁定在稳定站姿。
- 先空载，再轻接地；先更小幅阶跃，再更小幅扫频。
- 先保持 `kp` 不变，用末端响应形态判断是否需要优先增加 `kd`。
- 如果空载不抖、接地抖，优先怀疑并联耦合、接触耦合和滤波相位滞后，不要直接大幅加 `kp`。
- 任何测试都先从最小激励开始，不直接使用大幅位置阶跃。

## 测试前固定项

| 项目 | 建议值 | 备注 |
|---|---|---|
| 机器人状态 | 吊保护或可靠支撑 | 避免跌倒 |
| 其他关节 | 锁定在稳定站姿 | 减少耦合 |
| 被测自由度模式 | 单自由度末端小扰动 | 不做大幅动作 |
| 初始 `kp/kd` | 当前部署值 | 先不改 |
| 记录频率 | `>= 500 Hz`，建议 `1000 Hz` | 尽量与控制频率一致 |
| 每次改动 | 只改一个变量 | 便于归因 |

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

左脚 `pitch` 小阶跃：

```bash
cd build
./native_ros2_ankle_identifier \
  --ros-args \
  -p mode:=step \
  -p test_side:=left \
  -p test_axis:=pitch \
  -p step_amplitude_rad:=0.005 \
  -p pre_hold_sec:=2.0 \
  -p active_sec:=1.0 \
  -p post_hold_sec:=2.0 \
  -p repeat_count:=3 \
  -p test_kp:=35.0 \
  -p test_kd:=0.8 \
  -p csv_path:=/tmp/left_pitch_step.csv
```

左脚 `roll` 小阶跃：

```bash
cd build
./native_ros2_ankle_identifier \
  --ros-args \
  -p mode:=step \
  -p test_side:=left \
  -p test_axis:=roll \
  -p step_amplitude_rad:=0.005 \
  -p pre_hold_sec:=2.0 \
  -p active_sec:=1.0 \
  -p post_hold_sec:=2.0 \
  -p repeat_count:=3 \
  -p test_kp:=35.0 \
  -p test_kd:=0.8 \
  -p csv_path:=/tmp/left_roll_step.csv
```

左脚 `pitch` 正弦辨识：

```bash
cd build
./native_ros2_ankle_identifier \
  --ros-args \
  -p mode:=sine \
  -p test_side:=left \
  -p test_axis:=pitch \
  -p sine_amplitude_rad:=0.004 \
  -p sine_frequency_hz:=1.0 \
  -p pre_hold_sec:=2.0 \
  -p active_sec:=8.0 \
  -p post_hold_sec:=2.0 \
  -p repeat_count:=1 \
  -p test_kp:=35.0 \
  -p test_kd:=0.8 \
  -p csv_path:=/tmp/left_pitch_sine_1hz.csv
```

5. 结束条件

- 节点按设定轮次完成后自动退出
- CSV 自动写入指定路径
- 出现明显异响、持续振荡、明显耦合摆动时立即停止

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
| IMU 局部角速度 | 否，但推荐 | 看接触振动传播 |
| 接触状态 | 否，但推荐 | 区分空载/接地 |

## 实验 1：空载小阶跃

目的：快速看末端主方向超调、振荡、稳定时间、左右一致性和 pitch-roll 交叉耦合。

| 项目 | 建议值 |
|---|---|
| 输入类型 | 末端自由度位置阶跃 |
| 幅值 | `0.005 rad` 起，最多先到 `0.02 rad` |
| 保持时间 | `1 s` |
| 重复次数 | 正向 3 次，反向 3 次 |
| 被测对象 | 左右踝 `pitch` 与 `roll` 逐个测试 |
| 中止条件 | 明显异响、持续振荡、输出异常增大、明显耦合摆动 |

记录指标：

| 指标 | 记录内容 |
|---|---|
| 上升时间 | `10% -> 90%` |
| 超调量 | 峰值偏离目标百分比 |
| 稳定时间 | 进入并保持在误差带内的时间 |
| 稳态误差 | 最终误差 |
| 主方向是否振荡 | 无 / 轻微 / 明显 |
| 交叉方向响应 | 无 / 轻微 / 明显 |
| 左右一致性 | 左右差异是否明显 |

## 实验 2：空载正弦扫频

目的：识别容易激发并联踝抖动的频段，判断末端闭环带宽、耦合和相位滞后趋势。

| 项目 | 建议值 |
|---|---|
| 输入类型 | 末端自由度正弦位置命令 |
| 幅值 | `0.003 ~ 0.008 rad` |
| 频率点 | `0.5, 1, 2, 3 Hz` |
| 每个频点时长 | `8 ~ 10 s` |
| 被测对象 | 左右踝 `pitch` 与 `roll` 逐个测试 |

记录指标：

| 指标 | 记录内容 |
|---|---|
| 主方向幅值比 | `q / q_des` |
| 主方向相位滞后 | `q` 相对 `q_des` 的延迟趋势 |
| 交叉方向幅值 | 耦合响应是否被激发 |
| 是否出现共振 | 某频段响应放大 |
| effort 波动 | 是否随频率明显放大 |

## 实验 3：轻接地小阶跃

目的：验证接触条件下并联踝末端是否比空载更容易抖，以及耦合是否放大。

| 项目 | 建议值 |
|---|---|
| 输入类型 | 末端自由度位置阶跃 |
| 幅值 | `0.005 ~ 0.015 rad` |
| 工况 | 吊保护，脚掌轻触地面 |
| 保持时间 | `1 s` |
| 重复次数 | 正反各 3 次 |

重点观察：

| 现象 | 含义 |
|---|---|
| 空载稳定、接地抖 | 接触耦合问题明显，优先看 `kd` 和 `lpf_conf.wc` |
| 接地后交叉方向响应明显增大 | 并联耦合在接触状态下被放大 |
| 接地后 effort 明显放大 | 接触刚度放大了控制环响应 |
| 接地后左右差异扩大 | 地面接触或机械一致性存在问题 |

## 实验 4：轻接地低频扫频

目的：验证实际接触工况下容易触发并联踝抖动和耦合的频段。

| 项目 | 建议值 |
|---|---|
| 输入类型 | 末端自由度正弦位置命令 |
| 幅值 | `0.003 ~ 0.006 rad` |
| 频率点 | `0.5, 1, 2, 3 Hz` |
| 每个频点时长 | `8 s` |
| 工况 | 脚掌轻接地 |

## 调参决策表

| 辨识结果 | 优先动作 |
|---|---|
| 阶跃超调大，存在衰减振荡 | 先增加 `kd` |
| 响应偏软、跟踪慢、无明显抖动 | 先增加 `kp` |
| 空载正常，接地才抖 | 先小幅增加 `kd`，再看是否降低 `lpf_conf.wc` |
| 高频小抖明显，扫频中高频段放大 | 先增加 `kd`，必要时降低 `lpf_conf.wc` |
| 主方向激励带出明显交叉方向响应 | 优先评估并联耦合，不直接大幅加 `kp` |
| 左右脚响应差异明显 | 先排查装配、摩擦、零位，不先改统一参数 |
| effort 经常接近饱和 | 不先加 `kp`，先看命令幅值和接触工况 |

## 建议起步执行顺序

1. 左右踝 `pitch` 与 `roll` 空载小阶跃
2. 左右踝 `pitch` 与 `roll` 空载低频扫频
3. 轻接地小阶跃
4. 轻接地低频扫频
5. 汇总左右对比结论
6. 汇总主方向与交叉耦合结论
7. 再决定优先改 `kp`、`kd` 或 `lpf_conf.wc`

## 辨识记录表

| 轮次 | 自由度 | 工况 | 输入类型 | 幅值 | 频率/保持时间 | 当前 `kp` | 当前 `kd` | 超调 | 稳定时间 | 主方向是否抖动 | 交叉耦合是否明显 | effort 是否异常 | 结论 | 下一步 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
