# 13_dead_zone_audit

状态：`done`

## 进入背景

在 `11` 和 `12` 的执行链/并联兑现分析之外，新的窗口统计显示：

- `right_ankle_roll` 的 `swing` 窗 `pos_des_raw` 更小
- `touchdown` 窗 `pos_des_raw` 更大
- `swing` 窗的小信号兑现更容易落入死区 / 阈值敏感区

这说明部分 lag 不应再默认优先解释为机械结构问题，而需要先考虑小信号死区、阈值响应和低幅值兑现困难。

## 目标

1. 审核 `right_ankle_roll` 的 `pos_des_raw` 在 `swing` 窗的量级分布。
2. 细化到 `0.05 rad` 分箱，并给出 `dead_zone_dominant / mixed_dead_zone_and_realization / realization_dominant` 的 case-level 读法。
3. 将死区理论纳入 `11 / 12 / 05` 的统一口径，避免后续所有延迟都先归因到机械结构。

## 已知事实

基于现有 `t27` swing-only `pos_des_raw` 统计：

- `swing` 窗 `|pos_des_raw|` 在各 case 间大致落在 `0.0779 ~ 0.1742 rad`。
- `swing` 窗 `|pos_des_raw| <= 0.10 rad` 的比例在各 case 间大致落在 `0.3619 ~ 0.8119`。
- `swing` 窗的小信号特征并非只在低 kp case 才出现，高 kp case 里也存在明显的小幅 `pos_des_raw`。

这意味着：

- 小幅 swing `pos_des_raw` 更容易落入死区或阈值敏感区。
- touchdown 的更大输出不再是 A 线主对象；`touchdown` 仍主要留给 `05 / 12C` 的几何残差解释。

## 计划与完成状态

1. 把 `right_ankle_roll` 的 `swing pos_des_raw` 结果以 `0.05 rad` 粒度写入结果文件。
2. 审核 `11` 和 `12` 中哪些 swing lag 适合改为“死区优先、结构残余”的解释。
3. 给出 case-level 的 swing 判读，不再只停留在均值层面。
4. 只对“输出小但 lag 大”的 swing 窗口才优先怀疑 dead-zone，不再统一指向机械结构。

以上条目已完成，收口见结果文档。

## 成功标准

本专项至少要收敛出下面两类窗口：

1. `dead_zone_dominant`
2. `mixed_dead_zone_and_realization`

并明确说明：

- 哪些 swing lag 不能再直接归因到机械结构
- 哪些 lag 仍需保留给执行兑现不足或几何残差
- 哪些 case 已经可以明确不再按 dead-zone 主导理解

## 当前收口

结果见 [13_dead_zone_audit.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/13_dead_zone_audit.md:1)。本线已确认：`swing` 期 `right_ankle_roll` 的 `pos_des_raw` 小信号特征稳定存在，因此 `swing` lag 不再默认先归机械结构；touchdown residual 仍交给 `05/12C`。
