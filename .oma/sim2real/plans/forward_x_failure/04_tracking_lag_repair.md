# Round 3B Tracking Lag 修复线

状态：`ready to execute`。本线由 [03_ankle_landing_attitude_resolution.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/03_ankle_landing_attitude_resolution.md:1) 直接触发。

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

## 通过标准

本线关闭条件：

1. 新日志中原先两次 `tracking_lag` 类样本不再出现
2. `tracking_lag` 不再是主导判因
3. 没有把问题简单转移成更强的过冲/振荡
4. `foot_flat_error_touch_rad` 有实质下降

## 失败判据

若出现以下任一情况，则停止沿当前参数方向继续推：

- touchdown 前后出现明显振荡
- `foot_flat_error_touch_rad` 不降反升
- `tracking_lag` 不变，但 `command_not_flat` / `coupled_geometry` 明显主导

## 下一步衔接

- 若本线成功：回到 Round 3 主线复判 `command_not_flat` 与 `coupled_geometry`
- 若本线失败：不要继续盲目增大踝参数，转向几何/映射或策略侧问题
