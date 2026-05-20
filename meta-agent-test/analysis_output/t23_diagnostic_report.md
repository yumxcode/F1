# T23 真机关节诊断报告

**日期**: 2026-05-20
**数据**: `test_logs/data_csv/t23_joint_20260519_1_real.csv`
**时长**: 40.0s, 4000帧, 100Hz
**可用列**: `timestamp_ns`, `pos_*`, `vel_*`, `target_*`, `target_lpf_*`
**注意**: 此数据集只有关节层数据, 无 action/effort/base_euler/contact/phase 列, 分析范围受限

---

## 核心发现

### 1. 踝关节 target_lpf 严重发散 (P0 Bug)

**所有4个踝关节的 target_lpf 已经发散到物理不可能的范围:**

| 关节 | target raw range | target_lpf range | lpf/raw 倍率 |
|---|---:|---:|---:|
| L_AnkP | 0.76 rad | **31.79 rad** | 41.8x |
| L_AnkR | 1.13 rad | **44.09 rad** | 39.1x |
| R_AnkP | 0.76 rad | **36.56 rad** | 48.1x |
| R_AnkR | 0.95 rad | **34.38 rad** | 36.1x |

**根因推测**: target_lpf 初始值为 denormal 浮点数 (如 `4.6377e-310`), LPF 积分器从此异常状态开始累积, 导致输出发散到远超关节物理限位的值。

> 髋/膝关节的 target_lpf 正常 (lpf/raw ≈ 1.0x), 说明问题仅限于踝关节 LPF 初始化。

### 2. 髋/膝关节 PD 跟踪几乎完全失效

**使用 raw target 作为参考, 髋/膝关节几乎不跟踪指令:**

| 关节组 | mean RMS | mean \|corr\| | 状态 |
|---|---:|---:|---|
| Hip Pitch | 1.12 rad | 0.058 | 完全不跟踪 |
| Hip Roll | 0.62 rad | 0.134 | 几乎不跟踪 |
| Hip Yaw | 0.63 rad | 0.028 | 完全不跟踪 |
| Knee | 0.50 rad | 0.044 | 几乎不跟踪 |
| Ankle Pitch | 0.37 rad | 0.149 | 弱跟踪 |
| Ankle Roll | 0.28 rad | 0.288 | 部分跟踪 |

> **结论**: pos↔target 相关系数接近零 (0.03-0.13), 说明 PD 控制器无法将目标位置转化为实际位置。这比 t27 中报告的 Hip Roll 追踪比 3.5% 更严重——现在是全部 8 个髋/膝关节都处于这种状态。

### 3. 左右不对称严重

| 关节 | pos_corr (L-R) | tgt_corr (L-R) | L 跟踪 RMS | R 跟踪 RMS |
|---|---:|---:|---:|---:|
| **HipR** | **-0.835** | +0.405 | 0.431 | 0.807 |
| **Knee** | **-0.446** | -0.727 | 0.503 | 0.492 |
| **AnkR** | **-0.583** | -0.035 | 0.328 | 0.242 |
| HipY | +0.712 | -0.604 | 0.707 | 0.546 |

- **Hip Roll**: 左右目标本应同向 (tgt_corr=+0.405), 但实际位置却反向 (pos_corr=-0.835)
- **Knee**: 左右目标已反向 (tgt_corr=-0.727), 实际位置也反向 (pos_corr=-0.446)
- **Hip Yaw 偏移**: 左右均值差 -0.76 rad, 可能反映机器人持续转向

### 4. Hip Roll 下极限饱和

| 关节 | tgt 上饱和% | tgt 下饱和% | pos 上饱和% | pos 下饱和% |
|---|---:|---:|---:|---:|
| L_HipR (limit ±0.2) | 44.9% | 22.8% | 0.0% | **90.8%** |
| R_HipR (limit ±0.2) | 41.3% | 52.2% | 0.7% | 1.1% |

**左 Hip Roll 90.8% 时间位置停在 -0.2 rad 下限**, 这说明机械限位或软限位被触发, 关节无法响应正的 target 指令。

