# Round 3D Delay Chain Probe

状态：`active`。本专项用于回答一个更直接的问题：

1. 模型输出 `action` 到关节目标 `target` 是否存在明显延迟
2. 关节目标到关节位姿 `pos`、执行器电流 `current` 的响应延迟各是多少
3. 延迟主要出现在输出侧、踝侧，还是执行链侧

## 目标

把“感觉上不对”的问题拆成可测的时间链：

- `action -> target`
- `target -> current`
- `current -> pos`
- `target -> pos`

如果 `action -> target` 近似 0，而后两段有明显滞后，则优先怀疑执行链和机构，而不是 policy 输出本身。

## 数据口径

本轮先使用同一时间戳的三份历史日志：

- `t25_action_20260326_102002.csv`
- `t23_joint_20260326_102002.csv`
- `t3_current_20260326_102002.csv`

这组三份日志在字段上分别对应：

- `action_*`：模型输出
- `target_*`、`pos_*`、`vel_*`：关节目标与反馈
- `current_*`：执行器电流反馈

## 分析脚本

- [06_delay_chain_probe.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/06_delay_chain_probe.py:1)

## 通过标准

1. 给出 ankle / hip / knee 的分段延迟估计
2. 明确判断延迟主要在哪一段
3. 若当前日志不足以分辨 motor state 与 joint state，需要补录 `/actuator_states`

