# 10_execution_chain_disentanglement

状态：`active`

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

## 当前阶段性判断

基于 t27 现有诊断日志，先使用 `pos_des_lpf -> pos` 作为执行链代理后，H2 的代理判定已经支持：

- `lpf -> pos` 迟滞在多数样本里明显存在
- `sole_roll` 仍主要跟随执行链，不直接跟随 output

但由于仓库中还没有补录 `/actuator_states`，这仍然不是严格的 actuator-state 分解，只能作为 H2 的代理结论。

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

### Phase A. 补更细的执行链日志

当前 `t27` 只能看到：

- `action`
- `pos_des_raw`
- `pos_des_lpf`
- `pos`

下一轮要补：

- `/actuator_states`
- 如果可行，再加电机侧 `current / velocity / position` 或等价状态

目标：

- 把 `lpf -> pos` 拆成 `lpf -> actuator` 和 `actuator -> pos`
- 观察高 `kp` 下到底是哪一段变慢

### Phase B. 同轨迹多组 kp 重复测

用相同路线、相同前 4 步口径，至少比较：

- `25 / 0.5`
- `35 / 0.5`
- `40 / 0.8`
- `50 / 0.8`

目标：

- 判断高 `kp` 时的 lag 是稳定增大，还是只在某些步放大
- 看低 `kp` 是否只是把滞后压住，但不改变镜像偏置

### Phase C. 接触窗和腾空窗分离

仍然只看：

- swing 窗
- touchdown 窗

但增加：

- `actuator` 与 `sole_roll` 的局部相位关系
- `pos_des_lpf` 与 `actuator` 的相位关系

目标：

- 判断滞后是在接触前就已形成，还是在接触瞬间才被放大

### Phase D. 左右脚硬件差异复核

如果 A/B/C 之后还是能看到稳定的左右镜像签名，就要把重点转向硬件：

- 双执行器出力一致性
- 机械间隙
- 回程差
- 编码器零位漂移
- 足底接触边缘变化

## 成功标准

本专项至少要回答下面两个问题中的一个：

1. `lpf -> pos` 的滞后主要是通信/驱动段，还是机械/机构段
2. 左右镜像 `roll` 偏置主要是映射/符号链，还是硬件退化放大

## 与主线的关系

如果本专项不能把 `coupled_geometry` 再收紧一层，那么后续应优先走：

- 并联映射符号核对
- `/actuator_states` 级别日志补录
- 左右脚接触工况硬件排查
