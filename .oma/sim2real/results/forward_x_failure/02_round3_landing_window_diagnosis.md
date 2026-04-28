# Round 3 摆腿清高与落地窗口联合诊断结果

轮次目标：基于 `t26_round3_diag` 真机日志与回放分析，判断前向推进失败时的主导阻塞项是否来自摆腿清高不足、髋膝时序/跟踪问题，还是 touchdown 时脚板姿态控制失败。

## 数据源

- 原始日志：
  - [t26_round3_diag_20260427_170011.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t26_round3_diag_20260427_170011.csv)
- 分析输出：
  - [t26_round3_diag_20260427_170011_fk_metrics.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_fk_metrics.csv)
  - [t26_round3_diag_20260427_170011_touchdown_summary.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_touchdown_summary.csv)
  - [t26_round3_diag_20260427_170011_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/t26_round3_diag_20260427_170011_summary.md)

## 本轮分析说明

- `t26` 日志已改为严格同帧采样：`action / joint state / pos_des / tau_des` 在同一策略帧落盘。
- touchdown 检测已按新版脚本更新：
  - `stable touchdown` 下降速度阈值放宽到更贴近真机的范围
  - `first_contact` 搜索改为 `geom_ok + sustained contact` 优先，降低早期噪声误判
  - 候选 touchdown 去重，避免同一 stable touchdown 被重复统计
  - 在保留 `primary_flag` 的同时，新增 `all_flags` 与并发布尔列，避免单一旗标遮蔽信息
- 本轮统计后的独立 touchdown 数为 `8`，不再使用旧版 `7` 次口径。

## 阶段结果

| 项目 | 结果 | 结论 | 后续动作 |
|---|---|---|---|
| `touchdown_count_after_dedup` | `8` 次独立 touchdown | 新版检测在放宽稳定触地阈值后补出 `1` 次左脚事件，事件边界更完整 | 继续以该版本分析脚本为准 |
| `primary_flag_distribution` | `8/8 = severe_foot_flat_touchdown` | 主导问题不是轻微不平，而是系统性的严重斜脚板触地 | 优先进入踝落地姿态专项 |
| `concurrent_flags_overview` | `foot_clearance_deficit = 6/8`；`hip_knee_tracking_lag = 8/8`；`early_knee_extension = 5/8`；`tracking_lag = 8/8` | touchdown 事件层面普遍伴随多问题共现，旧版“只保留一个标签”的口径低估了并发风险 | 后续结果必须同时看 `primary_flag` 与 `all_flags` |
| `swing_clearance_overview` | `max_swing_clearance mean = 0.0815 m`；`-50 ms clearance mean = 0.0001 m` | 摆腿中期并非完全抬不起来，但 touchdown 前余量几乎耗尽，且 `6/8` 事件已触发 clearance 缺口 | 作为次级问题保留，后续继续检查摆腿后段提前下放 |
| `hip_knee_tracking_overview` | `hip_err@-50 ms mean = 0.1484 rad`；`knee_err@-50 ms mean = -0.1019 rad`；存在 `hip_err < 0` 与 `|knee_err| > 0.39 rad` 个例 | 髋膝偏差不是旧结论里的“弱存在”，而是 touchdown 事件层面普遍共现；但从主旗标看仍被脚板不平覆盖 | 不作为本轮第一阻塞，但不能再简单降到“个别异常” |
| `touchdown_side_distribution` | `left = 4`，`right = 4` | 新版事件计数下左右脚样本数对称，不能再沿用“右腿略多”的旧表述 | 后续踝姿态专项继续左右脚分别统计 |

## 关键统计

- `Touchdowns analyzed = 8`
- `Mean max swing clearance = 0.0815 m`
- `Mean clearance at minus 50 ms = 0.0001 m`
- `Mean touchdown foot-flat error = 1.6766 rad`
- `Mean hip_err_minus_50ms = 0.1484 rad`
- `Mean knee_err_minus_50ms = -0.1019 rad`
- `Mean knee_peak_to_touchdown = 0.2188 s`
- `Concurrent flag counts = severe_flat 8 / clearance 6 / hip_knee 8 / early_knee_extension 5 / tracking_lag 8`

范围：

- `max_swing_clearance_m`: `0.0264 ~ 0.1372 m`
- `clearance_at_minus_50ms_m`: `-0.1107 ~ 0.1141 m`
- `foot_flat_error_touch_rad`: `1.5691 ~ 1.9376 rad`
- `hip_err_minus_50ms_rad`: `-0.2028 ~ 0.4114 rad`
- `knee_err_minus_50ms_rad`: `-0.5889 ~ 0.4523 rad`
- `knee_peak_to_touchdown_sec`: `0.0801 ~ 0.3502 s`

