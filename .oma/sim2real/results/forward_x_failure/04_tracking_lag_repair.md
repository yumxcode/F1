# Round 3B Tracking Lag 修复线结果

轮次目标：验证仅通过提升 `right_ankle_roll_joint` 的执行参数，是否能关闭 Round 3 中的 `tracking_lag` 样本，并避免把问题转移成新的 touchdown 异常。

## 数据范围与有效性

本轮采用“前 `4` 个 touchdown 优先”的口径。理由是：

- 一旦某一步 touchdown 失稳，后续多步会被污染
- 因此前几步更能代表原始问题，而不是失稳后的连锁反应

本轮纳入的有效数据：

- `35 / 0.5 baseline`：
  - [t26_round3_diag_20260427_170011.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t26_round3_diag_20260427_170011.csv)
- `35 / 0.5 retest`：
  - [t26复测.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t26复测.csv)
- `50 / 0.8`：
  - [t27_tracking_lag_b1_diag_20260428_161322.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_161322.csv)
- `40 / 0.8`：
  - [t27_tracking_lag_b1_diag_20260428_162312.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_162312.csv)
- `25 / 0.5`：
  - [t27_tracking_lag_b1_diag_20260428_163825.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_163825.csv)
- `4 ankles = 25 / 0.5`：
  - [t27_tracking_lag_b1_diag_20260428_164817.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_164817.csv)

当前剔除的无效数据：

- `40 / 0.5`：
  - [t27_tracking_lag_b1_diag_20260428_155015.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_155015.csv)
  - [t27_tracking_lag_b1_diag_20260428_155055.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_155055.csv)

剔除原因：

- 两段数据全程 `left_contact = 1, right_contact = 1`
- 无有效 touchdown 边沿
- 左右脚相对高度近似常值
- 不适合用 Round 3 touchdown 诊断链判断根因

额外说明：

- [t27_tracking_lag_b1_diag_20260428_152240.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_tracking_lag_b1_diag_20260428_152240.csv) 与 [t26复测.csv](/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t26复测.csv) 为同一文件内容，不重复计入

## 前 4 步对比结果

### 1. `35 / 0.5 baseline`

- `touchdowns_all = 8`
- `touchdowns_first4 = 4`
- `foot_flat_error_mean_first4 = 1.7489 rad`
- `early4_root = command_not_flat 2 / coupled_geometry 2`

前 `4` 步事件：

- `left @ 1777280412.454 -> coupled_geometry`
- `right @ 1777280413.084 -> command_not_flat`
- `left @ 1777280414.804 -> command_not_flat`
- `right @ 1777280414.944 -> coupled_geometry`

### 2. `35 / 0.5 retest`

- `touchdowns_all = 6`
- `touchdowns_first4 = 4`
- `foot_flat_error_mean_first4 = 1.6753 rad`
- `early4_root = command_not_flat 3 / tracking_lag 1`

前 `4` 步事件：

- `right @ 1777360960.719 -> command_not_flat`
- `right @ 1777360961.409 -> tracking_lag`
- `left @ 1777360961.699 -> command_not_flat`
- `left @ 1777360963.249 -> command_not_flat`

### 3. `50 / 0.8`

- `touchdowns_all = 7`
- `touchdowns_first4 = 4`
- `foot_flat_error_mean_first4 = 1.7502 rad`
- `early4_root = command_not_flat 2 / coupled_geometry 2`

前 `4` 步事件：

- `left @ 1777364003.922 -> command_not_flat`
- `right @ 1777364003.932 -> coupled_geometry`
- `right @ 1777364004.092 -> coupled_geometry`
- `left @ 1777364004.412 -> command_not_flat`

现场观察补充：

- 视觉上有几步向前
- 但右脚 touchdown 后在 `roll` 方向左右晃动明显

这与分析一致：`tracking_lag` 虽未在前 `4` 步占主导，但问题被推向了 `coupled_geometry`，且 `foot_flat_error` 没有下降。

### 4. `40 / 0.8`

- `touchdowns_all = 11`
- `touchdowns_first4 = 4`
- `foot_flat_error_mean_first4 = 1.6601 rad`
- `early4_root = command_not_flat 2 / filter_delay 1 / tracking_lag 1`

前 `4` 步事件：

