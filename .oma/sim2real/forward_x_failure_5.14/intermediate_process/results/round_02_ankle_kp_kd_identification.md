# Round 2 踝关节 Kp/Kd 辨识结果

轮次目标：在真机悬空和触地两类工况下完成踝关节 `kp/kd` 闭环辨识，并用统一的“跟踪率 + 阻尼质量”判据收敛候选参数。

## 当前状态

- `Round 2` 仍在进行中，不能视为完成。
- 已完成内容：
  - 四个自由度的触地工况首轮阶跃扫描
  - `right_ankle_roll_joint` 的悬空补测：`kp=35`，`kd=0.5/0.8/1.0`
  - `right_ankle_pitch_joint` 的悬空补测：`kp=35, kd=0.5`
  - `right_ankle_pitch_joint` 的完全触地补测：`kp=20/35/50/100, kd=0.5`
- 未完成内容：
  - `left_ankle_pitch_joint` 与 `left_ankle_roll_joint` 的悬空工况补测
  - `right_ankle_pitch_joint` 的悬空对照补测：`kp=100, kd=0.8`
  - 用统一新判据回看并重排全部触地数据
  - 对“无超调但欠跟踪”的配置重新排序，形成可执行候选集

## 一页结论

- 这轮最大的纠偏不是找到最终 `kp/kd`，而是纠正了评价准则：
  - `no_overshoot + no_zero_crossing` 不能直接当作优解
  - `tracking_ratio` 明显低于 `1.0` 的配置，本质上是偏软欠跟踪
- 当前最明确的负结论有两条：
  - `right_ankle_roll_joint` 的 `kp=35` 在悬空下从 `kd=0.5` 到 `1.0` 都不是收口点
  - `right_ankle_pitch_joint` 的完全触地 `kd=0.5` 支路不是有效收敛方向
- 当前最需要补齐的不是更多触地点，而是：
  - 左脚两轴悬空数据
  - `right_ankle_pitch_joint` 在 `kp=100, kd=0.8` 下的悬空对照
- 因此 `Round 2` 现在只能写“局部结论已形成”，不能写“参数已收敛”。

## 当前覆盖矩阵

| 自由度 | 触地首轮 | 触地补测 | 悬空补测 | 当前状态 |
|---|---|---|---|---|
| `left_ankle_pitch_joint` | 已完成 | 无 | 无 | 证据不足，不能排序收口 |
| `left_ankle_roll_joint` | 已完成 | 无 | 无 | 证据不足，不能排序收口 |
| `right_ankle_pitch_joint` | 已完成 | `kd=0.5` 支路已补 | `kp=35, kd=0.5` 已补 | 已形成局部负结论，但还缺 `100/0.8` 悬空对照 |
| `right_ankle_roll_joint` | 已完成 | 无 | `kp=35, kd=0.5/0.8/1.0` 已补 | 已形成“接触条件强分裂”结论 |

## 本轮纠偏

此前文档把以下现象当成主要优化目标：

- `no_overshoot`
- `no_zero_crossing`

这不够。因为在本轮部分数据里，“无超调”只是由于响应幅值过小，主轴根本没冲到目标值。这样的配置本质上是偏软欠跟踪，不是好的阻尼。

新的判断原则：

- 真正的无超调：`actual_step ≈ command_step`，且无振荡
- 需要排除的伪优解：`actual_step << command_step`，只是因为系统太软所以没冲过目标
- 后续统一使用 `tracking_ratio = actual_step / command_step` 作为主指标之一

## 测试范围

- 测试对象：
  - `left_ankle_pitch_joint`
  - `left_ankle_roll_joint`
  - `right_ankle_pitch_joint`
  - `right_ankle_roll_joint`
- 接触条件：
  - 悬空工况：右脚两轴已部分补测，左脚两轴与 `right pitch 100/0.8` 对照仍待补
  - 脚完全着地工况：已完成首轮扫描
- 固定条件：
  - `mode = step`
  - `step_amplitude_rad = 0.015`
  - `active_sec = 1.0`
  - `repeat_count = 3`
  - `publish_rate_hz = 1000`

## 触地工况首轮结果

