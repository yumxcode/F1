# Round 2D 踝关节一致性与响应性复测执行单

状态：✅ `completed`。本轮已完成全部四个自由度的复测与判因，结论已并入 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md)。**本执行单保留仅作历史参考。**

> **Round 2D 主要结论：**
> - 四个关节的 air 重复性已确认，Round 2A 可以收口。
> - 此前 left roll 异常已确认为踝关节螺栓松动导致，复紧后数据有效。
> - 历史 ground 数据因测试口径误差全部废除，不参与退化量判断。
> - 当前 best_air_candidate：left pitch 80/0.8，left roll 80/1.0，right roll 50/0.8，right pitch 40/0.8。

## 本轮目的

- 复测四个踝轴在相同测试口径下的重复一致性。
- 验证 `air -> ground` 的退化是否稳定、是否左右不对称。
- 判断主要矛盾更接近以下哪一类：
  - `A`：并联踝本体闭环就不稳定，air 下也收不住
  - `B`：air 可收敛，但一触地就明显退化，说明接触耦合/结构柔顺性是主因
  - `C`：辨识可收敛，但 walking 落地仍调不平，说明 RL torque 路径、LPF、相位滞后或落地时序才是主因

## 关键背景

- 当前 `Round 2` 总体策略仍保持不变：
  - `Round 2A`：先找 `best_air_candidate`
  - `Round 2B`：再测 `ground degradation`
  - `Round 2C`：必要时再看接触耦合与 `lpf_conf.wc`
- 本轮不是重新大范围扫点，而是做“复测 + 判因”。
- 现有实现里，RL walking 的踝轴命令链是：
  - `pos_des = action * action_scale + init_state`
  - `tau_des = kp * (pos_des - q) + kd * (0 - dq)`
  - `tau_des` 再经过低通后发到 `effort`
- 辨识模块当前发的是 `position + kp/kd` 形式，因此它更像“关节/接触辨识”，不是完整 walking torque 路径复现。

## 本轮核心假设

1. 如果同一自由度在 `air` 下 3 次重复结果分散很大：
   - 优先怀疑本体机械/传感链一致性差
   - 不能先怪 walking 时序

2. 如果 `air` 下稳定，但 `ground` 下稳定掉幅或新增振荡：
   - 优先怀疑并联结构在接触条件下的等效刚度/阻尼变化
   - 以及脚底接触几何、落地姿态误差放大

3. 如果辨识里 `air/ground` 都还行，但 walking 时仍“原地踏步/后退”：
   - 优先怀疑落地瞬间姿态没对齐、踝轴 torque 路径相位滞后、或策略预期的接触时序被真机打乱

## 测试对象

- `left_ankle_pitch_joint`
- `left_ankle_roll_joint`
- `right_ankle_pitch_joint`
- `right_ankle_roll_joint`

## 每个自由度的复测对象

每个自由度只测两个点：

- `air_best_or_provisional`
  - 用当前阶段最优点
  - 目的：看本体闭环重复一致性
- `ground_same_point`
  - 用完全相同的 `kp/kd`
  - 目的：只测接触退化，不在本轮引入新参数

当前建议点位：

| 自由度 | air/ground 复测点 |
|---|---|
| `left_ankle_pitch_joint` | `kp=80, kd=0.5` |
| `left_ankle_roll_joint` | `kp=30, kd=0.5` |
| `right_ankle_pitch_joint` | `kp=30, kd=0.5` |
| `right_ankle_roll_joint` | `kp=50, kd=0.8` |

说明：
- 这些点当前都还只是 `provisional`，不是最终部署值。
- 本轮不追求再扫出新最优点，只追求先把“重复性”和“退化量”测实。

## 固定测试口径

- `mode = step`
- `step_amplitude_rad = 0.015`
- `active_sec = 1.0`
- `repeat_count = 3`
- `publish_rate_hz = 1000`

额外约束：
- 每个自由度按 `air -> ground` 紧邻执行，避免跨天、跨机状态变化太大。
- 每个点完成后立即分析，不累计到最后统一看。
- 若 ground 工况明显放大抖动或异响，立即终止该自由度 ground 复测。

