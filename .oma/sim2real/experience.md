# 踝关节并联结构 Kp/Kd 辨识经验单

## 1. 经验背景与价值

踝关节并联结构 `kp/kd` 辨识，是 sim2real 阶段的重要基础工作，可为策略落地、控制参数回写和真机稳定性提升提供支撑。

核心难点在于：

- 真机踝关节是并联结构，不能按“单电机单关节”方式理解
- 策略输出落到真实机器人后，会经过并联机构、驱动链路和地面接触共同作用
- 如果不先完成局部闭环参数辨识，后续对步态、滤波或策略参数的调整容易混因

## 2. 本轮新增经验

这次 round2 最重要的纠偏不是某个具体 `kp/kd`，而是评价准则：

- `no_overshoot + no_zero_crossing` 不是充分条件
- 真正好的“无超调”应当接近 `actual_step ≈ command_step`
- 如果 `actual_step` 明显小于 `command_step`，系统只是偏软欠跟踪，不是阻尼优良

因此，后续所有 step 辨识都必须至少同时看：

- `tracking_ratio = actual_step / command_step`
- 是否过零
- 是否振荡
- `peak_time_sec`
- `settling_time_sec`
- `coupled_motion`

## 3. 通用方案

这次沉淀出的有效方案是“单自由度、小扰动、悬空与触地分开”的并联关节辨识路线：

- 只测试四个末端自由度：
  - `left_ankle_pitch_joint`
  - `left_ankle_roll_joint`
  - `right_ankle_pitch_joint`
  - `right_ankle_roll_joint`
- 一次只激励一个主自由度，同时记录同侧耦合自由度
- 重点看主方向跟踪、交叉耦合、是否过零、是否振荡
- 悬空和触地必须分开记录，不能混着得结论

本次主测试条件：

- `mode = step`
- `step_amplitude_rad = 0.015`
- `active_sec = 1.0`
- `repeat_count = 3`
- `publish_rate_hz = 1000`

## 4. 核心代码实现

核心实现见 [ankle_identifier_module.cc](/Users/yumx/code/X1/agibot_x1_infer/src/module/ankle_identifier_module/src/ankle_identifier_module.cc:1)。

关键点：

- 从 YAML 读取 `mode / test_side / test_axis / test_kp / test_kd / step_amplitude_rad / repeat_count / publish_rate_hz`
- 根据 `side + axis` 自动映射主测试关节和同侧耦合关节
- 首次收到 `/joint_states` 后抓取基线姿态，避免硬编码站姿
- 直接发布 `/joint_cmd`，并记录目标值、实际位置、速度、effort
- 用 `pre_hold -> active -> post_hold` 的阶段组织每次实验

工程价值：

- 把辨识激励和正常控制器解耦
- 不只看目标位置，还能区分“主轴跟踪差”和“接触耦合放大”

## 5. 数据分析代码

分析脚本是 [analyze_ankle_identifier_csv.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/analyze_ankle_identifier_csv.py:1)。

当前脚本对 `step` 数据输出的关键指标包括：

- `command_step`
- `actual_step`
- `tracking_ratio`
- `coupled_motion`
- `peak_overshoot`
- `steady_error`
- `rise_time_sec`
- `peak_time_sec`
- `settling_time_sec`
- `zero_crossing_count`
- `response_class`

当前分类含义：

- `well_damped_tracking`：跟踪率足够且无过零
- `undershoot_soft`：无明显振荡，但跟踪率明显不足

## 6. 数据分析方法

推荐分析顺序：

1. 先过滤工况
   - 悬空和触地分开看
2. 再排除明显失稳
   - 超调
   - 过零
   - 振荡
3. 在剩余配置中比较跟踪能力
   - 优先保留 `tracking_ratio` 更接近 `1.0` 的配置
4. 最后比较工程代价
   - `peak_time_sec`
   - `settling_time_sec`
   - effort
   - 耦合量

## 7. 当前可复用结论

- 对并联关节，优先做末端自由度辨识，不要按单电机理解
- 悬空和触地都要测，缺一不可
- 不能把“无超调”直接等价成“参数好”
- 数据分析脚本必须保留主轴、耦合轴、effort，而不是只看目标与位置
- 当目标是服务部署决策时，工程上可解释的指标比复杂模型拟合更有价值

## 8. 当前不应过早下的结论

以下说法在 round2 当前阶段都不应直接成立：

- “四个自由度已经全部收敛”
- “当前主问题不是阻尼不足”
- “可以直接进入低速步态验证”

这些都必须等悬空和触地两类工况都完成后再判断。
