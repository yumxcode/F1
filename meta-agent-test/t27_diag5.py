import pandas as pd
import numpy as np
import os

BASE = '/Users/yumx/code/robot_x/X1/agibot_x1_infer'
df = pd.read_csv(os.path.join(BASE, 't27_tracking_lag_b1_diag_20260520_165013.csv'))
df['t_s'] = (df['timestamp_ns'] - df['timestamp_ns'].iloc[0]) / 1e9

# Confirm: in static phase, are ALL positions constant?
static = df[df['t_s'] >= 3.5]

print("=== Position std in static phase (t>=3.5s) ===")
joints = [
    'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw',
    'left_knee_pitch', 'left_ankle_pitch', 'left_ankle_roll',
    'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw',
    'right_knee_pitch', 'right_ankle_pitch', 'right_ankle_roll'
]
for jn in joints:
    std = static[f'pos_{jn}_joint'].std()
    tag = jn.split('_', 1)[1]
    side = jn.split('_')[0][0].upper()
    flag = "<<< LOCKED" if std < 1e-10 else ""
    print(f"  {side}_{tag}: pos_std={std:.2e} {flag}")

# Check: right_hip_yaw and right_ankle_roll have NaN corr in static phase
# This is because pos is constant (zero variance)
print(f"\nRight hip yaw pos values: {static['pos_right_hip_yaw_joint'].unique()}")
print(f"Right ankle roll pos values: {static['pos_right_ankle_roll_joint'].unique()}")

# === FOCUS ON TOGGLE PHASE (the actual walking period) ===
toggle = df[df['t_s'] < 3.5]
print(f"\n=== TOGGLE PHASE ANALYSIS (t<3.5s, {len(toggle)} samples) ===")
print("This is the only period with actual walking dynamics.")

# Tracking error during genuine walking
print(f"\n=== Joint Tracking During Walking (Toggle Phase) ===")
print(f"{'Joint':<28} {'RMSE':>8} {'Corr':>8} {'EffortMean':>10} {'LagMs':>8} {'ActionStd':>10} {'PosStd':>10}")
print("-" * 86)
for jn in joints:
    a = toggle[f'action_{jn}_joint'].values
    p = toggle[f'pos_{jn}_joint'].values
    e = toggle[f'effort_{jn}_joint'].values
    rmse = np.sqrt(np.mean((p - a) ** 2))
    corr = np.corrcoef(a, p)[0, 1]
    
    # Cross-corr for lag (subsampled for toggle phase since it's shorter)
    lags = np.arange(-15, 16)
    cors = []
    for lag in lags:
        if lag < 0:
            c = np.corrcoef(a[-lag:], p[:lag])[0, 1] if len(a[-lag:]) > 10 else 0
        elif lag > 0:
            c = np.corrcoef(a[:-lag], p[lag:])[0, 1] if len(a[:-lag]) > 10 else 0
        else:
            c = np.corrcoef(a, p)[0, 1]
        cors.append(c)
    best_idx = np.argmax(cors)
    best_lag = lags[best_idx]
    
    tag = jn.split('_', 1)[1]
    side = jn.split('_')[0][0].upper()
    print(f"{side}_{tag:<26} {rmse:>8.4f} {corr:>8.4f} {np.mean(np.abs(e)):>10.2f} {best_lag*10:>+7}ms {np.std(a):>10.4f} {np.std(p):>10.4f}")

# Contact pattern during walking
print(f"\n=== Walking Contact Pattern ===")
print(f"Left contact mean: {toggle['left_contact'].mean()*100:.1f}%")
print(f"Right contact mean: {toggle['right_contact'].mean()*100:.1f}%")

# Base orientation during walking
print(f"\n=== Base Orientation During Walking ===")
for col in ['base_euler_x', 'base_euler_y', 'base_euler_z']:
    print(f"{col}: start={toggle[col].iloc[0]:.4f}, end={toggle[col].iloc[-1]:.4f}, delta={toggle[col].iloc[-1]-toggle[col].iloc[0]:.4f}")

# Ang vel during walking
for col in ['base_ang_vel_x', 'base_ang_vel_y', 'base_ang_vel_z']:
    print(f"{col}: mean={toggle[col].mean():.4f}, std={toggle[col].std():.4f}, max_abs={np.max(np.abs(toggle[col])):.4f}")

# Is the robot actually walking? Check if both contacts are 1 most of the time during toggle
both1 = (toggle['left_contact'] == 1) & (toggle['right_contact'] == 1)
print(f"\nBoth contacts=1 during toggle phase: {np.sum(both1)}/{len(toggle)} = {np.sum(both1)/len(toggle)*100:.1f}%")
# If both=1 most of the time even during "walking", the gait is double-support-dominant

