# 强化学习 Sim-to-Real 离线一致性比对 (Offline Parity Check) 测试方案

> **当前执行阶段：T_M 专项测试**（T1 / T2 / T3 / T4 日志已禁用，仅记录 T_M 数据）

## 1. 测试背景
在强化学习部署至物理样机时，存在明显的两段差距（Gap），导致 Pytorch（`.pt`）训练环境下的动作表现与真机 ONNX 推理环境表现不一致。本测试的核心目的在于通过阶段剥离，精确定位“误差源”究竟发生在哪一部分逻辑中，是模型部署推理出的问题，还是特征处理出的问题。

---

## 2. 差异分层与原理解析
强化学习动作执行的全链路为：
`传感器设备` -> `特征工程(C++)/Env(Py)` -> `神经网络推理(ONNX/.pt)` -> `动作指令`

通过隔离不同阶段，我们将问题排查分为两步进行验证测试：
1. **Inference Gap 测试（模型转换排查）**：完全隔离前置的特征工程。我们向 `.pt` 仿真模型和 `.onnx` 真机模型灌入**字节级完美一致**的历史打平矩阵（Observations Vector），对比最终计算出的目标动作集合是否存在数值精度误差或截断错误。
2. **Observation Gap 测试（特征组装排查）**：在确认模型推理引擎一致后，排查前置工程。我们向 Python 和 C++ 送入**完全相同的高频原始传感器日志(`t4_raw`)**，对比双端吐出的观测重组大拼表（Observation History）是否因为低通滤波、四元数计算、滑窗堆叠方向不一致等操作导致特征漂移。

---

## 3. 前置条件与所需文件

### 3.1 目标模型规格（本次测试范围）
| 属性 | 值 |
|---|---|
| 动作输出维度 | **12 维**（左右腿各 6 关节）|
| 观测输入维度 | **3102 维**（含历史滑窗的展平向量）|
| 模型文件格式 | `.pt`（训练侧）/ `.onnx`（部署侧）|

### 3.2 12 维动作关节顺序映射
| 索引 | 关节名称 | 左/右 |
|:---:|---|:---:|
| 0 | `left_hip_pitch_joint` | 左 |
| 1 | `left_hip_roll_joint` | 左 |
| 2 | `left_hip_yaw_joint` | 左 |
| 3 | `left_knee_pitch_joint` | 左 |
| 4 | `left_ankle_pitch_joint` | 左 |
| 5 | `left_ankle_roll_joint` | 左 |
| 6 | `right_hip_pitch_joint` | 右 |
| 7 | `right_hip_roll_joint` | 右 |
| 8 | `right_hip_yaw_joint` | 右 |
| 9 | `right_knee_pitch_joint` | 右 |
| 10 | `right_ankle_pitch_joint` | 右 |
| 11 | `right_ankle_roll_joint` | 右 |

### 3.3 所需文件清单
在正式执行各步骤前，请确认以下文件均已就位：

**`test_logs/data_csv/`（T2 常规日志）**

| 文件 | 来源 | 用途 |
|---|---|---|
| `*.pt` 模型权重 | 训练产出 | Step 2：PT 前向推理 |
| `*.onnx` 模型文件 | Export 产出 | 对比参照（已部署至真机）|
| `t25_action_<timestamp>.csv` | 真机 C++ 日志（T2） | Step 2：ONNX 输出基准 |
| `cfg/rl_x1.yaml` | 项目配置 | 关节顺序 / PD 参数 |

**`test_logs/data_csv/t_m/`（T_M Step 1 专属，walk_leg 触发，时间戳对齐）**

| 文件 | 格式 | 频率 | 用途 |
|---|---|:---:|---|
| `tm_obs_input_<timestamp>.bin` | binary float32，shape `[N, 3102]` | 策略频率 | Step 2：ONNX 输入基准 |
| `tm_raw_joint_pos_<timestamp>.csv` | CSV，`timestamp_ns` + 12 列 | 1000 Hz | Step 3：关节位置原始值 |
| `tm_raw_joint_vel_<timestamp>.csv` | CSV，`timestamp_ns` + 12 列 | 1000 Hz | Step 3：关节速度原始值 |
| `tm_raw_motor_current_<timestamp>.csv` | CSV，`timestamp_ns` + 12 列 | 1000 Hz | Step 3：电机电流原始值 |
| `tm_raw_imu_quat_<timestamp>.csv` | CSV，`timestamp_ns` + w/x/y/z | 1000 Hz | Step 3：IMU 四元数 |
| `tm_raw_imu_gyro_<timestamp>.csv` | CSV，`timestamp_ns` + x/y/z | 1000 Hz | Step 3：IMU 陀螺仪 |
| `tm_raw_imu_accel_<timestamp>.csv` | CSV，`timestamp_ns` + x/y/z | 1000 Hz | Step 3：IMU 加速度 |

