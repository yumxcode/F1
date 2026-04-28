# Round 3 低速步态验证方案

状态：`draft only`。本方案仅作为 `Round 2` 收口后的候选执行稿，当前不得执行。

目标：在不改动策略模型与步态时序参数的前提下，仅替换 `rl_walk_leg` 的踝关节 `kp/kd` 为 `Round 2` 收敛候选值，验证真机低速行走的连续性、推进性和踝关节抖动是否改善。

## 本轮假设

- `Round 1` 的主要症状中，踝关节轻微抖动和推进不足可能主要来自并联踝关节闭环参数过软，而不是策略输出幅度本身。
- `Round 2` 已在完全着地工况下给出一组暂存候选值，但尚未完成悬空对照，因此这里只能先保留最小改动验证草案。
- 如果只改踝关节参数后，连续性或抖动已经明显改善，就没有必要立即引入 `lpf_conf.wc`、`action_scale` 等新变量。

## 采用参数

`rl_walk_leg`：
- `left_ankle_pitch_joint: kp=100, kd=0.8`
- `left_ankle_roll_joint: kp=80, kd=0.8`
- `right_ankle_pitch_joint: kp=100, kd=0.8`
- `right_ankle_roll_joint: kp=60, kd=0.8`

说明：
- 上述参数当前只是 `Round 2` 触地侧的暂存候选值，不代表最终收敛值。
- 只有当 `Round 2` 文档明确关闭后，才允许把这组参数写入真正执行轮。

保持不变：
- `action_scale = 0.5`
- `cycle_time = 0.7`
- `cmd_threshold = 0.05`
- `lpf_conf.wc = 100`

## 执行前检查

- 确认 [rl_x1.yaml](/Users/yumx/code/X1/agibot_x1_infer/src/module/control_module/cfg/rl_x1.yaml:326) 的 `rl_walk_leg` 参数已更新到本轮目标值。
- 确认 [deploy_info.json](/Users/yumx/code/X1/agibot_x1_infer/.oma/deploy_info.json:1) 与源码配置一致。
- 确认没有其他节点同时发布 `/joint_cmd`。
- 确认保护吊具、急停和扶持人员到位。

## 实验顺序

1. `zero -> stand -> hold`
2. `walk_leg` 零速命令，持续 `5 s`
3. `walk_leg` 前向 `x = 0.2 m/s`，持续 `10 s`
4. `walk_leg` 前向 `x = 0.3 m/s`，持续 `10 s`
5. 若第 4 步稳定，再执行 `x = 0.4 m/s`，持续 `10 s`

约束：
- 不在本轮同时测试横移、转向或 `walk_leg_arm`
- 任一步出现明显踝关节高频抖动、足端连续拍地或姿态失稳，立即退出并记录停止条件

## 重点观测项

- 连续行走时间是否从 `~10 s` 提升
- 步态是否仍然偏“踏步前进”
- 踝关节轻微抖动是否减弱、消失或转移到特定单侧/单轴
- 前进命令下是否出现新的左右不对称
- 身体俯仰、横摆是否因为分轴参数导致明显偏置

## 记录要求

- 至少记录每个速度档位的开始/结束时间和人工观察结论
- 若系统已有 gait/contact 日志，保留原始日志文件路径
- 结果文件需明确写出：
  - 是否通过 `low_speed_walk`
  - 最稳定速度档位
  - 最先暴露的问题类型
  - 是否需要进入 `lpf_conf.wc` 调整

## 决策规则

- 若 `x = 0.3 m/s` 可稳定维持，且踝抖明显减轻：
  - 将 `low_speed_walk` 标记为通过
  - 下一轮进入 `lateral_and_yaw`
- 若连续性改善但仍有可重复的踝高频抖动：
  - 保持当前 `kp/kd`
  - 下一轮优先测试 `lpf_conf.wc`
- 若比 `Round 1` 更差，或出现新的明显不对称：
  - 回查 `right roll = 60/0.8` 与左右脚分轴差异
  - 必要时回退到 `right roll = 70/0.8` 做对照轮
