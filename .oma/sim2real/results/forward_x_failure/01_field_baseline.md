# Round 1 实机实验结果

轮次目标：完成基础部署链路验证，确认站立与 RL 小速度初测是否可用。

统一进展和指标口径见 [00_forward_x_failure_progress_review.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/00_forward_x_failure_progress_review.md:1)。

## 阶段结果

| 阶段 | 结果 | 结论 | 后续动作 |
|---|---|---|---|
| `sensor_and_sign_check` | 均无问题 | 传感器链路、关节顺序、符号方向、零位基础检查通过 | 进入站立与 RL 测试 |
| `zero -> stand -> hold` | 均无问题 | 基础 PD 站立稳定，无明显过冲或抖动问题 | 保持当前 `pd_zero/pd_stand` 不变 |
| `rl_idle_and_in_place_step` | 给 `x = 0.4 m/s` 小速度命令后可正常行走，但连续行走时间不长，约 `10 s`；行走姿态偏踏步前进；踝关节有轻微抖动；动作幅度正常 | 当前问题集中在踝关节轻微抖动和步态推进性不足，暂不优先调整 `action_scale` | 先做踝关节 `kp/kd` 辨识，再决定优先调整 `kd`、`kp` 还是 `lpf_conf.wc` |

## 本轮结论

- 基础部署链路已跑通。
- 真机已具备进入踝关节 `kp/kd` 辨识的条件。
- 现阶段优先关注：
  - 踝关节轻微抖动
  - 行走连续性不足，约 `10 s`
  - 行走形态偏踏步前进
- 现阶段暂不建议优先修改：
  - `action_scale`
  - `pd_zero/pd_stand`

## 指标字典

| 指标 / 现象 | 含义 | 当前用途 |
|---|---|---|
| `sensor_and_sign_check` | 传感器、关节顺序、符号和零位基础检查 | 确认不是基础链路错误 |
| `zero -> stand -> hold` | 零位、站立位、保持站立流程 | 确认 PD 站立基础稳定 |
| `rl_idle_and_in_place_step` | RL 小速度初测 | 暴露前进不足和踝轻微抖动 |
| `action_scale` | 策略输出到关节目标的缩放 | 当前不是第一优先修改项 |
