# t27 真机行走不稳分析报告

- **数据源**: `test_logs/data_csv/t27_joint_20260518_1_real.csv`
- **数据行数**: 2052
- **时长**: 20.509 s
- **采样率**: 100.0 Hz
- **dt min/max**: 9.442/10.284 ms
- **平台**: 智元X1 (F1) | R52/R86-2/R86-3, 12DOF

## 1. 基体姿态稳定性

| 指标 | mean | std | RMS | range | abs_p95 | abs_max |
|---|---:|---:|---:|---:|---:|---:|
| roll_x(rad) | 0.04731 | 0.02247 | 0.05237 | 0.12434 | 0.06172 | 0.09443 |
| pitch_y(rad) | 0.04842 | 0.02268 | 0.05347 | 0.11867 | 0.06693 | 0.08762 |
| yaw_z(rad) | -0.69877 | 0.20150 | 0.72724 | 0.73635 | 0.83230 | 0.83230 |
| gyro_x(rad/s) | 0.26734 | 0.40766 | 0.48750 | 3.38598 | 0.75762 | 1.95242 |
| gyro_y(rad/s) | 0.02539 | 0.31397 | 0.31499 | 3.76868 | 0.68222 | 2.15168 |
| gyro_z(rad/s) | -0.31881 | 0.59736 | 0.67711 | 5.87735 | 1.28821 | 3.31249 |

> **评判**: roll std=0.0225 rad, pitch std=0.0227 rad. 人形机器人稳定行走的参考阈值: roll std < 0.02 rad, pitch std < 0.03 rad. ⚠ 超过阈值
> gyro_x abs_p95=0.7576 rad/s, 反映侧向摆动剧烈程度。

## 2. 接触状态与步态相

| 指标 | 左足 | 右足 |
|---|---|---:|
| 接触占比 | 0.136 | 0.669 |
| 接触切换次数 | 171 | 202 |

> 单足支撑相过多(>0.7)表示双足支撑不足，行走不稳。期望双足支撑占比≈0.2~0.3。
## 3. 关节跟踪误差分析

### 3.1 按RMS误差排序

| 关节 | 类型 | 目标 | RMS_err | mean_err | std_err | max_abs_err | 目标范围 | 实际范围 | Pos/目标 | 零滞相关 | 延迟ms | 延迟相关 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| right_hip_pitch_joint | 串行 | des_lpf | 0.6408 | 0.4060 | 0.4958 | 1.2416 | 2.2262 | 0.5530 | 0.248 | 0.233 | 130.0 | 0.444 |
| left_hip_roll_joint | 串行 | des_lpf | 0.3958 | -0.0328 | 0.3944 | 1.5892 | 1.7930 | 0.2046 | 0.114 | 0.107 | 60.0 | 0.411 |
| right_hip_roll_joint | 串行 | des_lpf | 0.3894 | 0.1712 | 0.3497 | 1.4632 | 1.6825 | 0.2514 | 0.149 | -0.159 | 130.0 | 0.018 |
| right_knee_pitch_joint | 串行 | des_lpf | 0.3869 | 0.1408 | 0.3603 | 0.9637 | 1.0795 | 0.9135 | 0.846 | -0.242 | 120.0 | 0.135 |
| left_hip_pitch_joint | 串行 | des_lpf | 0.3498 | 0.1432 | 0.3191 | 1.4142 | 2.1498 | 0.3816 | 0.177 | 0.129 | 130.0 | 0.374 |
| right_ankle_pitch_joint | 并行 | des_raw | 0.3307 | 0.1676 | 0.2851 | 0.6896 | 0.7600 | 0.4408 | 0.580 | 0.420 | -190.0 | 0.537 |
| right_hip_yaw_joint | 串行 | des_lpf | 0.3299 | -0.1443 | 0.2967 | 0.9388 | 1.7125 | 0.6309 | 0.368 | 0.224 | 50.0 | 0.406 |
| left_knee_pitch_joint | 串行 | des_lpf | 0.3162 | -0.2229 | 0.2243 | 0.7393 | 1.2543 | 0.5540 | 0.442 | 0.213 | 110.0 | 0.564 |
| left_ankle_pitch_joint | 并行 | des_raw | 0.2823 | 0.1203 | 0.2554 | 0.6875 | 0.7600 | 0.3598 | 0.473 | -0.230 | 80.0 | -0.083 |
| left_hip_yaw_joint | 串行 | des_lpf | 0.2433 | 0.0507 | 0.2380 | 0.7838 | 1.6201 | 0.4497 | 0.278 | -0.044 | 40.0 | 0.199 |
| right_ankle_roll_joint | 并行 | des_raw | 0.2380 | -0.1338 | 0.1969 | 0.5594 | 1.0493 | 0.5493 | 0.524 | 0.340 | 50.0 | 0.398 |
| left_ankle_roll_joint | 并行 | des_raw | 0.1783 | 0.0110 | 0.1779 | 0.7017 | 1.2800 | 0.4571 | 0.357 | 0.258 | 60.0 | 0.452 |

### 3.2 关节扭矩跟踪 (tau_lpf vs actual effort)