| 对象 | 参数 | 工况 | 结果 | 当前判断 |
|---|---|---|---|---|
| `left pitch` | `kp=90, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.009277`，`tracking_ratio ≈ 0.618`，无超调、无过零、无振荡 | 偏软欠跟踪，不能因无超调判优 |
| `left pitch` | `kp=95, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.008566`，`tracking_ratio ≈ 0.571`，`steady_error ≈ -0.001597` | 劣于 `90/0.8` |
| `left pitch` | `kp=100, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.009178`，`tracking_ratio ≈ 0.612`，`peak_time_sec ≈ 0.055692`，无超调、无过零、无振荡 | 仍明显欠跟踪，不能直接收口 |
| `left pitch` | `kp=105, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.009629`，`tracking_ratio ≈ 0.642`，`steady_error ≈ -0.001685`，`peak_time_sec ≈ 0.299386` | 跟踪略升但迟滞更明显，需结合悬空工况再判 |
| `left pitch` | `kp=100, kd=1.0` | 非最终一致工况 | 历史结果显示加大 `kd` 会压低响应 | 当前不作为优先方向 |
| `left roll` | `kp=70, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.007265`，`tracking_ratio ≈ 0.484`，`peak_time_sec ≈ 0.194319` | 明显偏软 |
| `left roll` | `kp=80, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.007145`，`tracking_ratio ≈ 0.476`，`peak_time_sec ≈ 0.035329`，无超调、无过零、无振荡 | 仍属欠跟踪，不应直接列为最优 |
| `left roll` | `kp=90, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.006259`，`tracking_ratio ≈ 0.417`，`coupled_motion ≈ -0.001950` | 劣于 `80/0.8` |
| `left roll` | `kp=100, kd=0.8` | 脚完全着地 | 两次结果分别 `actual_step ≈ 0.004599` 与 `0.003863` | 明显偏软，排除 |
| `right pitch` | `kp=100, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.011267`，`tracking_ratio ≈ 0.751`，`steady_error ≈ 0.000114`，无超调、无过零、无振荡 | 触地首轮中相对更接近可用，但仍未达到理想跟踪 |
| `right pitch` | `kp=105, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.009831`，`tracking_ratio ≈ 0.655`，耦合略小但主轴跟踪下降 | 不优于 `100/0.8` |
| `right roll` | `kp=20, kd=0.5` | 脚完全着地 | `actual_step ≈ 0.009360`，`tracking_ratio ≈ 0.624`，`peak_time_sec ≈ 0.047694`，无超调、无过零、无振荡 | 稳定但明显欠跟踪，不优于 `35/0.5` |
| `right roll` | `kp=35, kd=0.5` | 脚完全着地 | `actual_step ≈ 0.010059`，`tracking_ratio ≈ 0.671`，`peak_time_sec ≈ 0.049345`，无超调、无过零、无振荡 | 当前触地工况下的相对最好对照点，但仍明显欠跟踪，不能收口 |
| `right roll` | `kp=50, kd=0.5` | 脚完全着地 | `actual_step ≈ 0.009380`，`tracking_ratio ≈ 0.625`，`peak_time_sec ≈ 0.046359`，无超调、无过零、无振荡 | 不优于 `35/0.5`，说明该方向非单调改善 |
| `right roll` | `kp=80, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.006009`，`tracking_ratio ≈ 0.401`，`steady_error ≈ 0.000918`，无超调、无过零、无振荡 | 明显偏软 |
| `right roll` | `kp=70, kd=0.8` | 脚完全着地 | 两次结果均值约 `actual_step ≈ 0.0070`，`tracking_ratio ≈ 0.467`，离散存在但整体优于 `80/0.8` | 仍偏软 |
| `right roll` | `kp=60, kd=0.8` | 脚完全着地 | `actual_step ≈ 0.010256`，`tracking_ratio ≈ 0.684`，`peak_time_sec ≈ 0.040694`，无超调、无过零、无振荡 | 在已测触地样本中数值略高，但与 `35/0.5` 一样仍明显欠跟踪，需悬空复核 |

## `right_ankle_roll_joint` 悬空工况补测

