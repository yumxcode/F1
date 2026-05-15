# Sim2Real Ankle 关键指标差值汇总

## 读法

- 差值统一定义为 `Δ = real - sim`。
- 正值表示真机更大，负值表示仿真更大。
- 28 号报告负责前 6 步窗口级分析：延迟、amplitude_gain、target 换向频率、触地姿态。
- `claude_stability_metrics_v2` 负责全文件频域/残差分析：`fn_swing_hz`、`fn_stance_hz`、`zeta_hat`、`tau_hat_ms`、`PM_theory_deg`。
- `zeta_hat` 不是严格阶跃响应阻尼比，只能看作步态接地后残差 envelope 衰减指标。真实 step 响应无超调时，应优先相信 step 响应对闭环阻尼的判断。

## 1. 专门延迟分析

来源：`28_forward_x_failure_first6_step_detailed_report.md`，差分互相关，按 swing / touchdown 窗口统计。

| window | axis | real lag ms | sim lag ms | Δ lag ms | real corr | sim corr | 判断 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| swing | ankle_pitch | 76.0 | 80.2 | -4.2 | 0.306 | 0.427 | real/sim 延迟量级接近 |
| swing | ankle_roll | 77.3 | 56.9 | +20.4 | 0.379 | 0.696 | real roll 略慢，但不是主要 gap |
| touchdown | ankle_pitch | 21.0 | 16.9 | +4.1 | 0.058 | 0.425 | touchdown pitch 相关性低，延迟仅作参考 |
| touchdown | ankle_roll | 22.5 | 29.6 | -7.1 | 0.252 | 0.525 | touchdown 延迟差异不大 |

结论：延迟是 roll 自激的必要背景条件，但 real 与 sim 延迟量级接近，不能单独解释“真机抖、仿真不抖”。真机多出来的是机械弹性储能、冲击能量注入和低阻尼通道。

## 2. Amplitude Gain

来源：28 号报告，`amplitude_gain = joint_amp / target_amp`，只统计 `target_amp >= 10 mrad` 的有效周期。这个指标更适合观察“欠跟踪、过跟踪、自激/谐振风险”，比频域 `transfer_gain` 更贴近前 6 步窗口现象。

| window | axis | real gain | sim gain | Δ gain | 判断 |
| --- | --- | ---: | ---: | ---: | --- |
| swing | ankle_pitch | 1.26 | 0.52 | +0.74 | real 接近/略过跟踪，sim 明显欠幅值响应 |
| swing | ankle_roll | 1.38 | 0.37 | +1.01 | real roll 响应强且离散，sim roll 摆动响应严重不足 |
| touchdown | ankle_pitch | 1.26 | 0.40 | +0.86 | real 落地 pitch 有冲击过冲，sim 接触过刚 |
| touchdown | ankle_roll | 1.10 | 0.68 | +0.42 | real touchdown roll 更容易被冲击放大 |

补充关键比值：

| 指标 | real | sim | Δ | 判断 |
| --- | ---: | ---: | ---: | --- |
| touchdown ankle_pitch joint_range / target_range | 2.843 | 0.365 | +2.478 | real 落地期 pitch 大幅过冲，sim 欠响应 |
| swing ankle_roll tracking ratio | 0.765 | 0.202 | +0.563 | sim 摆动 roll 建模明显偏弱 |
| ankle_roll 自激点数量 `ratio > 1` | 7 | 0 | +7 | 真机存在额外能量通道，sim 没有复现 |

判断：这组指标支持“真机 ankle roll 存在低阻尼/负阻尼自激通道”。增加 `Kd` 后稳定很多，与该判断一致：`Kd` 增大后能耗散弹性释放和接触冲击注入的能量，roll 剧烈抖动消失。

## 3. Target 换向频率

来源：28 号报告。`target dir_chg` 可粗略观察小窗口内控制指令频率，`joint dir_chg` 可观察实际响应频率。换向频率约为振荡频率的 2 倍。