> **时间戳对齐说明：** `t_m/` 目录下所有文件由同一次 `walk_leg` 触发，文件名共享相同的 `YYYYMMDD_HHMMSS` 后缀，可直接按文件名配对使用。

---

## 4. 具体执行步骤规划

### Step 1: 准备真机的输入输出基准记录
本着“控制变量法”，需要先从 C++ 端捕获 ONNX 模型的前向传播入参以及输出：
1. **修改真机部署逻辑 `rl_controller.cc`**：
   - 增加日志记录机制，文件命名为 `t26_obs_network_input_<timestamp>.bin`。
   - 在程序执行至 `session_ptr_->Run(...)` 模型运行调用前的瞬间，将当前观测数组指针 `observations_.data()`（`3102` 维 float32，对应 12 维动作输出模型）以**二进制追加写入**方式导出：
     ```cpp
     // 每帧追加写入 3102 个 float32（约 12 KB/帧，50Hz 下 20s ≈ 12 MB）
     fwrite(observations_.data(), sizeof(float), 3102, fp_obs_);
     ```
   - 选用二进制格式而非 CSV 的原因：写入延迟 < 0.1 ms，不干扰 50/100 Hz 控制循环；同等数据量下文件体积约为 CSV 的 1/3。
   - **记录时长：连续稳定行走 20 秒**（50 Hz → 1000 帧，文件约 12 MB；100 Hz → 2000 帧，约 24 MB）。
     - Step 2 Inference Gap 验证：5~10 秒即可判断（确定性比对）。
     - Step 3 Observation Gap 验证：需要完整 20 秒以捕捉滤波器/相位时钟的累积漂移。
2. **收集数据**：运行部署真机/C++级系统测试，进入 `walk_leg` 模式后自动触发，确认日志目录存有：
   - `test_logs/data_csv/t_m/tm_obs_input_<timestamp>.bin`（binary float32，shape `[N, 3102]`，Step 2 输入基准）
   - `test_logs/data_csv/t_m/tm_raw_*_<timestamp>.csv`（6 份，20s @ 1000Hz，Step 3 原始传感器基准，**与 bin 文件时间戳相同**）
   - `test_logs/data_csv/t25_action_<timestamp>.csv`（Step 2 输出基准）

### Step 2: 第一阶段比对 (Pytorch inference vs ONNX log)
该步骤不要求挂载复杂的机器人物理模拟引擎。
1. **构建 Python 测试脚本：**
   - 加载强化学习模型环境依赖及 `.pt` 模型权重文件（`model.eval()` 推理模式）。
   - 读取 `tm_obs_input_<timestamp>.bin`，解析为 `(N_frames, 3102)` 的 Float32 Tensor：
     ```python
     obs_np = np.fromfile("tm_obs_input_...bin", dtype=np.float32).reshape(-1, 3102)
     obs_tensor = torch.tensor(obs_np)  # (N_frames, 3102)
     ```
   - 逐帧执行 `with torch.no_grad(): pt_action = model(obs_tensor)`，输出应为 `(N_frames, 12)` 的动作张量。
   - **Python 脚本框架参考：**
     ```python
     import torch, pandas as pd, numpy as np, matplotlib.pyplot as plt

     # 加载模型
     model = torch.jit.load("path/to/model.pt").eval()

     # 读取 C++ 端观测日志 (每行 3102 个 float)
     obs_np  = np.fromfile("tm_obs_input_...bin", dtype=np.float32).reshape(-1, 3102)
     onnx_df = pd.read_csv("t25_action_...csv")          # 12 列 action

     obs_tensor = torch.tensor(obs_np, dtype=torch.float32)
     with torch.no_grad():
         pt_action = model(obs_tensor).numpy()           # (N, 12)

     onnx_action = onnx_df.iloc[:, :12].values           # (N, 12)
     diff = pt_action - onnx_action
     l2_per_frame = np.linalg.norm(diff, axis=1)         # (N,)

     # 可视化
     fig, axes = plt.subplots(12, 1, figsize=(14, 24), sharex=True)
     joint_names = [
         "L_hip_pitch","L_hip_roll","L_hip_yaw","L_knee","L_ank_pitch","L_ank_roll",
         "R_hip_pitch","R_hip_roll","R_hip_yaw","R_knee","R_ank_pitch","R_ank_roll",
     ]
     for i, ax in enumerate(axes):
         ax.plot(pt_action[:, i], label="PT")
         ax.plot(onnx_action[:, i], label="ONNX", linestyle="--")
         ax.set_ylabel(joint_names[i], fontsize=7)
         ax.legend(fontsize=6)
     plt.tight_layout()
     plt.savefig("inference_gap_compare.png", dpi=150)
     print(f"Max L2 per frame: {l2_per_frame.max():.6f}  Mean: {l2_per_frame.mean():.6f}")
     ```
