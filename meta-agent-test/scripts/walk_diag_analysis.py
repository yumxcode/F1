#!/usr/bin/env python3
"""
高速行走不稳 - 诊断分析脚本
数据: walk_diag_20260523_152341.csv (1000行, 133列)
分析目标: 识别机器人高速行走(0.8 m/s)时的失稳原因
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# === Config ===
DATA_PATH = "../test_logs/data_csv/walk_diag_20260523_152341.csv"
RESULTS_DIR = "results"
Path(RESULTS_DIR).mkdir(exist_ok=True)

# === Load ===
df = pd.read_csv(DATA_PATH)
t = (df['timestamp_ns'] - df['timestamp_ns'].iloc[0]) / 1e9  # time in seconds

# === Split: pre-speedup (v=0) and high-speed (v=0.8) ===
threshold_idx = (df['cmd_linear_x'] > 0.1).idxmax()
df_off  = df.iloc[:threshold_idx]   # stationary
df_walk = df.iloc[threshold_idx:]   # 0.8 m/s walking
t_off  = t.iloc[:threshold_idx]
t_walk = t.iloc[threshold_idx:] - t.iloc[threshold_idx]

print(f"===== Data Summary =====")
print(f"Total frames: {len(df)}")
print(f"Stationary phase (v=0): {len(df_off)} frames, {t_off.iloc[-1]:.2f}s")
print(f"Walking phase (v=0.8): {len(df_walk)} frames, {t_walk.iloc[-1]:.2f}s")
print(f"Sampling rate (approx): {1 / (t.iloc[1] - t.iloc[0]):.0f} Hz")

# ===========================
# 1. BASE ATTITUDE STABILITY
# ===========================
print(f"\n===== Base Attitude Analysis =====")
for axis, label in [('base_euler_x', 'Roll'), ('base_euler_y', 'Pitch'), ('base_euler_z', 'Yaw')]:
    off_mean = df_off[axis].mean()
    off_std  = df_off[axis].std()
    walk_mean = df_walk[axis].mean()
    walk_std  = df_walk[axis].std()
    walk_range = df_walk[axis].max() - df_walk[axis].min()
    print(f"{label:6s} | off: {off_mean:+.4f}±{off_std:.4f} rad | walk: {walk_mean:+.4f}±{walk_std:.4f} rad | range: {walk_range:.4f} rad")

# Yaw drift rate
yaw_start = df_walk['base_euler_z'].iloc[0]
yaw_end   = df_walk['base_euler_z'].iloc[-1]
yaw_drift_rate = (yaw_end - yaw_start) / (t_walk.iloc[-1])
print(f"\nYaw drift: {yaw_start:.4f} → {yaw_end:.4f} over {t_walk.iloc[-1]:.2f}s")
print(f"Yaw drift rate: {yaw_drift_rate:.4f} rad/s ({np.degrees(yaw_drift_rate):.2f} deg/s)")

# ===========================
# 2. ANGULAR VELOCITY ANALYSIS
# ===========================
print(f"\n===== Base Angular Velocity =====")
for axis, label in [('base_ang_vel_x', 'ω_x'), ('base_ang_vel_y', 'ω_y'), ('base_ang_vel_z', 'ω_z')]:
    off_mean = df_off[axis].mean()
    off_std  = df_off[axis].std()
    walk_mean = df_walk[axis].mean()
    walk_std  = df_walk[axis].std()
    walk_max = df_walk[axis].abs().max()
    print(f"{label:6s} | off: {off_mean:+.4f}±{off_std:.4f} rad/s | walk: {walk_mean:+.4f}±{walk_std:.4f} rad/s | max_abs: {walk_max:.4f} rad/s")

# ===========================
# 3. JOINT TRACKING ERROR (pos_des_raw vs pos)
# ===========================
print(f"\n===== Joint Tracking Error (pos - pos_des_raw) =====")
joint_pairs = [
    ('left_hip_pitch_joint',  'left hip pitch'),
    ('left_hip_roll_joint',   'left hip roll'),
    ('left_hip_yaw_joint',    'left hip yaw'),
    ('left_knee_pitch_joint', 'left knee pitch'),
    ('left_ankle_pitch_joint','left ankle pitch'),
    ('left_ankle_roll_joint', 'left ankle roll'),
    ('right_hip_pitch_joint', 'right hip pitch'),
    ('right_hip_roll_joint',  'right hip roll'),
    ('right_hip_yaw_joint',   'right hip yaw'),
    ('right_knee_pitch_joint','right knee pitch'),
    ('right_ankle_pitch_joint','right ankle pitch'),
    ('right_ankle_roll_joint','right ankle roll'),
]

tracking_errors = []
for jname, jlabel in joint_pairs:
    pos_col = f'pos_{jname}'
    des_col = f'pos_des_raw_{jname}'
    err_walk = (df_walk[pos_col] - df_walk[des_col]).abs()
    tracking_errors.append({
        'joint': jlabel,
        'mean_err': err_walk.mean(),
        'max_err': err_walk.max(),
        'std_err': err_walk.std(),
    })

tracking_df = pd.DataFrame(tracking_errors)
print(tracking_df.to_string(index=False))

# Highlight worst
worst = tracking_df.loc[tracking_df['mean_err'].idxmax()]
print(f"\n⚠ Worst tracking: {worst['joint']} (mean err={worst['mean_err']:.4f} rad)")

# ===========================
# 4. JOINT VELOCITY ANALYSIS
# ===========================
print(f"\n===== Joint Velocity during Walking =====")
vel_stats = []
for jname, jlabel in joint_pairs:
    vel_col = f'vel_{jname}'
    vel_stats.append({
        'joint': jlabel,
        'mean_abs_vel': df_walk[vel_col].abs().mean(),
        'max_abs_vel': df_walk[vel_col].abs().max(),
        'std_vel': df_walk[vel_col].std(),
    })

vel_df = pd.DataFrame(vel_stats)
print(vel_df.to_string(index=False))

# ===========================
# 5. JOINT EFFORT (TORQUE) ANALYSIS
# ===========================
print(f"\n===== Joint Effort during Walking =====")
effort_stats = []
for jname, jlabel in joint_pairs:
    eff_col = f'effort_{jname}'
    effort_stats.append({
        'joint': jlabel,
        'mean_abs_effort': df_walk[eff_col].abs().mean(),
        'max_abs_effort': df_walk[eff_col].abs().max(),
    })

effort_df = pd.DataFrame(effort_stats)
print(effort_df.to_string(index=False))

# ===========================
# 6. COMMAND vs ACTUAL — ACTION column
# ===========================
print(f"\n===== Command Action Range (walking) =====")
action_stats = []
for jname, jlabel in joint_pairs:
    act_col = f'action_{jname}'
    action_stats.append({
        'joint': jlabel,
        'min_action': df_walk[act_col].min(),
        'max_action': df_walk[act_col].max(),
        'range': df_walk[act_col].max() - df_walk[act_col].min(),
    })

action_df = pd.DataFrame(action_stats)
print(action_df.to_string(index=False))

# ===========================
# 7. IMU ACCELERATION
# ===========================
print(f"\n===== IMU Acceleration (walking) =====")
for axis in ['imu_accel_x', 'imu_accel_y', 'imu_accel_z']:
    print(f"{axis}: mean={df_walk[axis].mean():.2f}, std={df_walk[axis].std():.2f}, max_abs={df_walk[axis].abs().max():.2f} m/s²")

# ===========================
# 8. is_parallel flag analysis — detect control dropouts
# ===========================
print(f"\n===== is_parallel Flags (walking) =====")
parallel_cols = [c for c in df.columns if c.startswith('is_parallel')]
for col in parallel_cols:
    vals = df_walk[col].unique()
    if len(vals) > 0:
        print(f"  {col}: values={vals}")

# Check if any is_parallel drops to 0 during walking
parallel_drops = 0
for col in parallel_cols:
    if 0 in df_walk[col].values:
        drops = (df_walk[col] == 0).sum()
        if drops > 0:
            print(f"  ⚠ {col}: {drops} frames with is_parallel=0")
            parallel_drops += 1
if parallel_drops == 0:
    print("  ✅ No parallel flag drops detected")

# ===========================
# 9. NaN detection
# ===========================
print(f"\n===== NaN Detection =====")
nan_counts = df_walk.isna().sum()
nan_cols = nan_counts[nan_counts > 0]
if len(nan_cols) > 0:
    print("Columns with NaN values during walking:")
    for col, cnt in nan_cols.items():
        print(f"  {col}: {cnt}/{len(df_walk)} NaN")
else:
    print("  No NaN values detected during walking")

# ===========================
# 10. clip_count analysis
# ===========================
print(f"\n===== Clip Events =====")
if 'clip_count' in df.columns:
    clip_during_walk = df_walk['clip_count'].max() - df_walk['clip_count'].iloc[0]
    print(f"Clip count at walk start: {df_walk['clip_count'].iloc[0]}")
    print(f"Clip count at walk end:   {df_walk['clip_count'].iloc[-1]}")
    print(f"New clip events during walking: {clip_during_walk}")
    
    # Clip rate over time
    clip_series = df_walk['clip_count'].values
    clip_deltas = np.diff(clip_series)
    clip_frames = np.where(clip_deltas > 0)[0]
    if len(clip_frames) > 0:
        print(f"Clip events at frames (rel to walk start): {clip_frames.tolist()}")

# ===========================
# 11. Phase-lag analysis (hip roll specifically — known issue from exp_mpc2ne75)
# ===========================
print(f"\n===== Hip Roll Symmetry Analysis =====")
left_roll_pos  = df_walk['pos_left_hip_roll_joint'].values
right_roll_pos = df_walk['pos_right_hip_roll_joint'].values
left_roll_des  = df_walk['pos_des_raw_left_hip_roll_joint'].values
right_roll_des = df_walk['pos_des_raw_right_hip_roll_joint'].values

# Left-right position asymmetry
l_r_diff = left_roll_pos - right_roll_pos
print(f"Left-Right hip roll position asymmetry: mean={l_r_diff.mean():.4f}, std={l_r_diff.std():.4f}, max_abs={np.abs(l_r_diff).max():.4f} rad")

# Left-right tracking error asymmetry
left_err = np.abs(left_roll_pos - left_roll_des)
right_err = np.abs(right_roll_pos - right_roll_des)
print(f"Left hip roll tracking error:  mean={left_err.mean():.4f}, max={left_err.max():.4f} rad")
print(f"Right hip roll tracking error: mean={right_err.mean():.4f}, max={right_err.max():.4f} rad")

# ===========================
# 12. Generate plots
# ===========================
print(f"\n===== Generating plots... =====")

fig, axes = plt.subplots(4, 2, figsize=(18, 20))

# Plot 1: Base Euler angles
ax = axes[0, 0]
ax.plot(t_walk, df_walk['base_euler_x'], label='Roll', linewidth=1)
ax.plot(t_walk, df_walk['base_euler_y'], label='Pitch', linewidth=1)
ax.plot(t_walk, df_walk['base_euler_z'], label='Yaw', linewidth=1)
ax.set_title('Base Euler Angles (Walking Phase)')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Angle (rad)')
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 2: Base angular velocity
ax = axes[0, 1]
ax.plot(t_walk, df_walk['base_ang_vel_x'], label='ω_x', linewidth=1)
ax.plot(t_walk, df_walk['base_ang_vel_y'], label='ω_y', linewidth=1)
ax.plot(t_walk, df_walk['base_ang_vel_z'], label='ω_z', linewidth=1)
ax.set_title('Base Angular Velocity')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Ang Vel (rad/s)')
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 3: Hip Roll — tracking
ax = axes[1, 0]
ax.plot(t_walk, left_roll_pos, label='Left pos', linewidth=1)
ax.plot(t_walk, left_roll_des, label='Left des', linewidth=1, linestyle='--')
ax.plot(t_walk, right_roll_pos, label='Right pos', linewidth=1)
ax.plot(t_walk, right_roll_des, label='Right des', linewidth=1, linestyle='--')
ax.set_title('Hip Roll — Position vs Desired')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Position (rad)')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Plot 4: Hip Roll — effort
ax = axes[1, 1]
ax.plot(t_walk, df_walk['effort_left_hip_roll_joint'], label='Left', linewidth=1)
ax.plot(t_walk, df_walk['effort_right_hip_roll_joint'], label='Right', linewidth=1)
ax.set_title('Hip Roll Effort')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Effort (Nm?)')
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 5: IMU Acceleration
ax = axes[2, 0]
ax.plot(t_walk, df_walk['imu_accel_x'], label='X', linewidth=1)
ax.plot(t_walk, df_walk['imu_accel_y'], label='Y', linewidth=1)
ax.plot(t_walk, df_walk['imu_accel_z'], label='Z', linewidth=1)
ax.set_title('IMU Acceleration (Walking)')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Accel (m/s²)')
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 6: Knee pitch tracking
ax = axes[2, 1]
ax.plot(t_walk, df_walk['pos_left_knee_pitch_joint'], label='Left pos', linewidth=1)
ax.plot(t_walk, df_walk['pos_des_raw_left_knee_pitch_joint'], label='Left des', linewidth=1, linestyle='--')
ax.plot(t_walk, df_walk['pos_right_knee_pitch_joint'], label='Right pos', linewidth=1)
ax.plot(t_walk, df_walk['pos_des_raw_right_knee_pitch_joint'], label='Right des', linewidth=1, linestyle='--')
ax.set_title('Knee Pitch — Position vs Desired')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Position (rad)')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Plot 7: Hip yaw tracking
ax = axes[3, 0]
ax.plot(t_walk, df_walk['pos_left_hip_yaw_joint'], label='Left pos', linewidth=1)
ax.plot(t_walk, df_walk['pos_des_raw_left_hip_yaw_joint'], label='Left des', linewidth=1, linestyle='--')
ax.plot(t_walk, df_walk['pos_right_hip_yaw_joint'], label='Right pos', linewidth=1)
ax.plot(t_walk, df_walk['pos_des_raw_right_hip_yaw_joint'], label='Right des', linewidth=1, linestyle='--')
ax.set_title('Hip Yaw — Position vs Desired')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Position (rad)')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Plot 8: Phase signal
ax = axes[3, 1]
ax.plot(t_walk, df_walk['phase_sin'], label='sin', linewidth=1)
ax.plot(t_walk, df_walk['phase_cos'], label='cos', linewidth=1)
ax.set_title('Gait Phase Reference')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Value')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
fig.savefig(f"{RESULTS_DIR}/walk_diag_overview.png", dpi=150)
print(f"Saved: {RESULTS_DIR}/walk_diag_overview.png")
plt.close()

print(f"\n===== Analysis Complete =====")
