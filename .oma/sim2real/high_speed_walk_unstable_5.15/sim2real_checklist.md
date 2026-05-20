# Sim2Real Checklist — high_speed_walk_unstable

_Algorithm: rl_walk_leg | Hardware: X1 | Policy: src/module/control_module/policy/rl_walk_leg.onnx_

关联资料:

- 部署基线: `.oma/deploy_info.json`
- RL 配置: `src/module/control_module/cfg/rl_x1.yaml`
- 控制器: `src/module/control_module/src/rl_controller.cc`
- 当前总结: `.oma/sim2real/high_speed_walk_unstable_5.15/SUMMARY.md`

## 当前状态

| 项目 | 当前值 |
|---|---|
| 当前 sim2real 轮次 | Round 1c |
| 当前轮状态 | analyzed; hold parameter escalation |
| 当前重点 | t27 Kp/Kd 45 real diagnostic |
| 当前问题 | 自研算法高速行走不稳 |
| Standalone warning | `.oma/best.json` 缺失，deploy gate advisory |

## 阶段总览

| 阶段 | 状态 | 目标 | 方案 | 最近结果 |
|---|---|---|---|---|
| context_and_contract_check | completed | 读取部署栈和当前配置，确认基线 | 本文件 + `SUMMARY.md` | `.oma/deploy_info.json` 已同步当前踝 `30/1.5` |
| initial_t23_screen | completed | 用现有 t23 日志筛查执行链压力，并完成 t23 sim/real 对比 | `scripts/analyze_t23_joint_tracking.py` | `results/round_00b_t23_sim_real_compare.md` |
| high_speed_boundary_and_logging | in_progress | 找当前参数稳定速度边界，并采集完整日志 | `plans/round_01_high_speed_boundary_and_logging.md` | `results/round_01c_t27_kpkd_45_real_diagnostic.md` |
| parameter_identification | in_progress | 按 Round 1 证据决定髋/膝/踝/节律辨识方向 | `plans/round_01b_hip_kpkd_response_test.md` | `results/round_01c_t27_kpkd_45_real_diagnostic.md` |
| fix_validation | pending | 对单一修复方向做 A/B 验证 | 待创建 | 待更新 |
| deployment_decision | pending | 决定 deploy / hold / return to design | 待创建 | 待更新 |

## 轮次索引

| 轮次 | 状态 | 目标 | 结果文件 |
|---|---|---|---|
| Round 0 | completed | 现有 t23 关节日志初筛 | `results/round_00_t23_initial_screen.md` |
| Round 0b | completed | t23 sim/real 关节跟踪对比 | `results/round_00b_t23_sim_real_compare.md` |
| Round 1 | planned | 高速边界与完整日志采集 | 待生成 |
| Round 1b E1 | analyzed; hold | hip_pitch `60/6` + hip_yaw `45/7` 响应增强 A/B 实验 | `results/round_01b_e1_kpkd_real_compare.md` |
| Round 1c | analyzed; hold | t27 full log for Kp/Kd `45/3,45/3,45/4,80/10,30/1.5,30/1.5` | `results/round_01c_t27_kpkd_45_real_diagnostic.md` |
| Round 1d | completed | 所有关节 target hit 与 pos 跟随独立分析 | `results/round_01d_all_joint_target_hit_pos_following.md` |

## 当前结论

- t23 sim/real 对比显示 real 平均 RMS 是 sim 的 `1.43x`，mean best-delay correlation 从 `0.757` 降到 `0.231`。
- 最大 real-minus-sim gap 集中在髋 pitch、膝和髋 yaw；当前不应默认沿用上一轮“踝关节是唯一主因”的结论。
- sim/real target range 不完全一致，尤其 real 髋 pitch/yaw 目标幅值明显更大；下一轮必须做 matched-condition 复采。
- 若做部署侧参数实验，优先执行 `round_01b_hip_kpkd_response_test.md` 中的 E1: hip_pitch `50/5 -> 60/6`，hip_yaw `35/6 -> 45/7`，hip_roll 暂不改。
- Round 1 必须采集 t27 类完整诊断日志: cmd、phase、action、pos、pos_des、tau、parallel flag、IMU、接触或可推断 touchdown 信息、视频时间点。
- Round 1c t27 显示当前 Kp/Kd 45 配置缓解了 `right_hip_roll` 正向饱和，但 hip_roll 仍低响应；`left_hip_roll` 上限 hit `59.6%`，零 yaw 命令下 yaw range `0.736 rad`，left/right contact fraction `0.136/0.669`。不建议继续直接加 hip_roll Kp，下一步优先查 yaw/roll/contact 耦合和 `cycle_time=0.55`。
- Round 1d 单独梳理所有关节 target hit 与 pos 跟随: clamp 主导为 `right_ankle_pitch_joint`、`left_hip_roll_joint`、`left_ankle_pitch_joint`; 低实现但非 clamp 主导为 `right_hip_roll_joint`、`left_hip_pitch_joint`、`right_hip_pitch_joint`; 下一轮用该表作为 pass/fail dashboard。

## 维护规则

- 本文件只维护总览，不写大段实验细节。
- 具体方案写到 `plans/`。
- 每轮结果写到 `results/round_NN_{desc}.md`。
- 每完成一轮: 更新当前轮次、状态、阶段总览、轮次索引、当前结论。
