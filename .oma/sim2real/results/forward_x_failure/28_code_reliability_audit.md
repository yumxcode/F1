# 代码可靠性审查报告

> 审查对象：`28_forward_x_failure_first6_step_stage_analysis.py` + `03a_round3_landing_window_analysis.py`  
> 目的：评估分析数据和结论的可信度，识别方法论缺陷与可靠边界  
> 日期：2026-05-08

---

## 一、总体评级

| 模块 | 可靠性 | 主要风险 |
|------|--------|---------|
| 数据加载（`load_csv`）| ✅ 高 | 无明显问题 |
| FK 计算（`attach_fk_metrics`）| ⚠️ 中 | BASE_Z 固定、foot_vz 偏差 |
| 触地检测（`detect_touchdowns`）| ⚠️ 中 | 时刻精度 ±20-40ms |
| 延迟估计（`best_lag_samples`）| ⚠️ 中-低 | 短窗口退化率高，粒度 ~10ms |
| 抖动指标（`jitter_metrics`）| ✅ 中-高 | range 受异常值影响 |
| 周期提取（`extract_cycles`）| ⚠️ 中 | 小幅值 gain 完全不可靠 |
| 触地姿态读取 | ✅ 高 | 取决于触地时刻精度 |
| 相位曲线采样 | ✅ 高 | 线性插值，方法正确 |

**结论：定性结论（real/sim 存在系统性差距、35/0.5 右踝失效存在）可信；具体定量数值（lag_ms、gain 精确值）需保留误差裕度。**

---

## 二、逐模块详细审查

### 2.1 数据加载 ✅ 可靠

```python
def load_csv(path: str):
    row["time_sec"] = row["timestamp_ns"] / 1e9
```

- 直接 CSV 解析，字段映射无歧义
- 时间轴用 `timestamp_ns / 1e9` 转秒，精度 1ns，正确
- 空行过滤（`timestamp_ns is None`）正常
- `joint_pos`（`pos_*_joint`）字段直接来自传感器记录，没有二次推算

**无可靠性问题。**

---

### 2.2 FK 计算 ⚠️ 有系统性偏差

#### 2.2.1 BASE_Z 固定为 0.82m

```python
BASE_Z = 0.82
data.qpos[2] = BASE_Z   # 每帧都强制使用固定质心高度
```

步行时机器人质心实际上下浮动约 ±2–4cm，这里被固定为常数。

**对 `rel_height`（left_foot_z - right_foot_z）的影响：**  
由于两脚计算时 base_z 相同偏移，相减后偏移量消除，**rel_height 不受 BASE_Z 固定值影响**。这个量用于触地门控，是可靠的。

**对 `foot_vz`（足部 z 方向速度）的影响：**
```python
rows[idx][f"{side}_foot_vz"] = (curr_z - prev_z) / dt
```
由于 base_z 固定，FK 输出的 foot_z 不包含质心上下运动的贡献。真机行走时质心 z 有约 ±0.02–0.04 m/cycle 的振荡，对应速度约 ±0.05–0.10 m/s。而触地检测的速度门控：

```python
TOUCHDOWN_DESCENT_VEL_MPS = 0.02   # 下降速度阈值
TOUCHDOWN_SETTLE_VEL_MPS  = 0.05   # 稳定速度阈值
```

**这些阈值与质心振荡速度同量级**，因此 foot_vz 的估计误差可能导致触地时刻检测偏移 1–4 帧（约 10–40ms）。

#### 2.2.2 姿态偏置校正（side_bias）的可靠性

```python
stable_rows = [
    row for row in rows
    if int(row[f"{side}_contact"]) == 1
    and int(row[f"{'right' if side == 'left' else 'left'}_contact"]) == 1
    and abs(row["base_euler_x"]) <= 0.20
    and abs(row["base_euler_y"]) <= 0.20
    ...
]
if stable_rows:
    roll_bias = statistics.median(...)
else:
    roll_bias = 0.0
```

