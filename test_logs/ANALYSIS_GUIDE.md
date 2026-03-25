# 测试数据分析脚本使用指南

## 环境准备

### 安装依赖
```bash
pip install -r requirements.txt
```

### 依赖包
- **pandas** >= 1.3.0 — 数据读取和处理
- **numpy** >= 1.21.0 — 数值计算
- **matplotlib** >= 3.4.0 — 图表绘制
- **scipy** >= 1.7.0 — 科学计算（可选）

---

## 脚本使用说明

### 1. T1 静态测试分析 (`analyze_t1.py`)

#### 功能
- **T1-1**: 零位偏差分析 — 关节位置与 init_state 对比
- **T1-2**: IMU 稳定性分析 — 角速度/欧拉角噪声统计
- **T1-3**: 关节速度噪声分析 — 3σ 范围评估

#### 用法
```bash
# 基本分析
python analyze_t1.py t1_static_20260324_170000.csv

# 生成图表和报告
python analyze_t1.py t1_static_20260324_170000.csv --plot --report

# 指定输出目录
python analyze_t1.py t1_static_20260324_170000.csv --plot --output-dir ./results
```

#### 输出图表
| 文件名 | 内容 |
|---|---|
| `t1_1_joint_offset.png` | 各关节位置偏差时间序列 |
| `t1_2_imu_angular_velocity.png` | IMU 角速度时间序列 |
| `t1_2_imu_euler_angles.png` | IMU 欧拉角时间序列 |
| `t1_3_joint_velocity_noise.png` | 关节速度噪声（含 ±3σ 参考线） |

#### 判断标准
| 指标 | 通过条件 |
|---|---|
| T1-1 零位偏差均值 | < 0.02 rad (≈1.15°) |
| T1-2 角速度均值 | < 0.005 rad/s |
| T1-2 角速度标准差 | < 0.01 rad/s |
| T1-2 欧拉角标准差 | < 0.005 rad |
| T1-3 速度噪声 3σ | < 0.1 rad/s |

---

### 2. T2 动态性能测试分析 (`analyze_t2.py`)

#### 功能
- **T2-2**: 步态周期一致性分析
- **T2-3**: 关节轨迹跟踪误差
- **T2-4**: 机身姿态稳定性
- **T2-5**: Action 饱和率分析

#### 用法
```bash
# 自动查找最新数据
python analyze_t2.py --plot

# 指定时间戳
python analyze_t2.py --timestamp 20260324_170000 --plot

# 指定目录
python analyze_t2.py --data-dir ./test_logs --plot
```

#### 输出图表
| 文件名 | 内容 |
|---|---|
| `t2_2_gait_cycle.png` | 足端接触状态和步态周期 |
| `t2_3_joint_tracking.png` | 关节位置跟踪（实际 vs 目标） |
| `t2_4_body_pose.png` | 机身欧拉角和角速度 |

#### 判断标准
| 指标 | 通过条件 |
|---|---|
| 步态周期变异系数 | < 10% |
| 关节跟踪误差（一般） | < 0.10 rad |
| 关节跟踪误差（膝关节） | < 0.15 rad |
| Action 饱和率 | < 5%（良好）/ < 15%（可接受） |

---

### 3. T3 电机电流测试分析 (`analyze_t3.py`)

#### 功能
- **T3-1**: 峰值电流 vs 额定值/峰值限制
- **T3-2**: RMS 电流和功率估算
- **T3-3**: 电流波形统计、尖峰检测

#### 用法
```bash
# 自动查找最新数据
python analyze_t3.py --plot --report

# 指定文件
python analyze_t3.py t3_current_20260324_170000.csv --plot --report
```

#### 输出图表
| 文件名 | 内容 |
|---|---|
| `t3_current_timeseries.png` | 电流时间序列（含额定值参考线） |
| `t3_current_distribution.png` | 电流分布直方图 |
| `t3_current_vs_velocity.png` | 电流-速度散点图 |
| `t3_peak_current_comparison.png` | 峰值电流 vs 额定电流条形图 |

#### 判断标准
| 指标 | 状态 |
|---|---|
| 峰值 < 额定值 | ✓ 正常 |
| 额定值 < 峰值 < 峰值限制 | ⚠ 超过额定值 |
| 峰值 > 峰值限制 | ✗ 超过峰值限制 |
| 电流尖峰占比 | < 5%（正常） |

#### 自定义电机配置
修改 `analyze_t3.py` 中的 `_default_motor_config` 方法：
```python
def _default_motor_config(self):
    config = {}
    config['left_hip_pitch'] = {'rated_current': 12.0, 'peak_limit': 18.0}
    # ... 根据实际电机参数修改
    return config
```

---

### 4. 综合分析工具 (`analyze_all.py`)

#### 功能
- 自动扫描所有测试数据
- 一键分析最新测试
- 生成综合摘要报告

#### 用法
```bash
# 列出所有可用数据
python analyze_all.py --list

# 分析最新数据（推荐）
python analyze_all.py --analyze-latest --plot --report
```

#### 输出
分析结果保存在 `analysis_YYYYMMDD_HHMMSS/` 子目录中，包含：
- `summary_report.txt` — 综合摘要
- `t1_report.txt` — T1 详细报告
- `t3_report.txt` — T3 详细报告
- `*.png` — 各项图表

---

## 故障排查

### 常见问题

1. **ModuleNotFoundError: No module named 'pandas'**
   ```bash
   pip install -r requirements.txt
   ```

2. **FileNotFoundError: 未找到测试数据文件**
   - 确认程序已运行并完成数据采集
   - 检查 `test_logs/` 目录下是否有 CSV 文件

3. **中文显示为方块**
   - 安装中文字体或修改 matplotlib 配置
   - 或注释掉 `plt.rcParams['font.sans-serif']` 行

4. **图表分辨率不够**
   - 修改 `fig.savefig(..., dpi=300)` 提高分辨率

---

## 高级用法

### Python API 调用
```python
from analyze_t1 import T1Analyzer

analyzer = T1Analyzer('test_logs/t1_static_20260324_170000.csv')
df_offset = analyzer.analyze_t1_1_zero_offset()  # 返回 DataFrame
analyzer.plot_results('./output')
```

### 批量分析
```python
from pathlib import Path
from analyze_t1 import T1Analyzer

for csv_file in sorted(Path('test_logs').glob('t1_static_*.csv')):
    analyzer = T1Analyzer(csv_file)
    analyzer.analyze_t1_1_zero_offset()
```

### 导出到 Excel
```python
df = analyzer.analyze_t1_1_zero_offset()
df.to_excel('t1_analysis.xlsx', index=False)
```

---

## 最佳实践

1. **测试后立即分析** — 及时发现异常
2. **保存分析结果** — 建立历史数据库
3. **对比多次测试** — 评估重复性和稳定性
4. **与仿真数据对比** — 量化 sim-to-real gap
5. **关注趋势变化** — 硬件老化和参数漂移