## 结果解读

### 1. 主导阻塞项已经明确：严重脚板不平触地

本轮 `8/8` 的独立 touchdown 全部命中 `severe_foot_flat_touchdown`。  
`foot_flat_error_touch_rad` 的范围为 `1.5691 ~ 1.9376 rad`，说明这不是“小角度不平”，而是明显的斜脚板、滚动式或边缘式 touchdown。

结论：

- 触地瞬间脚底姿态控制失败是本批数据中最一致、最强的故障模式。
- 仅根据 `foot_clearance_deficit` 或 `hip_knee_tracking_lag` 继续推进，会掩盖更上游的 touchdown 姿态问题。
- 这里的“主导”指 `primary_flag` 层面；并不代表 clearance、髋膝、执行链问题不存在。

### 2. 摆腿清高不是完全没有问题，但当前不是首要矛盾

`max_swing_clearance` 平均为 `0.0815 m`，部分步达到 `0.11 ~ 0.14 m`，说明摆腿中期并非始终抬不起来。  
但 `clearance_at_minus_50ms_m` 平均只有 `0.0001 m`，并且 `6/8` 事件命中 `foot_clearance_deficit`，说明 touchdown 前 `50 ms` 的足高余量在多数步里已经被消耗完，存在后半段提前下放的问题。

结论：

- 当前更像“摆腿后段 clearance 保持不住”，而不是单纯“中期峰值抬脚不够”。
- 这一问题应作为脚板姿态问题后的次级问题继续保留。

### 3. 髋膝跟踪/时序问题在 touchdown 事件层面普遍共现，但仍不是主旗标

本轮可见较大的个别误差：

- `hip_err_minus_50ms_rad` 最大 `0.4114 rad`
- `hip_err_minus_50ms_rad` 最小 `-0.2028 rad`
- `knee_err_minus_50ms_rad` 最大幅值 `0.5889 rad`

这说明髋膝摆动跟踪或时序并非完全正常。新版脚本下，`8/8` touchdown 事件都同时命中 `hip_knee_tracking_lag`，说明它不是边缘现象。  
但在 `primary_flag` 优先级下，这些问题没有成为第一标签，因为 touchdown 时脚板不平仍构成更强的上游阻塞。

结论：

- 髋膝问题不是被否定，而是被降级为“并发二级问题”。
- 需要在脚板姿态问题收敛后复判，但不能再按旧口径把它描述成“只有少量异常样本”。

### 4. 需要区分“事件级并发 flag”和“踝轴根因分类”

新版 `03a` 输出里的 `all_flags` 是 touchdown 事件层面的并发观测标签，目的是回答：

- 这一步 touchdown 同时暴露了哪些坏现象

后续 `03b` 的 `command_not_flat / tracking_lag / coupled_geometry` 则是踝主导轴上的三层根因分类，目的是回答：

- 对这一步严重脚板不平，主导踝轴更像是哪一类上游原因

因此：

- `has_tracking_lag = 8/8` 不等于三层根因里的 `tracking_lag = 8`
- `has_command_not_flat = 0` 也不等于三层根因里没有 `command_not_flat`

两者不冲突，只是分析层级不同。

## 本轮结论

- Round 3 已完成第一轮真实日志判因。
- 本轮主导问题已明确为：`severe_foot_flat_touchdown`
- 与旧版结论相比，需同步修正两点：
  - 事件数改为 `8`，左右脚样本改为 `4/4`
  - 不能再用“只看单一 `primary_flag`”去概括所有并发问题
- 当前不允许直接进入低速步态复测或 Round 4 候选验证。
- 当前不建议把主要精力放在继续争论 `foot_clearance_deficit` 与 `hip_knee_tracking_lag` 谁更主导，因为 touchdown 姿态问题更上游。

## 下一步动作

按优先级推进：

1. 新建或补充 **踝落地姿态专项**
   - 重点分析 touchdown 前后 `sole_pitch / sole_roll`
   - 重点分析 `ankle_pitch_err_touch_rad / ankle_roll_err_touch_rad`
   - 区分 `command_not_flat / tracking_lag / coupled_geometry / filter_delay`

2. 保留 **摆腿后段清高专项**
   - 继续看 `clearance_at_minus_50ms / -20ms`
   - 重点区分“中期峰值不足”还是“后半段提前下放”

3. 暂缓 **低速前进复测**
   - 进入 Round 4 的门槛仍关闭
   - 必须先证明 severe flat-touchdown 不再是主导阻塞

## 阻塞状态

- `Round 4 low_speed_walk_validation_candidate`: `blocked`
- 阻塞原因：`severe_foot_flat_touchdown` 未关闭
