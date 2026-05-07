# Real vs Sim `10/11` Execution Chain Compare (2026-05-06)

目标：

- 重新审查此前 `10 / 11` 的分析
- 直接对比 real 与 sim 在执行链层的结论
- 明确哪些对比是有效的，哪些因为日志层级不同只能弱比较

## 先给边界

这次对比必须先承认一个事实：

- **real `10/11`** 拥有 actuator-state 级数据
  - 可以拆到：
    - `actuator_cmd -> actuator_state`
    - `actuator_state -> joint_pos`
    - `joint_pos -> bias-corrected FK foot-frame residual`
- **sim 当前没有 actuator-state**
  - 只能做到降级版：
    - `action -> pos_des_raw`
    - `pos_des_raw -> pos_des_lpf`
    - `tau_des_raw -> tau_des_lpf`
    - `pos_des_raw -> pos`

所以：

1. `10/11 real` 和 `sim` **不能做一一物理等价比较**
2. 但可以做：
   - 上游 output 是否是主瓶颈
   - 关节 realization 是否存在明显左右差
   - 当前 lag 量级是否已经大到会破坏 gait

## `joint->sole` 口径说明

本文件中的 `joint->sole` 目前应严格读成：

> `joint -> baseline-corrected FK foot-frame residual`

而不是：

> `joint -> true sole contact edge`

当前 `sole` 信号来自 FK 计算，并且已经做过每侧 `sole_roll/sole_pitch` bias-correction。也就是说，旧的“未经偏置修正的 raw FK sole 整体偏大”问题，已经不再是当前 `11/19` 结果的直接来源。

但这仍不是最终物理真值，因为：

1. 它仍然是 FK foot-frame proxy，不是真实接触边缘或力接触中心。
2. bias 估计时选 stable rows 仍使用 `left_contact/right_contact` 作为辅助筛选条件，因此 bias 参考姿态并非完全脱离 contact proxy。

因此，当前 `joint->sole` 可以用于说明后半段 residual 的存在与量级，但不能单独证明 residual 的物理来源已经锁定为真实 sole/contact edge 问题；这部分仍需要 `05D` 去区分 foot-frame 定义、接触边缘、机械非线性和策略 touchdown 目标。

另外，当前 `11c/11d` 已对 `joint->sole` 增加 corr-gated 汇总：

- `joint_sole_lag_ms_raw`：保留原始值，供审计边界样本
- `joint_sole_lag_ms`：默认汇总值，仅保留 `joint_sole_corr >= 0.20` 的事件

这么做是因为 touchdown 短窗口里，`joint->sole` 更容易出现“相关峰退化但 lag 命中大边界值”的假大值。当前应优先看 filtered 值，再结合 raw 审核是否存在稳定后段 residual。

## Real `10/11` 当前结论

来源：

- [10_execution_chain_disentanglement.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/10_execution_chain_disentanglement.md:1)
- [11_execution_chain_lag_analysis.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/11_execution_chain_lag_analysis.md:1)
- [round3_execution_chain_lag_multi_sample_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/round3/round3_execution_chain_lag_multi_sample_summary.md:1)

### Real `10`

保留有效的结论是：

1. `output` 不是主瓶颈
2. `sole_roll` / foot residual 更主要跟随执行链，而不是直接跟随 output
3. actuator-state 证据支持：
   - `actuator_cmd -> actuator_state` 不是主滞后段
   - 更明显的滞后落在 `actuator_state -> joint_pos`

### Real `11`

保留有效的结论是：

1. `state -> joint` 的大 lag 在 `swing` 期就已经存在，不是 touchdown 才出现
2. `touchdown` 窗未表现出“lag 一定更大”，因此不再把“接触放大 lag”作为默认主解释
3. `cmd -> state` 不是主瓶颈
4. 左右存在明显不对称，但**慢侧不稳定**，不能简化成固定单侧硬件故障

多样本 actuator-state 概览：

| real case | swing mean state->joint (ms) | touchdown mean state->joint (ms) | swing mean joint->sole (ms) | touchdown mean joint->sole (ms) |
|---|---:|---:|---:|---:|
| `25/0.4 all_ankles` | `71.81` | `23.56` | `92.00` | `71.81` |
| `30/0.4 all_ankles` | `93.55` | `26.05` | `26.05` | `11.84` |
| `35/0.5 all_ankles` | `66.05` | `4.63` | `76.47` | `74.16` |
| `40/0.8 all_ankles` | `37.75` | `20.59` | `16.02` | `48.05` |

## Sim 当前可比结论

来源：

- [17_sim_round3_reaudit_with_video_fact.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/17_sim_round3_reaudit_with_video_fact.md:1)
- [sim_t27_03_06_summary.md](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_t27_03_06_summary.md:1)
- [sim_t27_06_joint_lag_table.csv](/Users/yumx/code/X1/agibot_x1_infer/real2sim/table/sim/sim_t27_06_joint_lag_table.csv:1)