2. **偏差校验分析：**
   - 提取生成的 **12 维** `PT_Action`（对应左右腿各 6 个关节，顺序见 §3.2 映射表）。
   - 从对应的 `t25_action_...csv` 文件中并行提取同时间戳范围的 `ONNX_Action`。
   - 绘制差异曲线，比对 **L2-Norm（欧氏距离）最大误差值**。
   - **判定准则：**
     - 如果曲线近乎重合（单帧差 $< 1e-4$），说明 ONNX 导出无损。可以放心执行 Step 3。
     - 如果差值极大甚至波动频率对不上，必须打住：检查 `.onnx` 算子是否掉精度、重做 Export 或确认 `.pt` 的输入滑窗 `Sequence` 与 `Batch` 层叠顺序是否和 C++ Flat Array 一一对应。

### Step 3: 第二阶段比对 (Observation engineering sync)
当 Step 2 确认权重一致时，说明 Gap 来自前置的传感器加工。
1. **提取同轨数据：**
   - 直接读取 `test_logs/data_csv/t_m/` 目录下的 6 份原始传感器 CSV（与 `tm_obs_input` binary **同一次 walk_leg 触发、同一时间窗口**），无需额外对齐裁切：
     ```python
     import pandas as pd, numpy as np, glob

     tm_dir = "test_logs/data_csv/t_m"
     ts = "20260415_092100"  # 与 tm_obs_input_*.bin 相同的时间戳后缀

     df_pos  = pd.read_csv(f"{tm_dir}/tm_raw_joint_pos_{ts}.csv",   index_col="timestamp_ns")
     df_vel  = pd.read_csv(f"{tm_dir}/tm_raw_joint_vel_{ts}.csv",   index_col="timestamp_ns")
     df_quat = pd.read_csv(f"{tm_dir}/tm_raw_imu_quat_{ts}.csv",    index_col="timestamp_ns")
     df_gyro = pd.read_csv(f"{tm_dir}/tm_raw_imu_gyro_{ts}.csv",    index_col="timestamp_ns")
     # 读取 tm_obs 基准（用于对比组装结果）
     obs_ref = np.fromfile(f"{tm_dir}/tm_obs_input_{ts}.bin", dtype=np.float32).reshape(-1, 3102)
     ```
   - 所有文件均以 `timestamp_ns` 列作为对齐主键，20 秒窗口完全一致，可直接逐帧对比。
2. **3102 维观测向量典型构成参考（12 关节模型）：**
   > 以下为常见 RL Observation 拼表结构，**请对照实际训练代码确认顺序及维度**：

   | 组件 | 维度 | 说明 |
   |---|:---:|---|
   | 基座线速度 `base_lin_vel` | 3 | Body 坐标系下 |
   | 基座角速度 `base_ang_vel` | 3 | IMU 陀螺仪 |
   | 重力投影向量 `projected_gravity` | 3 | 四元数转换得到 |
   | 速度指令 `commands` | 3 | vx, vy, yaw_rate |
   | 关节位置 `dof_pos` (×历史帧) | 12×H | 滑窗展平 |
   | 关节速度 `dof_vel` (×历史帧) | 12×H | 滑窗展平 |
   | 上一帧动作 `last_action` | 12 | |
   | 步态相位 `phase` | 2 | sin/cos |
   | **合计** | **3102** | H 由实际滑窗长度决定 |

3. **重走测试台特征组装逻辑：**
   - 不开启任何物理驱动，仅调用 IsaacGym / RL 框架的 `env.compute_observations(tm_raw_data)` 组装环境重塑。
   - 重点检查易错点：
     - 低通滤波器初始化状态（`Init_Zeros` vs `Init_First_Frame`）
     - 四元数转欧拉角/重力投影的坐标系约定（NED vs ENU）
     - 滑窗堆叠方向（最新帧在前 vs 在后）
     - 相位时钟是否与真机控制周期严格同步
   - 同步记录被丢弃/保留的相位数据、手柄虚拟指令等。
4. **偏差校验分析：**
   - 将组装后的 PyTorch 最终观测拼表（**3102 维**）与真机实际下发的拼表（`tm_obs_input` binary 中的 3102 维浮点数组）逐帧、逐维度展开对比。
   - 建议按组件分段绘图，快速定位漂移发生的维度区间。
   - **判定准则：** 必能发现某些维度出现特征跳跃、`Init_Zeros` 长度不对或滤波器时钟漂移等核心逻辑不一致 Bug。

