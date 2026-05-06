# Round 3A 踝落地姿态专项结果

轮次目标：在 [02_round3_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/02_round3_landing_window_diagnosis.md:1) 已确认 `8/8 = severe_foot_flat_touchdown` 的基础上，进一步回答：

1. touchdown 不平主要由 `pitch` 还是 `roll` 主导  
2. 对主导轴进入 `raw -> lpf -> q` 三层判因  
3. 判断更像 `command_not_flat`、`tracking_lag`、`filter_delay` 还是 `coupled_geometry`

## 数据与脚本

- 原始日志：
  - [t26_round3_diag_20260427_170011.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t26_round3_diag_20260427_170011.csv)
- Round 3 touchdown 汇总：
  - [t26_round3_diag_20260427_170011_touchdown_summary.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_touchdown_summary.csv:1)
- 专项分析脚本：
  - [03a_round3_landing_window_analysis.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/03a_round3_landing_window_analysis.py:1)
  - [03b_round3_ankle_landing_attitude_classification.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/03b_round3_ankle_landing_attitude_classification.py:1)
- 专项输出：
  - [t26_round3_diag_20260427_170011_ankle_attitude_classification.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_ankle_attitude_classification.csv:1)
  - [t26_round3_diag_20260427_170011_ankle_attitude_classification.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_ankle_attitude_classification.md:1)
  - [t26_round3_diag_20260427_170011_ankle_attitude_ranked_by_flat_error.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_ankle_attitude_ranked_by_flat_error.csv:1)
  - [t26_round3_diag_20260427_170011_ankle_attitude_ranked_by_tracking_error.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_ankle_attitude_ranked_by_tracking_error.csv:1)
- 阶跃试验支撑：
  - [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_02_ankle_kp_kd_identification.md:1)
  - [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md:1)

## 本轮口径

### touchdown 姿态分型

- `touchdown_attitude_type`
  - `toe_first_like` / `heel_first_like`：由 `sole_pitch_touch_rad` 符号决定
  - `roll_negative_dominant` / `roll_positive_dominant`：由 `sole_roll_touch_rad` 符号决定
- 当前不直接把 `roll_positive/negative` 映射成“内侧/外侧先落”，因为这依赖已确认的足底坐标系符号约定

### 三层判因口径

当前踝关节为并联踝，日志里不存在可直接使用的 `ankle pos_des_lpf`。因此本专项的三层实际定义为：

1. `raw`：`pos_des_raw_*`
   - 表示 touchdown 前踝关节的原始位置意图
2. `lpf`：`tau_des_lpf_*`
   - 表示并联踝滤波后的执行链输出
3. `q`：`pos_*`
   - 表示实际关节位置

此外，本轮三层判因已加入实测执行时延补偿：

- 实测时延：EtherCAT 主站发出指令，到踝关节电机开始出现响应，约 `20 ms`
- 小阶跃执行完成时间：在 `300 kp / 5 kd` 条件下，约 `10 ms`
- 因此 `command_not_flat / filter_delay / tracking_lag` 的判定，不再直接看 touchdown 同帧 `raw`
- 而是改看 `touchdown - 20 ms` 的 `raw / tau_des_lpf`，再和 `touchdown` 时刻的 `q` 对应
- 同时补充 `delay sweep`：
  - `Δt = 10 / 20 / 30 ms`
  - 每个 `Δt` 不取单点，而是使用 `±10 ms` 窗口统计，降低单点噪声敏感性

这不是抽象上的理想三层，而是当前代码、日志字段与实测时延下能真实落地的三层。

## 主要结果

### 1. touchdown 主导轴已明确为 roll，不是 pitch

统计结果：

- `Touchdowns classified = 8`
- `Attitude dominant axis counts = {'roll': 8}`
- `Touchdown type counts = {'roll_positive_dominant': 4, 'roll_negative_dominant': 4}`

结论：

- 本批数据里 `8/8` touchdown 都不是 pitch 主导，而是 `roll` 主导的不平触地
- 这意味着后续专项修复优先轴应切到 `ankle roll`，不是先去改 ankle pitch

