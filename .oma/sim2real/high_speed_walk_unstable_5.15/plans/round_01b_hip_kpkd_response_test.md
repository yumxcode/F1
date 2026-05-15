# Round 01b Hip Kp/Kd Response Test

_Date: 2026-05-15 | Issue: high_speed_walk_unstable_5.15 | Target config: `src/module/control_module/cfg/rl_x1.yaml`_

## Goal

验证提高 hip 关节 PD 增益是否能改善 real 中 hip 执行响应，并观察高速行走稳定性是否改善。

本实验只验证 deployment-side 参数，不改策略、不改 `action_scale`、不改 `cycle_time`。

## Current Active Baseline

当前 `rl_walk_leg` 活跃配置为 1.2m/s 配置，不是 `.oma/deploy_info.json` 中记录的旧 `cycle_time=0.7`:

| Joint group | Current Kp | Current Kd |
|---|---:|---:|
| hip_pitch | `50.0` | `5.0` |
| hip_roll | `40.0` | `3.0` |
| hip_yaw | `35.0` | `6.0` |
| knee_pitch | `80.0` | `10.0` |
| ankle_pitch | `20.0` | `1.5` |
| ankle_roll | `30.0` | `1.5` |

当前 `cycle_time=0.55`，`action_scale=0.5`。

## Evidence From t23 Sim/Real Compare

| Observation | Evidence | Implication |
|---|---|---|
| hip_pitch real gap 最大 | hip_pitch RMS real/sim `2.61x`, corr `0.878 -> 0.178` | 应优先提高 hip_pitch 跟踪能力 |
| hip_yaw real target 更激进且响应下降 | hip_yaw RMS real/sim `1.84x`, target range real/sim `2.37x` | hip_yaw 可小幅提高响应，但需防止 yaw-roll 耦合 |
| hip_roll 在 sim 和 real 都低响应 | pos/target 约 `0.13~0.15` | 不建议第一轮大幅提高 hip_roll；先隔离 pitch/yaw |
| knee 也有明显 gap | knee RMS real/sim `2.02x` | 本轮先不改 knee，避免同时改变摆腿落脚与支撑刚度 |

## Recommended Experiment Order

### E0 Baseline Repeat

先用当前配置复跑一次短程，采集 t23 或完整日志。

目的:

- 确认当前配置下问题可复现。
- 给 E1/E2 提供同日地面、同电量、同温度、同操作输入的 baseline。

### E1 Recommended First Change: hip_pitch + hip_yaw, leave hip_roll unchanged

这是建议优先执行的参数。只提高最大 gap 的 hip_pitch 和 hip_yaw，保持 hip_roll 不变，降低横向/roll 通道突然变硬导致侧向发散的风险。

```yaml
    stiffness:  [60.0, 40.0, 45.0,  80.0,  20.0, 30.0,
                 60.0, 40.0, 45.0,  80.0,  20.0, 30.0]
    damping:    [6.0,  3.0,  7.0,   10.0,  1.5,  1.5,
                 6.0,  3.0,  7.0,   10.0,  1.5,  1.5]
```

Rationale:

- hip_pitch: `50/5 -> 60/6`，Kp +20%，Kd 同步增加，避免只加 Kp 导致超调和高频振荡。
- hip_yaw: `35/6 -> 45/7`，Kp +29%，Kd 小幅增加，避免 yaw 响应提高后横摆摆动变大。
- hip_roll 保持 `40/3`，因为其低响应在 sim 中也存在，第一轮不应把它与 real-only 执行链问题混在一起。

### E2 Add hip_roll only if E1 improves forward tracking but still shows roll instability

如果 E1 后 hip_pitch/yaw tracking 改善，但视频或 IMU 显示机身 roll 仍明显发散，再加入 hip_roll 中等增强。

```yaml
    stiffness:  [60.0, 50.0, 45.0,  80.0,  20.0, 30.0,
                 60.0, 50.0, 45.0,  80.0,  20.0, 30.0]
    damping:    [6.0,  4.0,  7.0,   10.0,  1.5,  1.5,
                 6.0,  4.0,  7.0,   10.0,  1.5,  1.5]
```

Rationale:

- hip_roll: `40/3 -> 50/4`，先做 +25% Kp、+33% Kd 的保守提高。
- 不建议第一轮直接用注释中的 `hip_roll=60, kd=3`，因为 Kp 大幅上升但 Kd 不变会降低相对阻尼，更容易把侧向接触冲击放大。

### E3 Fallback if E1 becomes sharper but oscillatory

如果 E1 出现高频抖动、落脚冲击明显增加、髋部发热或电流升高，回退到半步参数。

```yaml
    stiffness:  [55.0, 40.0, 40.0,  80.0,  20.0, 30.0,
                 55.0, 40.0, 40.0,  80.0,  20.0, 30.0]
    damping:    [6.0,  3.0,  7.0,   10.0,  1.5,  1.5,
                 6.0,  3.0,  7.0,   10.0,  1.5,  1.5]
```

Rationale:

- Kp 降低，但保留较高 Kd，判断问题是响应不足还是阻尼不足。

## Do Not Use As First Test

不建议第一轮直接切到配置文件注释中的 1.35m/s 增益:

```yaml
# stiffness:  [60.0, 60.0, 60.0, 150.0, 40.0, 35.0, ...]
# damping:    [5.0,  3.0,  5.0,  12.0,  1.0,  1.0,  ...]
```

原因:

- 同时改变 hip、knee、ankle，无法归因。
- knee Kp 从 `80` 到 `150`，会强烈改变支撑/摆腿动态。
- hip_yaw Kd 从当前 `6` 降到 `5`，与“提高响应同时保持阻尼”的目标不一致。
- ankle Kp/Kd 也被改动，会重新引入上一轮已处理过的踝部变量。

## Test Protocol

每组参数都按同样流程执行:

1. 原地 RL idle 5-10 s，确认无髋部高频抖动和异常电流。
2. 低速短走，确认左右对称、无明显 foot slap。
3. 进入目标高速前，使用同一命令 ramp，不要手动快速阶跃。
4. 每组只跑短窗口，出现 roll 快速增大、髋部振荡、脚尖拖地、过热、电流异常立即停止。
5. 每组至少记录 t23；最好记录 t27/full log: `cmd`、`phase`、`action`、`pos_des_raw`、`pos`、`tau/effort`、IMU、contact 或视频同步点。

## Pass / Fail Criteria

E1/E2 可继续推进的条件:

- hip_pitch RMS 或 aligned tracking error 下降至少 `15-20%`。
- hip/knee delay 没有继续增大。
- IMU roll/pitch 没有比 baseline 更快发散。
- 无新增髋部高频抖动、过热、电流异常。

判定失败或回退的条件:

- 走得更硬但更不稳。
- touchdown 冲击明显变大。
- hip_roll/yaw 出现左右摆振。
- tracking RMS 没下降，corr 也没有改善。

## Recommendation

优先执行 E1。若 E1 提升 hip tracking 且没有新增振荡，再执行 E2。若 E1 出现冲击或振荡，执行 E3 或回退 baseline，不要继续增大 Kp。