| 关节 | tau_lpf p95 | effort p95 | 最大effort | tau-effort相关 |
|---|---:|---:|---:|---:|
| right_hip_pitch_joint | nan | 14.432 | 31.429 | nan |
| left_hip_roll_joint | nan | 33.675 | 75.043 | nan |
| right_hip_roll_joint | nan | 38.364 | 65.812 | nan |
| right_knee_pitch_joint | nan | 32.992 | 95.458 | nan |
| left_hip_pitch_joint | nan | 14.579 | 31.526 | nan |
| right_ankle_pitch_joint | 14.099 | 13.588 | 24.375 | 0.205 |
| right_hip_yaw_joint | nan | 10.623 | 26.935 | nan |
| left_knee_pitch_joint | nan | 29.280 | 76.117 | nan |
| left_ankle_pitch_joint | 21.268 | 9.220 | 23.475 | 0.473 |
| left_hip_yaw_joint | nan | 10.476 | 26.496 | nan |
| right_ankle_roll_joint | 12.685 | 10.930 | 20.035 | 0.652 |
| left_ankle_roll_joint | 11.185 | 10.789 | 20.451 | 0.842 |

### 3.3 并行关节限位触碰分析

| 关节 | 下限触碰率 | 上限触碰率 |
|---|---:|---:|
| right_ankle_pitch_joint | 14.3% | 51.7% |
| left_ankle_pitch_joint | 15.9% | 9.6% |
| right_ankle_roll_joint | 0.3% | 0.0% |
| left_ankle_roll_joint | 0.0% | 1.4% |

## 4. 左右腿对称性分析

| 左关节 | 右关节 | RMS误差差 | 位置范围比(L/R) | 目标范围比(L/R) | 延迟差(ms) | 力矩p95比(L/R) |
|---|---:|---:|---:|---:|---:|
| left_hip_pitch_joint | right_hip_pitch_joint | 0.2910 | 0.690 | 0.966 | 0.0 | 1.010 |
| left_hip_roll_joint | right_hip_roll_joint | 0.0064 | 0.814 | 1.066 | 70.0 | 0.878 |
| left_hip_yaw_joint | right_hip_yaw_joint | 0.0866 | 0.713 | 0.946 | 10.0 | 0.986 |
| left_knee_pitch_joint | right_knee_pitch_joint | 0.0707 | 0.606 | 1.162 | 10.0 | 0.887 |
| left_ankle_pitch_joint | right_ankle_pitch_joint | 0.0484 | 0.816 | 1.000 | 270.0 | 0.679 |
| left_ankle_roll_joint | right_ankle_roll_joint | 0.0597 | 0.832 | 1.220 | 10.0 | 0.987 |

## 5. 最严重问题汇总

### 5.1 Top 3 最大RMS跟踪误差
- **right_hip_pitch_joint**: RMS=0.6408 rad, 延迟=130.0ms, 相关=0.444
- **left_hip_roll_joint**: RMS=0.3958 rad, 延迟=60.0ms, 相关=0.411
- **right_hip_roll_joint**: RMS=0.3894 rad, 延迟=130.0ms, 相关=0.018
### 5.2 Top 3 最大延迟
- **right_ankle_pitch_joint**: 延迟=-190.0ms, 相关=0.537, RMS=0.3307
- **left_hip_pitch_joint**: 延迟=130.0ms, 相关=0.374, RMS=0.3498
- **right_hip_pitch_joint**: 延迟=130.0ms, 相关=0.444, RMS=0.6408
### 5.3 Top 3 最大力矩输出
- **right_knee_pitch_joint**: max effort=95.458 Nm, p95=32.992
- **left_knee_pitch_joint**: max effort=76.117 Nm, p95=29.280
- **left_hip_roll_joint**: max effort=75.043 Nm, p95=33.675

## 6. 结论与建议

### 发现的问题
1. **基体侧向摆动过大**: roll std=0.0225 rad (阈值0.02)
2. **right_hip_pitch_joint跟踪不良**: RMS=0.6408 rad, 延迟=130.0ms
3. **left_hip_roll_joint跟踪不良**: RMS=0.3958 rad, 延迟=60.0ms
4. **左右不对称**: left_hip_pitch_joint/right_hip_pitch_joint RMS误差差=0.2910 rad
5. **左右不对称**: left_hip_yaw_joint/right_hip_yaw_joint RMS误差差=0.0866 rad
6. **左右不对称**: left_knee_pitch_joint/right_knee_pitch_joint RMS误差差=0.0707 rad
7. **左右不对称**: left_ankle_pitch_joint/right_ankle_pitch_joint RMS误差差=0.0484 rad
8. **左右不对称**: left_ankle_roll_joint/right_ankle_roll_joint RMS误差差=0.0597 rad
9. **扭矩跟踪差**: left_ankle_pitch_joint, right_ankle_pitch_joint 的tau-effort相关<0.5，电机力矩响应异常

### 建议

1. **降低侧向(roll)晃动**: 检查hip_roll关节的PD增益，增加Kp或Kd抑制侧向摆动；考虑增加踝关节roll方向刚度。
3. **减小执行延迟**: left_hip_pitch_joint, left_hip_roll_joint, left_hip_yaw_joint 延迟>130ms，检查通信延迟或关节伺服响应设置。
4. **修正左右不对称**: 检查机械装配是否水平，左右电机参数是否一致。
5. **校准电机力矩环**: 对扭矩跟踪差的关节进行力矩环参数整定，检查电流反馈是否正常。
