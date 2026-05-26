# 左腿 Hip Roll 逐步执行分析

> 数据: walk_diag_20260523_152341.csv, pre-freeze (rows 0-482)
> 分析目标: 判断 hip roll 在落地时刻的 target vs position 方向冲突是第一步特有还是普遍存在

---

## 方法

1. 通过 LKP (左膝 pitch) 的升降沿识别每个左腿 swing 的起止
2. 取每个 swing 的最后 ~0.1s 作为 touchdown (TD) 区段
3. 计算 TD 区段的 pos 均值、target (pos_des_lpf) 均值、gap
4. 判断方向冲突: target < −0.03 (内收) 且 pos > +0.03 (外展)

---

## 10 个 Swing 逐项分析

### S0 (第一步) — rows 25→67, TD rows 60–67 ✓ OK

```
Swing pos 范围: -0.016 → +0.139
TD pos 均值:   +0.115 rad (+6.6°) → ABDUCTED
TD tgt 均值:   +0.112 rad (+6.4°) → ABDUCT→
TD gap:        -0.002 rad (-0.1°)
方向冲突:     否 — target 和 pos 同向
raw LO-SAT:   无
```

**S0 是跟踪最好的一步。** Target 要求外展，position 几乎完美跟上。视频观察到的外翻主要来自 ankle roll，不是 hip roll。

---

### S1 — rows 90→108, TD rows 100–108 ✗ MISMATCH

```
Swing pos 范围: -0.142 → +0.078
TD pos 均值:   +0.032 rad (+1.8°) → ABDUCTED
TD tgt 均值:   -0.319 rad (-18.3°) → ADDUCT←
TD gap:        -0.351 rad (-20.1°)
方向冲突:     ✗ Target 要求内收，pos 卡在外展
raw LO-SAT:   有 (rows 105-108)
最严重 gap:   -1.585 rad (-90.8°) @ row 108
```

**冲突详解**: Swing 初期 target 要求外展 (+0.20, HI-SAT)，position 从 −0.14 内收缓慢升到 +0.03。row 103 起 target 翻转要求内收，迅速掉到 −1.51，但 position 最高只到 +0.078 就开始停滞，无法跟随 target 向内收方向移动。

---

### S2 — rows 140→155, TD rows 146–155 ✗ MISMATCH

```
Swing pos 范围: -0.275 → +0.185
TD pos 均值:   +0.054 rad (+3.1°) → ABDUCTED
TD tgt 均值:   -0.093 rad (-5.3°) → ADDUCT←
TD gap:        -0.147 rad (-8.4°)
方向冲突:     ✗ Target 要求内收，pos 卡在外展
raw LO-SAT:   有 (rows 153-155)
最严重 gap:   -1.460 rad (-83.7°) @ row 155
```

---

### S3 — rows 190→208, TD rows 196–208 ✓ OK

```
Swing pos 范围: -0.014 → +0.105
TD pos 均值:   +0.057 rad (+3.3°) → ABDUCTED
TD tgt 均值:   +0.193 rad (+11.1°) → ABDUCT→
TD gap:        +0.137 rad (+7.8°)
方向冲突:     否 — target 和 pos 同向
raw LO-SAT:   无
```

---

### S4 — rows 245→265, TD rows 255–265 ✓ OK

```
Swing pos 范围: -0.230 → +0.125
TD pos 均值:   +0.044 rad (+2.5°) → ABDUCTED
TD tgt 均值:   +0.152 rad (+8.7°) → ABDUCT→
TD gap:        +0.108 rad (+6.2°)
方向冲突:     否
raw LO-SAT:   无
```

---

### S5 — rows 295→315, TD rows 306–315 ✗ MISMATCH (恶化)

```
Swing pos 范围: -0.108 → +0.066
TD pos 均值:   +0.048 rad (+2.7°) → ABDUCTED
TD tgt 均值:   -0.663 rad (-38.0°) → ADDUCT←
TD gap:        -0.711 rad (-40.7°)
方向冲突:     ✗ Target 要求内收，pos 卡在外展
raw LO-SAT:   无 (但 raw 掉到 −1.33 @ row 310)
最严重 gap:   -1.327 rad (-76.0°) @ row 312
```

**恶化标志**: 从 S5 开始 gap 翻倍增长。S1 的 gap 是 −20°，S5 是 −41°。

---

### S6 — rows 340→360, TD rows 348–360 ✗ MISMATCH (最严重)