### 5. Hip Pitch 速度异常

`L_HipP` 和 `R_HipP` 的 mean|vel| 分别为 5.57 和 6.12 rad/s, **91% 帧速度超过 5 rad/s**。这不是正常的关节运动, 更像高频振荡。

---

## T23 vs T27 对比

| 指标 | t27 (20s) | t23 (40s) | 趋势 |
|---|---|---|:---|
| Hip Roll pos↔target corr | ≈0 (左), -0.19 (右) | -0.20 (左), 0.07 (右) | 同样差 |
| Hip Pitch pos↔target corr | +0.09 (左), +0.19 (右) | -0.05 (左), -0.07 (右) | **更差** |
| Knee pos↔target corr | +0.14 (左), -0.32 (右) | -0.02 (左), -0.06 (右) | **更差** |
| Ankle target_lpf 状态 | 正常 | **❌ 发散 (36-48x)** | **新增严重Bug** |
| Hip Roll pos stuck | 左卡在 ±0.1 | 左卡在 -0.2 (90.8%) | 更严重 |

> **总体趋势: t23 关节跟踪质量比 t27 更差**, 且 t23 新增了踝关节 target_lpf 发散的严重问题。

---

## 修复建议

### P0 — 立即修复

| 优先级 | 问题 | 修复方案 |
|---|---|:---|
| **P0** | 踝关节 target_lpf 发散 | 修复 LPF 初始化: 用当前 target 值初始化 LPF 状态, 阻止 denormal 值进入积分器 |
| **P0** | 髋/膝关节 PD 完全不跟踪 | 大幅提高 Hip/Knee Kp (当前估计 30-45 → 建议 80-120), 验证电机是否正常响应 |
| **P0** | 左 Hip Roll 卡在 -0.2 下限 | 检查机械限位/软限位配置, 确认 R86 电机力矩是否足以推动关节 |

### P1 — 建议修复

| 优先级 | 问题 | 修复方案 |
|---|---|:---|
| **P1** | Hip Pitch 高频振荡 (91%帧 >5rad/s) | 增加 Kd 阻尼项抑制振荡 (当前 ~3.0 → 建议 6.0-8.0) |
| **P1** | Hip Roll 目标饱和 (41-52%) | 放宽 Hip Roll 限位 (当前 ±0.2 → ±0.3 rad) 或降低 action_scale |
| **P1** | Hip Yaw 左右不对称 (均值差 -0.76 rad) | 检查左右 yaw 零位标定 |
| **P1** | 补充缺失的日志列 | 在数据记录中添加 action, effort, base_euler, contact, phase 列, 便于完整诊断 |

### P2 — 深入调查

- 做关节阶跃响应测试, 独立验证 PD 增益和电机响应
- 检查 R86 执行器力矩上限, 确认 hip_roll 能否克服重力负载
- 确认 t23 使用的 PD 配置与 t27 是否相同

---

## 诊断图索引

| 文件名 | 内容 |
|---|---|
| `t23_00_target_lpf_quality.png` | 踝关节 target vs target_lpf 散点 (暴露 LPF 发散) |
| `t23_01_joint_tracking.png` | 全部 12 关节 pos vs target 时间序列 |
| `t23_02_scatter_target_vs_pos.png` | target-pos 散点图 (跟踪质量) |
| `t23_03_joint_velocities.png` | 关节速度时间序列 |
| `t23_04_bilateral.png` | 左右关节对比 |
| `t23_05_error_ranking.png` | 跟踪误差排序 |
| `t23_06_delay_vs_corr.png` | 延迟 vs 相关性散点 |

---

## 验证方法

1. **修复 LPF 初始化后**: 重跑数据采集, target_lpf range 应接近 target raw range (比值 0.8-1.2x)
2. **提高 PD 后**: pos↔target 相关系数应从 ~0.05 提升到 >0.5
3. **左 Hip Roll**: 位置不应 90%+ 时间停在 -0.2 rad 下限
4. **Hip Pitch 速度**: mean|vel| 应从 >5 rad/s 降至 <2 rad/s