| window | axis | real target Hz | sim target Hz | Δ target Hz | real joint Hz | sim joint Hz | Δ joint Hz | 判断 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| swing | ankle_pitch | 22.3 | 16.7 | +5.6 | 7.8 | 9.6 | -1.8 | real target 更抖，但 joint 被机械低通压住 |
| swing | ankle_roll | 32.4 | 24.6 | +7.8 | 13.8 | 14.0 | -0.2 | real roll target 高频更重，joint 响应频率相近 |
| touchdown | ankle_pitch | 23.7 | 12.4 | +11.3 | 6.4 | 3.7 | +2.7 | real touchdown target 高频明显更强 |
| touchdown | ankle_roll | 36.6 | 24.8 | +11.8 | 11.5 | 7.5 | +4.0 | real 落地 roll 被更强高频 target 激励 |

带宽判断：

| 项 | real | sim | Δ | 判断 |
| --- | ---: | ---: | ---: | --- |
| swing target 振荡频率约值 | 11-18 Hz | 8-12 Hz | real 高 3-6 Hz | 两者都远超 76 ms 延迟下约 3.28 Hz 稳定带宽 |
| real target 高频超限倍数 | 3-5x | 2-4x | real 更严重 | target 低通/动作平滑仍是关键措施 |

判断：高频 target 是激励源，`Kd` 增大只能提高耗散，不能从根上降低输入频率。因此 KD 有效但最好同时做 target smoothing 或 action LPF。

## 4. 触地姿态分析

来源：28 号报告。这里保留最能解释触地冲击和 roll 失稳的指标。

| 指标 | real | sim | Δ | 判断 |
| --- | ---: | ---: | ---: | --- |
| touchdown ankle_pitch mean 平均值 | -0.119 rad | -0.232 rad | +0.113 rad | 真机落地背屈少约 6.5 deg，缓冲不足 |
| touchdown knee_pitch std 范围 | 0.071-0.233 rad | 0.017-0.054 rad | +0.054 到 +0.179 rad | 真机膝落地一致性差 |
| touchdown ankle_pitch std 范围 | 0.070-0.161 rad | 0.017-0.070 rad | +0.053 到 +0.091 rad | 真机踝 pitch 落地离散更大 |
| touchdown ankle_roll std 范围 | 0.098-0.155 rad | 0.020-0.134 rad | +0.021 到 +0.078 rad | 真机 roll 离散偏大，但 sim 5008 已接近 |

关键异常点：

| case / step | real | sim 对照 | Δ | 判断 |
| --- | ---: | ---: | ---: | --- |
| 35/0.5 step4 TD sole_roll | -17.5 deg | -0.1 deg | -17.4 deg | 右踝锁死后脚掌严重内翻，关节角 0 掩盖真实姿态 |
| 35/0.5 step5 SP sole_roll | -35.8 deg | -13.9 deg | -21.9 deg | 支撑踝极度内翻，稳定性已失效 |
| 40/0.8 step6 TD ank_roll | +23.6 deg | -1.0 deg | +24.6 deg | 右踝外翻与目视翻机一致 |
| 40/0.8 step6 TD sole_roll | +12.6 deg | 0.0 deg | +12.6 deg | 脚掌实际外翻，触地冲击和 roll 失稳叠加 |

判断：触地姿态数据支持“真机落地冲击更强、roll 姿态更容易累积并失稳”。增加 `Kd` 后稳定，说明真机需要更多耗散来压住 touchdown 后的弹性释放和冲击回弹。

## 5. 频率与残差阻尼指标

来源：`claude_stability_metrics_v2_summary.csv`，匹配 case 只比较 `25/0.4` 和 `35/0.5`。

| case | axis | real fn_swing | sim fn_swing | Δ fn_swing | real fn_stance | sim fn_stance | Δ fn_stance | real zeta_hat | sim zeta_hat | Δ zeta | real tau_hat | sim tau_hat | Δ tau | 判断 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 25/0.4 | ankle_pitch | 3.456 | 3.226 | +0.230 | 3.297 | 3.261 | +0.036 | 0.082 | 0.347 | -0.265 | 583.9 | 182.3 | +401.6 | real 残差衰减更慢，但该 zeta 不是 step 阻尼 |
| 25/0.4 | ankle_roll | 3.456 | 3.226 | +0.230 | 3.846 | 3.804 | +0.042 | 0.279 | 0.080 | +0.198 | 214.4 | 552.2 | -337.8 | roll 的残差阻尼方向与 pitch 不一致 |
| 35/0.5 | ankle_pitch | 4.278 | 3.696 | +0.581 | 3.279 | 3.261 | +0.018 | 0.102 | 0.307 | -0.204 | 479.5 | 186.0 | +293.6 | real pitch 残差慢衰减，且 35/0.5 有失效事件污染 |
| 35/0.5 | ankle_roll | 2.869 | 3.696 | -0.827 | 3.279 | 3.805 | -0.526 | 0.145 | 0.113 | +0.032 | 361.2 | 372.3 | -11.1 | roll 残差 zeta 接近，不支持单靠该指标判定 |

