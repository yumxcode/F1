# 21 Real vs Sim Combined Conclusion

来源文档：

- [18_real_vs_sim_residual_acceptance_comparison.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/18_real_vs_sim_residual_acceptance_comparison.md:1)
- [19_real_vs_sim_execution_chain_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/19_real_vs_sim_execution_chain_compare.md:1)
- [20_real_vs_sim_joint_jitter_compare.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/20_real_vs_sim_joint_jitter_compare.md:1)

## 统一结论

`real forward_x_failure` 不是单一的 roll 外翻、单一 output 延迟或单一 `kp/kd` 问题，而是 **touchdown 几何 / 接触残差已经越过 sim 稳定前走时的可接受包络，并与执行链 `state -> joint -> sole` 残差放大叠加；高 `kp` 进一步把这种越界残差表现成 swing / touchdown 阶段更大的真实 joint 调整量，并在 touchdown 阶段表现为更重的 roll/pitch 局部抖动，最终破坏有效支撑和前向推进**。

换成可操作的判断：

- `18` 说明 real 的 touchdown residual 已经超出 sim 可接受范围，最稳定的超限项是双侧 `pitch residual`、右脚不再水平、左脚 roll 峰值偏大，以及 `joint -> sole` residual 放大链过重。
- `19` 说明 real/sim 的差别不是“sim 没有 lag、real 有 lag”，而是 sim 的 imperfect realization 仍可带着前走，real 的执行链残差已经与 touchdown residual 叠加到 failure 区；real 主滞后更靠近 `state -> joint`，且在 swing 期已经存在。
- `20/24/25` 说明旧 ankle-pitch 低速 contact proxy 会污染早期 touchdown 序列，已改为 FK 足端高度/速度为主、hip pitch 相位校验的 kinematic detector；新窗口下 real/sim 步态周期重新一致，real 的问题保留为更大的 roll/pitch joint 调整幅值、调整路径和 tracking error，其中 roll touchdown 仍是最重异常点，pitch touchdown 高频结论降级。

因此后续收口应采用这一条主线：

> sim 允许存在轻微左脚外翻和局部 realization 偏差，但 residual 与 joint 调整/兑现误差仍低于稳定前走边界；real 则是 touchdown residual、执行链兑现残差和高 `kp` 调整负担共同越界，所以降低 `kp` 只能减轻表现，不能单独恢复前向推进。

## 对下一步的约束

1. 不再把“看到 roll 触地”直接等同为主因；sim 也有轻微 roll 外翻但能前走。
2. 不再把 output 端作为第一修复入口；18/19/20 都不支持 output 是主瓶颈。
3. 不再只扫 `kp/kd` 试图关闭问题；`kp` 更像放大器，不能解释 residual 越界本身。
4. 下一步优先验证 touchdown foot/contact frame 与真实接触边缘：先确认 `joint -> sole` residual 的物理含义，再决定是修 frame/contact 建模、执行链兑现，还是策略侧 touchdown 姿态目标。
