# Real vs Sim Residual Acceptance Comparison (2026-05-06)

目标：

- 不再把 `sim` 和 `real` 的 failure 现象混为一谈
- 以 **sim 稳定前走** 时的左脚外翻残余，定义一个“可接受残余参考包络”
- 再把 **真机校准后 `03/05`** 放到这个包络旁边，看哪些 residual 已经超限

相关输入：

- sim 复审结果：
  [17_sim_round3_reaudit_with_video_fact.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/17_sim_round3_reaudit_with_video_fact.md:1)
- real 审计结果：
  [16_real_round3_logic_audit_after_sim_contrast.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/16_real_round3_logic_audit_after_sim_contrast.md:1)

## 比较口径

这里的 `03` 指标都使用：

- **baseline-corrected foot-frame residual**

也就是：

- `foot_flat_error_touch_rad`
- `sole_roll_touch_rad`
- `sole_pitch_touch_rad`

都已经做过同日志稳态双支撑基线校准。

## Step 1: 定义 sim 可接受包络

sim 已知事实：

- 机器人能稳定前走
- 左脚有视觉可见外翻
- 右脚基本正常

因此 sim 不是“零残差”，而是“**带有限度残差但仍可接受**”。

### sim `03` 侧向统计

| side | events | mean_flat | max_flat | mean_abs_roll | max_abs_roll | mean_abs_pitch | 主标签 |
|---|---:|---:|---:|---:|---:|---:|---|
| left | `11` | `0.1162` | `0.2174` | `0.1090` | `0.2002` | `0.0361` | `residual_not_large_enough` 为主 |
| right | `5` | `0.0356` | `0.1632` | `0.0336` | `0.1624` | `0.0060` | `residual_not_large_enough` 为主 |

### sim 可接受参考

从视频和统计同时看，更合理的“可接受参考”是：

1. 左脚允许存在轻中度 roll 外翻残余  
   参考量级：
   - `left mean_flat ≈ 0.12`
   - `left mean_abs_roll ≈ 0.11`
   - 峰值大约到 `0.20 ~ 0.22`

2. 右脚应接近水平  
   大多数 case 是：
   - `right mean_flat ≈ 0.00 ~ 0.01`
   - `right mean_abs_roll ≈ 0.00 ~ 0.01`
   
   只有 `4005` 出现小幅偏离，但整体仍没影响稳定前走。

3. sim 中主标签应仍以 `residual_not_large_enough` 为主  
   一旦大量进入 `tracking_lag / command_not_flat / coupled_geometry`，就更接近不可忽略残差，而不再是“可带着前走的局部瑕疵”。

## Step 2: 真机 `03` 与 sim 包络对照

### 真机校准后 `03`

| side | events | mean_flat | max_flat | mean_abs_roll | max_abs_roll | mean_abs_pitch | 主标签结构 |
|---|---:|---:|---:|---:|---:|---:|---|
| left | `3` | `0.2998` | `0.4188` | `0.1541` | `0.3910` | `0.2084` | `coupled_geometry` 主导 |
| right | `5` | `0.2107` | `0.3788` | `0.0794` | `0.3043` | `0.1783` | `tracking_lag / command_not_flat / coupled_geometry` 混合 |

### 逐项对照

| 指标 | sim 可接受参考 | real left | real right | 是否超限 |
|---|---|---:|---:|---|
| `mean_flat` | left `~0.12`, right `~0.00~0.01` | `0.2998` | `0.2107` | **双侧超限** |
| `max_flat` | left `~0.22`, right 通常远低于此 | `0.4188` | `0.3788` | **双侧超限** |
| `mean_abs_roll` | left `~0.11`, right `~0.00~0.01` | `0.1541` | `0.0794` | left 中度超限，right 明显超限 |
| `mean_abs_pitch` | left `~0.04`, right `~0.01` | `0.2084` | `0.1783` | **双侧严重超限** |
| 主标签 | `residual_not_large_enough` 为主 | `coupled_geometry` 主导 | 非 `residual_not_large_enough` 为主 | **超限** |

### 真机 `03` 的超限项

真机相对 sim 可接受包络，最明确超限的是：

1. **双侧 pitch residual**
   - sim:
     - left `mean_abs_pitch ≈ 0.036`
     - right `mean_abs_pitch ≈ 0.006`
   - real:
     - left `0.208`
     - right `0.178`

   这是当前最稳定、最明显的超限项。

