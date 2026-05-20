#!/usr/bin/env python3
"""
t27 真机行走不稳分析脚本
分析维度：
  1. 基础姿态稳定性 (base_euler_x/y/z) + 角速度
  2. 足端接触对称性 (left/right_contact)
  3. 关节跟踪误差 (pos_des_lpf vs pos)
  4. 关节速度分析
  5. hip_roll 侧向通道专项分析
  6. 相位与步态周期分析
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ── 加载数据 ──
data_dir = Path("/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv")
df = pd.read_csv(data_dir / "t27_joint_20260518_1_real.csv")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

# ── 时间归一化 ──
t0 = df['timestamp_ns'].iloc[0]
t = (df['timestamp_ns'] - t0) / 1e9  # seconds
dt = np.diff(t)
print(f"Duration: {t.iloc[-1]:.2f}s, Frames: {len(df)}")
print(f"Mean dt: {np.mean(dt)*1000:.2f}ms, std: {np.std(dt)*1000:.4f}ms")
print(f"Effective freq: {1/np.mean(dt):.1f}Hz")

# ── Phase info ──
phase_sin = df['phase_sin'].values
phase_cos = df['phase_cos'].values
phase = np.arctan2(phase_sin, phase_cos) % (2*np.pi)
cycle_time = 0.7  # from test plan

# ═══════════════════════════════════════════════════════
# 1. 基础姿态稳定性
# ═══════════════════════════════════════════════════════
fig, axes = plt.subplots(3, 2, figsize=(14, 10), sharex=True)

for i, (name, col) in enumerate([
    ('Roll (x)', 'base_euler_x'),
    ('Pitch (y)', 'base_euler_y'),
    ('Yaw (z)', 'base_euler_z'),
]):
    val = df[col].values
    ax = axes[i, 0]
    ax.plot(t, val, linewidth=0.5)
    ax.set_ylabel(f'{name} [rad]')
    ax.axhline(y=val.mean(), color='r', linestyle='--', alpha=0.5, label=f'mean={val.mean():+.4f}')
    ax.axhline(y=val.mean() + val.std(), color='orange', linestyle=':', alpha=0.5)
    ax.axhline(y=val.mean() - val.std(), color='orange', linestyle=':', alpha=0.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_title(f'{name}: σ={val.std():.5f} rad, range=[{val.min():+.4f}, {val.max():+.4f}]')

for i, (name, col) in enumerate([
    ('AngVel Roll', 'base_ang_vel_x'),
    ('AngVel Pitch', 'base_ang_vel_y'),
    ('AngVel Yaw', 'base_ang_vel_z'),
]):
    val = df[col].values
    ax = axes[i, 1]
    ax.plot(t, val, linewidth=0.5, alpha=0.8)
    ax.axhline(y=0, color='k', linestyle='-', linewidth=0.3)
    ax.set_ylabel(f'{name} [rad/s]')
    ax.grid(True, alpha=0.3)
    ax.set_title(f'{name}: σ={val.std():.4f}, range=[{val.min():+.3f}, {val.max():+.3f}]')

axes[2,0].set_xlabel('Time [s]')
axes[2,1].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(data_dir / 't27_01_base_stability.png', dpi=150)
plt.close()
print("\n✅ 1. Base stability plot saved.")

# ═══════════════════════════════════════════════════════
# 2. 足端接触对称性
# ═══════════════════════════════════════════════════════
left_contact = df['left_contact'].values
right_contact = df['right_contact'].values

l_contact_pct = left_contact.mean() * 100
r_contact_pct = right_contact.mean() * 100
double_stance_pct = ((left_contact == 1) & (right_contact == 1)).mean() * 100
flight_pct = ((left_contact == 0) & (right_contact == 0)).mean() * 100

print(f"\n📊 Contact Analysis:")
print(f"  Left contact ratio:  {l_contact_pct:.1f}%")
print(f"  Right contact ratio: {r_contact_pct:.1f}%")
print(f"  Double stance: {double_stance_pct:.1f}%")
print(f"  Flight phase:  {flight_pct:.1f}%")
print(f"  Asymmetry: |L-R| = {abs(l_contact_pct - r_contact_pct):.1f}%")

# 检测 contact transitions
l_transitions = np.sum(np.abs(np.diff(left_contact)))
r_transitions = np.sum(np.abs(np.diff(right_contact)))
print(f"  Left contact transitions:  {int(l_transitions)}")
print(f"  Right contact transitions: {int(r_transitions)}")

fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
axes[0].plot(t, left_contact, label=f'Left ({l_contact_pct:.1f}%)', linewidth=0.5)
axes[0].plot(t, right_contact + 0.05, label=f'Right ({r_contact_pct:.1f}%)', linewidth=0.5, alpha=0.7)
axes[0].set_ylabel('Contact (0/1)')
axes[0].legend()
axes[0].grid(True, alpha=0.3)
axes[0].set_title(f'Foot Contact (Double Stance: {double_stance_pct:.1f}%, Flight: {flight_pct:.1f}%)')

# 接触异步/失稳检测：统计双足同时离地时长
flight_segments = []
in_flight = False
flight_start = 0
for i in range(len(left_contact)):
    if left_contact[i] == 0 and right_contact[i] == 0:
        if not in_flight:
            flight_start = i
            in_flight = True
    else:
        if in_flight:
            flight_dur = t.iloc[i] - t.iloc[flight_start]
            flight_segments.append(flight_dur)
            in_flight = False

if flight_segments:
    axes[1].bar(range(len(flight_segments)), flight_segments, alpha=0.6)
    axes[1].set_ylabel('Duration [s]')
    axes[1].set_title(f'Flight Phase Segments (total={len(flight_segments)}, max={max(flight_segments):.3f}s)')
    print(f"  Flight segments: {len(flight_segments)}, max duration: {max(flight_segments):.3f}s")
else:
    axes[1].text(0.5, 0.5, 'No pure flight phases', transform=axes[1].transAxes)

axes[1].set_xlabel('Flight segment #')
axes[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(data_dir / 't27_02_contact_analysis.png', dpi=150)
plt.close()
print("✅ 2. Contact analysis plot saved.")

# ═══════════════════════════════════════════════════════
# 3. 关节跟踪误差分析
# ═══════════════════════════════════════════════════════
joint_names = [
    'left_hip_pitch_joint', 'left_hip_roll_joint', 'left_hip_yaw_joint',
    'left_knee_pitch_joint', 'left_ankle_pitch_joint', 'left_ankle_roll_joint',
    'right_hip_pitch_joint', 'right_hip_roll_joint', 'right_hip_yaw_joint',
    'right_knee_pitch_joint', 'right_ankle_pitch_joint', 'right_ankle_roll_joint',
]

tracking_errors = {}
fig, axes = plt.subplots(6, 2, figsize=(16, 18), sharex=True)
short_names = [
    'L_HipP', 'L_HipR', 'L_HipY', 'L_Knee', 'L_AnkP', 'L_AnkR',
    'R_HipP', 'R_HipR', 'R_HipY', 'R_Knee', 'R_AnkP', 'R_AnkR',
]

for i, (jname, sname) in enumerate(zip(joint_names, short_names)):
    pos = df[f'pos_{jname}'].values
    pos_des = df[f'pos_des_lpf_{jname}'].values
    
    # Check if pos_des exists (may be NaN on some joints like ankle)
    if pos_des is not None and not np.all(np.isnan(pos_des)):
        err = pos - pos_des
        tracking_errors[jname] = err
        rms = np.sqrt(np.mean(err**2))
        max_err = np.max(np.abs(err))
        
        row, col = i % 6, i // 6
        ax = axes[row, col]
        ax.plot(t, pos, label='actual', linewidth=0.4, alpha=0.8)
        ax.plot(t, pos_des, label='desired', linewidth=0.4, alpha=0.6, linestyle='--')
        ax.fill_between(t, pos, pos_des, alpha=0.15, color='red')
        ax.set_ylabel(f'{sname} [rad]')
        ax.set_title(f'{sname}: RMS={rms:.4f}, max|err|={max_err:.4f}', fontsize=9)
        ax.legend(fontsize=6)
        ax.grid(True, alpha=0.3)
    else:
        row, col = i % 6, i // 6
        ax = axes[row, col]
        ax.plot(t, pos, label='actual', linewidth=0.4)
        ax.set_ylabel(f'{sname} [rad]')
        ax.set_title(f'{sname}: no des_lpf', fontsize=9)
        ax.grid(True, alpha=0.3)

axes[5,0].set_xlabel('Time [s]')
axes[5,1].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(data_dir / 't27_03_joint_tracking.png', dpi=150)
plt.close()

# ── 打印跟踪误差统计 ──
print(f"\n📊 Joint Tracking Error (RMS / max|err|):")
for jname, err in tracking_errors.items():
    sname = short_names[joint_names.index(jname)]
    rms = np.sqrt(np.mean(err**2))
    max_e = np.max(np.abs(err))
    print(f"  {sname:12s}: RMS={rms:.4f} rad, max|err|={max_e:.4f} rad")
print("✅ 3. Joint tracking plot saved.")

# ═══════════════════════════════════════════════════════
# 4. 关节速度分析
# ═══════════════════════════════════════════════════════
fig, axes = plt.subplots(6, 2, figsize=(16, 14), sharex=True)
for i, (jname, sname) in enumerate(zip(joint_names, short_names)):
    vel = df[f'vel_{jname}'].values
    row, col = i % 6, i // 6
    ax = axes[row, col]
    ax.plot(t, vel, linewidth=0.4)
    ax.axhline(y=0, color='k', linewidth=0.3)
    ax.set_ylabel(f'{sname} [rad/s]')
    ax.set_title(f'{sname}: σ={np.std(vel):.3f}, range=[{vel.min():+.2f}, {vel.max():+.2f}]', fontsize=9)
    ax.grid(True, alpha=0.3)
axes[5,0].set_xlabel('Time [s]')
axes[5,1].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(data_dir / 't27_04_joint_velocities.png', dpi=150)
plt.close()
print("✅ 4. Joint velocity plot saved.")

# ═══════════════════════════════════════════════════════
# 5. Hip Roll 专项分析（已知关键问题）
# ═══════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("📊 5. HIP ROLL CHANNEL ANALYSIS (known failure mode)")
print('='*60)

for side, jname in [('Left', 'left_hip_roll_joint'), ('Right', 'right_hip_roll_joint')]:
    pos = df[f'pos_{jname}'].values
    pos_des = df[f'pos_des_lpf_{jname}'].values
    vel = df[f'vel_{jname}'].values
    effort = df[f'effort_{jname}'].values
    tau_des = df[f'tau_des_lpf_{jname}'].values
    action = df[f'action_{jname}'].values
    
    print(f"\n--- {side} Hip Roll ---")
    print(f"  Pos range: [{pos.min():+.4f}, {pos.max():+.4f}], mean={pos.mean():+.4f}")
    print(f"  Vel range: [{vel.min():+.3f}, {vel.max():+.3f}], σ={vel.std():.3f}")
    print(f"  Effort range: [{effort.min():+.2f}, {effort.max():+.2f}]")
    
    # 跟踪误差
    if not np.all(np.isnan(pos_des)):
        err = pos - pos_des
        rms = np.sqrt(np.mean(err**2))
        max_err = np.max(np.abs(err))
        corr = np.corrcoef(pos, pos_des)[0, 1] if len(pos) > 1 else 0
        print(f"  Tracking: RMS={rms:.4f}, max|err|={max_err:.4f}, corr={corr:.3f}")
        
        # 检查是否饱和 (pos stuck at limit)
        pos_unique = np.unique(np.round(pos, 4))
        print(f"  Unique pos values: {len(pos_unique)} (out of {len(pos)} frames)")
        if len(pos_unique) < 20:
            print(f"  ⚠️  {side} Hip Roll appears SATURATED / STUCK! Unique values={pos_unique[:10]}")
    
    # 力矩相关
    if not np.all(np.isnan(tau_des)):
        tau_err = effort - tau_des if not np.all(np.isnan(tau_des)) else None
        if tau_err is not None:
            print(f"  Torque tracking: RMS={np.sqrt(np.mean(tau_err**2)):.2f}")

# 左右对比
l_pos = df['pos_left_hip_roll_joint'].values
r_pos = df['pos_right_hip_roll_joint'].values
print(f"\n--- Bilateral Hip Roll Asymmetry ---")
print(f"  Left mean:  {l_pos.mean():+.4f}, Right mean: {r_pos.mean():+.4f}")
print(f"  Diff (L-R mean): {l_pos.mean() - r_pos.mean():+.4f}")
print(f"  L range: [{l_pos.min():+.4f}, {l_pos.max():+.4f}]")
print(f"  R range: [{r_pos.min():+.4f}, {r_pos.max():+.4f}]")

fig, axes = plt.subplots(3, 1, figsize=(14, 10))
# Hip roll position comparison
axes[0].plot(t, l_pos, label='Left Hip Roll', linewidth=0.6)
axes[0].plot(t, r_pos, label='Right Hip Roll', linewidth=0.6, alpha=0.7)
axes[0].set_ylabel('Position [rad]')
axes[0].set_title('Hip Roll Bilateral Comparison')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Hip roll tracking errors
l_err = l_pos - df['pos_des_lpf_left_hip_roll_joint'].values
r_err = r_pos - df['pos_des_lpf_right_hip_roll_joint'].values
axes[1].plot(t, l_err, label='Left tracking err', linewidth=0.6)
axes[1].plot(t, r_err, label='Right tracking err', linewidth=0.6, alpha=0.7)
axes[1].axhline(y=0, color='k', linewidth=0.3)
axes[1].set_ylabel('Pos tracking error [rad]')
axes[1].set_title('Hip Roll Tracking Error')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

# Hip roll effort / torque
l_effort = df['effort_left_hip_roll_joint'].values
r_effort = df['effort_right_hip_roll_joint'].values
axes[2].plot(t, l_effort, label='Left effort', linewidth=0.6)
axes[2].plot(t, r_effort, label='Right effort', linewidth=0.6, alpha=0.7)
axes[2].set_ylabel('Effort [Nm]')
axes[2].set_title('Hip Roll Effort Comparison')
axes[2].legend()
axes[2].grid(True, alpha=0.3)
axes[2].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(data_dir / 't27_05_hip_roll_analysis.png', dpi=150)
plt.close()
print("✅ 5. Hip roll analysis plot saved.")

# ═══════════════════════════════════════════════════════
# 6. 各关节动作 vs 实际位置对比（控制链延迟分析）
# ═══════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("📊 6. ACTION vs POSITION (control chain latency proxy)")
print('='*60)

for jname, sname in zip(joint_names, short_names):
    action = df[f'action_{jname}'].values
    pos = df[f'pos_{jname}'].values
    # cross-correlation to find approximate delay
    if len(action) > 50:
        # simple proxy: correlation at 0 lag
        corr = np.corrcoef(action, pos)[0, 1]
        print(f"  {sname:12s}: action-pos corr={corr:.3f}")

# ═══════════════════════════════════════════════════════
# 7. 步态周期一致性（phase）
# ═══════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("📊 7. GAIT CYCLE ANALYSIS")
print('='*60)

# Check phase progression
phase_step = np.diff(phase)
phase_step[phase_step < -np.pi] += 2*np.pi  # unwrap
expected_step = 2*np.pi / (cycle_time * (1/np.mean(dt)))

print(f"  Expected phase step: {expected_step:.5f} rad/frame")
print(f"  Mean phase step: {np.mean(phase_step):.5f} rad/frame")
print(f"  Phase step std: {np.std(phase_step):.5f}")
print(f"  Cycle time from phase: {2*np.pi / np.mean(phase_step) * np.mean(dt):.3f}s")

# Detect when cmd_linear_x changes
cmd_x = df['cmd_linear_x'].values
cmd_start = np.where(cmd_x > 0.01)[0]
if len(cmd_start) > 0:
    cmd_start_idx = cmd_start[0]
    print(f"  Command vx > 0 starts at t={t.iloc[cmd_start_idx]:.2f}s (frame {cmd_start_idx})")

# ── 相位 vs base_euler_x（roll）的耦合 ──
phase_norm = phase / (2*np.pi)
euler_x = df['base_euler_x'].values

# Find gait cycles
cycles = np.floor(phase_norm).astype(int)
unique_cycles = np.unique(cycles)
print(f"  Total gait cycles: {len(unique_cycles)}")

# Per-cycle roll analysis
cycle_roll_stats = []
for cyc in unique_cycles:
    mask = cycles == cyc
    if mask.sum() > 10:
        roll_seg = euler_x[mask]
        cycle_roll_stats.append({
            'cycle': cyc,
            'roll_mean': roll_seg.mean(),
            'roll_std': roll_seg.std(),
            'roll_range': roll_seg.max() - roll_seg.min(),
        })

if cycle_roll_stats:
    roll_means = [c['roll_mean'] for c in cycle_roll_stats]
    roll_stds = [c['roll_std'] for c in cycle_roll_stats]
    roll_ranges = [c['roll_range'] for c in cycle_roll_stats]
    print(f"  Per-cycle roll: mean range={np.mean(roll_ranges):.4f}, σ_range={np.std(roll_ranges):.4f}")
    print(f"  Roll drift trend: {roll_means[0]:+.4f} → {roll_means[-1]:+.4f} (Δ={roll_means[-1]-roll_means[0]:+.4f})")
    
    # 检测roll发散趋势
    if len(roll_means) > 5:
        from scipy import stats
        slope, _, _, p_val, _ = stats.linregress(range(len(roll_means)), roll_means)
        print(f"  Roll mean drift slope: {slope:.6f} rad/cycle (p={p_val:.4f})")
        if abs(slope) > 0.001 and p_val < 0.05:
            print(f"  ⚠️  Significant roll drift detected!")

# ═══════════════════════════════════════════════════════
# 8. 全面关节健康报告
# ═══════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("📊 8. COMPREHENSIVE JOINT HEALTH REPORT")
print('='*60)

for jname, sname in zip(joint_names, short_names):
    pos = df[f'pos_{jname}'].values
    vel = df[f'vel_{jname}'].values
    effort = df[f'effort_{jname}'].values
    
    # 位置范围检测
    pos_unique_ratio = len(np.unique(np.round(pos, 4))) / len(pos)
    
    # 速度过大检测
    vel_high = np.sum(np.abs(vel) > 5.0) / len(vel) * 100
    
    # 力矩过大检测
    effort_high = np.sum(np.abs(effort) > 10.0) / len(effort) * 100 if not np.all(np.isnan(effort)) else 0
    
    flags = []
    if pos_unique_ratio < 0.1:
        flags.append('⚠️STUCK/SATURATED')
    if vel_high > 5:
        flags.append(f'⚠️HIGH_VEL({vel_high:.0f}%)')
    if effort_high > 5:
        flags.append(f'⚠️HIGH_EFF({effort_high:.0f}%)')
    
    flag_str = ' | '.join(flags) if flags else 'OK'
    print(f"  {sname:12s}: pos_uniq={pos_unique_ratio:.1%} vel_high={vel_high:.0f}% effort_high={effort_high:.0f}% [{flag_str}]")

print(f"\n{'='*60}")
print("Analysis complete. All plots saved to test_logs/data_csv/")
print('='*60)