- `left @ 1777364593.457 -> filter_delay`
- `left @ 1777364593.967 -> command_not_flat`
- `right @ 1777364594.187 -> tracking_lag`
- `left @ 1777364594.487 -> command_not_flat`

### 5. `25 / 0.5`

- `touchdowns_all = 8`
- `touchdowns_first4 = 4`
- `foot_flat_error_mean_first4 = 1.5580 rad`
- `early4_root = command_not_flat 4`

前 `4` 步事件：

- `right @ 1777365506.462 -> command_not_flat`
- `right @ 1777365507.162 -> command_not_flat`
- `left @ 1777365507.512 -> command_not_flat`
- `left @ 1777365508.142 -> command_not_flat`

现场观察补充：

- `roll` 方向左右晃动较 `50 / 0.8` 明显减轻
- 但前向推进不足

这与分析一致：`25 / 0.5` 并没有把主问题修掉，而是把右脚 `roll` 向过度翻转压下去后，更直接地暴露出 `command_not_flat + foot_clearance_deficit`。

### 6. `4 ankles = 25 / 0.5`

- `touchdowns_all = 36`
- `touchdowns_first4 = 4`
- `foot_flat_error_mean_first4 = 1.6850 rad`
- `early4_root = coupled_geometry 3 / command_not_flat 1`

前 `4` 步事件：

- `left @ 1777366098.099 -> coupled_geometry`
- `right @ 1777366098.459 -> coupled_geometry`
- `right @ 1777366098.749 -> command_not_flat`
- `left @ 1777366098.819 -> coupled_geometry`

现场观察补充：

- 4 个 ankle 都调软后，脚掌多余抖动明显减少
- 稳定性提升
- 但整体更像稳定踏步，前进不足

这与分析一致：执行链层面的抖动被压住后，问题不再表现为 `tracking_lag` 或 `filter_delay`，而更直接地暴露为 `coupled_geometry` 主导，外加一部分 `command_not_flat`。

### 7. 延迟链结果的再审查

基于 [06_delay_chain_probe.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/06_delay_chain_probe.md:1) 的补充结果，`04` 线里原先对 `tracking_lag` 的口径需要再收紧：

- `action -> target` 近似 `0 ms`
  - 所以这条线不能解释成模型输出链本身太慢
- `target -> current` 大约 `20 ~ 30 ms`
  - 说明执行器/通信/驱动链确实有响应延迟
- `current -> pos` 约 `80 ~ 145 ms`
  - 说明机械响应和机构侧滞后也是真实存在的

因此：

1. `tracking_lag` 线是成立的，但它更准确地表示“执行链跟不上”，不是 policy 输出晚了。
2. 这条延迟并不能单独解释 `coupled_geometry`。
3. 这条延迟也不能替代 `command_not_flat`，因为 `command_not_flat` 仍然是上游意图层面的证据。

## 统一结论

### 1. `severe_foot_flat_touchdown` 仍是前几步的稳定主问题

所有有效数据的前 `4` 个 touchdown 都继续命中 `severe_foot_flat_touchdown`。  
说明单纯调 `right_ankle_roll_joint` 执行参数，不能把主问题从 touchdown 严重脚板不平中拉出来。

### 2. `tracking_lag` 不是前几步里的稳定主因

在“前 `4` 步优先”口径下：

- `35 / 0.5 retest` 中有 `1` 个 `tracking_lag`
- `40 / 0.8` 中有 `1` 个 `tracking_lag`
- `50 / 0.8` 前 `4` 步没有 `tracking_lag`

因此 `tracking_lag` 并非当前最稳定、最上游、最值得单独靠增益扫掉的主因。

### 3. 单轴 `right_ankle_roll_joint` 调参会在多个根因标签之间转移表现

- `35 / 0.5 baseline`：`command_not_flat / coupled_geometry`
- `35 / 0.5 retest`：`command_not_flat / tracking_lag`
- `50 / 0.8`：`command_not_flat / coupled_geometry`
- `40 / 0.8`：`command_not_flat / filter_delay / tracking_lag`
- `25 / 0.5`：`command_not_flat`
- `4 ankles = 25 / 0.5`：`coupled_geometry / command_not_flat`