### 2. 跟踪主导轴并不完全等于 touchdown 姿态主导轴

统计结果：

- `Ankle tracking dominant axis counts = {'ankle_roll': 4, 'ankle_pitch': 4}`

解释：

- touchdown 几何姿态本身是 `roll` 主导
- 但按 `ankle_pitch_err_touch_rad / ankle_roll_err_touch_rad` 看，执行链误差有 `4` 次显示 `ankle_pitch` 更大

结论：

- 不能把“脚板 roll 主导不平”简单理解成“只看 ankle roll 误差就够了”
- `ankle pitch` 仍可能通过耦合几何影响最终的脚底 roll 姿态

### 3. 三层判因结果：`command_not_flat` 为主，`tracking_lag` 次之，`filter_delay` 当前无证据

统计结果：

- `Three-layer root cause counts = {'coupled_geometry': 2, 'command_not_flat': 4, 'tracking_lag': 2}`
- `Delay sweep counts = {'10ms': {'coupled_geometry': 2, 'command_not_flat': 4, 'tracking_lag': 2}, '20ms': {'coupled_geometry': 2, 'command_not_flat': 4, 'tracking_lag': 2}, '30ms': {'coupled_geometry': 2, 'command_not_flat': 4, 'tracking_lag': 2}}`
- `Delay-sweep stable touch-downs = 8/8`

即：

- `command_not_flat = 4`
- `tracking_lag = 2`
- `coupled_geometry = 2`
- `filter_delay = 0`

解释：

#### `command_not_flat`

判定含义：

- 在 `touchdown - 20 ms` 的有效作用窗口里，主导轴 `raw` 目标仍没有把踝关节持续往更平的方向收
- 有些步甚至在整个 `-100 / -50 / -20 ms / touch` 窗口内，`raw_flattening_intent_ratio = 0`

代表样本：

- `right @ 1777280413.094`
- `left @ 1777280414.814`
- `left @ 1777280414.954`
- `left @ 1777280415.464`

结论：

- 这类步态的上游问题更像“策略在 touchdown 前没给出足够正确的收平意图”
- 单纯提高执行跟踪能力，未必能根治

#### `tracking_lag`

判定含义：

- `touchdown - 20 ms` 时 `raw` 意图已经存在
- `tau_des_lpf` 也没有显著衰减
- 但 `touchdown` 时 `q` 对主导踝关节目标仍有较大滞后

代表样本：

- `right @ 1777280415.674`
- `right @ 1777280415.204`

结论：

- 右腿至少有两次 touchdown 更像执行链跟不上，而不是命令没给
- 这两次应优先检查 `ankle roll` 执行响应与并联踝映射

### 4. 阶跃试验对 `tracking_lag` 的直接支撑

当前 `walk` 阶段踝参数仍是 `kp=35, kd=0.5`，见 [rl_x1.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/module/control_module/cfg/rl_x1.yaml:330)。

结合已有阶跃试验结果，可以把“walk 踝参数响应不足会不会导致 Round 3 问题”回答得更具体：

#### `right_ankle_pitch_joint`

见 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_02_ankle_kp_kd_identification.md:136) 到 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_02_ankle_kp_kd_identification.md:151)：

- 完全触地 `kp=35, kd=0.5`
- `tracking_ratio(window_mean) ≈ 0.442`
- `peak_time_sec ≈ 0.338`
- 文档结论：明显欠跟踪，且峰值时间远超 walking 预算，在完全触地工况下不可用

这说明对 pitch 轴来说，`35/0.5` 在触地小修正场景下已经不是“边缘可用”，而是明确偏软、偏慢。

#### `right_ankle_roll_joint`

见 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_02_ankle_kp_kd_identification.md:88) 到 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_02_ankle_kp_kd_identification.md:89)：

- 完全触地 `kp=35, kd=0.5`
- `tracking_ratio ≈ 0.671`
- `peak_time_sec ≈ 0.049`
- 当前判断：触地下的相对最好对照点，但仍明显欠跟踪，不能收口

