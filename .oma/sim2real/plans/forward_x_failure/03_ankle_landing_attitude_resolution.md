# Round 3A 踝落地姿态专项问题解决方案

状态：`done`。本专项由 [02_round3_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/02_round3_landing_window_diagnosis.md:1) 直接触发。当前结论已沉淀为：touchdown 姿态 `8/8` roll 主导，三层根因分布为 `command_not_flat 4 / tracking_lag 2 / coupled_geometry 2`；后续 `04/05/06-13` 已进一步把 `tracking_lag` 收为执行链问题，把 `coupled_geometry` 收为 touchdown foot-space / contact residual。

统一进展和指标口径见 [00_forward_x_failure_progress_review.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/00_forward_x_failure_progress_review.md:1)。

## 目标

在不盲目扩展问题面的前提下，把“严重斜脚板触地”拆解为可执行的四类根因，并通过最小干预试验判断问题属于：

- `command_not_flat`
- `tracking_lag`
- `filter_delay`
- `coupled_geometry`

只有当主导根因被明确并至少完成一轮针对性修复后，才允许回到低速前进验证。

## 当前已知事实

来自 [02_round3_landing_window_diagnosis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/02_round3_landing_window_diagnosis.md:1)：

- 独立 touchdown：`7`
- `7/7 = severe_foot_flat_touchdown`
- `mean foot_flat_error_touch_rad = 1.6916`
- `mean max_swing_clearance = 0.0820 m`
- `mean clearance_at_minus_50ms = 0.0018 m`

解释：

- 摆腿中期不是完全抬不起来
- 但 touchdown 时脚板姿态严重不平，已经成为更上游的阻塞项
- clearance 与髋膝问题保留，但当前不作为第一主线

## 专项根因假设

### H1. `command_not_flat`

策略在 touchdown 前给出的 ankle pitch/roll 原始目标，本身就不能把脚底收平。

特征：

- `pos_des_raw` 在 touchdown 前 `50 ms / 20 ms` 已经对应明显斜脚
- `pos_des_raw - q` 不一定大
- 提高踝跟踪不会根本解决问题

### H2. `tracking_lag`

策略目标基本正确，但实际 ankle pitch/roll 在 touchdown 前跟不上。

特征：

- `pos_des_raw` 或 `pos_des_lpf` 已经朝平脚方向收敛
- `q` 仍明显滞后
- `ankle_pitch_err_touch / ankle_roll_err_touch` 大

### H3. `filter_delay`

raw 目标方向正确，但 `pos_des_lpf` 或实际下发命令到达过晚，调平动作迟到。

特征：

- `pos_des_raw` 提前变化
- `pos_des_lpf` 明显滞后于 raw
- touchdown 时 `q` 还没开始有效收敛

### H4. `coupled_geometry`

单轴看起来误差不大，但 pitch/roll 组合后的脚底姿态仍然斜。

特征：

- 单看 ankle pitch 或 ankle roll，误差都不算极端
- 但 `foot_flat_error` 很大
- 往往伴随左右脚、内外侧、脚尖脚跟接触模式不一致

## 执行结论（已完成 ✅）

> 本专项已全部完成。Phase A/B/C 均已执行，结果见 [results/03_ankle_landing_attitude_resolution.md](../../results/forward_x_failure/03_ankle_landing_attitude_resolution.md)。
> **核心结论**：`8/8` roll 主导；三层根因为 `command_not_flat 4 / tracking_lag 2 / coupled_geometry 2`；后续 `04` 处理 `tracking_lag`，`05` 处理 `coupled_geometry`，`filter_delay` 无稳定主导证据。

## 解决策略

本专项不一次性改很多量。按”先判因，再小步修复”的顺序推进。

### Phase A. 纯分析分型（✅ 已完成）

基于现有 `t26` 结果，把 touchdown 进一步分成姿态型：

- `toe_first_like`：脚尖先落
- `heel_first_like`：脚跟先落
- `inside_edge_like`：脚内侧先落
- `outside_edge_like`：脚外侧先落

输出：

- 每次 touchdown 的 `sole_pitch_touch_rad`
- 每次 touchdown 的 `sole_roll_touch_rad`
- `ankle_pitch_err_touch_rad`
- `ankle_roll_err_touch_rad`

判定目的：

- 区分主要是 pitch 轴没收平，还是 roll 轴没收平
- 判断左右脚是否存在不同模式

### Phase B. 命令链与跟踪链判因（✅ 已完成）

对 touchdown 前 `100 / 50 / 20 ms` 做三层比较：

