import pandas as pd
import numpy as np
import os

BASE = '/Users/yumx/code/robot_x/X1/agibot_x1_infer'
df = pd.read_csv(os.path.join(BASE, 't27_tracking_lag_b1_diag_20260520_165013.csv'))
df['t_s'] = (df['timestamp_ns'] - df['timestamp_ns'].iloc[0]) / 1e9

# When does cmd switch from 0 to 0.8?
cmd_changes = np.where(np.diff(df['cmd_linear_x'].values) != 0)[0]
print("cmd_linear_x changes at:")
for cc in cmd_changes:
    print(f"  idx={cc}, t={df['t_s'].iloc[cc]:.2f}s, from {df['cmd_linear_x'].iloc[cc]:.1f} to {df['cmd_linear_x'].iloc[cc+1]:.1f}")

# When contacts stop toggling?
# Last contact==0 indices
last_l0 = np.where(df['left_contact']==0)[0][-1] if np.any(df['left_contact']==0) else -1
last_r0 = np.where(df['right_contact']==0)[0][-1] if np.any(df['right_contact']==0) else -1
print(f"\nLast left_contact==0 at idx={last_l0}, t={df['t_s'].iloc[last_l0]:.2f}s")
print(f"Last right_contact==0 at idx={last_r0}, t={df['t_s'].iloc[last_r0]:.2f}s")

# === KEY ANALYSIS: Joint tracking during the toggling phase (first ~3.5s) vs static phase ===
# toggling: t < 3.5s, static: t > 3.5s
toggle = df[df['t_s'] < 3.5]
static = df[df['t_s'] >= 3.5]

joints = [
    'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw',
    'left_knee_pitch', 'left_ankle_pitch', 'left_ankle_roll',
    'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw',
    'right_knee_pitch', 'right_ankle_pitch', 'right_ankle_roll'
]

print(f"\n=== Joint Tracking: Toggle Phase (t<3.5s, {len(toggle)} samples) vs Static (t>=3.5s, {len(static)} samples) ===")
print(f"{'Joint':<28} {'Toggle_RMSE':>12} {'Static_RMSE':>12} {'Toggle_Corr':>12} {'Static_Corr':>12}")
print("-" * 80)

for jn in joints:
    at = toggle[f'action_{jn}_joint'].values
    pt = toggle[f'pos_{jn}_joint'].values
    as_ = static[f'action_{jn}_joint'].values
    ps = static[f'pos_{jn}_joint'].values
    
    rmse_t = np.sqrt(np.mean((pt - at) ** 2))
    rmse_s = np.sqrt(np.mean((ps - as_) ** 2))
    corr_t = np.corrcoef(at, pt)[0, 1]
    corr_s = np.corrcoef(as_, ps)[0, 1]
    
    tag = jn.split('_', 1)[1]
    side = jn.split('_')[0][0].upper()
    label = f"{side}_{tag}"
    print(f"{label:<28} {rmse_t:>12.4f} {rmse_s:>12.4f} {corr_t:>12.4f} {corr_s:>12.4f}")

# === Hip Roll and Ankle Roll during static phase ===
print(f"\n=== Ankle/Hip Roll during static phase ===")
for jn in ['left_hip_roll', 'right_hip_roll', 'left_ankle_roll', 'right_ankle_roll']:
    a = static[f'action_{jn}_joint'].values
    p = static[f'pos_{jn}_joint'].values
    e = static[f'effort_{jn}_joint'].values
    std_a = np.std(a)
    std_p = np.std(p)
    side = jn.split('_')[0][0].upper()
    tag = jn.split('_', 1)[1]
    print(f"{side}_{tag}: action_std={std_a:.4f}, pos_std={std_p:.4f}, pos/action_ratio={std_p/(std_a+1e-6):.3f}, effort_mean={np.mean(e):.2f}")

# === Effort analysis: static phase ===
print(f"\n=== Effort Static Phase (absolute) ===")
print(f"{'Joint':<28} {'Mean|Effort|':>12} {'Std|Effort|':>12}")
print("-" * 54)
for jn in joints:
    e = np.abs(static[f'effort_{jn}_joint'].values)
    tag = jn.split('_', 1)[1]
    side = jn.split('_')[0][0].upper()
    print(f"{side}_{tag:<26} {np.mean(e):>12.2f} {np.std(e):>12.2f}")

# === Check: is this a b1 diag test? The filename says "b1_diag" ===
# The B1 diagnostic probably means baseline 1 — running the policy with specific settings

# === Key insight: right_hip_pitch RMSE is 3.8 overall but let's check ===
print(f"\n=== Right Hip Pitch: action vs pos samples ===")
print("First 10 of static phase:")
sub = static[['t_s', 'action_right_hip_pitch_joint', 'pos_right_hip_pitch_joint', 'effort_right_hip_pitch_joint']].head(10)
print(sub.to_string())

# Check right_ankle_roll correlation: -0.7945 is very negative!
# That means the position moves OPPOSITE to the action
print(f"\n=== Right Ankle Roll Detail (static phase) ===")
a = static['action_right_ankle_roll_joint'].values
p = static['pos_right_ankle_roll_joint'].values
e = static['effort_right_ankle_roll_joint'].values
print(f"action: mean={np.mean(a):.4f}, std={np.std(a):.4f}")
print(f"pos: mean={np.mean(p):.4f}, std={np.std(p):.4f}")
print(f"effort: mean={np.mean(e):.4f}, std={np.std(e):.4f}")
print(f"pos/action regression: {np.polyfit(a, p, 1)}")

# What magnitude does action_right_ankle_roll oscillate at?
print(f"\nRight ankle roll action amplitude (peak-to-peak): {np.max(a)-np.min(a):.4f}")
print(f"Right ankle roll pos amplitude (peak-to-peak): {np.max(p)-np.min(p):.4f}")
print(f"Ratio: {(np.max(p)-np.min(p))/(np.max(a)-np.min(a)+1e-6):.3f}")