进一步看分步结果 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md:179) 到 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md:199)：

- `right roll`
- 小幅值 `0.015 rad ground`：`tracking_ratio ≈ 0.415`
- 大幅值 `0.100 rad ground`：`tracking_ratio ≈ 0.832`
- 结论：存在强幅值依赖，本质更像接触阈值/静摩擦效应，而不是单纯 `kp` 全局不足

这条结论对 Round 3 很重要，因为 touchdown 前调平动作往往就是小幅修正。  
也就是说，**即使 `right roll` 在大幅值阶跃下可以恢复，仍然可能在 touchdown 小幅调平场景里跟不上。**

#### 对 Round 3 的解释边界

综合判断：

- `35/0.5` 的响应不足，**可以直接支撑 Round 3 里的 `tracking_lag`**
- 它也会放大 touchdown 前后的小幅调平失败
- 但它**不能单独解释** `command_not_flat`
- 也**不能单独解释** `coupled_geometry`

因此当前更准确的结论是：

- `tracking_lag` 线：已有 step 试验证据强支撑
- `command_not_flat` 线：仍是上游意图问题，不能靠加大踝参数直接证明或消除
- `coupled_geometry` 线：仍需单独查机构耦合、零位和几何映射

#### `coupled_geometry`

判定含义：

- `touchdown - 20 ms` 时 `raw` 一直在收平
- `tau_des_lpf` 也有响应
- 到 `touchdown` 时主导轴 `q` 误差仍不足以单独解释脚底姿态
- 但最终脚底姿态依然严重不平

代表样本：

- `left @ 1777280412.454`
- `right @ 1777280414.944`

结论：

- 这类样本更像“单轴链路解释不了全部问题”
- 需要继续查 pitch/roll 耦合、零位偏置或左右脚几何差异

#### `filter_delay`

本轮没有样本命中。

当前结论：

- 在加入 `20 ms` 延迟补偿后，现有日志里仍看不到“raw 已明显改变，但 lpf 层大幅衰减或显著迟到”的一致证据
- 所以 `filter_delay` 不是当前第一优先级
- 且在 `10 / 20 / 30 ms` 三个候选延迟中心下，标签保持一致，说明当前这批样本对这段延迟区间并不敏感

## 排序表解读

### 1. 按脚板不平程度排序

见：

- [t26_round3_diag_20260427_170011_ankle_attitude_ranked_by_flat_error.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_ankle_attitude_ranked_by_flat_error.csv:1)

前两名：

1. `left @ 1777280412.454`
   - `foot_flat_error_touch_rad = 1.9376`
   - `sole_roll_touch_rad = 1.9310`
   - `three_layer_root_cause = coupled_geometry`
2. `right @ 1777280414.944`
   - `foot_flat_error_touch_rad = 1.8971`
   - `sole_roll_touch_rad = -1.8943`
   - `three_layer_root_cause = coupled_geometry`

说明：

- 最严重的左脚样本，不是简单的命令缺失，而更像几何/耦合问题
- `right @ 1777280414.944` 在 `20 ms` 延迟补偿后稳定归入 `coupled_geometry`
- 新补出的 `left @ 1777280415.464` 不是孤立噪声点，它在 `10 / 20 / 30 ms` delay sweep 下都稳定落在 `command_not_flat`

### 2. 按主导踝关节跟踪误差排序

见：

- [t26_round3_diag_20260427_170011_ankle_attitude_ranked_by_tracking_error.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_ankle_attitude_ranked_by_tracking_error.csv:1)

前两名：

1. `right @ 1777280415.204`
   - `effective_delay_to_touch_tracking_err_rad = 0.3514`
   - `three_layer_root_cause = tracking_lag`
2. `right @ 1777280415.674`
   - `effective_delay_to_touch_tracking_err_rad = 0.3064`
   - `three_layer_root_cause = tracking_lag`

说明：

- 延迟补偿后，真正最该优先看的 tracking 样本集中到右腿两次 touchdown
- 这比原先直接看同帧 `raw - q` 更符合实际执行因果

