# Ankle Step Response

本目录从 `.oma/sim2real/` 中提取踝关节阶跃响应 / `Kp/Kd` 辨识资料，作为独立归档入口。

状态：`independent_archive`

来源范围：`.oma/sim2real/plans/`、`.oma/sim2real/results/`、`.oma/sim2real/*.py`

## 目录结构

```text
sim2real/ankle_step_response/
├── plans/
│   ├── ankle_kp_kd_identification.md
│   └── round_02/
│       ├── 00_overview.md
│       ├── 01_round_02a_air_kpkd_batch.md
│       ├── 02_round_02b_ground_degradation_test.md
│       ├── 03_round_02c_contact_degradation_fix.md
│       ├── 04_round_02d_consistency_retest.md
│       ├── round_02_next_kpkd_batch.md
│       └── round_02d_ankle_consistency_retest.md
├── results/
│   ├── result_5.14.md
│   └── result_5.14_early.md
└── scripts/
    ├── analyze_ankle_identifier_csv.py
    └── set_ankle_identifier_config.py
```

## 读取顺序

1. 先读 `plans/ankle_kp_kd_identification.md`，了解整体辨识目标、测试原则、判据和启动流程。
2. 再读 `plans/round_02/00_overview.md`，了解 Round 2 的阶段拆分。
3. 按 `01 -> 02 -> 03 -> 04` 顺序读取 Round 2A/2B/2C/2D 方案。
4. 最终结果以 `results/result_5.14.md` 为准。
5. `results/result_5.14_early.md` 是早期阶段性结果，只用于追溯旧判断如何被修正。

## 内容边界

- 本目录只保存踝关节阶跃响应 / `Kp/Kd` 闭环辨识相关资料。
- 本目录不承载具体动态任务问题分析，也不把阶跃辨识结论和任何单独故障主题绑定。
- `.oma/sim2real/` 中的原始过程文件仍保留，本目录是面向复查和复用的独立副本。

## 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/analyze_ankle_identifier_csv.py` | 分析 ankle identifier 产出的阶跃 CSV，输出 `tracking_ratio`、超调、过零、峰值时间、稳定时间和响应分类 |
| `scripts/set_ankle_identifier_config.py` | 切换 ankle identifier 配置中的测试侧、测试轴、`kp/kd`、阶跃幅值和输出 CSV 路径 |

## 来源映射

| 本目录文件 | 原始路径 |
|---|---|
| `plans/ankle_kp_kd_identification.md` | `.oma/sim2real/plans/ankle_kp_kd_identification.md` |
| `plans/round_02/00_overview.md` | `.oma/sim2real/plans/sim2real_steps/ankle_kp_kd/00_overview.md` |
| `plans/round_02/01_round_02a_air_kpkd_batch.md` | `.oma/sim2real/plans/sim2real_steps/ankle_kp_kd/01_round_02a_air_kpkd_batch.md` |
| `plans/round_02/02_round_02b_ground_degradation_test.md` | `.oma/sim2real/plans/sim2real_steps/ankle_kp_kd/02_round_02b_ground_degradation_test.md` |
| `plans/round_02/03_round_02c_contact_degradation_fix.md` | `.oma/sim2real/plans/sim2real_steps/ankle_kp_kd/03_round_02c_contact_degradation_fix.md` |
| `plans/round_02/04_round_02d_consistency_retest.md` | `.oma/sim2real/plans/sim2real_steps/ankle_kp_kd/04_round_02d_consistency_retest.md` |
| `plans/round_02/round_02_next_kpkd_batch.md` | `.oma/sim2real/plans/round_02_next_kpkd_batch.md` |
| `plans/round_02/round_02d_ankle_consistency_retest.md` | `.oma/sim2real/plans/round_02d_ankle_consistency_retest.md` |
| `results/result_5.14.md` | `.oma/sim2real/results/sim2real_steps/ankle_kp_kd/round_02_ankle_kp_kd_identification.md` |
| `results/result_5.14_early.md` | `.oma/sim2real/results/round_02_ankle_kp_kd_identification.md` |
| `scripts/analyze_ankle_identifier_csv.py` | `.oma/sim2real/analyze_ankle_identifier_csv.py` |
| `scripts/set_ankle_identifier_config.py` | `.oma/sim2real/set_ankle_identifier_config.py` |