| 参数 | 工况 | 结果 | 当前判断 |
|---|---|---|---|
| `kp=35, kd=0.5` | 悬空 | `tracking_ratio(window_mean) ≈ 1.106`，`peak_tracking_ratio ≈ 1.184`，`tail_tracking_ratio ≈ 1.146`，`final_tracking_ratio ≈ 0`，`response_class = sustained_oscillation` | 不是欠跟踪，而是明显欠阻尼；active 内冲过头，post 又回到基线附近 |
| `kp=35, kd=0.8` | 悬空 | `tracking_ratio(window_mean) ≈ 1.191`，`peak_tracking_ratio ≈ 1.251`，`tail_tracking_ratio ≈ 1.239`，`final_tracking_ratio ≈ 0.010`，`response_class = single_overshoot` | 相比 `0.5` 振荡更少、更干净，但仍是明显过冲后回落，不是稳态跟踪 |
| `kp=35, kd=1.0` | 悬空 | `tracking_ratio(window_mean) ≈ 1.190`，`peak_tracking_ratio ≈ 1.255`，`tail_tracking_ratio ≈ 1.236`，`final_tracking_ratio ≈ 0.012`，`response_class = single_overshoot` | 与 `0.8` 基本同类，没有继续改善，不优于 `0.8` |

### `right roll` 悬空工况阶段结论

- `kp=35` 这条支路在悬空下已经说明问题：
  - `kd=0.5` 时是持续振荡
  - `kd=0.8` 和 `kd=1.0` 时振荡被压到单次过冲
  - 但两者都仍然是“过冲后回落”，不是稳定跟踪到目标
- 因此当前不能再把 `right roll` 简单理解为“kp 太小”。
- 悬空和触地下表现分裂明显：
  - 触地下 `35/0.5` 是明显欠跟踪
  - 悬空下 `35/0.5` 却是明显欠阻尼
- 这说明 `right_ankle_roll_joint` 对接触条件高度敏感，当前问题不是单参数单调优化，而是接触耦合和等效动力学差异。

## `right_ankle_pitch_joint` 悬空工况补测

| 参数 | 工况 | 结果 | 当前判断 |
|---|---|---|---|
| `kp=35, kd=0.5` | 悬空 | `tracking_ratio(window_mean) ≈ 0.921`，`peak_tracking_ratio ≈ 1.053`，`tail_tracking_ratio ≈ 0.965`，`overshoot_ratio ≈ 0.053`，`rise_time_sec ≈ 0.048`，`peak_time_sec ≈ 0.088` | 主轴幅值和时间响应已接近可用区间，但轮次间仍有轻度振荡与一致性问题，属于接近可用但未收口 |

### `right pitch` 悬空工况阶段结论

- `right_ankle_pitch_joint` 在悬空 `kp=35, kd=0.5` 下，与 `right roll` 的强分裂表现不同：
  - 主轴峰值仅小幅超目标
  - `active` 尾段已接近目标
  - 时间预算满足 walking 需求
- 当前主要问题不是明显欠跟踪，也不是明显过冲失控，而是：
  - 不同轮次之间仍存在轻度振荡
  - 响应一致性还不够稳定
- 因此该点可视为 `right pitch` 的一个接近可用边缘点，值得在其附近继续微调，但不能直接收口。

## `right_ankle_pitch_joint` 完全触地工况补测

| 参数 | 工况 | 结果 | 当前判断 |
|---|---|---|---|
| `kp=20, kd=0.5` | 完全触地 | `tracking_ratio(window_mean) ≈ 0.453`，`peak_tracking_ratio ≈ 0.519`，`tail_tracking_ratio ≈ 0.519`，`peak_time_sec ≈ 0.384`，`response_class = undershoot_soft` | 稳定但明显欠跟踪，且峰值时间远超 walking 预算，不可用 |
| `kp=35, kd=0.5` | 完全触地 | `tracking_ratio(window_mean) ≈ 0.442`，`peak_tracking_ratio ≈ 0.481`，`tail_tracking_ratio ≈ 0.481`，`peak_time_sec ≈ 0.338`，`response_class = undershoot_soft` | 明显欠跟踪且峰值时间远超 walking 预算，在完全触地工况下不可用 |
| `kp=50, kd=0.5` | 完全触地 | `tracking_ratio(window_mean) ≈ 0.388`，`peak_tracking_ratio ≈ 0.435`，`tail_tracking_ratio ≈ 0.435`，重复间分裂明显：一轮极慢，另外两轮仅建立到约四分之一目标 | 不但未改善 `35/0.5`，反而引入更强的工况分裂，不应继续沿该方向收口 |
| `kp=100, kd=0.5` | 完全触地 | `tracking_ratio(window_mean) ≈ 0.402`，`peak_tracking_ratio ≈ 0.477`，`tail_tracking_ratio ≈ 0.477`，重复间同样分裂：一轮幅值接近但时间极慢，另外两轮幅值仅约四分之一 | 在 `kd=0.5` 这条线上继续增大 `kp` 不能形成可用收敛方向 |

