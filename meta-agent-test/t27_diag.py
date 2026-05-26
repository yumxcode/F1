import pandas as pd
import numpy as np

df = pd.read_csv('../t27_tracking_lag_b1_diag_20260520_165013.csv')
print(f"=== Data Overview ===")
print(f"Rows: {len(df)}")
duration_s = (df['timestamp_ns'].max() - df['timestamp_ns'].min()) / 1e9
print(f"Duration: {duration_s:.2f}s")
dts = np.diff(df['timestamp_ns'].values) / 1e6
print(f"Sample interval ms: mean={np.mean(dts):.2f}, std={np.std(dts):.2f}")

print(f"\n=== Command ===")
print(f"cmd_linear_x: mean={df['cmd_linear_x'].mean():.4f}, max={df['cmd_linear_x'].max():.4f}")
print(f"cmd_linear_y: mean={df['cmd_linear_y'].mean():.4f}")
print(f"cmd_angular_z: mean={df['cmd_angular_z'].mean():.4f}")

print(f"\n=== Contact ===")
print(f"Left contact: {df['left_contact'].mean()*100:.1f}%")
print(f"Right contact: {df['right_contact'].mean()*100:.1f}%")

print(f"\n=== Base Euler (rad) ===")
for col in ['base_euler_x', 'base_euler_y', 'base_euler_z']:
    print(f"{col}: mean={df[col].mean():.4f}, std={df[col].std():.4f}, min={df[col].min():.4f}, max={df[col].max():.4f}")

y0 = df['base_euler_z'].iloc[0]
y1 = df['base_euler_z'].iloc[-1]
print(f"Yaw drift: delta={(y1-y0)*180/np.pi:.1f}deg")

# === Joint tracking error ===
joints = [
    'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw',
    'left_knee_pitch', 'left_ankle_pitch', 'left_ankle_roll',
    'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw',
    'right_knee_pitch', 'right_ankle_pitch', 'right_ankle_roll'
]

print(f"\n=== Joint Tracking (action vs pos) ===")
print(f"{'Joint':<28} {'RMSE':>8} {'Corr':>8} {'EffortMean':>12} {'EffortMax':>12} {'LagMs':>8}")
print("-" * 80)

for jn in joints:
    a = df[f'action_{jn}_joint'].values
    p = df[f'pos_{jn}_joint'].values
    e = df[f'effort_{jn}_joint'].values
    rmse = np.sqrt(np.mean((p - a) ** 2))
    corr = np.corrcoef(a, p)[0, 1]
    
    lags = np.arange(-60, 61)
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
    label = f"{side}_{tag}"
    
    print(f"{label:<28} {rmse:>8.4f} {corr:>8.4f} {np.mean(e):>12.2f} {np.max(np.abs(e)):>12.2f} {best_lag*10:>+7}ms")

# === NaN Analysis ===
print(f"\n=== NaN Analysis ===")
nan_cols = df.columns[df.isna().any()].tolist()
print(f"NaN columns: {nan_cols}")
for nc in nan_cols:
    print(f"  {nc}: {df[nc].isna().sum()} NaN ({df[nc].isna().sum()/len(df)*100:.1f}%)")

# === is_parallel flags ===
print(f"\n=== is_parallel flags ===")
for jn in joints:
    col = f'is_parallel_{jn}_joint'
    if col in df.columns:
        vals = df[col].unique()
        print(f"  {jn}: unique={vals}, mean={df[col].mean():.3f}")

# === Contact vs Phase ===
print(f"\n=== Contact duty factor ===")
df['phase'] = np.arctan2(df['phase_sin'], df['phase_cos'])
df['phase_bin'] = pd.cut(df['phase'], bins=8, labels=False)
contact_by_phase = df.groupby('phase_bin').agg({'left_contact': 'mean', 'right_contact': 'mean'})
print(contact_by_phase.to_string())

# === Base angular velocity ===
print(f"\n=== Base Angular Vel (rad/s) ===")
for col in ['base_ang_vel_x', 'base_ang_vel_y', 'base_ang_vel_z']:
    print(f"{col}: mean={df[col].mean():.6f}, std={df[col].std():.6f}, max_abs={np.max(np.abs(df[col])):.6f}")