1. `pos_des_raw`
2. `pos_des_lpf`
3. `q`

判定规则：

- 若 `raw` 本身不平：归 `command_not_flat`
- 若 `raw` 平、`lpf` 不平：归 `filter_delay`
- 若 `lpf` 已平、`q` 不平：归 `tracking_lag`
- 若单轴都不极端但组合后不平：归 `coupled_geometry`

### Phase C. 最小干预修复试验（✅ 已完成，见 04_tracking_lag_repair）

一次只动一个变量，优先级如下：

1. **若主因是 `tracking_lag`**
   - 回到 ankle pitch/roll 对应执行链
   - 仅调整 touchdown 主导轴的跟踪能力
   - 优先顺序：
     - 对应轴 `kp/kd`
     - 力矩输出路径检查
     - 并联踝限幅/响应方向检查

2. **若主因是 `filter_delay`**
   - 单独建立 ankle touchdown LPF 小步试验
   - 仅改：
     - `lpf_conf.wc`
     - 或 touchdown 前窗口的局部滤波策略

3. **若主因是 `command_not_flat`**
   - 不在部署层继续硬调踝参数
   - 回到策略侧设计反馈：
     - reward
     - observation
     - touchdown 前姿态约束

4. **若主因是 `coupled_geometry`**
   - 先检查并联踝 pitch/roll 组合映射
   - 再看零位、偏置和左右脚几何不一致

## 建议试验矩阵

### Test A1. 现有日志分型复盘

输入：

- 当前 `t26_round3_diag_20260427_170011.csv`

输出：

- 每次 touchdown 的姿态类型
- 统计 pitch 主导还是 roll 主导
- 左右脚差异

### Test A2. 同参数重复采样

目标：

- 先确认 severe flat-touchdown 是否稳定复现
- 避免基于单段日志做过度修复

要求：

- 至少再采 `左右脚各 5` 次独立 touchdown
- 仍用当前参数，不做改动

### Test B1. 踝 pitch 主导轴试验

前提：

- 若分型显示 pitch 主导更明显

动作：

- 只改 ankle pitch 相关修复变量
- 其余保持不变

观察：

- `sole_pitch_touch_rad`
- `foot_flat_error_touch_rad`
- `ankle_pitch_err_touch_rad`

### Test B2. 踝 roll 主导轴试验

前提：

- 若分型显示 roll 主导更明显

动作：

- 只改 ankle roll 相关修复变量

观察：

- `sole_roll_touch_rad`
- `foot_flat_error_touch_rad`
- `ankle_roll_err_touch_rad`

### Test C. 低风险复测门槛确认

只有在 A/B 判因收敛后，才允许做短窗口低速复测：

- `x = 0.2 m/s`
- 持续 `5 ~ 10 s`
- 仅验证 severe flat-touchdown 是否明显减少

## 通过标准（执行结果对照）

本专项关闭条件对照：

1. ✅ 新日志中左右脚各至少 `5` 次独立 touchdown（Round 3：`8` 次）
2. ❌ `severe_foot_flat_touchdown` 仍是主导判因（`8/8`）—— **问题仍未关闭**，已转向 `05` 专项深挖
3. ❌ `foot_flat_error_touch_rad` mean = `1.69～1.94 rad`，仍系统性落在 `> 1.0 rad`
4. ✅ 已明确归因：roll 主导，三层根因 `command_not_flat 4 / tracking_lag 2 / coupled_geometry 2`

> 本专项"判因"目标达成，"修复"目标未达成（问题仍在 `05` 推进中）。Round 4 继续阻塞。

## 阻塞规则（当前仍触发）

以下条件当前仍满足，Round 4 继续阻塞：

- ❌ `severe_foot_flat_touchdown` 仍为主导判因（`05C` 收口为 `fk_foot_frame_residual_candidate`，`05D` 待执行）
- ❌ touchdown 仍系统性斜脚板落地

## 产物要求（已完成）

- ✅ 新的 `t27` 系列诊断日志已采集
- ✅ `touchdown_summary.csv` 系列产出
- ✅ 结果文档已完成（见 [results/03_ankle_landing_attitude_resolution.md](../../results/forward_x_failure/03_ankle_landing_attitude_resolution.md)）：
  - ✅ roll 主导（非脚尖/脚跟 pitch），内外侧接触边缘后续由 `05D` 验证
  - ✅ roll 为主导轴，pitch 参与低
  - ✅ 归因完成：`command_not_flat 4 / tracking_lag 2 / coupled_geometry 2`
  - ✅ 下一步明确：`tracking_lag` → `04`，`coupled_geometry` → `05`