---

## 4.1 日志系统实时性风险评估

> **状态：待实测验证**。以下为理论分析，部署后需通过 stderr 日志与 `timestamp_ns` 间距确认是否掉帧。

### 当前 I/O 负载（walk_leg 最坏情况）

进入 `walk_leg` 后，以下 logger 同时活跃：

| Logger | 频率 | 文件数 | 格式 | 说明 |
|---|:---:|:---:|---|---|
| T2 | 策略频率 | 4 CSV | ofstream | decimation 周期 |
| T3 | 策略频率 | 1 CSV | ofstream | decimation 周期 |
| **T4** | **1000 Hz** | **6 CSV** | ofstream | 40s |
| T_M obs | 策略频率 | 1 binary | fwrite | 20s |
| **T_M raw** | **1000 Hz** | **6 CSV** | ofstream | 20s |

- **1000 Hz 路径每帧写 12 行 CSV**（T4 6 份 + T_M raw 6 份），缓冲态约 12-60 μs。
- **主要风险：** `std::ofstream` 缓冲区满时触发 `write()` 系统调用；在 eMMC/Flash 存储上可能产生 200 μs ~ 2 ms 的不可控延迟，超出 1 ms 控制周期预算。
- **数据冗余：** T4 与 T_M raw 在 walk_leg 前 20 秒完全重叠，同一帧传感器数据写了两遍。

### 掉帧检测方法

部署后用以下 Python 检查 `timestamp_ns` 间距是否均匀：

```python
import pandas as pd, numpy as np

df = pd.read_csv("test_logs/data_csv/t_m/tm_raw_joint_pos_<ts>.csv")
dt_us = df["timestamp_ns"].diff().dropna() / 1000  # 转 μs
print(f"帧间距: mean={dt_us.mean():.0f} μs, max={dt_us.max():.0f} μs, std={dt_us.std():.0f} μs")
print(f"超过 1.5ms 的帧数: {(dt_us > 1500).sum()} / {len(dt_us)}")
# 如果 max > 2000 μs 或 "超过 1.5ms" 比例 > 1%，表明日志 I/O 导致掉帧
```

### 若实测掉帧，优先执行以下方案

| 优先级 | 方案 | 改动量 | 预期效果 |
|:---:|---|---|---|
| 1 | T4 与 T_M raw 互斥：walk_leg 仅启 T_M raw，不启 T4 | 最小（加 if 条件） | I/O 减半 |
| 2 | T_M raw 改 binary（`fwrite`）代替 CSV | 中等 | 写延迟降 5-10× |
| 3 | 异步双缓冲：控制线程仅 memcpy 到环形缓冲，后台线程落盘 | 较大 | 彻底消除 flush 尖峰 |

---

## 5. 后续工作流分配建议

### T_M 专项测试（当前阶段）

**当前状态**：T1 / T2 / T3 / T4 已在 `rl_controller.cc` 中禁用（`_logging_enabled_ = false`），仅 T_M 活跃。

- [x] **已完成**：`rl_controller.cc` / `.h` 中 T_M 日志实现（obs binary + 6 份同步原始传感器 CSV）
- [ ] **真机测试**：编译部署，进入 `walk_leg` 模式后稳定行走 **20 秒**，确认 `test_logs/data_csv/t_m/` 目录内生成：
  - `tm_obs_input_<timestamp>.bin`（50 Hz ≈ 12 MB，100 Hz ≈ 24 MB）
  - `tm_raw_joint_pos/vel/motor_current/imu_quat/gyro/accel_<timestamp>.csv`（6 份，共同时间戳）
- [ ] 执行採帧检查：用 §4.1 中的 Python 脚本检查 `timestamp_ns` 间距均匀性（max < 2ms）
- [ ] 完成 Step 2：参照 §4/Step 2 Python 脚本框架，实现 `inference_gap_check.py`，输出 `inference_gap_compare.png`

### 按结果分支执行
- [ ] **若 Step 2 通过**：继续执行 Step 3，实现 `observation_gap_check.py`，逐组件对比 3102 维观测向量。
- [ ] **若 Step 2 不通过**：优先排查 ONNX 导出精度，对比 `torch.onnx.export` 时的 `opset_version`、动态轴设置以及输入 `Batch/Sequence` 维度顺序。

### 验收产出物
| 产出文件 | 验收标准 |
|---|---|
| `inference_gap_compare.png` | 12 条关节曲线 PT/ONNX 近乎重合，单帧 L2 $< 1e-4$ |
| `observation_gap_compare.png` | 3102 维逐维度差值热力图，无明显持续漂移段 |
