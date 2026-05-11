# Forward X Failure Overall Plan

状态：`active`

## 当前问题定义

`forward_x_failure` 当前收敛为一个踝关节闭环稳定性问题：

```text
real 踝关节低阻尼 / 欠阻尼
  -> target 或 touchdown 冲击接近闭环模态时被放大
  -> touchdown 期 joint range / path / tracking error 大于 sim
  -> 前向步态无法稳定推进
```

当前不再把问题主因写成：

- FK foot-frame / contact frame 残差未确认。
- coupled geometry 主导。
- dead-zone 主导。
- policy output 延迟主导。
- 旧 touchdown detector 或 raw foot-frame 指标主导。

这些分支已从当前 plan/result 中删除，避免和主线冲突。

## 保留证据链

当前只保留能支持欠阻尼/谐振主线的文档：

| 文档 | 用途 |
|---|---|
| `01_field_baseline.md` | 记录真机初始现象：前向行走短时可用，但踝关节抖动和推进不足存在 |
| `20_real_vs_sim_joint_jitter_compare.md` | 证明 real touchdown 尤其 roll 轴 joint range/path/tracking error 高于 sim |
| `28_forward_x_failure_first6_step_detailed_report.md` | 前 6 步细粒度证据：real 存在 touchdown 过冲、自激点、右踝失效风险 |
| `28_code_reliability_audit.md` | 说明保留结论的可靠边界 |
| `31_first6_joint_change_frequency_tables.md` | target/joint 频率和折返统计 |
| `31b_first6_joint_change_frequency_by_kp.md` | Kp/Kd 分组频率与响应统计 |
| `32_complete_swing_support_frequency_tables.md` | swing/support 完整周期频率统计 |
| `33_kp_kd_stability_theory_plan.md` | 二阶系统解释：低 Kd 导致低阻尼、谐振峰和长衰减 |
| `34_ankle_resonance_peak_validation.md` | 现有 real/sim 数据的谐振候选统计 |

## 当前结论

1. real 的问题不是单纯 target 高频，也不是单纯延迟。  
   real/sim 延迟量级相近，sim 没有同等幅值放大。

2. real touchdown 期的踝关节响应更重。  
   `roll touchdown` 的 real joint range/path/tracking error 明显高于 sim，是主问题窗口。

3. 踝关节表现符合低阻尼系统风险。  
   理论模型中 `Kp35/Kd0.5`、`Kp40/Kd0.8` 的阻尼比低，谐振峰高；提高 `Kd` 可降低 `M_r` 和衰减时间。

4. 当前最强风险对象是：

```text
right_ankle_roll
touchdown
Kp40/Kd0.8 及相近低阻尼配置
```

5. 现有 walking data 已能定位风险，但不能替代 step/sine 专项实验。  
   欠阻尼主线已成立为当前工程判断；若要给出严格 `zeta_step` 和 `f_n_closed_loop`，仍需专项辨识。

## 下一步计划

只保留一个执行计划：

[14_ankle_resonance_peak_validation.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/14_ankle_resonance_peak_validation.md:1)

该计划后续只做两件事：

1. 用 step / sine sweep 确认 `right_ankle_roll` 的 `zeta_step`、`f_n_closed_loop_hz`、`peak_gain_at_freq`。
2. 用 `Kp40/Kd0.8` 与更高阻尼配置对照，验证提高 `Kd` 是否降低 touchdown 过冲和自激点。

## 结束条件

当前问题关闭需要满足：

```text
real right_ankle_roll touchdown:
  amplitude_gain 降到 <= 1.0 附近
  residual_target_power_ratio 降到 < 3
  tracking_err_rms 明显下降
  step/sine 得到的 zeta_step 不再处于高风险低阻尼区
  forward x 命令可连续稳定推进
```
