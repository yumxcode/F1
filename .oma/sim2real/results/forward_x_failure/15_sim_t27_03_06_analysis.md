# Sim T27 `03/06` Analysis (2026-05-06)

> Audit note (2026-05-06): this document is superseded by [17_sim_round3_reaudit_with_video_fact.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/17_sim_round3_reaudit_with_video_fact.md:1).  
> The old conclusion that sim reproduced `severe_foot_flat_touchdown` / `command_not_flat` was inconsistent with video facts: sim multiple `kp/kd` cases walk forward normally, with only mild visible left-foot roll residual and no obvious swing/touchdown jitter. The old read was polluted by raw FK foot-frame bias and must not be used as current evidence.

- Source directory: `test_logs/data_csv/sim`
- Source cases:
  - `t27_tracking_lag_b1_diag_20260506_133905_2504.csv`
  - `t27_tracking_lag_b1_diag_20260506_133024_3505.csv`
  - `t27_tracking_lag_b1_diag_20260506_134153_4005.csv`
  - `t27_tracking_lag_b1_diag_20260506_134417_5008.csv`
- Generated tables:
  - [sim_t27_03_06_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_t27_03_06_summary.md:1)
  - [sim_t27_03_06_case_summary.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_t27_03_06_case_summary.csv:1)
  - [sim_t27_03_touchdown_classification.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_t27_03_touchdown_classification.csv:1)
  - [sim_t27_06_group_lag_summary.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_t27_06_group_lag_summary.csv:1)

## 总结

这 4 个仿真 case 按 `03` 口径都没有解决 touchdown 斜脚问题：

- `4/4` case 的前 `4` 个 touchdown 全部是 `severe_foot_flat_touchdown`
- `4/4` case 的 touchdown 主导轴全部是 `roll`
- `mean_flat_error_rad` 都在 `1.61 ~ 1.70 rad`

按 `03b` 三层判因看，仿真主因更偏向 `command_not_flat`，而不是纯 `tracking_lag`：

- `2504`: `command_not_flat 3`, `tracking_lag 1`
- `3505`: `command_not_flat 2`, `tracking_lag 1`, `coupled_geometry 1`
- `4005`: `command_not_flat 2`, `filter_delay 1`, `coupled_geometry 1`
- `5008`: `command_not_flat 4`

这和当前真机阶段性判断有一个明显差别：

- 真机 `03`/后续链路已经逐步把主收口点推向 touchdown foot-space/contact residual
- 当前仿真 `03` 更像还停留在“指令未充分收平脚掌”这一层

## 指标解释

| 指标 | 含义 |
|---|---|
| `mean_flat_error_rad` | 前 `4` 个 touchdown 的平均 foot-flat error |
| `dominant_axis_counts` | touchdown 时 `sole_pitch/sole_roll` 的主导轴统计 |
| `root_cause_counts` | `03b` 三层分类结果统计 |
| `mean_action_to_raw_lag_ms` | sim 版 `06`：`action -> pos_des_raw` 延迟代理 |
| `mean_raw_to_lpf_lag_ms` | sim 版 `06`：`pos_des_raw -> pos_des_lpf` 延迟代理 |
| `mean_tau_raw_to_tau_lpf_lag_ms` | sim 版 `06`：`tau_des_raw -> tau_des_lpf` 延迟代理 |
| `mean_raw_to_pos_lag_ms` | sim 版 `06`：`pos_des_raw -> pos` 总体现象代理 |

## Case 总表

| case | kp/kd | mean_flat_error_rad | dominant_axis_counts | root_cause_counts | ankle action->raw ms | ankle raw->lpf ms | ankle tau_raw->tau_lpf ms | ankle raw->pos ms |
|---|---|---:|---|---|---:|---:|---:|---:|
| `2504` | `25/0.4` | `1.6122` | `{'roll': 4}` | `{'command_not_flat': 3, 'tracking_lag': 1}` | `0.0` | `0.0` | `10.7126` | `144.6204` |
| `3505` | `35/0.5` | `1.6272` | `{'roll': 4}` | `{'command_not_flat': 2, 'tracking_lag': 1, 'coupled_geometry': 1}` | `0.0` | `0.0` | `11.7464` | `30.8343` |
| `4005` | `40/0.5` | `1.6956` | `{'roll': 4}` | `{'command_not_flat': 2, 'filter_delay': 1, 'coupled_geometry': 1}` | `0.0` | `0.0` | `16.4022` | `32.8045` |
| `5008` | `50/0.8` | `1.6390` | `{'roll': 4}` | `{'command_not_flat': 4}` | `0.0` | `0.0` | `11.4632` | `30.0908` |

## 03 结论

1. 仿真和真机在 touchdown 现象层是一致的  
   都表现为严重的 roll 主导斜脚 touchdown。

2. 仿真当前比真机更强地指向 `command_not_flat`  
   `5008` 已经是 `4/4 command_not_flat`，`2504/3505/4005` 也都以 `command_not_flat` 为最大类。

3. 仿真里 `coupled_geometry` 还没有像真机那样占主导  
   这说明当前仿真对接触/foot-frame residual 的表达，可能仍弱于真实系统。

## 06 结论

这批 sim `t27` 没有 actuator cmd/state，所以不能直接复用真机完整版 `06`。本次只能做降级版：

- `action -> pos_des_raw`
- `pos_des_raw -> pos_des_lpf`
- `tau_des_raw -> tau_des_lpf`
- `pos_des_raw -> pos`

从结果看：

1. `action -> raw` 基本都是 `0 ms`  
   说明策略输出到 raw joint target 这层，在仿真里几乎没有显著离散延迟。

2. `raw -> lpf` 也是 `0 ms`  
   说明 `pos_des_lpf` 对 `pos_des_raw` 基本同拍，至少在当前日志分辨率下没有额外显著滞后。

3. 更可见的延迟在 `tau_raw -> tau_lpf` 和 `raw -> pos`  
   - `tau_raw -> tau_lpf`: 约 `10.7 ~ 16.4 ms`
   - `ankle raw -> pos`: 除 `2504` 外大多在 `30 ~ 33 ms`

4. `2504` 的 `ankle raw -> pos = 144.6 ms` 不应直接当成纯延迟真值  
   细看 joint 级结果，它由 `3/4` 个 ankle joint 的 `187 ~ 198 ms` 拉高，另一个 `right_ankle_roll_joint` 却是 `0 ms`。这更像波形相关性/接触阶段形状异常导致的 lag 代理失真，而不是一个干净的一致性执行延迟。

## 当前判断

基于这轮仿真 `03/06`，更合理的收口是：

- 仿真已经复现了“roll 主导严重斜脚 touchdown”
- 但仿真主因更偏 `command_not_flat`
- 真机主因则已经更靠近 foot-space/contact residual

所以，**真实系统与仿真系统的关键差异，不只是延迟大小，而是 touchdown 接触/几何残差在真机上的权重明显更高。**
