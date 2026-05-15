# claude_stability_metrics_v2 统计汇总

## 数据与方法

- 输入：`test_logs/data_csv/*.csv` 和 `test_logs/data_csv/sim/*.csv` 中的 8 个 T27 轨迹文件。
- 指标：raw / lpf 参考分开统计，摆动相频率按 phase-gated 窗口估计，支撑相阻尼按 touchdown envelope 拟合，延迟按逐窗口相关统计。
- 结果文件：`claude_stability_metrics_v2_detail.csv`、`claude_stability_metrics_v2_summary.csv`、`claude_stability_metrics_v2_real_sim_compare.csv`。

## 指标释义

- `e_rms_rad`：关节跟踪误差 RMS，单位 rad。
- `e_rms_delay_aligned_rad`：按 `delay_ms_median` 对齐 target / pos 后重新计算的关节跟踪误差 RMS，单位 rad。
- `fn_swing_hz`：摆动相主频，单位 Hz。
- `fn_stance_hz`：接地后振铃主频，单位 Hz。
- `transfer_gain`：目标到关节的频域幅值增益估计。
- `transfer_coherence`：目标与关节在主频附近的相干度，越高表示频域估计越可靠。
- `transfer_gain_delay_aligned`：按延迟对齐后重新计算的频域幅值增益估计。
- `transfer_coherence_delay_aligned`：按延迟对齐后重新计算的主频相干度。
- `delay_ms_median`：逐窗口互相关得到的延迟中位数，单位 ms。
- `zeta_hat`：接地后振铃估计得到的阻尼比。
- `zeta_r2`：阻尼拟合的拟合优度，越高越可信。
- `tau_hat_ms`：由阻尼估计得到的衰减时间常数，单位 ms。
- `A_peak`：接地后早期峰值相对后段幅值的过冲倍数。
- `fn_theory_hz`：按理论刚度/惯量反推的自然频率，单位 Hz。
- `zeta_theory`：按 `Kp`、`Kd` 和默认等效惯量计算的理论阻尼比。
- `tau_theory_ms`：理论衰减时间常数，单位 ms。
- `PM_theory_deg`：理论相位裕度近似值，单位 deg。
- `quality_flags`：质量标记，提示该行有哪些低置信度或空参考问题。

## 关键结论

- 这批 CSV 里 `pos_des_lpf_*` 的有效值比例为 0，因此 `lpf` 参考只保留为“空基准”记录，不参与有效汇总。
- real 端的 transfer coherence 普遍偏低，说明 raw 目标到关节的频域传递估计置信度不高。
- sim 的 coherence 明显更高，说明仿真链路更接近单输入线性响应。
- real 相比 sim，匹配 case 上的延迟中位数整体更大，尤其是 `25/0.4 ankle_pitch` 和 `35/0.5 ankle_pitch`。
- `zeta_hat` 不是阶跃响应阻尼比，而是“步态接地后 tracking residual 的 envelope 衰减估计”。它受触地事件、目标轨迹变化、接触冲击和相位窗口影响，不能直接等同于你在 sim 阶跃响应里看到的二阶系统阻尼。

## 延迟对齐复核

| kpkd | axis | real_e_rms | real_e_rms_aligned | sim_e_rms | sim_e_rms_aligned | real_transfer | real_transfer_aligned | sim_transfer | sim_transfer_aligned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 25/0.4 | ankle_pitch | 0.32212 | 0.32219 | 0.26760 | 0.25696 | 0.08380 | 0.07760 | 0.16244 | 0.16085 |
| 25/0.4 | ankle_roll | 0.29748 | 0.29633 | 0.22117 | 0.21846 | 0.13158 | 0.12946 | 0.26696 | 0.25301 |
| 35/0.5 | ankle_pitch | 0.46398 | 0.46486 | 0.26425 | 0.23912 | 0.00146 | 0.00149 | 0.27562 | 0.27587 |
| 35/0.5 | ankle_roll | 0.24306 | 0.25122 | 0.16740 | 0.16600 | 0.07368 | 0.07971 | 0.49090 | 0.49065 |

结论：脚本现在同时输出未对齐和 delay-aligned 指标。当前这批数据里，对齐后 `e_rms` 与 `transfer_gain` 没有发生方向性反转；real/sim 差异主要仍来自接触/轨迹残差和频域相干度差异。`transfer_gain` 的幅值理论上不受纯延迟影响，延迟主要影响相位；这里保留 aligned 版本是为了降低有限窗口和非平稳步态对统计的影响。

## 阻尼与阶跃响应的关系