### `right pitch` 触地/悬空对比结论

- `right_ankle_pitch_joint` 在 `kp=35, kd=0.5` 下呈现出明显工况分裂：
  - 悬空工况：主轴幅值和时间响应接近可用区间
  - 完全触地工况：主轴只建立到目标的大约一半，且响应明显拖慢
- 这说明该参数不是普遍有效点，而是一个“悬空可、触地不可”的对照点。
- 对 `right pitch` 来说，当前不能沿 `35/0.5` 简单微调收口，而应重新围绕完全触地工况寻找可用区。
- 从完全触地 `kd=0.5` 这一整条扫描看：
  - `kp=20/35` 属于“稳定但明显不可用”
  - `kp=50/100` 属于“更分裂、且同样不可用”
- 因此对 `right pitch` 而言，`kd=0.5` 不是有效收敛支路，继续沿这条线加 `kp` 没有工程价值。

## 当前结论

- 当前不能给四个自由度下“综合最优”定论。
- 触地工况首轮数据显示：
  - 多个配置虽然没有超调、过零和振荡，但 `tracking_ratio` 只有约 `0.4 ~ 0.75`
  - 这说明系统主要问题之一仍是偏软欠跟踪，至少不能仅凭“无超调”就宣布收敛
- 已形成的稳定结论：
  - `right roll`：
    - 触地下 `35/0.5` 与 `60/0.8` 只是相对较好对照点，不是收口值
    - 悬空下 `kp=35` 配合 `kd=0.5/0.8/1.0` 均不成立：
      - `0.5` 为持续振荡
      - `0.8/1.0` 为单次过冲后回落
    - 结论：`right roll` 当前主问题不是单纯沿 `kp=35` 微调 `kd`，而是接触耦合与悬空/触地等效动力学差异
  - `right pitch`：
    - 悬空 `35/0.5` 是“接近可用但未收口”的边缘点，不是部署候选
    - 完全触地 `kd=0.5` 整条支路都不可用：
      - `20/35` 稳定但明显欠跟踪
      - `50/100` 更分裂且同样不可用
    - 结论：`kd=0.5` 对 `right pitch` 不是有效收敛方向，应停止继续沿这条线扫描
- 仍只能视为暂存判断的内容：
  - `right pitch kp=100, kd=0.8` 与 `right roll kp=60, kd=0.8` 在触地首轮中相对更接近可用
  - `left pitch` 与 `left roll` 触地下仍偏软，但由于缺少悬空对照，暂时不能决定是继续加 `kp` 还是转向 `kd/lpf`

## 后续动作

- 先补 `left_ankle_pitch_joint` 与 `left_ankle_roll_joint` 的悬空工况阶跃测试，沿用相同 `step_amplitude_rad = 0.015`。
- `right_ankle_pitch_joint` 下一步补悬空对照，优先测试 `kp=100, kd=0.8`。
- 对全部触地工况按新判据复排：
  - 先看 `tracking_ratio`
  - 再看是否振荡、是否过零、是否耦合放大
- 对 `tracking_ratio < 0.8` 的配置，不再写成“综合最优候选”。
- 只有在悬空工况跟踪正常、触地工况才抖或才欠跟踪时，才把重点转向接触耦合、`kd` 和 `lpf_conf.wc`。
- 在 `Round 2` 真正收敛前，不进入 `Round 3 low_speed_walk`。