解释：

- `fn_swing_hz` 和 `fn_stance_hz` 没有显示 real 存在一个远高于 sim 的单一主频。
- `zeta_hat` 是 touchdown residual envelope 拟合，不是阶跃响应阻尼比。
- 因此，“真机 ankle 欠阻尼，增加 KD 后明显稳定”这个工程判断，主要应由 amplitude_gain、自激点、触地姿态、roll 抖动消失来支撑，而不是由 `zeta_hat` 单独支撑。

## 6. 理论相位裕度与 Kd

来源：`claude_stability_metrics_v2_summary.csv`，理论值由 `Kp/Kd/J_eff_default` 计算。匹配 real/sim 同 Kp/Kd 时理论值相同，所以这里不做 real-sim 差值，而看随 Kd 的变化。

| Kp/Kd | fn_theory_hz | zeta_theory | tau_theory_ms | PM_theory_deg | 判断 |
| --- | ---: | ---: | ---: | ---: | --- |
| 25/0.4 | 2.562 | 0.1288 | 482.5 | 14.67 | 理论阻尼低，相位裕度小 |
| 30/0.4 | 2.806 | 0.1176 | 482.5 | 13.41 | Kp 增大但 Kd 不变，阻尼比更低 |
| 35/0.5 | 3.031 | 0.1360 | 386.0 | 15.49 | 仍是低阻尼 |
| 40/0.8 | 3.240 | 0.2036 | 241.3 | 23.00 | Kd 提高后理论阻尼和相位裕度明显改善 |
| 50/0.8 | 3.623 | 0.1821 | 241.3 | 20.63 | Kp 继续增大后阻尼比回落 |

判断：你观察到“增加 Kd 后稳定很多、ankle roll 不再剧烈抖动”，与理论表一致。`Kd` 提高会增加阻尼比、缩短衰减时间、提高相位裕度；这正好压制真机 roll 轴的弹性释放和接触冲击后振荡。

## 7. 总结判断

| 问题 | 证据 | 判断 |
| --- | --- | --- |
| 真机 ankle 是否有严重低阻尼/负阻尼问题 | `amplitude_gain` real > sim、real 有 7 个 `ratio > 1` 自激点、Kp40 step6 roll 失控、增加 Kd 后稳定 | 是，尤其在 ankle_roll 与 touchdown 后残余能量上 |
| sim 是否复现该问题 | sim gain 低、无自激点、roll 响应过刚/欠建模 | 没有充分复现 |
| 延迟是否是主要 real-sim 差异 | swing/TD lag real/sim 量级接近 | 不是差异主因，但它是负阻尼机制的背景条件 |
| target 高频是否重要 | real target dir_chg 比 sim 高 30% 以上，且两者都超带宽 | 是，建议继续做 action/target 低通 |
| 触地是否重要 | real touchdown pitch 过冲、sole_roll 大角度异常、35/0.5 锁死 | 是，接触冲击是触发器 |
| 单看 `zeta_hat` 是否能证明欠阻尼 | `zeta_hat` 方向混杂，且不是 step 阻尼 | 不能单独作为结论依据 |

最终结论：当前更稳妥的表述是，真机 ankle，尤其 ankle_roll，在前进行走中存在“低阻尼/负阻尼自激通道”：高频 target 与控制延迟提供相位亏欠，真实传动弹性和触地冲击提供能量，`Kd` 不足时 roll 振荡会被放大。增加 `Kd` 后稳定很多，是对这个机制的强支持。sim 当前更偏过刚、欠幅值响应，缺少真实弹性和冲击能量注入，因此没有复现真机的严重 roll 抖动。