**风险点**：对于 failure cases（如 35/0.5），后期步态不稳，双脚同时接触且姿态平稳的帧可能很少，导致 `roll_bias` 从寥寥几帧估计，中位数不稳定。如果 `stable_rows` 为空（极端失败场景），则 bias=0，姿态偏置未校正，`sole_roll/pitch` 数值偏移。

不过，本次分析（section 1–4）主要使用 `pos_*_joint`（关节编码器），不使用 `sole_roll/pitch`，因此姿态偏置校正的可靠性**不直接影响本报告的主要结论**。

---

### 2.3 触地检测 ⚠️ 时刻精度 ±10–40ms

#### 2.3.1 三层 fallback 逻辑

```python
def detect_touchdowns(rows):
    side_events = detect_touchdowns_from_kinematics(rows, side)   # 优先
    if not side_events:
        side_events = detect_touchdowns_from_contact(...)         # 次选
    if not side_events:
        side_events = detect_touchdowns_from_geometry(...)        # 兜底
```

优先使用 `kinematic_fk_hip` 而非 contact 信号。  
这意味着：即使 contact 信号很早触发，仍然以 FK 运动学为准。对 sim 数据，FK 可靠；对 real 数据，FK 精度受 BASE_Z 固定影响（如上）。

#### 2.3.2 `choose_stable_kinematic_touchdown_index` 的时刻漂移

```python
def choose_stable_kinematic_touchdown_index(rows, candidate_idx, side):
    end_idx = find_index_at_or_after(rows, rows[candidate_idx]["time_sec"] + KIN_STABLE_SEARCH_SEC)
    # KIN_STABLE_SEARCH_SEC = 0.08s
    ...
    for idx in range(candidate_idx, end_idx + 1):
        ...稳定性打分
```

在候选触地时刻前后 80ms 窗口内搜索"最稳定"帧作为触地时刻。这会使触地时刻**最多向后漂移 80ms**（朝稳定帧靠近），而稳定帧本质上是已经落地稳定后的帧，不是初次接触时刻。

**后果**：`event.timestamp_sec` 偏晚，所有窗口计算均以此为基准：
- `swing = event_time - 350ms .. event_time - 20ms`  → 往前平移，可能截掉部分摆动末期
- `touchdown = event_time - 50ms .. event_time + 100ms` → 触地窗口起点可能已在真实接触后 30ms，冲击瞬间数据可能丢失

**量化误差估计：** 触地时刻精度约 ±10–40ms，对 swing 窗口（330ms 有效长）影响有限（< 12%），对 touchdown 窗口（150ms）影响显著（可能漏掉初始冲击的 20–40ms 数据）。

#### 2.3.3 去重机制的"错误合并"风险

```python
TOUCHDOWN_DEDUP_SEC = 0.08
if same_side and (same_index or near_same_touch):
    # 保留 first_contact_time 更早的
    deduped[-1] = event
```

同侧 80ms 内的两次检测被合并为一个。正常步态同侧步周期约 0.5–0.8s，80ms 的去重窗口是安全的。但若检测到 ghost touchdown（伪触地），可能把真实触地合并给伪触地，导致 step 编号错位。

**实际影响**：sim 数据 contact 信号干净，风险低；real 数据在失效后期可能有乱序触地，轻度风险。

---

### 2.4 延迟估计 ⚠️ 核心方法有重要限制

```python
def best_lag_samples(x, y, max_lag_samples):
    x = zscore(first_differences(x))   # 差分后 z-score
    y = zscore(first_differences(y))
    best_lag, best_corr = 0, -1e9
    for lag in range(0, max_lag_samples + 1):   # ← 只搜正 lag
        corr = sum(a * b for a, b in zip(xs, ys)) / len(xs)
        if corr > best_corr: ...
    return best_lag, best_corr
```

#### 2.4.1 只搜索正向 lag（target 先于 joint）

搜索范围 `range(0, max_lag_samples+1)`，**不搜索负 lag**（joint 超前 target）。物理上关节不可能超前目标，这是正确的约束。但如果在噪声主导的情况下，真实相关峰在负 lag 侧被截断，最优 lag 会错误落在 lag=0，导致"无延迟"的假阳性判断。

