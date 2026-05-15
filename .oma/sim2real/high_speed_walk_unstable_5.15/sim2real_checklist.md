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
| 当前 sim2real 轮次 | Round 1 |
| 当前轮状态 | planned |
| 当前重点 | high_speed_boundary_and_logging |
| 当前问题 | 自研算法高速行走不稳 |
| Standalone warning | `.oma/best.json` 缺失，deploy gate advisory |

## 阶段总览

| 阶段 | 状态 | 目标 | 方案 | 最近结果 |
|---|---|---|---|---|
| context_and_contract_check | completed | 读取部署栈和当前配置，确认基线 | 本文件 + `SUMMARY.md` | `.oma/deploy_info.json` 已同步当前踝 `30/1.5` |
| initial_t23_screen | completed | 用现有 t23 日志筛查执行链压力，并完成 t23 sim/real 对比 | `scripts/analyze_t23_joint_tracking.py` | `results/round_00b_t23_sim_real_compare.md` |
| high_speed_boundary_and_logging | planned | 找当前参数稳定速度边界，并采集完整日志 | `plans/round_01_high_speed_boundary_and_logging.md` | 待实机 |
| parameter_identification | planned | 按 Round 1 证据决定髋/膝/踝/节律辨识方向 | `plans/round_01b_hip_kpkd_response_test.md` | 待实机 |
| fix_validation | pending | 对单一修复方向做 A/B 验证 | 待创建 | 待更新 |
| deployment_decision | pending | 决定 deploy / hold / return to design | 待创建 | 待更新 |

## 轮次索引

| 轮次 | 状态 | 目标 | 结果文件 |
|---|---|---|---|
| Round 0 | completed | 现有 t23 关节日志初筛 | `results/round_00_t23_initial_screen.md` |
| Round 0b | completed | t23 sim/real 关节跟踪对比 | `results/round_00b_t23_sim_real_compare.md` |
| Round 1 | planned | 高速边界与完整日志采集 | 待生成 |
| Round 1b | planned | hip Kp/Kd 响应增强 A/B 实验 | 待生成 |

## 当前结论

- t23 sim/real 对比显示 real 平均 RMS 是 sim 的 `1.43x`，mean best-delay correlation 从 `0.757` 降到 `0.231`。
- 最大 real-minus-sim gap 集中在髋 pitch、膝和髋 yaw；当前不应默认沿用上一轮“踝关节是唯一主因”的结论。
- sim/real target range 不完全一致，尤其 real 髋 pitch/yaw 目标幅值明显更大；下一轮必须做 matched-condition 复采。
- 若做部署侧参数实验，优先执行 `round_01b_hip_kpkd_response_test.md` 中的 E1: hip_pitch `50/5 -> 60/6`，hip_yaw `35/6 -> 45/7`，hip_roll 暂不改。
- Round 1 必须采集 t27 类完整诊断日志: cmd、phase、action、pos、pos_des、tau、parallel flag、IMU、接触或可推断 touchdown 信息、视频时间点。

## 维护规则

- 本文件只维护总览，不写大段实验细节。
- 具体方案写到 `plans/`。
- 每轮结果写到 `results/round_NN_{desc}.md`。
- 每完成一轮: 更新当前轮次、状态、阶段总览、轮次索引、当前结论。
