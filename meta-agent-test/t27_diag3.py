import pandas as pd
import numpy as np
import os

BASE = '/Users/yumx/code/robot_x/X1/agibot_x1_infer'
df = pd.read_csv(os.path.join(BASE, 't27_tracking_lag_b1_diag_20260520_165013.csv'))

df['t_s'] = (df['timestamp_ns'] - df['timestamp_ns'].iloc[0]) / 1e9

print("=== Contact State Timeline ===")
print("First 20 samples:")
print(df[['t_s', 'left_contact', 'right_contact']].head(20).to_string())

# Find transition
left_changes = np.where(np.diff(df['left_contact'].values) != 0)[0]
print(f"\nLeft contact changes count: {len(left_changes)}")
print(f"First 10 indices: {left_changes[:10]}")
print(f"Last 10 indices: {left_changes[-10:]}")

right_changes = np.where(np.diff(df['right_contact'].values) != 0)[0]
print(f"\nRight contact changes count: {len(right_changes)}")
print(f"First 10: {right_changes[:10]}")
print(f"Last 10: {right_changes[-10:]}")

# Phase rate
df['phase'] = np.arctan2(df['phase_sin'], df['phase_cos'])
df['phase_unwrapped'] = np.unwrap(df['phase'].values)
phase_rate = np.gradient(df['phase_unwrapped'].values) / 0.01
print(f"\nPhase rate mean: {np.mean(phase_rate):.2f} rad/s")
print(f"Phase rate first 5s: {np.mean(phase_rate[:500]):.2f}")
print(f"Phase rate last 5s: {np.mean(phase_rate[-500:]):.2f}")

# Walking mask
walking = np.abs(phase_rate) > 5
print(f"Walking %: {np.sum(walking)/len(walking)*100:.1f}%")

# Where walking stops
walking_changes = np.where(np.diff(walking.astype(int)) != 0)[0]
print(f"Walking state changes at: {walking_changes[:20]}")

# Check cmd
print(f"\ncmd_linear_x unique: {df['cmd_linear_x'].unique()}")

# Analyze only TOGGLING contact region
# Contacts toggle during walking; let's find where the toggling pattern exists
contact_sum = df['left_contact'] + df['right_contact']
# During walking, sum is usually 1 (single support) or occasionally 2 (double support)
# Sum > 0 always since both contacts are high
# Let's find where at least one contact is 0
any_zero = np.where((df['left_contact'] == 0) | (df['right_contact'] == 0))[0]
print(f"\nAny contact=0 count: {len(any_zero)}/{len(df)} ({len(any_zero)/len(df)*100:.1f}%)")
if len(any_zero) > 0:
    print(f"First: idx={any_zero[0]}, t={df['t_s'].iloc[any_zero[0]]:.2f}s")
    print(f"Last: idx={any_zero[-1]}, t={df['t_s'].iloc[any_zero[-1]]:.2f}s")

# So it seems the ENTIRE dataset has both contacts = 1 almost all the time
# Let me verify
print(f"\nContact==0 occurrences:")
print(f"  left_contact==0: {np.sum(df['left_contact']==0)}")
print(f"  right_contact==0: {np.sum(df['right_contact']==0)}")
print(f"  both==1: {np.sum((df['left_contact']==1) & (df['right_contact']==1))}")
print(f"  left==1 & right==0: {np.sum((df['left_contact']==1) & (df['right_contact']==0))}")
print(f"  left==0 & right==1: {np.sum((df['left_contact']==0) & (df['right_contact']==1))}")

# This suggests the robot has both feet on ground almost all the time
# It is NOT running a normal walking gait with swing phases
# This is likely a standing/balancing scenario at 0.8 m/s command?

# Let me check if the cmd_x=0.8 is from sim2real testing (it might be that
# the robot is actually stationary but the command is 0.8 for testing purposes)

# Let's check actual base velocities
print(f"\n=== Base Linear/Angular Motion ===")
print(f"base_euler_x range: {df['base_euler_x'].min():.4f} to {df['base_euler_x'].max():.4f}")
print(f"base_euler_y range: {df['base_euler_y'].min():.4f} to {df['base_euler_y'].max():.4f}")

# The roll (euler_x) goes from -0.1 to 0.19 — significant rocking
# This is consistent with the robot being unstable and rocking side-to-side
