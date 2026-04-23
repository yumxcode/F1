
## Real Origin vs Real New 对比结论

### 综合评分：**Real Origin 胜（28 : 14）**

| 维度 | Real Origin | Real New | 结论 |
|---|:---:|:---:|---|
| **跟踪误差** | 6 | 6 | 平手。Origin 在 left hip/knee/yaw 更好；New 在 right hip pitch/roll 显著改善（Δ=-0.07~-0.16） |
| **周期一致性** | **7** | 5 | Origin 更稳。New 的 knee_pitch、ankle 处周期间波动更大 |
| **与 Sim 接近度** | **9** | 3 | Origin 大幅胜出。New 在多数关节上偏离 Sim 更远 |
| **左右对称性** | **6** | 0 | Origin 完胜。New 的 ankle_roll 左右不对称达 0.50 rad |

### 各维度详细解读

**1. 跟踪误差（打平）**
- Real New 在右侧关节跟踪有进步：`right_hip_roll` 从 0.68→0.53（改善 23%），`right_hip_pitch` 从 0.40→0.33
- 但左侧部分关节变差：`left_hip_yaw` 从 0.22→0.27，`left_knee_pitch` 从 0.36→0.40

**2. 周期一致性（Origin 胜）**
- Real Origin 在 knee_pitch（0.056 vs 0.063-0.088）和 ankle（0.056-0.11 vs 0.097-0.16）上更稳定
- 说明 Origin 的步态重复性更好

**3. 与 Sim 接近度（Origin 大幅胜出 9:3）**
- Origin 的 hip 系列关节与 Sim 差距极小（0.06-0.09 rad）
- New 在 right_knee_pitch（0.24 vs 0.17）、right_ankle_roll（0.20 vs 0.13）处与 Sim 偏差更大

**4. 左右对称性（Origin 完胜 6:0）**
- **最关键差异**：Real New 的 `ankle_roll` 左右幅度差达 **0.50 rad**，Origin 仅 0.13
- New 的 `ankle_pitch` 不对称 0.18 rad（Origin 仅 0.02）
- 说明 Real New 存在明显的左右不对称问题，可能是硬件标定、地面条件或某侧关节异常导致

### 总结

> **Real Origin 整体更优**——步态更稳定、更对称、更接近仿真。Real New 虽然在右侧 hip 跟踪上有改善，但引入了显著的**左右不对称**和**周期不稳定**问题，建议排查 Real New 的踝关节硬件状态或地面条件差异。