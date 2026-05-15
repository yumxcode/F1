# 35 T27 Ankle Zeta and Natural Frequency Statistics

## 数据源

本轮已按指定口径重做统计：

- sim: `test_logs/data_csv/sim/t27*.csv`，共 `4` 个文件。
- real: `test_logs/data_csv/t27*.csv`，共 `12` 个文件。

## 方法说明

这些 `t27` 是走路诊断日志，不是单关节 step ringdown。因此本报告不再输出严格的 `zeta_step`。

统计口径：

- 输入：优先用 `pos_des_lpf_<joint>`；该列缺失或有效样本不足时回退到 `pos_des_raw_<joint>`。并联踝关节在部分日志里 `pos_des_lpf_*` 为 `NaN`，因此会自动使用 raw target。
- 输出：`pos_<joint>`。
- 残差：`pos - target`。
- 频率：残差在 `2.0~30.0 Hz` 的 FFT 峰值，记为 `f_modal_candidate_hz`。
- 阻尼近似：残差峰半功率带宽，`zeta_bandwidth = (f2 - f1) / (2 * f_peak)`。
- 等效自然频率：`f_n_equiv = f_peak / sqrt(1 - zeta_bandwidth^2)`。

可靠性筛选：

- 半功率左右边界都能找到。
- `0 < zeta_bandwidth < 1`。
- 残差峰相对频带中位功率 `>= 4x`。
- 残差峰处 `residual/target power >= 1x`。

注意：这是 walking-data 的等效闭环模态统计，用于 sim/real 对照和风险定位；最终阻尼比仍需 step/sine 专项实验确认。

## 重点汇总

| dataset | axis | case_label | joint_count | reliable_joint_count | median_f_modal_candidate_hz | median_zeta_bandwidth | median_f_n_equiv_hz | median_residual_target_power_ratio | source_rule |
|---|---|---|---|---|---|---|---|---|---|
| real | roll | 40/0.8 all_ankles | 2 | 2 | 2.83 | 0.0517 | 2.84 | 1.03 | reliable_only |
| sim | roll | 25/0.4 all_ankles | 2 | 1 | 2.83 | 0.0259 | 2.83 | 1.47 | reliable_only |
| sim | roll | 35/0.5 all_ankles | 2 | 1 | 2.88 | 0.0254 | 2.88 | 1.43 | reliable_only |
| sim | roll | 40/0.5 all_ankles | 2 | 1 | 2.88 | 0.0254 | 2.88 | 1.25 | reliable_only |
| sim | roll | 50/0.8 all_ankles | 2 | 1 | 2.88 | 0.0254 | 2.88 | 1.06 | reliable_only |

## 全量分组汇总