## 推荐执行顺序

1. `right_ankle_roll_joint @ 50/0.8`
2. `right_ankle_pitch_joint @ 30/0.5`
3. `left_ankle_roll_joint @ 30/0.5`
4. `left_ankle_pitch_joint @ 80/0.5`

排序理由：
- 右侧已有更清晰的阶段结论，适合作为先验对照。
- 左侧目前更像“能打到但收不住”，放后面便于根据前两条及时修正判据。

## 每条测试的执行模板

对每个自由度都执行以下 2 个 case：

1. `air`
2. `ground`

每个 case 都跑 3 次 step。

记录文件命名建议：

| Case | 示例 |
|---|---|
| air | `./log/right_roll_step_air_kp50_kd0.8_r2d.csv` |
| ground | `./log/right_roll_step_ground_kp50_kd0.8_r2d.csv` |

## 必须输出的指标

每个 CSV 都必须输出：

- `tracking_ratio`
- `tail_tracking_ratio`
- `peak_tracking_ratio`
- `rise_time_sec`
- `peak_time_sec`
- `settling_time_sec`
- `zero_crossing_count`
- `response_class`
- `coupled_motion`

每个自由度最终要补一张对照表：

| 字段 | 含义 |
|---|---|
| `air_mean_tracking_ratio` | 悬空平均跟踪率 |
| `air_std_tracking_ratio` | 悬空 3 次离散度 |
| `ground_mean_tracking_ratio` | 触地平均跟踪率 |
| `ground_std_tracking_ratio` | 触地 3 次离散度 |
| `degradation_ratio` | `ground_mean / air_mean` |
| `consistency_gap` | `ground_std - air_std` |
| `next_action` | 下一步动作 |

## 判因规则

### 判成 A：本体闭环就不稳

满足任一条即可：

- `air_std_tracking_ratio` 明显偏大，3 次结果分裂
- `air` 下就出现持续振荡或明显过零
- 左右同类自由度在 `air` 下差异就很大

下一步：
- 不进入 walking 验证
- 继续留在 `Round 2A`
- 先收敛本体 `kp/kd`

### 判成 B：接触退化是主因

满足全部：

- `air` 下可重复且基本可用
- `ground_tracking_ratio` 相对 `air` 明显下跌
- 或 ground 新增振荡 / 耦合放大 / 左右差异扩大

下一步：
- 进入 `Round 2C`
- 优先查接触耦合、脚底姿态、落地几何、`kd` 和 `lpf_conf.wc`

### 判成 C：walking 链路是主因

满足全部：

- `air` 与 `ground` 辨识都没有明显失败
- 但 walking 里仍出现落地斜脚、原地踏步或后退

下一步：
- 不再继续盲扫 `kp/kd`
- 转而记录 RL walking 期间的：
  - `ankle pos_des`
  - `ankle q`
  - `ankle dq`
  - `ankle effort`
  - 落地前后 `100~150 ms` 的时序对齐
- 重点判断 torque 路径与 LPF 相位滞后

## 今天这轮我更看重的结论

不是“哪组 `kp/kd` 最大”，而是下面这 3 个问题：

1. `air` 下到底能不能稳定复现？
2. `ground` 相比 `air` 退化多少，退化是否左右不对称？
3. 若辨识本身不差，walking 落地前 `ankle pitch/roll` 仍调不平，是不是控制链路相位问题而不是纯机械问题？

## 结束条件

本轮结束需要产出：

- 四个自由度的 `air` 复测结果
- 四个自由度的 `ground` 同点复测结果
- 每个自由度的：
  - `degradation_ratio`
  - `consistency_gap`
  - `next_action`
- 一个总体判断：
  - `A 本体闭环主导`
  - `B 接触退化主导`
  - `C walking 链路主导`

## 本轮结束后允许的动作

- 若多数自由度落到 `A`：继续 `Round 2A`
- 若多数自由度落到 `B`：进入 `Round 2C`
- 若多数自由度落到 `C`：停止继续盲扫 `kp/kd`，改做 RL walking 落地窗口日志分析