### Sim `10` 可比部分

sim 没有 actuator-state，所以不能复刻 real `10` 的 source disentanglement。

但有两条仍能保留：

1. `action -> raw = 0 ms`
2. `raw -> lpf = 0 ms`

这说明 sim 里也没有 evidence 支持“上游 output 发布链是主瓶颈”。

### Sim `11` 可比部分

sim 只能看 `raw -> pos` 这个总体现象代理。

各 case ankle 组均值：

| sim case | ankle mean raw->pos (ms) | tau_raw->tau_lpf (ms) |
|---|---:|---:|
| `25/0.4` | `144.62` | `10.71` |
| `35/0.5` | `30.83` | `11.75` |
| `40/0.5` | `32.80` | `16.40` |
| `50/0.8` | `30.09` | `11.46` |

需要特别说明：

- `25/0.4` 的 `144.62 ms` 已经在之前审过，主要由波形相关性失真抬高，不应直接当成真实物理延迟真值
- 除去这组异常，sim ankle 的 `raw -> pos` 更稳定地落在 `30 ~ 33 ms`

## Real vs Sim 对照

### 1. output 不是主瓶颈：两边一致

| 结论 | real | sim |
|---|---|---|
| output 是否是主瓶颈 | 否 | 否 |
| 证据 | `action->target ≈ 0`, `cmd->state` 不是主段 | `action->raw = 0`, `raw->lpf = 0` |

这条是一致的，没有冲突。

### 2. 执行链问题两边都有，但性质不同

| 维度 | real | sim |
|---|---|---|
| 可拆分层级 | 可拆到 `cmd->state` / `state->joint` / `joint->sole` | 只能看到 `raw->pos` 总体现象 |
| 主滞后段 | `state->joint` | 无法直接拆出；只能说 `raw->pos` 存在 |
| 是否 pre-contact 已存在 | 是，`swing` 窗已明显存在 | 无窗口化 actuator-state 证据，不能等价确认 |

因此当前最稳妥的说法是：

- sim 说明“关节 realization 不是完美的”
- real 说明“问题已经明确集中到 `state -> joint`，而且在接触前就存在”

### 3. 左右不对称：sim 有方向性，real 有强度但不稳定

#### sim

在与视频一致的几组里，左脚 roll realization 更差：

| sim case | left roll raw->pos (ms) | right roll raw->pos (ms) | 结论 |
|---|---:|---:|---|
| `25/0.4` | `198.18` | `0.00` | 左明显更差，但此 case 总 lag 代理失真偏大 |
| `35/0.5` | `17.62` | `11.75` | 左略差 |
| `40/0.5` | `24.60` | `24.60` | 对称 |
| `50/0.8` | `45.85` | `17.19` | 左明显更差 |

和视频结合后，可以接受的结论是：

> sim 确实存在左侧局部 realization 偏差，尤其体现在左 ankle roll。

#### real

real `11` 的结论是：

- 左右不对称很明显
- 但慢侧不稳定，不能写成“永远左差”

这两者不矛盾：

- sim 像“固定方向的小偏差”，还能走
- real 像“幅值更大且窗口/工况依赖更强的不稳定执行链残差”，已经进入 failure 区

### 4. 真正把 real 和 sim 拉开的，不是“有没有 lag”，而是 lag 是否越界

sim 已知事实：

- 左脚有轻微外翻
- realization 有一定左右差
- 但仍能稳定前进

real 已知事实：

- x 前进失败
- roll 触地伴随抖动
- 降 `kp` 后抖动减轻，但仍不能前进

结合 `10/11` 对照，最关键的差异不是：

> sim 没 lag，real 有 lag

而是：

> sim 的 lag / realization bias 仍停留在“局部缺陷但可带着走”的级别；  
> real 的执行链残差已经强到会和 touchdown residual 叠加，破坏有效支撑与推进。

这里的 `touchdown residual` 仍应优先理解为 corr-gated `joint->sole` 后段 residual，而不是 raw 均值本身。

## `0.5 m/s` 级步态下的 `pos_des -> joint_state` 稳定区间

当前新 touchdown detector 下，`0.5 m/s` 级步态的时间尺度大致是：

- real `35/0.5 all_ankles`：same-side period `0.646 s`，adjacent step interval `0.317 s`
- sim `35/0.5`：same-side period `0.700 s`，adjacent step interval `0.349 s`

这意味着：

- `30 ms` 延迟约占整步周期 `4% ~ 5%`
- `50 ms` 延迟约占整步周期 `7% ~ 8%`
- `70 ms` 延迟约占整步周期 `10%+`
- 若按相邻落脚间隔看，`70 ms` 已经吃掉约 `20%` 的局部控制窗口

基于当前 sim 能正常前进、real 进入 `forward_x_failure` 的现有数据，更实用的工程口径是：

