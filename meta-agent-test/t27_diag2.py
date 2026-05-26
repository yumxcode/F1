import pandas as pd
import numpy as np
import os

BASE = '/Users/yumx/code/robot_x/X1/agibot_x1_infer'
df = pd.read_csv(os.path.join(BASE, 't27_tracking_lag_b1_diag_20260520_165013.csv'))

joints_pair = [
    ('left_hip_pitch', 'right_hip_pitch'),
    ('left_hip_roll', 'right_hip_roll'),
    ('left_hip_yaw', 'right_hip_yaw'),
    ('left_knee_pitch', 'right_knee_pitch'),
    ('left_ankle_pitch', 'right_ankle_pitch'),
    ('left_ankle_roll', 'right_ankle_roll'),
]

print("=== Left-Right Asymmetry Analysis ===")
print(f"{'Joint':<20} {'L_RMSE':>10} {'R_RMSE':>10} {'Ratio':>8} {'L_Corr':>8} {'R_Corr':>8} {'L_|Effort|':>10} {'R_|Effort|':>10}")
print("-" * 90)

for lj, rj in joints_pair:
    la = df[f'action_{lj}_joint'].values
    lp = df[f'pos_{lj}_joint'].values
    ra = df[f'action_{rj}_joint'].values
    rp = df[f'pos_{rj}_joint'].values
    le = df[f'effort_{lj}_joint'].values
    re = df[f'effort_{rj}_joint'].values
    
    l_rmse = np.sqrt(np.mean((lp - la) ** 2))
    r_rmse = np.sqrt(np.mean((rp - ra) ** 2))
    l_corr = np.corrcoef(la, lp)[0, 1]
    r_corr = np.corrcoef(ra, rp)[0, 1]
    
    tag = lj.split('_', 1)[1]
    print(f"{tag:<20} {l_rmse:>10.4f} {r_rmse:>10.4f} {r_rmse/(l_rmse+1e-6):>8.2f} {l_corr:>8.4f} {r_corr:>8.4f} {np.mean(np.abs(le)):>10.2f} {np.mean(np.abs(re)):>10.2f}")

# Segment analysis
print(f"\n=== Early vs Late Segment (first 5s vs last 5s) ===")
n_5s = 500
first = df.iloc[:n_5s]
last = df.iloc[-n_5s:]

print(f"{'Metric':<25} {'First 5s':>12} {'Last 5s':>12} {'Change':>10}")
print("-" * 62)
print(f"{'L_contact':<25} {first['left_contact'].mean()*100:>11.1f}% {last['left_contact'].mean()*100:>11.1f}% {(last['left_contact'].mean()-first['left_contact'].mean())*100:>+9.1f}%")
print(f"{'R_contact':<25} {first['right_contact'].mean()*100:>11.1f}% {last['right_contact'].mean()*100:>11.1f}% {(last['right_contact'].mean()-first['right_contact'].mean())*100:>+9.1f}%")

print(f"{'base_euler_z (yaw)':<25} {first['base_euler_z'].mean():>11.3f}  {last['base_euler_z'].mean():>11.3f}  {last['base_euler_z'].mean()-first['base_euler_z'].mean():>+9.3f}")
print(f"{'base_euler_x (roll)':<25} {first['base_euler_x'].mean():>11.3f}  {last['base_euler_x'].mean():>11.3f}  {last['base_euler_x'].mean()-first['base_euler_x'].mean():>+9.3f}")

for lj in ['left_hip_roll', 'right_hip_roll', 'left_hip_pitch', 'right_hip_pitch']:
    a_first = first[f'action_{lj}_joint'].values
    p_first = first[f'pos_{lj}_joint'].values
    a_last = last[f'action_{lj}_joint'].values
    p_last = last[f'pos_{lj}_joint'].values
    
    rmse_first = np.sqrt(np.mean((p_first - a_first) ** 2))
    rmse_last = np.sqrt(np.mean((p_last - a_last) ** 2))
    
    tag = lj.split('_', 1)[1]
    side = lj.split('_')[0][0].upper()
    print(f"{side}_{tag}_RMSE{'':<17} {rmse_first:>11.4f}  {rmse_last:>11.4f}  {rmse_last-rmse_first:>+9.4f}")

# Hip Roll saturation check
print(f"\n=== Hip Roll Range Check ===")
for lj in ['left_hip_roll', 'right_hip_roll']:
    a = df[f'action_{lj}_joint'].values
    p = df[f'pos_{lj}_joint'].values
    side = lj.split('_')[0][0].upper()
    print(f"{side}_hip_roll: action=[{a.min():.4f}, {a.max():.4f}], pos=[{p.min():.4f}, {p.max():.4f}]")

# Phase cycle
print(f"\n=== Gait Cycle ===")
zcross = np.sum(np.diff(np.sign(df['phase_sin'].values)) != 0)
print(f"Zero crossings of sin: {zcross}, ~{zcross/2:.0f} cycles")
print(f"Cycle time estimate: {40/(zcross/2):.2f}s per cycle")

# Check if there's an obvious failure point
print(f"\n=== Ankle Roll Correlation Check ===")
for lj in ['left_ankle_roll', 'right_ankle_roll']:
    a = df[f'action_{lj}_joint'].values
    p = df[f'pos_{lj}_joint'].values
    side = lj.split('_')[0][0].upper()
    # Rolling correlation
    window = 200
    rolling_corr = []
    for i in range(0, len(a) - window, 50):
        c = np.corrcoef(a[i:i+window], p[i:i+window])[0, 1]
        rolling_corr.append(c)
    print(f"{side}_ankle_roll rolling corr: mean={np.mean(rolling_corr):.4f}, std={np.std(rolling_corr):.4f}, min={np.min(rolling_corr):.4f}")

# Base_ang_vel_z vs yaw correlation
print(f"\n=== Yaw Rate Integration ===")
ang_vel_z_mean = df['base_ang_vel_z'].mean()
print(f"Mean base_ang_vel_z: {ang_vel_z_mean:.4f} rad/s")
print(f"Expected yaw drift over 40s: {ang_vel_z_mean*40*180/np.pi:.1f} deg (from ang vel)")
print(f"Actual yaw drift: {(df['base_euler_z'].iloc[-1]-df['base_euler_z'].iloc[0])*180/np.pi:.1f} deg (from euler)")