#### 2.4.2 粒度 ≈ 1 帧（~10ms）

```python
max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt_sec, 1e-6))))
# MAX_LAG_SEC = 0.20, dt_sec ≈ 0.01 → max_lag_samples = 20
```

延迟搜索步长等于一帧（约 10ms）。lag_ms 的量化精度约 ±5ms，表中 lag_ms = 10, 20, 30... 均为 10ms 的整数倍，**不能精确到毫秒级**。

#### 2.4.3 短窗口下的退化

| 窗口 | 有效时长 | @10ms/frame | 对齐后最少样本（lag=200ms）|
|------|---------|------------|--------------------------|
| swing | 330ms | ~33帧 | ~13帧（lag=20帧后剩13帧）|
| touchdown | 150ms | ~15帧 | **~0帧（lag=15帧时全丢）** |

**touchdown 窗口仅 150ms，而 MAX_LAG_SEC=200ms，理论上最大 lag 已超过窗口长度**。代码中的 `MIN_SAMPLE_POINTS=10` 保护会让大多数 touchdown+大lag 的组合进入退化（返回 `nan,nan`），但 lag 会被初始化为 0，corr 为 -1e9，markdown 中打印为 `corr=0.000, lag=0.00`。

实际上数据中观察到大量 `corr=0.000, lag=149.99`（边界值），说明代码在有效样本不足时默认返回 `nan`，`lag_ms` 打印为边界值，这是退化标志。这个行为逻辑上正确，但报告中需明确区分"退化"和"零延迟"。

#### 2.4.4 差分后 z-score 的意义

对 `first_differences(x)` 做 z-score，等价于测量**速度信号**的相关性，而非位置信号。这是好的选择：位置信号可能有直流偏置导致假相关，差分消除直流；z-score 归一化消除幅值影响。**此方法论是正确的。**

#### 2.4.5 corr 的物理意义

```python
corr = sum(a * b for a, b in zip(xs, ys)) / len(xs)
```

由于 xs、ys 均已 z-score（均值≈0，std≈1），这等价于 Pearson 相关系数。`corr ∈ [-1, 1]` 时为有效估计；`corr > 1` 偶发（如 sim 中出现 1.0–1.2）是数值问题（z-score 后 std 不严格=1导致），不影响 lag 选取，但打印出来略显奇怪。

---

### 2.5 抖动指标 ✅ 基本可靠，`range` 注意异常值

```python
"range": max(signal) - min(signal),          # 受单点异常值影响
"direction_change_rate_hz": sign_flip_count(signal, DIFF_EPS_RAD) / duration_sec,
```

- `range = max - min`：若信号中有单点尖峰（传感器 glitch），range 会被严重高估。数据中 `40/0.8 step6 swing right roll range = 0.9246 rad` 是一个可疑值，可能就是单点尖峰。
- `direction_change_rate_hz` 使用死区 `DIFF_EPS_RAD = 5e-4 rad`（0.5 mrad），对高频小抖动有一定抑制。
- `dominant_frequency_hz` 使用手工 DFT，正确，但无汉明窗（无加窗），对短序列可能有频率泄漏。

**注意**：`jitter_metrics` 是在**对齐后的信号**上计算的，即已经按估计的 lag 偏移。如果 lag 估计不准，这些指标会在"错对齐"的信号上计算，但对 `range`、`path`、`dominant_freq` 影响不大（这些量不依赖相位对齐）。

---

### 2.6 周期提取与 Gain 分析 ⚠️ 小幅值桶不可信

```python
amplitude_gain = joint_amp / target_amp if target_amp > 1e-9 else math.nan
```

#### 2.6.1 Gain 对小幅值极度敏感

振幅分桶 `AMPLITUDE_BINS = (0.0, 0.005, 0.01, 0.02, 0.04, 0.08, 1.0)`  
**第一桶 [0, 0.005) rad = [0, 5 mrad)** 内的目标幅值约在关节传感器噪声量级（通常 1–3 mrad），此桶内的 `gain` 数字毫无意义：