这说明当前问题不是“只要把 right roll 调硬一点就能解决”的单因果问题。  
单轴参数变化只是在 `tracking_lag / filter_delay / coupled_geometry / command_not_flat` 之间转移表现。

### 4. 踝参数试验已经把问题范围收紧到 `coupled_geometry + command_not_flat`

- `50 / 0.8`：
  - 没有关闭主问题
  - 还在现场表现出右脚 `roll` 向左右晃动
  - 更像把问题推向 `coupled_geometry`
- `40 / 0.8`：
  - 仍保留 `tracking_lag`
  - 同时引入 `filter_delay`
- `25 / 0.5`：
  - `roll` 晃动减轻
  - 但前向推进不足
  - 前 `4` 步直接退化为 `command_not_flat 4 / 4`
- `4 ankles = 25 / 0.5`：
  - 脚掌多余抖动进一步减轻
  - 稳定性更好
  - 但前进不足依旧
  - 前 `4` 步主因变为 `coupled_geometry 3 / 4`

因此当前更准确的判断是：

- `right roll` 参数偏大时，更容易出现 touchdown 后 `roll` 向左右晃动
- `right roll` 参数偏小时，脚底姿态更平稳，但前向推进和 touchdown 前摆腿意图不足会直接暴露
- 当 4 个 ankle 都调软后，执行链抖动被进一步压低，但主问题并未关闭，而是更清楚地收敛到 `coupled_geometry + command_not_flat`

这说明本线按“踝参数扫参”整体收口，判定为：

- **单轴 `right roll` 扫参存在明显 tradeoff，未能形成可收敛修复路径**
- **调软 4 个 ankle 可以提升平稳性，但会把问题更明确地暴露为 `coupled_geometry + command_not_flat`，而不是关闭主问题**

### 5. 延迟链结果应作为并发因素，而不是主因替代

`06_delay_chain_probe` 给出的关键事实是：

- `action -> target ≈ 0 ms`
- `target -> current ≈ 20 ~ 30 ms`
- `current -> pos ≈ 80 ~ 145 ms`

这意味着：

1. `tracking_lag` 不是 policy 输出慢，而是执行链和机构响应慢。
2. 但因为 ankle 不是这份日志里最慢的一组，`tracking_lag` 不能替代 `coupled_geometry` 成为唯一解释。
3. `command_not_flat` 依旧是上游意图层问题，不能被“有延迟”这一事实吞掉。

## 后续动作（进度标记）

1. ✅ 不再继续盲目扩大 ankle `kp/kd` 扫参（已执行）
2. ✅ 保留 `tracking_lag` 为并发问题标签，不再作为当前第一修复入口（已执行）
3. ✅ 后续主线已转向 `05_coupled_geometry_probe`（已执行）
   - `coupled_geometry` → `05A/05B/05C` 完成，`05D` 待执行
   - `command_not_flat` → 在 `05` 系列排查中统一处理，不是单独根因
   - `filter_delay` → 无稳定主导证据，不再单独推进
4. 进入新的 `coupled_geometry` 专项排查阶段

## 指标字典

| 指标 / 标签 | 含义 | 当前用途 |
|---|---|---|
| `baseline` / `retest` | 同一 `35 / 0.5` 参数下的原始样本与复测样本 | 判断现象是否可重复 |
| `kp/kd` | ankle 控制参数组合 | 只用于观察 tradeoff，不作为单独修复结论 |
| `first_4_touchdowns` | 每组参数优先比较前 `4` 个 touchdown | 避免不同日志长度导致后段样本混入 |
| `severe_foot_flat_touchdown` | touchdown 时严重脚底不平 | 判断主问题是否关闭 |
| `tracking_lag` | 目标有调平意图但真实关节没到位 | 当前只作为并发标签，不再作为单轴第一修复入口 |
| `filter_delay` | LPF 后目标相对 raw 迟到 | `40 / 0.8` 中出现但未稳定成为主因 |
| `coupled_geometry` | joint-space 解释不完 foot-space 姿态 | 进入 `05` 的直接触发条件 |
| `command_not_flat` | touchdown 前目标本身不足以调平 | 与 coupled geometry 一起保留为后续主线 |
| `tradeoff_between_flags` | 调参后故障标签在多类之间转移 | 本轮否定继续盲扫 ankle `kp/kd` 的依据 |
