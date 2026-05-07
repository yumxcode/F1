# Round 3B Tracking Lag 修复线

状态：`executed / reinterpreted-by-audit`。本线由 [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/03_ankle_landing_attitude_resolution.md:1) 直接触发，本轮执行结论见 [04_tracking_lag_repair.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/04_tracking_lag_repair.md:1)。

2026-05-06 审计后，本线不再用旧 `severe_foot_flat_touchdown / command_not_flat` 标签作为修复成败真值；当前只保留其负结论：单轴 `kp/kd` 扫参不能关闭问题，且会在多个旧标签之间转移表现。因此 `kp/kd` 不是下一步第一入口。

## 目标

在不改策略的前提下，验证并修复 Round 3 中稳定出现的 `tracking_lag` 样本，重点确认：

1. 当前 `walk` 踝参数 `kp=35, kd=0.5` 是否不足以支撑 touchdown 小幅调平
2. 右腿 `ankle roll` 的执行链是否存在额外的响应问题
3. 提升执行能力后，`tracking_lag` 是否从 Round 3 判因中消失

## 当前依据

### Round 3 直接证据

来自 [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/03_ankle_landing_attitude_resolution.md:1)：

- `tracking_lag = 2`
- 稳定样本：
  - `right @ 1777280415.204`
  - `right @ 1777280415.674`
- `delay sweep (10 / 20 / 30 ms)` 下标签稳定，不是时延口径偶然产物

### 阶跃试验支撑

来自 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/round_02_ankle_kp_kd_identification.md:1) 与 [round_02_ankle_kp_kd_identification.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md:1)：

- `walk` 当前踝参数：`kp=35, kd=0.5`
- `right pitch` 在完全触地小阶跃下明确欠跟踪且严重偏慢
- `right roll` 在小幅值触地下存在明显欠跟踪，大幅值下可恢复，说明 touchdown 小修正能力仍不足

## 修复原则

本线只做执行链修复，不碰策略：

- 不动 `onnx`
- 不动 reward / observation
- 不动 gait phase

只动：

- `rl_walk_leg` 的踝 `kp/kd`
- 必要时检查并联踝限幅、力矩方向、零位

## 试验设计

### Test B1. Walk 踝参数保守增强

目标：

- 在不大幅改动系统行为的前提下，先验证 `35/0.5` 是否偏软

建议首组候选：

- `right_ankle_roll_joint`: `kp 35 -> 50`, `kd 0.5 -> 0.8`
- `right_ankle_pitch_joint`: 先不动，避免一次改两轴混因
- 左踝保持不变
- 本轮专项日志文件名前缀：`t27_tracking_lag_b1_diag_*`

观察：

- Round 3 两个 `tracking_lag` 样本是否消失
- `effective_delay_to_touch_tracking_err_rad` 是否明显下降
- 是否引入新的 touchdown 振荡或明显过冲

### 当前样本有效性约束

- `35 / 0.5`：保留，作为未改参 baseline
- `50 / 0.8`：保留，作为 B1 主试验样本
- `40 / 0.5`：**当前剔除，不纳入结论**

剔除原因：

- 现有两份 `40 / 0.5` 日志虽然参数反推一致，但两段数据全程表现为：
  - `left_contact = 1`
  - `right_contact = 1`
  - 无可用 touchdown 边沿
  - 相对脚高近似常值
- 因此它们更像“采集状态异常 / 未形成有效摆腿落地事件”的无效样本，而不是可用于 Round 3 touchdown 诊断的正常试验数据
- 在复测出新的 `40 / 0.5` 有效日志之前，禁止用这两份数据支持任何优劣判断

### Test B2. 右踝双轴一致性增强

前提：

- 若 B1 证明 `right roll` 改善有限，或 `ankle pitch` 误差仍显著

建议次组候选：

- `right_ankle_roll_joint`: `50 / 0.8`
- `right_ankle_pitch_joint`: 参考已测更接近可用点，向 `40~50 / 0.8` 靠拢

观察：

- `tracking_lag` 是否转移为 `command_not_flat` 或 `coupled_geometry`
- `foot_flat_error_touch_rad` 是否同步下降

### Test B3. 零位/执行链排查

只有在参数增强后 `tracking_lag` 仍稳定存在时执行：

- 检查并联踝方向符号
- 检查零位偏置
- 检查执行限幅或额外保护逻辑

## 通过标准（执行结果对照）

本线关闭条件对照：

1. ❌ 原先两次 `tracking_lag` 样本在部分参数组仍出现（在不同参数间转移）
2. ✅ `tracking_lag` 不是稳定、唯一可关闭的主导判因（已证明参数改变只转移表现）
3. ✅ 未出现明显转移成更强过冲/振荡（低 kp 方向可压住抖动）
4. ❌ `foot_flat_error_touch_rad` 无实质下降（仍 `severe_foot_flat_touchdown`）

> **收口**：本线以"否定性收口"关闭——单轴 right-roll 扫参不能关闭主问题，已停止继续盲扫。

## 失败判据（已触发）

以下条件已触发，已停止继续推参数：

- ✅（触发）高 kp 时 touchdown 后出现更明显接触抖动
- ✅（触发）`foot_flat_error_touch_rad` 未明显下降
- ✅（触发）`tracking_lag` 在 kp 变化时转移为 `command_not_flat / coupled_geometry`

## 下一步衔接（已执行）

- ✅ 本线按"否定性收口"关闭，已不再继续扩大踝参数
- ✅ 正式转向 `coupled_geometry / command_not_flat / filter_delay` 联合排查（`05_coupled_geometry_probe`）

## 本轮执行结论

当前按“前 `4` 个 touchdown 优先”的新口径，`04` 已完成一轮有效样本验证，结论如下：

- `35 / 0.5 baseline`：前 `4` 步为 `command_not_flat 2 / coupled_geometry 2`
- `35 / 0.5 retest`：前 `4` 步为 `command_not_flat 3 / tracking_lag 1`
- `50 / 0.8`：前 `4` 步为 `command_not_flat 2 / coupled_geometry 2`
- `40 / 0.8`：前 `4` 步为 `command_not_flat 2 / filter_delay 1 / tracking_lag 1`

统一判断：

1. 所有有效样本前 `4` 步仍然全部命中 `severe_foot_flat_touchdown`
2. `tracking_lag` 不是前 `4` 步里稳定、唯一、可单靠单轴增益关闭的主因
3. 仅沿 `right_ankle_roll_joint` 的单轴 `kp/kd` 调节，会在 `tracking_lag / filter_delay / coupled_geometry / command_not_flat` 之间转移表现，但不能关闭主问题
4. 因此本线按“单轴 right roll 参数扫描”收口，不再继续盲目扩大 `right_ankle_roll_joint` 参数

后续动作：

- 保留 `tracking_lag` 为并发问题标签，不再作为当前第一修复入口
- 优先转向 `command_not_flat / coupled_geometry / filter_delay` 的联合排查
