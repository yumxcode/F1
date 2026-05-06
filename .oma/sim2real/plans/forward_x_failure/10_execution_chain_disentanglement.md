# 10_execution_chain_disentanglement

状态：`done`

## 为什么要开这个专项

前序结果已经把问题统一收敛成：

- 高 `kp` 会放大接触窗内的相位滞后和抖动
- 低 `kp` 能压住抖动，但无法关闭 touchdown 不平和左右镜像 roll 偏置
- `sole_roll` 在 swing / touchdown 两个窗口里都更偏执行链响应，而不是即时 output
- `coupled_geometry` 不是单靠延迟就能解释掉的标签

但当前仍有两块没完全拆开：

1. `lpf -> pos` 里的执行链复合延迟到底拆成了哪几段
2. 几何镜像偏置到底是映射/符号链问题，还是硬件退化在接触下被放大

## 目标

把“高 kp 抖动 / 低 kp 不平”拆成更细的可测链路：

1. `output -> lpf`
2. `lpf -> actuator response`
3. `actuator response -> pos`
4. `pos -> sole_roll`

并尽量分辨：

- 输出链问题
- 执行链问题
- 并联映射问题
- 硬件退化问题

## 当前分析脚本

- [10a_execution_chain_disentanglement_h2_t27.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/10a_execution_chain_disentanglement_h2_t27.py:1)
- [11a_execution_chain_disentanglement_actuator_t27.py](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/plans/forward_x_failure/scripts/11a_execution_chain_disentanglement_actuator_t27.py:1)

## 当前阶段性判断

基于 t27 现有诊断日志，先使用 `pos_des_lpf -> pos` 作为执行链代理后，H2 的代理判定已经支持：

- `lpf -> pos` 迟滞在多数样本里明显存在
- `sole_roll` 仍主要跟随执行链，不直接跟随 output

在补上 `/actuator_cmd` 与 `/actuator_states` 后，这条判断已经从“代理结论”推进到“actuator-state 级别确认”：

- `actuator_cmd -> actuator_state` 在当前 `10 ms` 采样分辨率下未再表现出独立的大滞后段
- 更明显的迟滞落在 `actuator_state -> joint_pos`
- `sole_roll` 仍主要跟随执行链，不直接跟随 `action / pos_des_raw`

因此，当前 `10` 线的阶段结论是：

- `output` 侧不是主要矛盾
- 执行链迟滞是真实存在的并发放大器
- `coupled_geometry` 仍需与执行链迟滞并行解释，不能被简单替代
- 现有 `5` 组 proxy case 与 `1` 组 actuator-state case 的 cross-case 对比，也继续支持这个判断
- `40/0.8` 当前不再作为“output 主导”的独立反例使用；更合理的口径是：proxy 判据不稳，但主解释仍应回到“执行链主导 + coupled_geometry 并发偏置”

## 假设

### H1. 执行链复合延迟是主要放大器

含义：

- 高 `kp` 下，输出本身不一定错
- 但通信/驱动/机构响应太慢，导致 touchdown 时相位滞后被放大

可观察特征：

- `lpf -> actuator` 迟滞明显
- `actuator -> pos` 迟滞明显
- `sole_roll` 仍主要跟随执行链，不直接跟随 output

### H2. 并联映射/符号链仍在制造镜像偏置

含义：

- 左右脚在 swing 期就已经存在稳定镜像 `roll` 签名
- 这不是单纯延迟造成的

可观察特征：

- 左右脚 `sole_roll` 符号稳定相反
- `joint-space` 很小，但 `foot-space` 倾斜明显

### H3. 硬件退化只在接触工况被放大

含义：

- 真机以前能走，说明静态代码并非新近错误
- 但并联机构效率下降、间隙、摩擦、零位漂移可能把旧的脆弱性放大

可观察特征：

- 自由空间看起来还行
- 接触窗一来就出现高频抖动 / 迟滞 / 不收敛

## 计划的最小验证

### Phase A. actuator-state 日志补录与拆解

状态：`done`

已补录：

- `/actuator_cmd`
- `/actuator_states`

已完成：

- `pos_des_lpf -> pos` 代理判定
- `actuator_cmd -> actuator_state -> joint_pos -> sole_roll` 拆分
- 前 `4` 个 `touchdown` 的 actuator-state 级别来源判断

当前结论：

- `actuator_cmd -> actuator_state` 未见独立大滞后段
- 更明显的迟滞落在 `actuator_state -> joint_pos`
- `sole_roll` 仍主要跟随执行链

### Phase B. 同轨迹多组 kp 重复测

状态：`done`

用相同路线、相同前 4 步口径，至少比较：

- `25 / 0.5`
- `35 / 0.5`
- `40 / 0.8`
- `50 / 0.8`

目标：

- 判断高 `kp` 时的 lag 是稳定增大，还是只在某些步放大
- 看低 `kp` 是否只是把滞后压住，但不改变镜像偏置
- 当前已完成 `5` 组 proxy + `1` 组 `actuator-state` 的第一轮 cross-case 汇总
- 当前优先缺口是 `40/0.8` 的 `actuator-state` 样本，用于确认它是否只是 proxy 判据不稳，而非真正的 output 主导
- 其次补 `50/0.8` 的 `actuator-state` 样本

### Phase C. 接触窗和腾空窗分离

状态：`done`

仍然只看：

- swing 窗
- touchdown 窗

但增加：

- `actuator` 与 `sole_roll` 的局部相位关系
- `pos_des_lpf` 与 `actuator` 的相位关系

目标：

- 判断滞后是在接触前就已形成，还是在接触瞬间才被放大

### Phase D. 左右脚硬件差异复核

状态：`absorbed by 11/12`

如果 A/B/C 之后还是能看到稳定的左右镜像签名，就要把重点转向硬件：

- 双执行器出力一致性
- 机械间隙
- 回程差
- 编码器零位漂移
- 足底接触边缘变化

## 成功标准

本专项至少要回答下面两个问题中的一个：

1. `lpf -> pos` 的滞后主要是 `actuator_cmd -> actuator_state`，还是 `actuator_state -> joint_pos`
2. 左右镜像 `roll` 偏置主要是映射/符号链，还是硬件退化放大

## 与主线的关系

如果本专项不能把 `coupled_geometry` 再收紧一层，那么后续应优先走：

- 并联映射符号核对
- actuator-state 多组对比与左右脚差异复核
- 左右脚接触工况硬件排查

当前收口见 [10_execution_chain_disentanglement.md](/Users/yumx/code/X1/agibot_x1_infer/.oma/sim2real/results/forward_x_failure/10_execution_chain_disentanglement.md:1)：`output` 不是主瓶颈，`sole_roll` 主要跟随执行链，更明显的内部滞后落在 `actuator_state -> joint_pos`，后续已由 `11/12` 接管。
