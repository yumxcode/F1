# 踝关节欠阻尼/谐振分析 — 完整方案集

本文件夹汇总了 sim2real 行走测试中踝关节（ankle pitch/roll）欠阻尼与谐振问题的
全部分析方案、代码、报告和数据。

## 文件结构

```
ankle_damping_analysis/
├── README.md                                    # 本文件
│
│  ═══ 方案与方法论 ═══
├── ankle_damping_analysis_methodology.md        # 阻尼分析方法论（核心文档）
│                                                 #   - 指标定义（一/二/三级）
│                                                 #   - fn/ζ 获取方法（阶跃法/频域法/理论法）
│                                                 #   - 谐振判定标准与严重度分级
│                                                 #   - Kp/Kd 调整流程与参考值
│                                                 #   - 完整分析工作流与诊断矩阵
│
├── 谐振问题方案.html                             # 早期理论整理（HTML 交互式文档）
│                                                 #   含 PD 二阶系统推导、Mr/PM/延迟公式
│
│  ═══ 分析代码 ═══
├── ankle_damping_analysis.py                    # ★ 主分析脚本（可直接运行）
│                                                 #   输入: test_logs/data_csv/{sim,t27}*.csv
│                                                 #   输出: table/*.csv + *_report.md
│                                                 #   运行: conda run -n x1 python ankle_damping_analysis.py
│
├── claude_stability_metrics_v2.py               # v2 频域/残差分析脚本（参考）
│                                                 #   更细致的 coherence/delay 对齐分析
│
│  ═══ 分析报告 ═══
├── ankle_damping_analysis_report.md             # 自动生成报告（16 文件 × 4 关节）
│                                                 #   含全部指标的完整表格
│
├── ankle_damping_diagnostic_report.md           # ★ 完整诊断报告（手动分析）
│                                                 #   按方法论工作流对 6 个 Kp/Kd 参数组逐一诊断
│                                                 #   含 8 现象诊断矩阵、风险排名、Kd 调整建议
│
├── claude_stability_metrics_v2_report.md        # v2 频域分析报告
│                                                 #   real/sim 对比 + 延迟对齐复核
│
├── sim2real_ankle_key_metrics_delta_summary.md  # Sim2Real 关键指标差值汇总
│                                                 #   延迟/增益/换向频率/触地姿态/fn/ζ
│
│  ═══ 数据 ═══
└── table/
    ├── ankle_damping_detail.csv                 # 详细指标（64 行，每关节每文件）
    └── ankle_damping_summary.csv                # 汇总指标（18 行，按 case+axis 聚合）
```

## 快速开始

### 运行分析脚本

```bash
cd /path/to/agibot_x1_infer
conda run -n x1 python real2sim/ankle_damping_analysis/ankle_damping_analysis.py
```

**输入**：
- `test_logs/data_csv/t27*.csv` — 真机行走日志
- `test_logs/data_csv/sim/t27*.csv` — 仿真行走日志

**输出**：
- `table/ankle_damping_detail.csv` — 每个关节的完整指标
- `table/ankle_damping_summary.csv` — 按 case+axis 汇总
- `ankle_damping_analysis_report.md` — Markdown 报告

### 阅读顺序建议

1. **先读** `ankle_damping_analysis_methodology.md` — 了解指标定义和分析框架
2. **再读** `ankle_damping_diagnostic_report.md` — 看方法论在实际数据上的完整应用
3. **按需查阅** `sim2real_ankle_key_metrics_delta_summary.md` — 了解 real/sim 差异的初始发现
4. **按需查阅** `谐振问题方案.html` — 浏览器打开，交互式理论推导

## 核心结论摘要

- 所有实测 Kp/Kd (25/0.4, 30/0.4, 35/0.5, 40/0.8) 的阻尼比 ζ 均在 0.12–0.20
  远低于安全阈值 0.4，属于严重欠阻尼
- 真机 ankle_roll 存在负阻尼自激通道：高频 target + 控制延迟 + 机械弹性储能
  + 接地冲击 四因子叠加
- 增大 Kd 后（40/0.8）摆动相明显改善，但支撑相仍失控（step6 翻机）
- Kd 建议值：ζ=0.3 需 Kd≈1.0–1.2，ζ=0.4 需 Kd≈1.2–1.6
- 仿真未复现真机自激的根本原因：缺乏真实传动柔性和接触冲击能量注入

## 依赖

- Python 3.10+
- numpy, scipy, pandas
- conda 环境: `x1`