| 指标来源 | 当前脚本的 `zeta_hat` | 你看到的 sim 阶跃响应 |
| --- | --- | --- |
| 输入类型 | 步态轨迹 + 接地事件后的 tracking residual | 单关节或执行链路阶跃输入 |
| 窗口 | touchdown 后短窗口 | 阶跃后的完整响应 |
| 干扰 | 接触冲击、目标轨迹持续变化、左右腿相位、地面约束 | 通常更接近单输入单输出系统 |
| 可解释性 | 只能作为“接地后残差衰减快慢”的弱指标 | 更适合判断过阻尼/欠阻尼 |

因此，sim 阶跃曲线没有超调时，应优先相信阶跃响应对执行器闭环阻尼的判断。当前 `zeta_hat` 如果显示偏小，更合理的解释是：该估计器在步态接地残差信号上拟合到了慢衰减包络，不代表 sim 的阶跃闭环是严重欠阻尼。

## 与 28 号细粒度报告的关系

`28_forward_x_failure_first6_step_detailed_report.md` 主要分析前 6 步的窗口级抖动、幅值增益、换向频率和 touchdown 表现。本报告是全文件频域/残差统计，两者指标定义不同。

| 主题 | 28 号报告结论 | 本报告结论 | 是否冲突 |
| --- | --- | --- | --- |
| real 是否 20-30Hz 高频颤抖远超 sim | 不成立；real 与 sim 换向频率相近，sim pitch 换向甚至更高 | 本报告 `fn_swing_hz` 约 3-4Hz，不支持 real 存在单一高频主峰远超 sim | 不冲突 |
| sim 是否系统性欠跟踪 | 28 号报告的 `amplitude_gain = joint_amp / target_amp` 显示 sim 约 0.37-0.66，偏欠幅值响应 | 本报告的 `transfer_gain` 是主频附近 cross-spectrum 传递估计，且 sim coherence 高、real coherence 低 | 不直接可比；不能视为冲突 |
| real roll 问题 | real ankle_roll 速度/误差高于 sim，且 touchdown 阶段更差 | 本报告 real roll 的 RMS 通常高于 sim，方向一致 | 不冲突 |
| 延迟是否主要 gap | 28 号报告认为 swing lag real/sim 量级接近，touchdown lag 也接近，延迟不是主要 gap | 本报告的 `delay_ms_median` 用于对齐辅助，数值与 28 号报告不完全一致 | 数值有差异；应以 28 号专门延迟报告为准 |
| 阻尼判断 | 28 号报告不把步态数据当严格 step ringdown | 本报告也将 `zeta_hat` 降级为接地后 residual 衰减弱指标 | 不冲突 |

结论：两份报告的主线一致，即 real/sim gap 主要在接触期动态、roll 轴响应、真实机械柔性/冲击能量和策略高频 target 上，不是单纯“real 全局延迟更大”或“real 高频颤抖远超 sim”。本报告中的 `transfer_gain` 不等价于 28 号报告的 `amplitude_gain`；本报告中的 `delay_ms_median` 只用于 target/pos 对齐辅助，不作为最终延迟结论。

## Real 汇总

| source | kpkd | axis | e_rms_rad | fn_swing_hz | fn_stance_hz | transfer_gain | transfer_coherence | delay_ms_median | zeta_hat | zeta_r2 | tau_hat_ms | A_peak | quality_flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| real | 25/0.4 | ankle_pitch | 0.32212 | 3.45610 | 3.29683 | 0.08380 | 0.06564 | 94.99636 | 0.08240 | 0.41682 | 583.87991 | 1.73584 | low_coherence;low_zeta_r2;few_zeta_events |
| real | 25/0.4 | ankle_roll | 0.29748 | 3.45610 | 3.84630 | 0.13158 | 0.11086 | 49.99808 | 0.27879 | 0.38405 | 214.43756 | 1.85484 | low_coherence;low_zeta_r2;few_zeta_events |
| real | 30/0.4 | ankle_pitch | 0.31620 | 3.04008 | 3.26104 | 0.51872 | 0.20870 | 0.00000 | 0.15731 | 0.51760 | 320.99403 | 2.07347 | low_coherence;low_zeta_r2;few_zeta_events |
| real | 30/0.4 | ankle_roll | 0.36648 | 4.35594 | 3.80454 | 0.72770 | 0.18914 | -9.99949 | 0.29450 | 0.33152 | 232.54919 | 1.60094 | low_coherence;low_zeta_r2;few_zeta_events |
| real | 35/0.5 | ankle_pitch | 0.46398 | 4.27757 | 3.27883 | 0.00146 | 0.00900 | 99.99872 | 0.10249 | 0.44429 | 479.53952 | 1.30243 | low_coherence;low_zeta_r2;few_zeta_events |
| real | 35/0.5 | ankle_roll | 0.24306 | 2.86910 | 3.27883 | 0.07368 | 0.10099 | -59.99923 | 0.14540 | 0.63306 | 361.15560 | 1.57428 | low_coherence;low_zeta_r2;few_zeta_events |
| real | 40/0.8 | ankle_pitch | 0.31623 | 4.22412 | 3.27908 | 0.28560 | 0.20038 | 49.99552 | 0.15254 | 0.62415 | 323.93594 | 1.48311 | low_coherence;low_zeta_r2;few_zeta_events |
| real | 40/0.8 | ankle_roll | 0.21419 | 3.53913 | 5.46514 | 0.30493 | 0.16898 | -29.99732 | 0.10051 | 0.30986 | 553.15865 | 1.99138 | low_coherence;low_zeta_r2;few_zeta_events |