| `pos_des -> joint_state` 延迟 | 判断 |
|---|---|
| `<= 20 ~ 25 ms` | 理想目标区间 |
| `20 ~ 35 ms` | 当前可接受、通常仍可稳定前进 |
| `35 ~ 45 ms` | 边缘风险区 |
| `> 50 ms` | 当前问题场景下基本不可接受 |

这不是通用理论极限，而是本项目当前 `0.5 m/s` 级步态上的经验边界。

## 当前 sim / real 的可比量级

### sim

sim 侧最接近 `pos_des -> joint_state` 的口径是 `pos_des_raw -> pos`：

| sim case | ankle `raw -> pos` (ms) | 读法 |
|---|---:|---|
| `35/0.5` | `30.83` | 当前稳定前进可接受区间内 |
| `40/0.5` | `32.80` | 当前稳定前进可接受区间内 |
| `50/0.8` | `30.09` | 当前稳定前进可接受区间内 |

补充：

- `25/0.4` 的 `144.62 ms` 已确认主要由相关性失真抬高，不应当作真实物理延迟真值。
- 因此，当前 sim ankle 的可信量级应收口为 `30 ~ 33 ms`。

### real

real 侧没有与 sim 完全同构的全 ankle `pos_des_raw -> pos` 表，因此只能用两个最接近的代理：

1. `actuator_state -> joint_pos`（当前最强执行链代理）
2. `action -> joint`（右 ankle roll 单轴代理）

#### real `state -> joint`

| real case | swing `state -> joint` (ms) | touchdown `state -> joint` (ms) |
|---|---:|---:|
| `25/0.4 all_ankles` | `71.81` | `41.51` |
| `30/0.4 all_ankles` | `75.78` | `7.10` |
| `35/0.5 all_ankles` | `49.82` | `22.02` |
| `40/0.8 all_ankles` | `44.62` | `12.58` |

#### real `action -> joint`（right ankle roll）

| real case | swing `action -> joint` (ms) | touchdown `action -> joint` (ms) |
|---|---:|---:|
| `25/0.4 all_ankles` | `76.29` | `20.20` |
| `30/0.4 all_ankles` | `99.47` | `23.68` |
| `35/0.5 all_ankles` | `61.80` | `15.45` |
| `40/0.8 all_ankles` | `54.91` | `32.03` |

因此，当前最稳妥的收口是：

- sim：`pos_des -> joint_state` 的可比量级约 `30 ~ 33 ms`，仍在当前可稳定区间内
- real：touchdown 前的 swing 执行链 lag 常落在 `45 ~ 75+ ms`，已经明显越界
- real touchdown 前半段 lag 往往更短，但这不代表 touchdown 更健康，因为它后面还叠着 `joint -> sole/contact` residual

换句话说，当前 real / sim 的核心差异不是“sim 没 lag，real 有 lag”，而是：

> sim 的 `pos_des -> joint_state` 可比量级仍留在 `30 ms` 量级；  
> real 的 pre-contact 执行链 lag 经常落到 `50 ~ 70 ms` 甚至更高，已经足以侵占摆腿后段到 touchdown 前的有效控制窗口。

## 对此前 `10/11` 结论的修正

### `10`

`10` 的主结论可以保留：

- output 不是主瓶颈
- real 的 foot residual 更主要跟随执行链

但现在要补一句：

> sim 也支持“output 不是主瓶颈”；所以 `10` 不能用来解释 real/sim 差异本身，它只能说明 real 的问题不在 output 端。

### `11`

`11` 的主结论也可以保留：

- real 的主滞后段更接近 `state -> joint`
- 而且 pre-contact 已存在

但现在要补一句：

> sim 也存在左侧局部 realization 偏差，因此“有左右差”不是 real failure 的充分条件；  
> real 真正的问题是执行链残差已经与 touchdown residual 叠加到 failure 区，而不是单纯存在某个左/右 lag gap。

## 当前最稳妥的对照结论

1. real 与 sim 在 `10` 上一致：
   - output 都不是主瓶颈

2. sim 在 `11` 上只支持弱结论：
   - 存在局部 realization 偏差
   - 左脚 roll 往往比右脚更差

3. real 在 `11` 上支持强结论：
   - 主滞后段在 `state -> joint`
   - lag 在 `swing` 期就已存在
   - 左右不对称显著，但不是固定单侧故障

4. 因此，`10/11` 这条线对 real/sim 差异的真正解释是：

> sim 也有执行链 imperfect realization，但还没有越过“可正常前进”的边界；  
> real 则是执行链残差更重，并且和 touchdown 几何/接触残差叠加，最终进入 `forward_x_failure`。

这也解释了为什么：

- sim 左脚轻微外翻但不抖动，仍能前进
- real 降 `kp` 后抖动减轻，却仍然不前进

因为真正阻塞前进的，不只是“抖动有没有被压下去”，而是 **执行链残差 + touchdown residual 是否一起越界**。
