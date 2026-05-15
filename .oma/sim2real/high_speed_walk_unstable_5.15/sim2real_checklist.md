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
| initial_t23_screen | completed | 用现有 t23 日志筛查执行链压力 | `scripts/analyze_t23_joint_tracking.py` | `tables/t23_joint_tracking_summary.md` |
| high_speed_boundary_and_logging | planned | 找当前参数稳定速度边界，并采集完整日志 | `plans/round_01_high_speed_boundary_and_logging.md` | 待实机 |
| parameter_identification | pending | 按 Round 1 证据决定髋/膝/踝/节律辨识方向 | 待创建 | 待更新 |
| fix_validation | pending | 对单一修复方向做 A/B 验证 | 待创建 | 待更新 |
| deployment_decision | pending | 决定 deploy / hold / return to design | 待创建 | 待更新 |

## 轮次索引

| 轮次 | 状态 | 目标 | 结果文件 |
|---|---|---|---|
| Round 0 | completed | 现有 t23 关节日志初筛 | `results/round_00_t23_initial_screen.md` |
| Round 1 | planned | 高速边界与完整日志采集 | 待生成 |

## 当前结论

- 当前证据不足以判定高速不稳根因。
- t23 初筛显示最大执行压力在髋/膝，不应默认沿用上一轮“踝关节是唯一主因”的结论。
- Round 1 必须采集 t27 类完整诊断日志: cmd、phase、action、pos、pos_des、tau、parallel flag、IMU、接触或可推断 touchdown 信息、视频时间点。

## 维护规则

- 本文件只维护总览，不写大段实验细节。
- 具体方案写到 `plans/`。
- 每轮结果写到 `results/round_NN_{desc}.md`。
- 每完成一轮: 更新当前轮次、状态、阶段总览、轮次索引、当前结论。
