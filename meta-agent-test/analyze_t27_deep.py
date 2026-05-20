#!/usr/bin/env python3
"""t27 深层次分析：并行模式、力矩饱和、sim对比、控制链延迟"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

data_dir = Path("/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv")
df = pd.read_csv(data_dir / "t27_joint_20260518_1_real.csv")

t0 = df['timestamp_ns'].iloc[0]
t = (df['timestamp_ns'] - t0) / 1e9

joint_names = [
    'left_hip_pitch_joint', 'left_hip_roll_joint', 'left_hip_yaw_joint',
    'left_knee_pitch_joint', 'left_ankle_pitch_joint', 'left_ankle_roll_joint',
    'right_hip_pitch_joint', 'right_hip_roll_joint', 'right_hip_yaw_joint',
    'right_knee_pitch_joint', 'right_ankle_pitch_joint', 'right_ankle_roll_joint',
]
short_names = ['L_HipP','L_HipR','L_HipY','L_Knee','L_AnkP','L_AnkR',
               'R_HipP','R_HipR','R_HipY','R_Knee','R_AnkP','R_AnkR']

# ═══════════════════════════════════════════════════════════
# 1. is_parallel 模式分析
# ═══════════════════════════════════════════════════════════
print("=" * 70)
print("1. PARALLEL MODE ANALYSIS (is_parallel)")
print("=" * 70)
for jname, sname in zip(joint_names, short_names):
    col = f'is_parallel_{jname}'
    if col in df.columns:
        val = df[col].values
        parallel_pct = val.mean() * 100
        print(f"  {sname:12s}: is_parallel=True {parallel_pct:.1f}% of time")
    else:
        print(f"  {sname:12s}: no is_parallel column")

# ═══════════════════════════════════════════════════════════
# 2. 力矩追踪分析 (tau_des vs actual effort)
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("2. TORQUE ANALYSIS (tau_des_lpf vs effort)")
print("=" * 70)
fig, axes = plt.subplots(6, 2, figsize=(16, 16), sharex=True)
for i, (jname, sname) in enumerate(zip(joint_names, short_names)):
    effort = df[f'effort_{jname}'].values
    tau_des = df[f'tau_des_lpf_{jname}'].values
    
    row, col = i % 6, i // 6
    ax = axes[row, col]
    
    has_tau = not np.all(np.isnan(tau_des))
    if has_tau:
        tau_err = effort - tau_des
        rms_tau = np.sqrt(np.mean(tau_err**2))
        ax.plot(t, effort, label='effort(actual)', linewidth=0.5, alpha=0.7)
        ax.plot(t, tau_des, label='tau_des(lpf)', linewidth=0.5, alpha=0.5, linestyle='--')
        ax.set_title(f'{sname}: τ_RMS_err={rms_tau:.2f} Nm', fontsize=9)
    else:
        ax.plot(t, effort, linewidth=0.5, alpha=0.7)
        ax.set_title(f'{sname}: no tau_des', fontsize=9)
    
    ax.axhline(y=0, color='k', linewidth=0.3)
    ax.set_ylabel('Torque [Nm]')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=6)

axes[5,0].set_xlabel('Time [s]')
axes[5,1].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(data_dir / 't27_d2_torque_analysis.png', dpi=150)
plt.close()
print("✅ Torque analysis plot saved.")

# 力矩饱和统计
print("\nTorque Saturation (>10Nm) Summary:")
for jname, sname in zip(joint_names, short_names):
    effort = df[f'effort_{jname}'].values
    tau_des = df[f'tau_des_lpf_{jname}'].values
    has_tau = not np.all(np.isnan(tau_des))
    
    peak_effort = np.max(np.abs(effort))
    mean_abs_eff = np.mean(np.abs(effort))
    sat_pct = np.sum(np.abs(effort) > 10) / len(effort) * 100
    
    if has_tau:
        tau_peak = np.max(np.abs(tau_des[~np.isnan(tau_des)]))
        print(f"  {sname:12s}: peak_eff={peak_effort:6.1f} mean_abs={mean_abs_eff:5.1f} sat>{10}Nm={sat_pct:5.1f}% tau_des_peak={tau_peak:6.1f}")
    else:
        print(f"  {sname:12s}: peak_eff={peak_effort:6.1f} mean_abs={mean_abs_eff:5.1f} sat>{10}Nm={sat_pct:5.1f}% [no tau_des]")

# ═══════════════════════════════════════════════════════════
# 3. pos_des_raw vs pos_des_lpf (低通滤波效果)
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("3. COMMAND FILTER ANALYSIS (pos_des_raw → pos_des_lpf)")
print("=" * 70)
fig, axes = plt.subplots(6, 2, figsize=(16, 14), sharex=True)
for i, (jname, sname) in enumerate(zip(joint_names, short_names)):
    raw = df[f'pos_des_raw_{jname}'].values
    lpf = df[f'pos_des_lpf_{jname}'].values
    
    row, col = i % 6, i // 6
    ax = axes[row, col]
    
    has_both = not (np.all(np.isnan(raw)) or np.all(np.isnan(lpf)))
    if has_both:
        diff = raw - lpf
        ax.plot(t, raw, label='raw', linewidth=0.3, alpha=0.5)
        ax.plot(t, lpf, label='lpf', linewidth=0.5)
        ax.set_title(f'{sname}: raw-lpf max={np.max(np.abs(diff)):.4f}', fontsize=9)
    else:
        valid = raw if not np.all(np.isnan(raw)) else lpf
        ax.plot(t, valid, linewidth=0.4)
        ax.set_title(f'{sname}: only one signal available', fontsize=9)
    
    ax.set_ylabel('Pos [rad]')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=6)

axes[5,0].set_xlabel('Time [s]')
axes[5,1].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(data_dir / 't27_d3_command_filter.png', dpi=150)
plt.close()
print("✅ Command filter plot saved.")

# ═══════════════════════════════════════════════════════════
# 4. Control Chain Delay Estimation (cross-correlation)
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("4. CONTROL CHAIN DELAY ESTIMATION (action→pos)")  
print("=" * 70)

for jname, sname in zip(joint_names, short_names):
    action = df[f'action_{jname}'].values
    pos = df[f'pos_{jname}'].values
    
    # cross-correlation to find lag
    n = len(action)
    max_lag = min(100, n // 4)
    corrs = []
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            a, p = action[:lag], pos[-lag:]
        elif lag > 0:
            a, p = action[lag:], pos[:-lag]
        else:
            a, p = action, pos
        if len(a) > 10 and len(p) > 10:
            corr = np.corrcoef(a, p[:len(a)])[0, 1] if len(a) == len(p[:len(a)]) else 0
            corrs.append((lag, corr))
    
    if corrs:
        best_lag, best_corr = max(corrs, key=lambda x: abs(x[1]))
        print(f"  {sname:12s}: best corr={best_corr:.3f} @ lag={best_lag} frames ({best_lag*0.01:.2f}s)")

# ═══════════════════════════════════════════════════════════
# 5. 动作指令 vs 关节位置 — 散点图
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("5. ACTION vs POSITION SCATTER (control effectiveness)")
print("=" * 70)

fig, axes = plt.subplots(6, 2, figsize=(14, 18))
for i, (jname, sname) in enumerate(zip(joint_names, short_names)):
    action = df[f'action_{jname}'].values
    pos = df[f'pos_{jname}'].values
    vel = df[f'vel_{jname}'].values
    
    row, col = i % 6, i // 6
    ax = axes[row, col]
    scatter = ax.scatter(action, pos, c=np.abs(vel), cmap='plasma', s=1, alpha=0.5)
    ax.set_xlabel('Action [policy output]')
    ax.set_ylabel('Actual Position [rad]')
    
    # compute R²
    if np.std(action) > 1e-6 and np.std(pos) > 1e-6:
        corr = np.corrcoef(action, pos)[0, 1]
        ax.set_title(f'{sname}: R²={corr**2:.3f} (corr={corr:.3f})', fontsize=9)
    else:
        ax.set_title(f'{sname}: low variance', fontsize=9)
    
    ax.grid(True, alpha=0.2)
    ax.axhline(y=0, color='gray', linewidth=0.5)
    ax.axvline(x=0, color='gray', linewidth=0.5)

plt.tight_layout()
plt.savefig(data_dir / 't27_d5_action_vs_pos.png', dpi=150)
plt.close()
print("✅ Action vs position scatter plot saved.")

# ═══════════════════════════════════════════════════════════
# 6. 左右同关节对比 (L/R symmetry)
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("6. BILATERAL SYMMETRY ANALYSIS")
print("=" * 70)

pairs = [
    ('left_hip_pitch_joint', 'right_hip_pitch_joint', 'HipP'),
    ('left_hip_roll_joint', 'right_hip_roll_joint', 'HipR'),
    ('left_hip_yaw_joint', 'right_hip_yaw_joint', 'HipY'),
    ('left_knee_pitch_joint', 'right_knee_pitch_joint', 'Knee'),
    ('left_ankle_pitch_joint', 'right_ankle_pitch_joint', 'AnkP'),
    ('left_ankle_roll_joint', 'right_ankle_roll_joint', 'AnkR'),
]

for l_j, r_j, name in pairs:
    l_pos = df[f'pos_{l_j}'].values
    r_pos = df[f'pos_{r_j}'].values
    
    # Expected symmetry: L_pos ≈ -R_pos for some joints (hip roll, yaw)
    # For others: L_pos ≈ R_pos
    corr = np.corrcoef(l_pos, r_pos)[0, 1]
    mean_diff = np.mean(l_pos - r_pos)
    rms_diff = np.sqrt(np.mean((l_pos - r_pos)**2))
    
    print(f"  {name:12s}: L-R corr={corr:.3f}, mean_diff={mean_diff:+.4f}, RMS_diff={rms_diff:.4f}")

# ═══════════════════════════════════════════════════════════
# 7. 异常事件检测 — 找"跌倒"或"大扰动"时刻
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("7. ANOMALY DETECTION (large disturbance events)")
print("=" * 70)

# 检测 base_euler 剧烈变化
euler_x = df['base_euler_x'].values
euler_x_dot = np.abs(np.diff(euler_x)) / np.diff(t.values)
x_dot_peak = np.max(euler_x_dot)
x_dot_mean = np.mean(euler_x_dot)
print(f"  Base roll rate: mean={x_dot_mean:.4f}, peak={x_dot_peak:.4f} rad/s")

# 检测角速度峰值
for name, col in [('Roll', 'base_ang_vel_x'), ('Pitch', 'base_ang_vel_y'), ('Yaw', 'base_ang_vel_z')]:
    val = np.abs(df[col].values)
    print(f"  |AngVel {name:6s}|: mean={val.mean():.4f}, max={val.max():.4f}, >1rad/s={np.mean(val>1)*100:.1f}%")

# 检测关节位置异常跳变
print("\n  Joint position jump events (>0.5rad/frame):")
for jname, sname in zip(joint_names, short_names):
    pos = df[f'pos_{jname}'].values
    jumps = np.abs(np.diff(pos))
    n_jumps = np.sum(jumps > 0.5)
    if n_jumps > 0:
        print(f"    {sname:12s}: {n_jumps} jumps (max={jumps.max():.3f} rad/frame)")

# ═══════════════════════════════════════════════════════════
# 8. 足端接触 vs base roll 耦合分析
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("8. CONTACT vs BASE ROLL COUPLING")
print("=" * 70)

l_contact = df['left_contact'].values
r_contact = df['right_contact'].values

# 单脚支撑时 base_euler_x 的变化
for stance_name, stance_mask in [('LeftStance', l_contact == 1), ('RightStance', r_contact == 1)]:
    roll_in_stance = euler_x[stance_mask]
    if len(roll_in_stance) > 10:
        print(f"  {stance_name}: roll mean={roll_in_stance.mean():+.4f}, std={roll_in_stance.std():.4f}")

# flight phase roll
flight_mask = (l_contact == 0) & (r_contact == 0)
if flight_mask.sum() > 10:
    roll_flight = euler_x[flight_mask]
    print(f"  Flight: roll mean={roll_flight.mean():+.4f}, std={roll_flight.std():.4f}")

# ═══════════════════════════════════════════════════════════
# 9. 模拟 vs 真实对比 (t23数据)
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("9. SIM vs REAL COMPARISON (t23 data)")
print("=" * 70)

try:
    sim_df = pd.read_csv(data_dir / "t23_joint_20260515_1_sim.csv")
    real_df = pd.read_csv(data_dir / "t23_joint_20260515_1_real.csv")
    
    # 对齐时间
    t0_sim = sim_df['timestamp_ns'].iloc[0]
    t0_real = real_df['timestamp_ns'].iloc[0]
    t_sim = (sim_df['timestamp_ns'] - t0_sim) / 1e9
    t_real = (real_df['timestamp_ns'] - t0_real) / 1e9
    
    # 取前5秒
    sim_window = t_sim < 5
    real_window = t_real < 5
    
    print(f"  Sim frames: {len(sim_df)}, Real frames: {len(real_df)}")
    
    joint_map_sim = [
        'pos_left_hip_pitch_joint', 'pos_left_hip_roll_joint', 'pos_left_hip_yaw_joint',
        'pos_left_knee_pitch_joint', 'pos_left_ankle_pitch_joint', 'pos_left_ankle_roll_joint',
        'pos_right_hip_pitch_joint', 'pos_right_hip_roll_joint', 'pos_right_hip_yaw_joint',
        'pos_right_knee_pitch_joint', 'pos_right_ankle_pitch_joint', 'pos_right_ankle_roll_joint',
    ]
    
    fig, axes = plt.subplots(6, 2, figsize=(16, 16), sharex=True)
    for i, (jname, sname) in enumerate(zip(joint_map_sim, short_names)):
        sim_pos = sim_df[jname].values[:sum(sim_window)]
        real_pos = real_df[jname].values[:sum(real_window)]
        
        row, col = i % 6, i // 6
        ax = axes[row, col]
        ax.plot(t_sim[sim_window], sim_pos, label='sim', linewidth=0.6, alpha=0.7)
        ax.plot(t_real[real_window], real_pos, label='real', linewidth=0.6, alpha=0.7)
        ax.set_ylabel(f'{sname} [rad]')
        ax.set_title(f'{sname}: sim vs real (t23)', fontsize=9)
        ax.legend(fontsize=6)
        ax.grid(True, alpha=0.3)
    
    axes[5,0].set_xlabel('Time [s]')
    axes[5,1].set_xlabel('Time [s]')
    plt.tight_layout()
    plt.savefig(data_dir / 't27_d9_sim_vs_real_t23.png', dpi=150)
    plt.close()
    print("✅ Sim vs Real plot saved.")
    
    # 量化对比
    print("\n  Quantified SIM vs REAL (t23, first 5s):")
    for jname, sname in zip(joint_map_sim, short_names):
        sim_pos = sim_df[jname].values[:sum(sim_window)]
        real_pos = real_df[jname].values[:sum(real_window)]
        
        # resample real to sim length
        min_len = min(len(sim_pos), len(real_pos))
        sim_pos = sim_pos[:min_len]
        real_pos = real_pos[:min_len]
        
        rms_diff = np.sqrt(np.mean((sim_pos - real_pos)**2))
        print(f"  {sname:12s}: RMS_diff={rms_diff:.4f} rad")
    
except FileNotFoundError as e:
    print(f"  ⚠️ Could not load t23 data: {e}")
except Exception as e:
    print(f"  ⚠️ Error in sim/real comparison: {e}")

print("\n" + "=" * 70)
print("Deep analysis complete.")
print("=" * 70)
