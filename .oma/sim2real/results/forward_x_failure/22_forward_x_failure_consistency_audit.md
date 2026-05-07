# 22 Forward X Failure Consistency Audit

日期：2026-05-06

目的：基于今天新增的 sim 多 `kp/kd` 工况事实，统一审查 `forward_x_failure` plan / results，清理旧判断中的错误读法，明确当前现状和下一步。

## 今天新增的关键事实

1. sim 阶段多个 `kp/kd` 工况均能正常往前走。
2. sim 视觉上只有左脚存在轻微 roll 外翻残余。
3. sim 的 swing / touchdown 阶段无明显抖动。
4. 旧版 sim `03/06` 曾把 sim 大量判成 `severe_foot_flat_touchdown / command_not_flat`，这与视频事实冲突。
5. 复审后确认：旧版 `03` 和部分 `05` 推断受到 raw FK foot-frame 固定偏置污染，不能再把 raw `link_*_ankle_roll` 姿态直接当作真实脚底接触平面。

## 已清除的旧判断

以下判断只能作为历史过程记录，不能再作为当前主结论：

| 旧判断 | 当前状态 | 替代口径 |
|---|---|---|
| real `8/8 severe_foot_flat_touchdown` | superseded | 校准后 real 仍有可观 touchdown residual，但不是旧版 `1.6~1.9 rad` 级别 |
| real `8/8 roll dominant` | superseded | 校准后 real `03` 为 `pitch 6/8, roll 2/8` |
| sim 复现了严重 roll 主导斜脚 touchdown | superseded | sim 能稳定前走，仅左脚轻微外翻，且 residual 不足以触发 failure |
| sim 主因偏 `command_not_flat` | superseded | 旧版判因受 raw foot-frame 偏置污染；sim 主标签应以 `residual_not_large_enough` 为主 |
| `05C` 强收口为 `fk_foot_frame_residual_candidate 3/4` | superseded | 校准后 `05C` 分散到 `mapping_workpoint_residual / mixed_or_uncertain_contact_residual / pitch_roll_coupled_contact_residual / contact_geometry_residual` |
| 继续扫 `kp/kd` 是第一入口 | superseded | `kp` 是抖动放大器，不是 residual 越界根因 |

## 当前有效事实链

当前统一采用 [21_real_vs_sim_combined_conclusion.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/21_real_vs_sim_combined_conclusion.md:1) 的收口：

> `real forward_x_failure` 不是单一的 roll 外翻、单一 output 延迟或单一 `kp/kd` 问题，而是 touchdown 几何 / 接触残差已经越过 sim 稳定前走时的可接受包络，并与执行链 `state -> joint -> sole` 残差放大叠加；高 `kp` 进一步把这种越界残差表现成 swing / touchdown 阶段更重的真实 joint 抖动，尤其 touchdown 最明显，最终破坏有效支撑和前向推进。

分线事实：

| 子线 | 当前有效结论 |
|---|---|
| `15/17` sim 复审 | sim 多 `kp/kd` 都能前走；左脚轻微外翻可接受；旧版 sim `command_not_flat` 读法失效 |
| `16` real 审计 | real 旧版 `03/05` 被 frame 偏置污染；校准后仍有 residual，但主轴和强度必须降级重读 |
| `18` residual 包络 | real 超出 sim 可接受包络，最稳定的是双侧 pitch residual、右脚不再水平、左脚 roll 峰值偏大、`joint -> sole` 放大链过重 |
| `19` 执行链 | output 不是主瓶颈；real 主滞后更靠近 `state -> joint`，且 swing 期已存在 |
| `20/24/25` touchdown / 抖动 | 旧 ankle-pitch 低速 contact proxy 已确认会污染早期 touchdown 序列；改用 FK 足端高度/速度 + hip pitch 相位校验后，real/sim 周期一致，real 仍表现为更大的 joint range/path/track err；pitch touchdown 高频结论降级，roll touchdown 仍是最重异常点 |
| `21` 合并结论 | residual 越界 + 执行链兑现残差 + 高 `kp` 抖动放大共同导致 failure |

## Plan / Result 一致性审查结果

| 文档 | 审查处理 |
|---|---|
| `plans/00_problem_and_overall_plan.md` | 已作为当前总入口，删除“severe_foot_flat_touchdown 为当前主假设”的有效地位，改为引用 21/22 |
| `plans/01_landing_window_diagnosis.md` | 已标记为历史诊断计划；旧 `severe_foot_flat_touchdown` 只保留为 pre-audit 过程记录 |
| `plans/02_low_speed_walk_validation_candidate.md` | 继续 blocked；阻塞原因更新为 `05D foot/contact frame` 未完成 |
| `plans/03_ankle_landing_attitude_resolution.md` | 已标记为 pre-audit 专项；旧 roll 主导、`command_not_flat 4` 不再作为当前修复入口 |
| `plans/05_coupled_geometry_probe.md` | 已更新为当前第一优先级：`05D FK Foot-Frame / Contact` 现场复核 |
| `results/02_round3_landing_window_diagnosis.md` | 已有 audit note；旧 `8/8 severe` 保留为历史过程，不再作为当前结论 |
| `results/03_ankle_landing_attitude_resolution.md` | 已有 audit note；以后引用时优先引用 `16/18/21/22` |
| `results/05_coupled_geometry_probe.md` | 已有 audit note；旧强 `05C` 收口降级 |
| `results/15_sim_t27_03_06_analysis.md` | 已标记 superseded by `17`；旧 sim 严重斜脚结论失效 |
| `results/16-21` | 作为当前有效证据链 |

## 当前现状

1. 真机 failure 现象仍成立：x 前进不足，视觉 roll 方向触地/抖动，降 `kp` 后抖动减轻但仍不能恢复前进。
2. sim failure 不成立：多 `kp/kd` 工况均能正常前进，左脚轻微外翻属于可接受 residual。
3. 旧 raw FK foot-frame 直接判定脚底平面的做法已经失效。
4. 当前 real 的关键异常不是“有 roll 外翻”，而是 residual 已越过 sim 可接受包络，并叠加执行链兑现残差与 touchdown 抖动放大。
5. 当前没有证据支持 output 链是第一主因。
6. 当前没有证据支持继续盲扫 `kp/kd` 是第一主线。

## 下一步工作

第一优先级：执行 `05D FK Foot-Frame / Contact` 现场复核。

目标：确认 `joint -> sole residual` 的物理含义，区分下面三类：

1. `foot_frame_reference_mismatch`：FK foot body frame 与真实脚底平面不一致。
2. `real_contact_edge_bias`：真实足底接触边缘 / 接触线与模型定义不一致。
3. `dynamic_contact_deformation_or_release`：接触负载下出现动态变形、回差释放或传动兑现异常。

建议执行顺序：

1. 静态 frame 校验：站立或悬空小幅 roll/pitch 扫描，记录 FK `sole_roll/pitch` 与真实脚底平面测量方向是否一致。
2. 动态低速 touchdown 复核：当前低风险配置下采前 `4~8` 个 touchdown，同步日志和正/侧视视频。
3. 同轨迹 sim replay：尽量用 real 命令、phase 和目标轨迹回放，判断 sim 是否产生同方向 residual。
4. 复判修复入口：只有在 `05D` 之后，才决定是修 foot/contact 建模、执行链兑现，还是策略 touchdown 姿态目标。

当前禁止项：

1. 不再把“看到 roll 触地”直接当主因。
2. 不再把 sim `03` 旧判因当 failure 证据。
3. 不再以 `kp/kd` 扫参作为第一修复入口。
4. 不再直接用 raw FK foot body 姿态当真实脚底接触平面。