2. **右脚 residual 也偏大**
   sim 的视频事实是“右脚正常、接近水平”；  
   但真机右脚：
   - `mean_flat = 0.2107`
   - `max_flat = 0.3788`
   - `mean_abs_roll = 0.0794`
   - `mean_abs_pitch = 0.1783`

   所以真机不是“只有左脚坏”，而是**右脚也已经超出 sim 稳定前走的可接受范围**。

3. **左脚峰值 roll 仍过大**
   sim 左脚允许的 roll 峰值大约在 `0.20` 附近；  
   真机左脚 `max_abs_roll = 0.3910`，接近翻倍。

## Step 3: 真机 `05` 与 sim 包络对照

### 真机校准后 `05C`

| case | label | abs_roll | abs_pitch | abs_joint_roll | roll_gain | joint->sole lag ms |
|---|---|---:|---:|---:|---:|---:|
| `25/0.4 all_ankles` | `mapping_workpoint_residual` | `0.1614` | `0.0333` | `0.0467` | `8.2183` | `71.8` |
| `30/0.4 all_ankles` | `mixed_or_uncertain_contact_residual` | `0.0966` | `0.0245` | `0.0351` | `20.2632` | `11.8` |
| `35/0.5 all_ankles` | `pitch_roll_coupled_contact_residual` | `0.2554` | `0.1489` | `0.1101` | `155300.1526` | `74.2` |
| `40/0.8 all_ankles` | `contact_geometry_residual` | `0.1077` | `0.1122` | `0.1076` | `1.2734` | `48.0` |

### 对照 sim 可接受包络后的读法

1. `25/0.4 all_ankles`
   - `abs_roll = 0.1614`，略高于 sim 左脚平均，但仍接近 sim 左脚可接受峰值区
   - 真正超限的是：
     - `roll_gain = 8.2`
     - `joint->sole lag = 71.8 ms`
   
   也就是说，这个 case 不是“角度大到立刻不可接受”，而是**角度不算离谱，但 joint->foot residual 放大机制已经过重**。

2. `30/0.4 all_ankles`
   - `abs_roll = 0.0966`
   - `abs_pitch = 0.0245`
   
   这组从纯角度上看其实落在 sim 可接受区里，  
   所以它更像**边缘可接受 residual**，不是最能解释 real failure 的 case。

3. `35/0.5 all_ankles`
   - `abs_roll = 0.2554`，超过 sim 左脚可接受峰值
   - `abs_pitch = 0.1489`，远高于 sim 左脚 `0.036`
   - `joint->sole lag = 74.2 ms`
   
   这是当前真机 `05` 中**最明显超出 sim 可接受范围**的一组。

4. `40/0.8 all_ankles`
   - `abs_roll = 0.1077`，接近 sim 左脚平均
   - `abs_pitch = 0.1122`，明显高于 sim
   - `joint->sole lag = 48.0 ms`
   
   所以这组不是 roll 超限，而是**pitch residual + joint->sole lag** 超限。

## 最终对照结论

### sim: 左脚局部外翻但可稳定前走

可以接受的典型特征是：

- 左脚允许 `~0.1` 量级的 mean residual
- 左脚 roll 峰值可以到 `~0.2`
- 右脚大多接近水平
- 大多数 touchdown 仍是 `residual_not_large_enough`

### real: 已经超出“可接受残余范围”的项

最明确超限的是：

1. **双侧 pitch residual**
   - 这是最稳定、最系统性的超限项
   - 也是当前真机相对 sim 最不正常的地方

2. **右脚 residual 不再接近水平**
   - sim 的“右脚正常”在真机里不成立
   - 说明真机不是单侧小瑕疵，而是双侧都已经进入不可忽略残差区

3. **左脚 roll 峰值偏大**
   - 真机左脚最大 roll residual 已超过 sim 左脚稳定前走时的可接受峰值

4. **`joint->sole` residual 放大链过重**
   - 即使角度本身不总是非常离谱，真机 `05` 里多组 case 的
     - `roll_gain`
     - `joint->sole lag`
     
     已经明显重于 sim 可接受状态

## 当前最稳妥的收口

把 sim 和 real 并排后，最合理的结论不是：

> 真机只是比 sim “更外翻一点”

而是：

> sim 代表的是“左脚有局部外翻，但残余仍在可带着前走的范围内”；  
> real 则已经至少在 `双侧 pitch residual`、`右脚不再水平`、`左脚 roll 峰值`、`joint->sole residual 放大` 这几项上超出了可接受范围。

所以当前真机 `forward_x_failure` 更像是：

- 不是单一左脚外翻
- 而是 **双侧 touchdown residual 已整体越过 sim 可接受包络**
- 其中又以 **pitch residual 系统性超限** 最值得优先盯住