| 出现的 gain 值 | 实际含义 |
|---------------|---------|
| gain = 60 | target_amp = 0.001 rad（噪声），joint_amp = 0.060 rad（自由运动） |
| gain = 11 | target_amp = 0.003 rad（噪声），joint_amp = 0.033 rad |

这些高增益值**不反映真实的关节过激响应**，而是噪声主导的幅值比值。之前分析报告中引用的 `gain = 26.7` 和 `gain = 60.4` 均出现在 roll axis 的最小幅值桶，需要降低置信度。

**结论**：只有 `amp bin ≥ [0.020, 0.040)` 及以上的 gain 数据具有实际参考价值。

#### 2.6.2 周期提取的 target 驱动性

```python
diffs = [target[i + 1] - target[i] for i in range(len(target) - 1)]
# 按 target 方向切换分割周期
```

周期是按 **target 信号的方向变化**来切割的，而不是 joint 信号。这是合理选择（目标是分析关节对目标的响应），但如果 target 本身变化频繁（高频噪声），会切出大量极短周期（1–2帧），进入高频桶（>20Hz），制造"高频目标"的假象。

**检查**：代码中 `DIFF_EPS_RAD = 5e-4` 的死区会过滤掉 < 0.5mrad 的微小变化，有一定保护，但对 1–2 mrad 的颤抖仍会切周期。这可能高估真机 target 的高频成分。

---

### 2.7 stddev 使用总体公式（轻微偏差）

```python
return math.sqrt(sum((v - mu) ** 2 for v in valid) / len(valid))  # 除以 N
```

N=6 时，总体 std 约比样本 std（除以 N-1）低 8.3%（因子 √(5/6)=0.913）。对 real vs sim 对比结论（real 的 std 是 sim 的 5–15×）影响可忽略，**不影响定性结论**。

---

### 2.8 相位曲线（Section 4）的"跟踪率"计算 ⚠️ 定义需澄清

```python
target_range = max(target_values) - min(target_values)
joint_range  = max(joint_values)  - min(joint_values)
```

相位曲线 Section 4 中的"joint range / target range"并不是标准控制论意义的"跟踪率"。它的含义是：在整个摆动/支撑相内，关节位置曲线的峰峰值 vs 目标曲线的峰峰值。

**潜在问题**：
- 如果 target 和 joint 的极值发生时刻不同（有延迟），两者的 range 仍可相近，但实际跟踪误差可能很大
- 如果 target 单调变化而 joint 振荡，joint_range 可能大于 target_range（显示 gain > 1），不代表过激
- 这个指标只适合粗略判断"关节动了多少"，不能精确量化跟踪质量

之前分析报告中的"跟踪率 11–25%"数字，反映的是 **ankle roll 在摆动相内关节净位移仅为目标净位移的 11–25%**，这个定性结论是有意义的，但不宜直接作为频响增益的估计值。

---

## 三、各主要结论的可靠性重新评级

| 分析报告中的结论 | 可靠性 | 理由 |
|----------------|--------|------|
| Real ankle roll 跟踪率显著低于 sim（方向正确）| ✅ 可信 | 多步、多 case 一致 |
| 具体跟踪率数值（11–25%）| ⚠️ 参考 | 指标定义为 peak-to-peak 比值，非频响 gain |
| Real touchdown 窗口 corr≈0 多（方向正确）| ✅ 可信 | 窗口短导致的真实退化 |
| lag_ms 具体数值（如 10ms、179ms）| ⚠️ 低精度 | 量化步长 10ms，短窗口 lag 不稳定 |
| Real ankle_roll touchdown std >> sim（5-15×）| ✅ 可信 | 直接读 joint_pos，无复杂推算 |
| Gain=60 等极高增益 | ❌ 不可信 | 全部来自 <5mrad 最小幅值桶 |
| Gain>1（过激响应，≥20mrad桶）| ⚠️ 参考 | 有意义但混有延迟效应 |
| 35/0.5 step4 右踝 joint_range=0 | ✅ 可信 | 直接来自传感器 joint_pos |
| 35/0.5"电流保护触发"推断 | ⚠️ 推断 | 代码无法区分保护/数据丢失/控制输出零 |
| real vs sim 触地姿态 hip_pitch std 相当 | ✅ 可信 | 交替步态的正常对称效应 |
| real ankle_roll std 是 sim 的 5–15× | ✅ 高可信 | 直接读传感器，方法最简单可靠 |

