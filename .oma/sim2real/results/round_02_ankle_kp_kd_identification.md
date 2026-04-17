# Round 2 踝关节 Kp/Kd 辨识结果

轮次目标：在真机接触工况下完成踝关节 `kp/kd` 闭环辨识，先收敛 `left_ankle_pitch_joint` 的候选参数，再继续 `left roll/right pitch/right roll`。

## 测试范围

- 测试对象：`left_ankle_pitch_joint`
- 接触条件：
  - 早期数据包含“脚未完全着地”工况，仅用于确认信号链路与大致趋势
  - 最终结论以“脚完全着地”工况为准
- 固定条件：
  - `mode = step`
  - `step_amplitude_rad = 0.015`
  - `active_sec = 1.0`
  - `repeat_count = 3`
  - `publish_rate_hz = 1000`

## 阶段结果

| 对象 | 参数 | 工况 | 结果 | 结论 |
|---|---|---|---|---|
| `left pitch` | `kp=90, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.009277`，无超调、无过零、无振荡 | 可用，但主轴偏软 |
| `left pitch` | `kp=95, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.008566`，`steady_error ≈ -0.001597` | 劣于 `90/0.8`，排除 |
| `left pitch` | `kp=100, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.009178`，`peak_time_sec ≈ 0.055692`，无超调、无过零、无振荡 | 当前综合最优候选 |
| `left pitch` | `kp=105, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.009629`，但 `steady_error ≈ -0.001685`，`peak_time_sec ≈ 0.299386` | 增益有限，迟滞更明显，不优于 `100/0.8` |
| `left pitch` | `kp=100, kd=1.0` | 非最终一致工况 | 历史结果显示加大 `kd` 会压低响应 | 当前不作为优先方向 |

## 本轮结论

- `left_ankle_pitch_joint` 在“脚完全着地”工况下已完成一轮局部收敛。
- 当前候选参数定为：
  - `left ankle pitch: kp=100, kd=0.8`
- 本轮数据没有出现以下现象：
  - 超调
  - 过零
  - 衰减振荡
- 因此当前主问题不是阻尼不足，现阶段不优先增加 `kd`。
- `kp` 从 `100 -> 105` 后，主轴收益有限，但末段迟滞更明显：
  - `steady_error` 更负
  - `peak_time_sec` 变长
- 说明 `left pitch` 在完全着地工况下继续增大 `kp` 的收益已接近上限，不再继续向上扫描。
- 现阶段对 `left pitch` 的排序为：
  1. `kp=100, kd=0.8`
  2. `kp=105, kd=0.8`
  3. `kp=90, kd=0.8`
  4. `kp=95, kd=0.8`

## 后续动作

- 维持 `left pitch` 候选值 `kp=100, kd=0.8`
- 不再继续扫描更高 `kp`
- 暂不调整 `kd`
- 继续进入：
  - `left_ankle_roll_joint`
  - `right_ankle_pitch_joint`
  - `right_ankle_roll_joint`
- 待四个自由度都完成后，再判断：
  - 是否采用 `pitch/roll` 分轴参数
  - 是否需要再看 `lpf_conf.wc`