| dataset | axis | case_label | joint_count | reliable_joint_count | median_f_modal_candidate_hz | median_zeta_bandwidth | median_f_n_equiv_hz | median_residual_target_power_ratio | source_rule |
|---|---|---|---|---|---|---|---|---|---|
| real | pitch | 20260428_152240 | 2 | 2 | 2.88 | 0.0338 | 2.88 | 1.61 | reliable_only |
| real | pitch | 20260428_155015 | 2 | 2 | 2.86 | 0.0085 | 2.86 | 1.00 | reliable_only |
| real | pitch | 20260428_155055 | 2 | 1 | 2.86 | 0.0085 | 2.86 | 1.00 | reliable_only |
| real | pitch | 20260428_161322 | 2 | 1 | 2.86 | 0.0171 | 2.86 | 1.00 | reliable_only |
| real | pitch | 20260428_162312 | 2 | 2 | 2.88 | 0.0422 | 2.88 | 1.32 | reliable_only |
| real | pitch | 20260428_163825 | 2 | 2 | 2.83 | 0.0607 | 2.84 | 3.38 | reliable_only |
| real | pitch | 20260428_164817 | 2 | 2 | 2.87 | 0.0170 | 2.87 | 23.46 | reliable_only |
| real | pitch | 20260429_161248 | 2 | 2 | 2.86 | 0.0128 | 2.86 | 15.21 | reliable_only |
| real | pitch | 25/0.4 all_ankles | 2 | 2 | 2.83 | 0.0303 | 2.83 | 1.60 | reliable_only |
| real | pitch | 30/0.4 all_ankles | 2 | 2 | 3.56 | 0.0121 | 3.56 | 1.25 | reliable_only |
| real | pitch | 35/0.5 all_ankles | 2 | 1 | 2.86 | 0.0171 | 2.86 | 1.00 | reliable_only |
| real | pitch | 40/0.8 all_ankles | 2 | 1 | 2.93 | 0.0333 | 2.93 | 1.28 | reliable_only |
| real | roll | 20260428_152240 | 2 | 0 | 3.59 | 0.0212 | 3.59 | 0.95 | all_unreliable |
| real | roll | 20260428_155015 | 2 | 1 | 2.86 | 0.0085 | 2.86 | 1.00 | reliable_only |
| real | roll | 20260428_155055 | 2 | 2 | 3.58 | 0.0085 | 3.58 | 1.00 | reliable_only |
| real | roll | 20260428_161322 | 2 | 0 | 2.86 | 0.0171 | 2.86 | 1.00 | all_unreliable |
| real | roll | 20260428_162312 | 2 | 0 | 2.83 | 0.0517 | 2.84 | 0.97 | all_unreliable |
| real | roll | 20260428_163825 | 2 | 2 | 2.78 | 0.0530 | 2.79 | 1.11 | reliable_only |
| real | roll | 20260428_164817 | 2 | 0 | 2.84 | 0.0193 | 2.85 | 0.92 | all_unreliable |
| real | roll | 20260429_161248 | 2 | 0 | 2.86 | 0.0128 | 2.86 | 0.60 | all_unreliable |
| real | roll | 25/0.4 all_ankles | 2 | 0 | 2.86 | 0.0299 | 2.86 | 0.88 | all_unreliable |
| real | roll | 30/0.4 all_ankles | 2 | 1 | 4.27 | 0.0114 | 4.27 | 1.22 | reliable_only |
| real | roll | 35/0.5 all_ankles | 2 | 1 | 2.86 | 0.0171 | 2.86 | 1.00 | reliable_only |
| real | roll | 40/0.8 all_ankles | 2 | 2 | 2.83 | 0.0517 | 2.84 | 1.03 | reliable_only |
| sim | pitch | 25/0.4 all_ankles | 2 | 1 | 2.83 | 0.0259 | 2.83 | 1.40 | reliable_only |
| sim | pitch | 35/0.5 all_ankles | 2 | 1 | 2.88 | 0.0254 | 2.88 | 1.30 | reliable_only |
| sim | pitch | 40/0.5 all_ankles | 2 | 2 | 3.59 | 0.0212 | 3.59 | 1.43 | reliable_only |
| sim | pitch | 50/0.8 all_ankles | 2 | 2 | 3.59 | 0.0212 | 3.59 | 1.36 | reliable_only |
| sim | roll | 25/0.4 all_ankles | 2 | 1 | 2.83 | 0.0259 | 2.83 | 1.47 | reliable_only |
| sim | roll | 35/0.5 all_ankles | 2 | 1 | 2.88 | 0.0254 | 2.88 | 1.43 | reliable_only |
| sim | roll | 40/0.5 all_ankles | 2 | 1 | 2.88 | 0.0254 | 2.88 | 1.25 | reliable_only |
| sim | roll | 50/0.8 all_ankles | 2 | 1 | 2.88 | 0.0254 | 2.88 | 1.06 | reliable_only |

## 初步结论

1. sim 与 real 现在都来自 `t27*` 走路诊断日志，统计口径一致。
2. `zeta_bandwidth` 是频域半功率近似，不等价于 step 实验的 `zeta_step`；它适合比较 sim/real 的相对阻尼和峰宽。
3. 如果某组 `source_rule=all_unreliable`，说明该组残差谱不满足半功率/峰显著性条件，不能把其 `zeta` 当成稳定结论。
4. 下一步应优先看 detail 表中 `right_ankle_roll_joint` 的 real/sim 差异，尤其 `residual_target_power_ratio` 和 `output_target_gain_at_residual_peak`，再决定是否进入真实 step/sine 的 `kd` 扫描。

## 输出文件

- `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_t27_ankle_zeta_fn_detail.csv`
- `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_t27_ankle_zeta_fn_summary.csv`