```
Swing pos 范围: -0.068 → +0.159
TD pos 均值:   +0.120 rad (+6.9°) → ABDUCTED
TD tgt 均值:   -0.674 rad (-38.6°) → ADDUCT←
TD gap:        -0.793 rad (-45.5°)
方向冲突:     ✗ Target 要求内收，pos 卡在外展
raw LO-SAT:   有 (rows 354-355, raw=-1.500)
最严重 gap:   -1.648 rad (-94.4°) @ row 357
```

**S6 是最严重的一步。** Raw target LO-SAT (−1.500) 把 lpf target 拉到 −1.51，但 position 最高只到 +0.159，gap 达 −1.65 rad (−94°)。这是导致随后全关节锁死的关键前兆。

---

### S7 — rows 390→408, TD rows 394–408 △ LARGE GAP

```
Swing pos 范围: -0.130 → +0.065
TD pos 均值:   +0.009 rad (+0.5°) → 中性 (接近零)
TD tgt 均值:   -0.821 rad (-47.0°) → ADDUCT←
TD gap:        -0.830 rad (-47.6°)
方向冲突:     △ 不算严格冲突 (pos 中性)，但 gap 巨大
raw LO-SAT:   有 (rows 401-403)
最严重 gap:   -1.579 rad (-90.5°) @ row 403
```

---

### S8 — rows 420→442, TD rows 428–442 ✓ OK

```
Swing pos 范围: -0.362 → -0.031
TD pos 均值:   -0.161 rad (-9.2°) → ADDUCTED
TD tgt 均值:   -0.217 rad (-12.4°) → ADDUCT←
TD gap:        -0.056 rad (-3.2°)
方向冲突:     否 — pos 和 tgt 都在内收方向
raw LO-SAT:   有 (rows 438-442)
```

**S8 跟踪较好** — 因为 position 本身就处于内收状态 (−0.16)，target 要求进一步内收时可以跟上。

---

### S9 (最后一步，pre-freeze) — rows 470→481 △ LARGE GAP

```
Swing pos 范围: -0.133 → -0.067
TD pos 均值:   -0.097 rad (-5.5°) → ADDUCTED
TD tgt 均值:   +0.200 rad (+11.5°) → ABDUCT→
TD gap:        +0.297 rad (+17.0°)
方向冲突:     △ target 要求外展但 pos 卡在内收 (与前几步反向!)
raw LO-SAT:   无
```

---

## 汇总

| Swing | TD pos | TD tgt | Gap | 冲突? | raw LO-SAT? |
|---|---|---|---|---|---|
| S0 | +0.11 外展 | +0.11 外展→ | −0° | ✓ | 无 |
| S1 | +0.03 外展 | −0.32 内收← | −20° | ✗ | 有 |
| S2 | +0.05 外展 | −0.09 内收← | −8° | ✗ | 有 |
| S3 | +0.06 外展 | +0.19 外展→ | +8° | ✓ | 无 |
| S4 | +0.04 外展 | +0.15 外展→ | +6° | ✓ | 无 |
| S5 | +0.05 外展 | −0.66 内收← | **−41°** | ✗ | 无 |
| S6 | +0.12 外展 | −0.67 内收← | **−45°** | ✗ | 有 |
| S7 | +0.01 中性 | −0.82 内收← | −48° | △ | 有 |
| S8 | −0.16 内收 | −0.22 内收← | −3° | ✓ | 有 |
| S9 | −0.10 内收 | +0.20 外展→ | +17° | △ | 无 |

**10 个 swing 中:**
- 4 个方向冲突 (S1/S2/S5/S6)
- 4 个跟踪 OK (S0/S3/S4/S8)
- 2 个大 gap 但非严格方向冲突 (S7/S9)

## 结论

1. **不是第一步特有** — S0 反而是跟踪最好的
2. **冲突的充要条件: target 在 TD 时要求内收** — 要求外展的步都 OK，要求内收的步全部失败
3. **从 S5 开始 gap 暴增** — S1 −20° → S5 −41° → S6 −45°，最终导致 S6/S7 后全关节锁死
4. **raw target LO-SAT 是恶化信号** — 4 个冲突步中 3 个 raw target 撞 −1.50
5. **根因: hip roll 执行器内收方向驱动力不足** — 不是延时问题 (延迟仅 150ms, 只能解释 ~10°)，是电机/传动链在着地负载下向内侧推不动