## Sim 汇总

| source | kpkd | axis | e_rms_rad | fn_swing_hz | fn_stance_hz | transfer_gain | transfer_coherence | delay_ms_median | zeta_hat | zeta_r2 | tau_hat_ms | A_peak | quality_flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sim | 25/0.4 | ankle_pitch | 0.26760 | 3.22585 | 3.26091 | 0.16244 | 0.92924 | -27.49965 | 0.34734 | 0.34156 | 182.31586 | 2.32718 | low_zeta_r2;few_zeta_events |
| sim | 25/0.4 | ankle_roll | 0.22117 | 3.22585 | 3.80440 | 0.26696 | 0.84423 | 22.49971 | 0.08030 | 0.29308 | 552.23658 | 1.30872 | low_zeta_r2;few_zeta_events |
| sim | 35/0.5 | ankle_pitch | 0.26425 | 3.69647 | 3.26108 | 0.27562 | 0.90396 | -74.99520 | 0.30690 | 0.45996 | 185.96538 | 2.88763 | low_zeta_r2;few_zeta_events |
| sim | 35/0.5 | ankle_roll | 0.16740 | 3.69647 | 3.80459 | 0.49090 | 0.95359 | -62.49600 | 0.11338 | 0.43980 | 372.25699 | 1.04724 | low_zeta_r2;few_zeta_events |
| sim | 40/0.5 | ankle_pitch | 0.26132 | 3.61295 | 3.26091 | 0.24856 | 0.90713 | -119.99846 | 0.12960 | 0.50278 | 374.57755 | 2.88955 | low_zeta_r2;few_zeta_events |
| sim | 40/0.5 | ankle_roll | 0.15415 | 3.61295 | 3.80440 | 0.59524 | 0.95096 | 49.99936 | 0.10598 | 0.32853 | 398.59824 | 0.99492 | low_zeta_r2;few_zeta_events |
| sim | 50/0.8 | ankle_pitch | 0.25222 | 3.54415 | 3.80479 | 0.21268 | 0.87423 | 19.99770 | 0.12456 | 0.40978 | 340.80288 | 2.91426 | low_zeta_r2;few_zeta_events |
| sim | 50/0.8 | ankle_roll | 0.13471 | 3.54415 | 3.26125 | 0.60846 | 0.73215 | 4.99942 | 0.12724 | 0.35280 | 381.88051 | 1.39062 | low_zeta_r2;few_zeta_events |

## Real vs Sim 对比

| kpkd | axis | reference | real_minus_sim_e_rms_rad | real_minus_sim_delay_ms_median | real_minus_sim_fn_swing_hz | real_minus_sim_zeta_hat | real_over_sim_transfer_gain |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 25/0.4 | ankle_pitch | raw | 0.05452 | 122.49601 | 0.23025 | -0.26494 | 0.51588 |
| 25/0.4 | ankle_roll | raw | 0.07631 | 27.49837 | 0.23025 | 0.19849 | 0.49288 |
| 35/0.5 | ankle_pitch | raw | 0.19973 | 174.99392 | 0.58110 | -0.20441 | 0.00530 |
| 35/0.5 | ankle_roll | raw | 0.07566 | 2.49677 | -0.82737 | 0.03202 | 0.15009 |

## 说明

- `quality_flags` 包含 `low_coherence`、`low_zeta_r2`、`few_zeta_events`、`few_delay_windows` 等低置信度提示。
- `tau_hat_ms`、`zeta_hat`、`transfer_gain` 只有在对应事件/窗口满足置信度门槛时才会出现。
- `delay_ms_median` 是逐窗口统计后取中位数，不再使用拼接相关，避免跨步态窗口混叠。
