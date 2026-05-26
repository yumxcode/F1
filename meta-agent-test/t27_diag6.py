import pandas as pd
import numpy as np
import os

BASE = '/Users/yumx/code/robot_x/X1/agibot_x1_infer'
df = pd.read_csv(os.path.join(BASE, 't27_tracking_lag_b1_diag_20260520_165013.csv'))
df['t_s'] = (df['timestamp_ns'] - df['timestamp_ns'].iloc[0]) / 1e9
df['phase'] = np.arctan2(df['phase_sin'], df['phase_cos'])

toggle = df[df['t_s'] < 3.5].copy()

# Phase-resolved tracking
toggle['phase_bin'] = pd.cut(toggle['phase'], bins=8, labels=False)

print(f"=== Phase-resolved RMSE (Walking Only, 8 bins) ===")
header = f"{'Joint':<28} " + " ".join([f"{'B'+str(i):>8}" for i in range(8)])
print(header)
print("-" * 96)
for jn in ['left_hip_roll', 'right_hip_roll', 'left_hip_pitch', 'right_hip_pitch',
           'left_ankle_roll', 'right_ankle_roll', 'left_ankle_pitch', 'right_ankle_pitch']:
    rmse_by_phase = toggle.groupby('phase_bin').apply(
        lambda g: np.sqrt(np.mean((g[f'pos_{jn}_joint'] - g[f'action_{jn}_joint']) ** 2)) if len(g) > 0 else np.nan
    )
    tag = jn.split('_', 1)[1]
    side = jn.split('_')[0][0].upper()
    vals = " ".join([f"{v:>8.3f}" if not np.isnan(v) else f"{'N/A':>8}" for v in rmse_by_phase.values])
    print(f"{side}_{tag:<26} {vals}")

# State at walking stop
stop_idx = 322
print(f"\n=== State at walking stop (idx={stop_idx}, t={df['t_s'].iloc[stop_idx]:.2f}s) ===")
for col in ['base_euler_x', 'base_euler_y', 'base_euler_z', 'base_ang_vel_x', 'base_ang_vel_y', 'base_ang_vel_z']:
    print(f"  {col}: {df[col].iloc[stop_idx]:.4f}")
print(f"  cmd_linear_x: {df['cmd_linear_x'].iloc[stop_idx]:.4f}")

# Effort asymmetry during walking
pairs = [
    ('left_hip_pitch', 'right_hip_pitch'), ('left_hip_roll', 'right_hip_roll'),
    ('left_hip_yaw', 'right_hip_yaw'), ('left_knee_pitch', 'right_knee_pitch'),
    ('left_ankle_pitch', 'right_ankle_pitch'), ('left_ankle_roll', 'right_ankle_roll'),
]
print(f"\n=== Effort Asymmetry During Walking ===")
print(f"{'Joint':<20} {'L_|Effort|':>12} {'R_|Effort|':>12} {'Ratio R/L':>10}")
print("-" * 58)
for lj, rj in pairs:
    le = np.mean(np.abs(toggle[f'effort_{lj}_joint'].values))
    re = np.mean(np.abs(toggle[f'effort_{rj}_joint'].values))
    tag = lj.split('_', 1)[1]
    print(f"{tag:<20} {le:>12.2f} {re:>12.2f} {re/(le+1e-6):>10.2f}")

# Base orientation evolution
print(f"\n=== Base orientation evolution (last 50 samples before lock) ===")
last50 = df.iloc[272:323]
for col in ['base_euler_x', 'base_euler_y', 'base_euler_z']:
    s0 = last50[col].iloc[0]
    s1 = last50[col].iloc[-1]
    print(f"  {col}: {s0:.4f} -> {s1:.4f} (Δ={s1-s0:.4f})")

# Action vs Pos range during walking
print(f"\n=== Action vs Pos Range During Walking ===")
for jn in ['left_hip_roll', 'right_hip_roll', 'left_hip_pitch', 'right_hip_pitch']:
    a = toggle[f'action_{jn}_joint'].values
    p = toggle[f'pos_{jn}_joint'].values
    a_r = np.max(a) - np.min(a)
    p_r = np.max(p) - np.min(p)
    tag = jn.split('_', 1)[1]
    side = jn.split('_')[0][0].upper()
    print(f"  {side}_{tag}: action_range={a_r:.3f}, pos_range={p_r:.3f}, ratio={p_r/(a_r+1e-6):.3f}")

# Yaw drift during the 3.22s walking
print(f"\n=== Walking-Only Yaw Drift ===")
y0 = toggle['base_euler_z'].iloc[0]
y1 = toggle['base_euler_z'].iloc[-1]
print(f"  yaw: {y0:.3f} -> {y1:.3f}, drift={(y1-y0)*180/np.pi:.1f}deg over {toggle['t_s'].iloc[-1]:.2f}s")
print(f"  yaw rate: {(y1-y0)/toggle['t_s'].iloc[-1]:.3f} rad/s = {(y1-y0)/toggle['t_s'].iloc[-1]*180/np.pi:.1f} deg/s")

