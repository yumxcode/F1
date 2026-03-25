# Sim-to-Real 测试日志

本目录包含 T1/T2/T3 系列 sim-to-real 测试的日志文件和分析工具。

## 测试系列

### T1 静态测试
- **T1-1**: 零位偏差测试 — 关节位置与 init_state 的偏差
- **T1-2**: IMU 稳定性测试 — 角速度和欧拉角噪声
- **T1-3**: 关节速度噪声测试 — 静态下速度读数的 3σ 范围
- **T1-4**: 延迟测试 — JointState 接收到 JointCommand 发出的时间差

### T2 动态性能对比测试
- **T2-2**: 步态周期测试 — 足端接触周期一致性
- **T2-3**: 关节轨迹测试 — 实际位置与目标位置跟踪误差
- **T2-4**: 机身姿态测试 — 行走中 Roll/Pitch/Yaw 稳定性
- **T2-5**: 网络输出测试 — Action 饱和率分析

### T3 电机电流监测测试
- **T3-1**: 峰值电流测试 — 与额定值、峰值限制对比
- **T3-2**: 平均功耗测试 — RMS 电流和功率估算
- **T3-3**: 电流波形测试 — 统计特征和尖峰检测

## 文件命名规则

| 文件格式 | 说明 |
|---|---|
| `t1_static_YYYYMMDD_HHMMSS.csv` | T1 静态测试数据 |
| `t14_delay_YYYYMMDD_HHMMSS.csv` | T1-4 延迟测试数据 |
| `t22_gait_YYYYMMDD_HHMMSS.csv` | T2-2 步态周期数据 |
| `t23_joint_YYYYMMDD_HHMMSS.csv` | T2-3 关节轨迹数据 |
| `t24_pose_YYYYMMDD_HHMMSS.csv` | T2-4 机身姿态数据 |
| `t25_action_YYYYMMDD_HHMMSS.csv` | T2-5 网络输出数据 |
| `t3_current_YYYYMMDD_HHMMSS.csv` | T3 电机电流数据 |

## 快速开始

### 1. 安装依赖
```bash
cd test_logs
pip install -r requirements.txt
```

### 2. 运行测试（自动采集）
程序启动后自动开始采集数据，终端会打印：
```
[RLController] T1 CSV logging started (max 60000 frames)
[RLController] T2 CSV logging started (max 2000 frames)
[RLController] T3 CSV logging started (max 3000 frames)
[ControlModule] T1-4 delay logging started (max 30000 frames)
```

### 3. 分析数据
```bash
# 综合分析（推荐）
python analyze_all.py --analyze-latest --plot --report

# 分析单个测试
python analyze_t1.py t1_static_20260324_170000.csv --plot --report
python analyze_t2.py --plot
python analyze_t3.py --plot --report
```

## 注意事项

1. **采集频率**: T1 数据 1000Hz（每帧采集），T2/T3 数据约 100Hz（decimation 周期采集）
2. **采集时长**: T1 约 60s，T2 约 20s，T3 约 30s，T1-4 约 30s
3. **effort 字段**: T3 电流数据来自 `JointState.effort`，具体含义（力矩/电流）取决于硬件接口
4. **步态检测**: T2-2 使用踝关节速度阈值法，真机可能需要调整索引和阈值
5. **线程安全**: 所有日志写入在控制循环线程中完成，不影响实时性

## 分析脚本

| 脚本 | 功能 |
|---|---|
| `analyze_t1.py` | T1 静态测试分析（零位偏差、IMU、速度噪声） |
| `analyze_t2.py` | T2 动态测试分析（步态、关节跟踪、姿态、Action） |
| `analyze_t3.py` | T3 电流测试分析（峰值、功耗、波形） |
| `analyze_all.py` | 综合分析工具（一键分析所有测试） |

详细使用说明请参考 `ANALYSIS_GUIDE.md`。
