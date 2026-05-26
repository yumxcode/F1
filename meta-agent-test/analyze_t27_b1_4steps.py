#!/usr/bin/env python3
"""
t27 新数据 (b1_diag) 4步级联故障分析
Step 1: Hip Roll PD追踪失效
Step 2: 侧向稳定丧失
Step 3: 接触不对称
Step 4: Yaw漂移 / 完全失稳
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ── 数据加载 ──
csv_path = Path("/Users/yumx/code/robot_x/X1/agibot_x1_infer/t27_tracking_lag_b1_diag_20260520_165013.csv")
out_dir = Path("/Users/yumx/code/robot_x/X1/agibot_x1_infer/meta-agent-test/analysis_output")
out_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(csv_path)
t0 = df['timestamp_ns'].iloc[0]
t = (df['timestamp_ns'] - t0) / 1e9
N = len(df)
dt_median = np.median(np.diff(t))
fs = 1.0 / dt_median
dur = t.iloc[-1]

joint_names = [
    'left_hip_pitch_joint', 'left_hip_roll_joint', 'left_hip_yaw_joint',
    'left_knee_pitch_joint', 'left_ankle_pitch_joint', 'left_ankle_roll_joint',
    'right_hip_pitch_joint', 'right_hip_roll_joint', 'right_hip_yaw_joint',
    'right_knee_pitch_joint', 'right_ankle_pitch_joint', 'right_ankle_roll_joint',
]
short_names = ['L_HipP','L_HipR','L_HipY','L_Knee','L_AnkP','L_AnkR',
               'R_HipP','R_HipR','R_HipY','R_Knee','R_AnkP','R_AnkR']

# Transmission direction (from dcu_x1.yaml)
trans_directions = {
    'left_hip_pitch_joint': -1.0, 'right_hip_pitch_joint': -1.0,
    'left_hip_roll_joint': -1.0, 'right_hip_roll_joint': -1.0,
    'left_hip_yaw_joint': -1.0, 'right_hip_yaw_joint': -1.0,
    'left_knee_pitch_joint': -1.0, 'right_knee_pitch_joint': 1.0,
    'left_ankle_pitch_joint': 1.0, 'right_ankle_pitch_joint': 1.0,
    'left_ankle_roll_joint': 1.0, 'right_ankle_roll_joint': 1.0,
}

print(f"数据: {N} 行, 时长={dur:.1f}s, 采样率≈{fs:.1f}Hz")
print(f"时间范围: {t.iloc[0]:.2f}s ~ {t.iloc[-1]:.2f}s")

# ═══════════════════════════════════════════════════════════════
# Step 1: Hip Roll PD追踪失效分析 (含延迟校正 + 方向验证)
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 1: Hip Roll PD 追踪分析 (含互相关延迟校正 + 传动方向)")
print("=" * 70)

hip_roll_joints = ['left_hip_roll_joint', 'right_hip_roll_joint']
hip_roll_short = ['L_HipR', 'R_HipR']

for jname, sname in zip(hip_roll_joints, hip_roll_short):
    action = df[f'action_{jname}'].values
    pos = df[f'pos_{jname}'].values
    pos_des_raw = df[f'pos_des_raw_{jname}'].values
    pos_des_lpf = df[f'pos_des_lpf_{jname}'].values
    effort = df[f'effort_{jname}'].values

    # 核心诊断指标
    corr_action_pos = np.corrcoef(action, pos)[0, 1]
    corr_action_raw = np.corrcoef(action, pos_des_raw)[0, 1]
    corr_raw_pos = np.corrcoef(pos_des_raw, pos)[0, 1]

    # 追踪比
    action_range = np.max(action) - np.min(action)
    pos_range = np.max(pos) - np.min(pos)
    track_ratio = pos_range / action_range * 100 if action_range > 1e-6 else 0

    # RMS误差
    rms_raw2pos = np.sqrt(np.mean((pos_des_raw - pos)**2))

    # 互相关找最佳滞后 (pos_des_raw vs pos)
    n = len(pos_des_raw)
    max_lag = 50
    best_lag, best_corr = 0, -2
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            x, y = pos_des_raw[:lag], pos[-lag:]
        elif lag > 0:
            x, y = pos_des_raw[lag:], pos[:-lag]
        else:
            x, y = pos_des_raw, pos
        if len(x) > 10:
            c = np.corrcoef(x, y[:len(x)])[0, 1]
            if not np.isnan(c) and c > best_corr:
                best_corr, best_lag = c, lag

    # Δ方向一致性 (滤除小噪声)
    d_des = np.diff(pos_des_raw)
    d_pos = np.diff(pos)
    significant = np.abs(d_des) > 0.001
    same_sign = np.sum(np.sign(d_des[significant]) == np.sign(d_pos[significant]))
    opposite_sign = np.sum(np.sign(d_des[significant]) == -np.sign(d_pos[significant]))
    total = same_sign + opposite_sign

    dir_val = trans_directions[jname]
    print(f"\n  {sname} [transmission direction={dir_val:+.0f}]:")
    print(f"    零滞后 pos_des_raw ↔ pos   corr = {corr_raw_pos:+.4f}")
    print(f"    最佳滞后 pos_des_raw ↔ pos corr = {best_corr:+.4f} @ lag={best_lag}帧 ({best_lag*10:.0f}ms)")
    if best_corr > 0.4 and best_lag < 0:
        print(f"    ✓ 延迟{abs(best_lag)*10}ms后相关性强 → PD方向正确, 但存在相位滞后")
    elif best_corr > 0.4:
        print(f"    ✓ 最佳相关性强 → PD方向正确")
    else:
        print(f"    ✗ 最佳相关性仍弱 → PD追踪确实不足")
    print(f"    Δ方向一致率: {same_sign}/{total} ({same_sign/total*100:.1f}%)")
    print(f"    追踪比 pos/action          = {track_ratio:.1f}%")
    print(f"    pos 范围                   = [{np.min(pos):.4f}, {np.max(pos):.4f}]")
    print(f"    pos_des_raw 范围           = [{np.min(pos_des_raw):.4f}, {np.max(pos_des_raw):.4f}]")
    print(f"    pos_des_raw→pos RMS_err    = {rms_raw2pos:.4f} rad")
    print(f"    effort peak={np.max(np.abs(effort)):.1f} Nm, mean_abs={np.mean(np.abs(effort)):.1f} Nm")

# 全关节 零滞后 + 最佳滞后 对比
print("\n  全关节 零滞后 与 最佳滞后 相关性对比:")
print(f"  {'关节':>8s} {'方向':>4s} {'零滞后corr':>10s} {'最佳滞后corr':>12s} {'延迟':>8s} {'追踪比':>8s} {'诊断':>20s}")
all_delay_results = []
for jname, sname in zip(joint_names, short_names):
    pos_des_raw = df[f'pos_des_raw_{jname}'].values
    pos = df[f'pos_{jname}'].values
    action = df[f'action_{jname}'].values

    c0 = np.corrcoef(pos_des_raw, pos)[0, 1]

    n = len(pos_des_raw)
    max_lag = 50
    best_lag, best_corr = 0, -2
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            x, y = pos_des_raw[:lag], pos[-lag:]
        elif lag > 0:
            x, y = pos_des_raw[lag:], pos[:-lag]
        else:
            x, y = pos_des_raw, pos
        if len(x) > 10:
            c = np.corrcoef(x, y[:len(x)])[0, 1]
            if not np.isnan(c) and c > best_corr:
                best_corr, best_lag = c, lag

    action_range = np.max(action) - np.min(action)
    pos_range = np.max(pos) - np.min(pos)
    tr = pos_range / action_range * 100 if action_range > 1e-6 else 0

    dir_val = trans_directions[jname]
    # 诊断: 最佳滞后相关 > 0.4 → 方向正确但延迟; < 0.2 → PD确实失效
    if best_corr > 0.5:
        diag = "✓ 方向正确,含相位延迟"
    elif best_corr > 0.3:
        diag = "⚠ 方向正确,增益偏低"
    elif best_corr > 0.1:
        diag = "⚠ 追踪很弱"
    else:
        diag = "❌ 几乎不追踪"

    all_delay_results.append((sname, c0, best_corr, best_lag, tr, dir_val, diag))
    delay_ms = best_lag * 10  # 每帧10ms
    print(f"  {sname:>8s} {dir_val:>+4.0f} {c0:>+10.4f} {best_corr:>+12.4f} {delay_ms:>+6.0f}ms {tr:>7.1f}% {diag:>20s}")

# 全关节 action↔pos 排序 (零滞后)
print("\n  全关节 action↔pos 零滞后相关性排序:")
all_corrs = []
for jname, sname in zip(joint_names, short_names):
    action = df[f'action_{jname}'].values
    pos = df[f'pos_{jname}'].values
    pos_des_raw = df[f'pos_des_raw_{jname}'].values
    c_ap = np.corrcoef(action, pos)[0, 1]
    c_raw_pos = np.corrcoef(pos_des_raw, pos)[0, 1]
    action_range = np.max(action) - np.min(action)
    pos_range = np.max(pos) - np.min(pos)
    tr = pos_range / action_range * 100 if action_range > 1e-6 else 0
    all_corrs.append((sname, c_ap, c_raw_pos, tr))
all_corrs.sort(key=lambda x: x[1], reverse=True)
for sname, c_ap, c_raw_pos, tr in all_corrs:
    status = "✓" if c_ap > 0.4 else ("⚠" if c_ap > 0.2 else "❌")
    print(f"  {status} {sname:8s}: action↔pos={c_ap:+.4f}, raw↔pos={c_raw_pos:+.4f}, 追踪比={tr:.1f}%")

# ═══════════════════════════════════════════════════════════════
# Step 1 可视化: Hip Roll 控制链路
# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(18, 10))
for idx, (jname, sname) in enumerate(zip(hip_roll_joints, hip_roll_short)):
    action = df[f'action_{jname}'].values
    pos = df[f'pos_{jname}'].values
    pos_des_raw = df[f'pos_des_raw_{jname}'].values
    pos_des_lpf = df[f'pos_des_lpf_{jname}'].values
    effort = df[f'effort_{jname}'].values

    # 左: 时序
    ax1 = axes[idx, 0]
    ax1.plot(t, action, label='action', linewidth=0.6, alpha=0.5)
    ax1.plot(t, pos_des_raw, label='pos_des_raw', linewidth=0.8, alpha=0.7)
    ax1.plot(t, pos, label='pos (actual)', linewidth=1.0)
    ax1.set_ylabel('Position [rad]')
    ax1.set_title(f'{sname}: action → pos_des_raw → pos', fontsize=10)
    ax1.legend(fontsize=7)
    ax1.grid(True, alpha=0.3)

    # 右: 散点图
    ax2 = axes[idx, 1]
    ax2.scatter(pos_des_raw, pos, c=t, cmap='plasma', s=2, alpha=0.6)
    ax2.plot([pos_des_raw.min(), pos_des_raw.max()],
             [pos_des_raw.min(), pos_des_raw.max()], 'r--', linewidth=0.8, label='ideal y=x')
    ax2.set_xlabel('pos_des_raw [rad]')
    ax2.set_ylabel('pos (actual) [rad]')
    ax2.set_title(f'{sname}: PD追踪散点 (pos_des_raw vs pos)', fontsize=10)
    ax2.legend(fontsize=7)
    ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(out_dir / 't27_b1_step1_hip_roll_chain.png', dpi=150)
plt.close()
print("\n✅ Step1 图已保存: t27_b1_step1_hip_roll_chain.png")

# ═══════════════════════════════════════════════════════════════
# Step 2: 侧向稳定丧失
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 2: 侧向稳定丧失分析")
print("=" * 70)

euler_x = df['base_euler_x'].values
euler_y = df['base_euler_y'].values
euler_z = df['base_euler_z'].values
ang_vel_x = df['base_ang_vel_x'].values
ang_vel_y = df['base_ang_vel_y'].values
ang_vel_z = df['base_ang_vel_z'].values

for name, val in [('Roll (base_euler_x)', euler_x), ('Pitch (base_euler_y)', euler_y), ('Yaw (base_euler_z)', euler_z)]:
    print(f"  {name}: mean={np.mean(val):+.4f}, std={np.std(val):.4f}, "
          f"range=[{np.min(val):+.4f}, {np.max(val):+.4f}]")

for name, val in [('GyroX', ang_vel_x), ('GyroY', ang_vel_y), ('GyroZ', ang_vel_z)]:
    print(f"  |{name}|: mean={np.mean(np.abs(val)):.4f}, max={np.max(np.abs(val)):.4f}, "
          f">1rad/s={np.mean(np.abs(val)>1)*100:.1f}%")

# 侧向稳定评判
roll_std = np.std(euler_x)
pitch_std = np.std(euler_y)
print(f"\n  评判: roll_std={roll_std:.4f} rad (阈值0.02), pitch_std={pitch_std:.4f} rad (阈值0.03)")
if roll_std > 0.02:
    print(f"  ⚠ 侧向(roll)摆动超标!")
if pitch_std > 0.03:
    print(f"  ⚠ 俯仰(pitch)摆动超标!")

# 随时间演化的roll趋势
n_segments = 10
seg_len = len(euler_x) // n_segments
print(f"\n  Roll 时间分段分析 (每段约{dur/n_segments:.1f}s):")
for i in range(n_segments):
    seg = euler_x[i*seg_len:(i+1)*seg_len]
    print(f"    段{i+1} [{(i*seg_len)/fs:.1f}-{((i+1)*seg_len)/fs:.1f}s]: "
          f"mean={np.mean(seg):+.4f}, std={np.std(seg):.4f}, "
          f"range={np.max(seg)-np.min(seg):.4f}")

# ═══════════════════════════════════════════════════════════════
# Step 2 可视化: 基体稳定性
# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(3, 1, figsize=(18, 12), sharex=True)

axes[0].plot(t, euler_x, linewidth=0.8, label='Roll X')
axes[0].plot(t, euler_y, linewidth=0.8, label='Pitch Y')
axes[0].axhline(y=0, color='gray', linewidth=0.5)
axes[0].set_ylabel('Euler [rad]')
axes[0].set_title('Step2: 基体姿态角', fontsize=11)
axes[0].legend(fontsize=8)
axes[0].grid(True, alpha=0.3)

axes[1].plot(t, ang_vel_x, linewidth=0.6, label='AngVel X (roll)', alpha=0.8)
axes[1].plot(t, ang_vel_y, linewidth=0.6, label='AngVel Y (pitch)', alpha=0.8)
axes[1].plot(t, ang_vel_z, linewidth=0.6, label='AngVel Z (yaw)', alpha=0.8)
axes[1].axhline(y=0, color='gray', linewidth=0.5)
axes[1].axhline(y=1, color='red', linewidth=0.5, linestyle='--', alpha=0.5)
axes[1].axhline(y=-1, color='red', linewidth=0.5, linestyle='--', alpha=0.5)
axes[1].set_ylabel('Angular Vel [rad/s]')
axes[1].set_title('Step2: 基体角速度', fontsize=11)
axes[1].legend(fontsize=8)
axes[1].grid(True, alpha=0.3)

# Yaw 漂移
yaw_drift_rate = (euler_z[-1] - euler_z[0]) / dur
axes[2].plot(t, euler_z, linewidth=0.8, color='green')
axes[2].axhline(y=0, color='gray', linewidth=0.5)
axes[2].set_ylabel('Yaw [rad]')
axes[2].set_xlabel('Time [s]')
axes[2].set_title(f'Step2: Yaw漂移 (漂移率={yaw_drift_rate:.4f} rad/s = {np.rad2deg(yaw_drift_rate):.2f} deg/s)', fontsize=11)
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(out_dir / 't27_b1_step2_base_stability.png', dpi=150)
plt.close()
print("✅ Step2 图已保存: t27_b1_step2_base_stability.png")

# ═══════════════════════════════════════════════════════════════
# Step 3: 接触不对称
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 3: 接触不对称分析")
print("=" * 70)

l_contact = df['left_contact'].values
r_contact = df['right_contact'].values

l_frac = np.mean(l_contact)
r_frac = np.mean(r_contact)
both_frac = np.mean((l_contact == 1) & (r_contact == 1))
flight_frac = np.mean((l_contact == 0) & (r_contact == 0))

print(f"  左腿接触率:     {l_frac:.1%}")
print(f"  右腿接触率:     {r_frac:.1%}")
print(f"  双足支撑率:     {both_frac:.1%}")
print(f"  腾空率:         {flight_frac:.1%}")
print(f"  接触不对称:     {abs(l_frac - r_frac):.1%}")

# 接触切换频率
l_trans = np.sum(np.abs(np.diff(l_contact)))
r_trans = np.sum(np.abs(np.diff(r_contact)))
print(f"  左腿接触切换:   {l_trans} 次 (≈{l_trans/dur:.1f} Hz)")
print(f"  右腿接触切换:   {r_trans} 次 (≈{r_trans/dur:.1f} Hz)")

# 时间分段接触率
print(f"\n  接触率时间分段分析:")
for i in range(n_segments):
    l_seg = l_contact[i*seg_len:(i+1)*seg_len]
    r_seg = r_contact[i*seg_len:(i+1)*seg_len]
    print(f"    段{i+1}: L={np.mean(l_seg):.1%}, R={np.mean(r_seg):.1%}, "
          f"双足={np.mean((l_seg==1)&(r_seg==1)):.1%}, 腾空={np.mean((l_seg==0)&(r_seg==0)):.1%}")

# ═══════════════════════════════════════════════════════════════
# Step 3 可视化: 接触 + 基体耦合
# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(3, 1, figsize=(18, 10), sharex=True)

axes[0].fill_between(t, 0, 1, where=(l_contact==1), alpha=0.3, color='blue', label='Left Contact')
axes[0].fill_between(t, 0, 1, where=(r_contact==1), alpha=0.3, color='red', label='Right Contact')
axes[0].set_ylabel('Contact')
axes[0].set_title('Step3: 足端接触状态', fontsize=11)
axes[0].legend(fontsize=8, loc='upper right')
axes[0].set_ylim(0, 1.1)

# 接触不对称累积
cum_l = np.cumsum(l_contact) / np.arange(1, len(l_contact)+1)
cum_r = np.cumsum(r_contact) / np.arange(1, len(r_contact)+1)
axes[1].plot(t, cum_l, linewidth=1, color='blue', label='Left cumulative')
axes[1].plot(t, cum_r, linewidth=1, color='red', label='Right cumulative')
axes[1].axhline(y=0.5, color='gray', linewidth=0.5, linestyle='--')
axes[1].set_ylabel('Cumulative Contact Rate')
axes[1].set_title('Step3: 累积接触率演化', fontsize=11)
axes[1].legend(fontsize=8)
axes[1].grid(True, alpha=0.3)

# roll vs contact
axes[2].plot(t, euler_x, linewidth=0.6, color='purple', alpha=0.7, label='Roll X')
axes[2].fill_between(t, euler_x.min(), euler_x.max(),
                     where=((l_contact==1)&(r_contact==0)), alpha=0.15, color='blue', label='仅左脚')
axes[2].fill_between(t, euler_x.min(), euler_x.max(),
                     where=((l_contact==0)&(r_contact==1)), alpha=0.15, color='red', label='仅右脚')
axes[2].axhline(y=0, color='gray', linewidth=0.5)
axes[2].set_ylabel('Roll [rad]')
axes[2].set_xlabel('Time [s]')
axes[2].set_title('Step3: Roll角度 vs 单脚支撑相', fontsize=11)
axes[2].legend(fontsize=8)
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(out_dir / 't27_b1_step3_contact_asymmetry.png', dpi=150)
plt.close()
print("✅ Step3 图已保存: t27_b1_step3_contact_asymmetry.png")

# ═══════════════════════════════════════════════════════════════
# Step 4: Yaw漂移 / 完全失稳
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 4: Yaw漂移 / 完全失稳分析")
print("=" * 70)

# Yaw漂移速率
yaw_start = euler_z[0]
yaw_end = euler_z[-1]
yaw_drift = yaw_end - yaw_start
yaw_drift_rate_rads = yaw_drift / dur
yaw_drift_rate_degs = np.rad2deg(yaw_drift_rate_rads)

print(f"  Yaw 起始:      {yaw_start:+.4f} rad ({np.rad2deg(yaw_start):+.2f}°)")
print(f"  Yaw 最终:      {yaw_end:+.4f} rad ({np.rad2deg(yaw_end):+.2f}°)")
print(f"  总漂移量:      {yaw_drift:+.4f} rad ({np.rad2deg(yaw_drift):+.2f}°)")
print(f"  漂移速率:      {yaw_drift_rate_rads:+.4f} rad/s ({yaw_drift_rate_degs:+.2f}°/s)")
print(f"  |AngVel Z|:    mean={np.mean(np.abs(ang_vel_z)):.4f}, max={np.max(np.abs(ang_vel_z)):.4f}, "
      f">1rad/s={np.mean(np.abs(ang_vel_z)>1)*100:.1f}%")

# 命令速度 vs 实际行为
cmd_linear_x = df['cmd_linear_x'].values
cmd_linear_y = df['cmd_linear_y'].values
cmd_angular_z = df['cmd_angular_z'].values
print(f"\n  命令速度: lin_x={np.mean(cmd_linear_x):.3f}, lin_y={np.mean(cmd_linear_y):.3f}, ang_z={np.mean(cmd_angular_z):.4f}")

# 失稳评估
print(f"\n  失稳综合评估:")
yaw_severe = np.abs(yaw_drift_rate_degs) > 10
angvel_severe = np.max(np.abs(ang_vel_z)) > 3
roll_severe = roll_std > 0.05

if roll_severe:
    print(f"  ❌ 侧向严重失稳 (roll std={roll_std:.4f})")
else:
    print(f"  {'⚠' if roll_std>0.02 else '✓'} 侧向: roll_std={roll_std:.4f}")

if yaw_severe:
    print(f"  ❌ Yaw漂移严重 ({yaw_drift_rate_degs:.1f}°/s > 10°/s)")
else:
    print(f"  {'⚠' if np.abs(yaw_drift_rate_degs)>3 else '✓'} Yaw漂移: {yaw_drift_rate_degs:.1f}°/s")

if angvel_severe:
    print(f"  ❌ Yaw角速度峰值过大 (max={np.max(np.abs(ang_vel_z)):.1f} rad/s)")
else:
    print(f"  {'⚠' if np.max(np.abs(ang_vel_z))>1 else '✓'} Yaw角速度峰值: {np.max(np.abs(ang_vel_z)):.1f} rad/s")

# ═══════════════════════════════════════════════════════════════
# Step 4 可视化: 综合诊断面板
# ═══════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(20, 14))

# 4-panel 级联故障全景
gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

# Panel 1: Hip Roll 追踪 (Step 1)
ax1 = fig.add_subplot(gs[0, :])
for jname, sname, color in [('left_hip_roll_joint', 'L_HipR', 'blue'),
                              ('right_hip_roll_joint', 'R_HipR', 'red')]:
    pos_des_raw = df[f'pos_des_raw_{jname}'].values
    pos = df[f'pos_{jname}'].values
    c = np.corrcoef(pos_des_raw, pos)[0, 1]
    ax1.plot(t, pos_des_raw, linewidth=0.5, color=color, alpha=0.4, linestyle='--')
    ax1.plot(t, pos, linewidth=0.8, color=color, label=f'{sname} (raw↔pos corr={c:+.3f})')
ax1.axhline(y=0, color='gray', linewidth=0.3)
ax1.set_ylabel('Position [rad]')
ax1.set_title('Step1: Hip Roll pos_des_raw(虚线) vs pos(实线) — PD追踪', fontsize=10)
ax1.legend(fontsize=7)
ax1.grid(True, alpha=0.3)

# Panel 2: 基体稳定性 (Step 2)
ax2 = fig.add_subplot(gs[1, 0])
ax2.plot(t, euler_x, linewidth=0.8, label=f'Roll (std={roll_std:.3f})')
ax2.plot(t, euler_y, linewidth=0.8, label=f'Pitch (std={pitch_std:.3f})')
ax2.axhline(y=0, color='gray', linewidth=0.5)
ax2.set_ylabel('Euler [rad]')
ax2.set_title('Step2: 基体姿态角', fontsize=10)
ax2.legend(fontsize=7)
ax2.grid(True, alpha=0.3)

# Panel 3: 接触不对称 (Step 3)
ax3 = fig.add_subplot(gs[1, 1])
ax3.plot(t, cum_l, linewidth=1, color='blue', label=f'Left ({l_frac:.1%})')
ax3.plot(t, cum_r, linewidth=1, color='red', label=f'Right ({r_frac:.1%})')
ax3.axhline(y=0.5, color='gray', linewidth=0.5, linestyle='--')
ax3.set_ylabel('Cumulative Contact Rate')
ax3.set_xlabel('Time [s]')
ax3.set_title(f'Step3: 接触不对称 (Δ={abs(l_frac-r_frac):.1%})', fontsize=10)
ax3.legend(fontsize=7)
ax3.grid(True, alpha=0.3)

# Panel 4: Yaw漂移 (Step 4)
ax4 = fig.add_subplot(gs[1, 2])
ax4.plot(t, euler_z, linewidth=0.8, color='green')
ax4.axhline(y=0, color='gray', linewidth=0.5)
ax4.set_ylabel('Yaw [rad]')
ax4.set_xlabel('Time [s]')
ax4.set_title(f'Step4: Yaw漂移 ({np.rad2deg(yaw_drift):+.1f}°/{dur:.1f}s)', fontsize=10)
ax4.grid(True, alpha=0.3)

# Panel 5: 腿部关节 action↔pos 相关性条形图
ax5 = fig.add_subplot(gs[2, :])
names_ordered = [x[0] for x in all_corrs]
values_ordered = [x[1] for x in all_corrs]
colors = ['#2ecc71' if v > 0.4 else '#f39c12' if v > 0.2 else '#e74c3c' for v in values_ordered]
bars = ax5.bar(names_ordered, values_ordered, color=colors)
ax5.axhline(y=0, color='gray', linewidth=0.5)
ax5.axhline(y=0.2, color='orange', linewidth=0.8, linestyle='--', alpha=0.5, label='弱追踪阈值(0.2)')
ax5.axhline(y=0.4, color='green', linewidth=0.8, linestyle='--', alpha=0.5, label='正常追踪阈值(0.4)')
for bar, val in zip(bars, values_ordered):
    ax5.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 0.02 * np.sign(val),
             f'{val:+.3f}', ha='center', va='bottom' if val>0 else 'top', fontsize=7)
ax5.set_ylabel('Correlation (action ↔ pos)')
ax5.set_title('全关节 action↔pos 相关性排名', fontsize=10)
ax5.legend(fontsize=7)
ax5.grid(True, alpha=0.2, axis='y')

plt.savefig(out_dir / 't27_b1_step4_cascade_panorama.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ Step4 全景图已保存: t27_b1_step4_cascade_panorama.png")

# ═══════════════════════════════════════════════════════════════
# 汇总报告
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY: 4步级联故障诊断汇总")
print("=" * 70)

print(f"""
  Step 1 — Hip Roll PD追踪:
    L_HipR: action↔pos={all_corrs[[x[0] for x in all_corrs].index('L_HipR')][1]:+.4f}, 追踪比={all_corrs[[x[0] for x in all_corrs].index('L_HipR')][3]:.1f}%
    R_HipR: action↔pos={all_corrs[[x[0] for x in all_corrs].index('R_HipR')][1]:+.4f}, 追踪比={all_corrs[[x[0] for x in all_corrs].index('R_HipR')][3]:.1f}%

  Step 2 — 侧向稳定性:
    Roll std={roll_std:.4f} rad (阈值 0.02)
    Pitch std={pitch_std:.4f} rad (阈值 0.03)
    |GyroX| max={np.max(np.abs(ang_vel_x)):.3f} rad/s

  Step 3 — 接触不对称:
    L={l_frac:.1%} R={r_frac:.1%} 双足={both_frac:.1%} 腾空={flight_frac:.1%}
    不对称度 Δ={abs(l_frac-r_frac):.1%}

  Step 4 — Yaw漂移:
    漂移={np.rad2deg(yaw_drift):+.1f}° 速率={yaw_drift_rate_degs:+.1f}°/s
    |AngVel Z| max={np.max(np.abs(ang_vel_z)):.1f} rad/s
""")

# 输出文件汇总
print("生成的文件:")
for f in sorted(out_dir.glob('t27_b1_*')):
    print(f"  {f.name}")

print("\n分析完成。")