## 本轮结论

1. Round 3A Phase A 已完成：
   - touchdown 主导轴明确为 `roll`
   - 可以停止把 pitch 当成第一主轴

2. Round 3A Phase B 已进入并拿到初步判因：
   - 在 `20 ms` 延迟补偿后，主因分布为 `command_not_flat = 4`、`tracking_lag = 2`、`coupled_geometry = 2`
   - `filter_delay` 当前没有证据支撑
   - `delay sweep` 显示 `8/8` 样本在 `10 / 20 / 30 ms` 上标签稳定

3. 经 [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/04_tracking_lag_repair.md:1) 的后续试验验证，当前统一口径应进一步收紧为：
   - `tracking_lag` 线有证据，但单靠 `right_ankle_roll_joint` 单轴 `kp/kd` 扫参不能形成稳定修复路径
   - 单轴调参会在 `tracking_lag / filter_delay / coupled_geometry / command_not_flat` 之间转移表现
   - 因此当前最合理的修复优先级已调整为：
     1. `command_not_flat`
     2. `coupled_geometry`
     3. `filter_delay`
     4. `tracking_lag` 只作为并发问题复核，而不再单独作为第一修复入口

## 下一步动作（进度标记）

1. ✅ `command_not_flat` 主线 — 已在 `04/05` 中持续排查；`05C` 最终确认不是唯一根因，touchdown 残差归到 foot-space / contact frame

2. ✅ `coupled_geometry` 主线 — 已在 `05` 专项中深挖，`05A/05B/05C` 均已完成；当前收口为 `fk_foot_frame_residual_candidate 3/4`；⬜ 等待 `05D` 现场验证

3. ⬜ `filter_delay` 复核线 — **未正式完成**
   - `40/0.8` 下出现过 `filter_delay` 1 个样本，但后续多组试验中均未稳定复现
   - **当前处理**：`filter_delay` 无稳定主导证据，**不作为当前优先推进方向**；待问题整体收敛后如有必要再复核
   - 此条目不再主动推进

4. ✅ `tracking_lag` 复核线 — 已保留为并发问题标签；`04` 已证明单轴扫参不能关闭主问题，不再单独作为第一入口

## 指标字典

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `sole_pitch_touch_rad` | touchdown 时脚底 pitch 姿态 | 与 roll 对比，判断 touchdown 主导轴 |
| `sole_roll_touch_rad` | touchdown 时脚底 roll 姿态 | 当前 `8/8` roll 主导的核心依据 |
| `ankle_pitch_err_touch_rad` | touchdown 时 ankle pitch 目标 / 实际误差 | 判断 pitch 轴是否为跟踪主因 |
| `ankle_roll_err_touch_rad` | touchdown 时 ankle roll 目标 / 实际误差 | 判断 roll 轴是否存在 tracking lag |
| `command_not_flat` | 目标本身不足以把脚底调平 | 三层根因之一；后续不能单独解释全部 residual |
| `tracking_lag` | 目标已有调平意图但真实关节没到位 | 后续统一读作执行链响应问题 |
| `filter_delay` | raw 目标早于 LPF 目标，导致调平动作迟到 | 当前无稳定主导证据 |
| `coupled_geometry` | joint-space 角度不能充分解释 foot-space 姿态 | 后续收紧为 touchdown foot-space / contact residual |
| `effective_delay_to_touch_tracking_err_rad` | 经过延迟补偿后 touchdown 相关的跟踪误差 | 对 tracking_lag 样本做排序，不直接替代主因分类 |
| `root_cause_distribution` | 三层根因分类计数 | 当前统一为 `command_not_flat 4 / tracking_lag 2 / coupled_geometry 2` |

## 阻塞状态

- `Round 4 low_speed_walk_validation_candidate`: `blocked`
- 原因：
  - `severe_foot_flat_touchdown` 仍未关闭
  - `roll` 主导 touchdown 不平问题已明确，但还未进入针对性修复验证