---

## 四、关键方法论漏洞与改进建议

### 4.1 漏洞 1：延迟估计无退化阈值，与报告呈现不一致

代码始终返回 lag 和 corr，没有显式"valid/invalid"标记。报告中将 `corr=0.000` 解读为退化是合理的，但**不同读者可能误读低 corr 的 lag 数值**。

**改进**：在输出行中加入 `lag_valid = corr >= 0.3` 字段，明确区分有效和退化记录。

### 4.2 漏洞 2：touchdown 窗口（150ms）与 MAX_LAG（200ms）冲突

MAX_LAG_SEC = 0.20 > 0.15（touchdown 窗口长），理论上对齐后可能没有剩余样本。当前代码靠 `MIN_SAMPLE_POINTS=10` 保护（返回 nan），但实际上这个组合下，所有 lag > 50ms 的 touchdown 估计都应直接视为不可靠，与 swing 窗口不可同等对待。

**改进**：对 touchdown 窗口，建议 `MAX_LAG_SEC = 0.08`（窗口长度的一半），或完全放弃 touchdown 窗口的延迟估计，只保留 `aligned_track_err`（用 lag=0 的固定对齐）。

### 4.3 漏洞 3：小幅值 gain 桶污染报告

[0, 0.005) rad 桶的 gain 完全由噪声主导，应在输出时过滤或标注。

**改进**：在 `extract_cycles` 中增加 `if target_amp < 0.01: continue` 过滤，或在 markdown 中对最小幅值桶加显式免责注释。

### 4.4 漏洞 4：BASE_Z 固定影响 foot_vz 精度

**改进**：从 IMU 或腿部运动学估计质心 z 速度，加入到 foot_vz 补偿：
```python
# 当前
foot_vz = (curr_foot_z - prev_foot_z) / dt
# 改进（需要 imu_vz 字段）
foot_vz = (curr_foot_z - prev_foot_z) / dt + row.get("imu_linear_vel_z", 0.0)
```

### 4.5 漏洞 5：35/0.5 右踝"锁死"需进一步确认

报告推断为"电流过载保护"，但代码层面无法区分以下三种情况：
- (a) 执行器电流限幅保护
- (b) 控制器输出为 0（意图静止）
- (c) 数据录制时该关节字段丢失

**改进**：检查 step4 以后的 `pos_des_raw_right_ankle_*_joint` 字段是否也为 0（如果是，说明控制器输出为 0，而非执行器锁死）。若目标非零而 joint=0，才能确认是执行器级故障。

---

## 五、对前一份分析报告的修订建议

基于本次代码审查，对《前6步细粒度分析报告》的主要修订点：

1. **gain = 20–60 的"极高增益"段落**：需注明这些数值来自 < 5mrad 的最小幅值桶，不反映真实关节过激，建议删除或加注"不可靠"标注；

2. **lag_ms 精度声明**：lag 数值应说明精度为 ±10ms（量化步长），且 touchdown 窗口的 lag 基本不可用；

3. **跟踪率 11–25%**：应说明是 peak-to-peak 位移比，不是频域增益；

4. **"电流过载保护触发"推断**：降级为"疑似"，建议补充 `pos_des_raw` 字段核查；

5. **ankle_roll touchdown std 对比（real vs sim 5–15×）**：这是本报告最可靠的定量结论，无需修改，可以重点保留。

---

*代码审查结束。整体而言，分析框架逻辑严谨，方法论选择合适；主要可靠性风险集中在延迟估计的短窗口退化和小幅值 gain 的噪声主导，不影响核心定性结论。*
