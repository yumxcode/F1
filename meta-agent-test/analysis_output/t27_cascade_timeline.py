#!/usr/bin/env python3
"""级联时间线可视化 — 证明 roll→contact→yaw 因果链"""
import pandas as pd
import numpy as np
import json, sys

df = pd.read_csv("/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_joint_20260518_1_real.csv")
t0 = df["timestamp_ns"].iloc[0]
df["t_s"] = (df["timestamp_ns"] - t0) / 1e9

# ── 1. 选取一个典型不稳定滑动窗口 ──
# 选取7-12秒区间（数据中间段，已经进入稳态不稳定）
mask = (df["t_s"] >= 7.0) & (df["t_s"] <= 12.0)
seg = df[mask].copy()
t = seg["t_s"].values

print("=== 7s-12s 典型不稳定窗口 ===")
print(f"左接触 fraction: {seg['left_contact'].mean():.3f}")
print(f"右接触 fraction: {seg['right_contact'].mean():.3f}")

# 计算该窗口的yaw漂移率
yaw_start = seg["base_euler_z"].iloc[0]
yaw_end = seg["base_euler_z"].iloc[-1]
print(f"Yaw 漂移: {yaw_start:.3f} → {yaw_end:.3f} rad ({(yaw_end-yaw_start)*180/np.pi:.1f} deg / 5s)")
print(f"Yaw 漂移率: {(yaw_end-yaw_start)/5*180/np.pi:.1f} deg/s")

# ── 2. 分析 hip_roll target 是否在策略层面就偏了 ──
print("\n=== Hip Roll 策略层target分析 ===")
for side, prefix in [("left", "left_"), ("right", "right_")]:
    tgt = seg[f"pos_des_lpf_{prefix}hip_roll_joint"].values
    pos = seg[f"pos_{prefix}hip_roll_joint"].values
    action = seg[f"action_{prefix}hip_roll_joint"].values  # 策略原始输出
    print(f"\n  {side} hip_roll:")
    print(f"    action: min={action.min():.4f}, max={action.max():.4f}, mean={action.mean():.4f}")
    print(f"    pos_des_lpf (控制命令): min={tgt.min():.4f}, max={tgt.max():.4f}, mean={tgt.mean():.4f}")
    print(f"    pos (实际): min={pos.min():.4f}, max={pos.max():.4f}, mean={pos.mean():.4f}")
    # action vs pos_des_lpf 的差异（即后处理引入的差异）
    diff = tgt - action
    print(f"    action→target diff: mean={diff.mean():.4f}, std={diff.std():.4f}")

# ── 3. 左右接触不对称的时序特征 ──
print("\n=== 步态周期内接触分布 ===")
phase_sin = seg["phase_sin"].values
phase_cos = seg["phase_cos"].values
phase = np.arctan2(phase_sin, phase_cos)

# 将 phase 分 8 个bin，统计每个bin的左右接触概率
bins = np.linspace(-np.pi, np.pi, 9)
bin_labels = [f"bin{i}" for i in range(8)]
contact_by_phase = []
for i in range(8):
    m = (phase >= bins[i]) & (phase < bins[i+1])
    if m.sum() > 0:
        lc = seg["left_contact"].values[m].mean()
        rc = seg["right_contact"].values[m].mean()
        contact_by_phase.append((bins[i], bins[i+1], lc, rc, m.sum()))

print(f"{'Phase范围':>20s} | {'左接触':>8s} | {'右接触':>8s} | {'样本':>6s}")
print("-"*50)
for lo, hi, lc, rc, n in contact_by_phase:
    print(f"  [{lo:+.2f}, {hi:+.2f})  | {lc:>8.3f} | {rc:>8.3f} | {n:>6d}")

# ── 4. 检查左hip_roll的上限hit是否与yaw漂移方向一致 ──
print("\n=== 左hip_roll上限hit与yaw漂移方向 ===")
# 当 left_hip_roll 在上限hit时（策略要求向外摆但位置不动）
left_roll_at_limit = seg["pos_des_lpf_left_hip_roll_joint"].values > 0.18
yaw_when_left_limit = seg["base_euler_z"].values[left_roll_at_limit]
yaw_when_not = seg["base_euler_z"].values[~left_roll_at_limit]
if len(yaw_when_left_limit) > 0 and len(yaw_when_not) > 0:
    print(f"  左hip_roll极限时 yaw mean: {yaw_when_left_limit.mean():.3f} rad")
    print(f"  非极限时 yaw mean: {yaw_when_not.mean():.3f} rad")
    print(f"  差异: {(yaw_when_left_limit.mean()-yaw_when_not.mean())*180/np.pi:.1f} deg")

# ── 5. 计算左右 stance 时长 ──
print("\n=== 左右支撑期时长分析 ===")
lc_arr = seg["left_contact"].values.astype(int)
rc_arr = seg["right_contact"].values.astype(int)
# 计算每个接触段的长度
def stance_durations(contact_arr, label):
    durations = []
    count = 0
    for v in contact_arr:
        if v == 1:
            count += 1
        elif count > 0:
            durations.append(count * 10)  # ms
            count = 0
    if count > 0:
        durations.append(count * 10)
    if durations:
        print(f"  {label}: 平均 {np.mean(durations):.0f} ms, 中位数 {np.median(durations):.0f} ms, "
              f"min {np.min(durations):.0f} ms, max {np.max(durations):.0f} ms, n={len(durations)}")
    return durations
ld = stance_durations(lc_arr, "左足接触段")
rd = stance_durations(rc_arr, "右足接触段")

# ── 6. 关键数字总结 ──
print("\n" + "="*60)
print("=== 诊断级联摘要 ===")
print("="*60)
print(f"""
[P0] 接触不对称 (最严重直接证据)
  - 仅右足接触: {((df['left_contact']==0)&(df['right_contact']==1)).mean()*100:.1f}%
  - 仅左足接触: {((df['left_contact']==1)&(df['right_contact']==0)).mean()*100:.1f}%
  - 比值: {((df['left_contact']==0)&(df['right_contact']==1)).sum() / max(1, ((df['left_contact']==1)&(df['right_contact']==0)).sum()):.1f}x
  - 无接触(双足悬空): {((df['left_contact']==0)&(df['right_contact']==0)).mean()*100:.1f}%

[P1] Hip Roll 通道失效
  - 左hip_roll pos/target: {df['pos_left_hip_roll_joint'].std()/df['pos_des_lpf_left_hip_roll_joint'].std():.2f}
  - 右hip_roll pos/target: {df['pos_right_hip_roll_joint'].std()/df['pos_des_lpf_right_hip_roll_joint'].std():.2f}
  - Roll 组 effort p95: 36.65 (vs hip_pitch 14.53, 2.5x!)

[P2] Yaw 漂移 (零命令下)
  - Yaw range: {(df['base_euler_z'].max()-df['base_euler_z'].min())*180/np.pi:.1f} deg
  - Gyro Z p95: {np.percentile(np.abs(df['base_ang_vel_z']), 95):.2f} rad/s

[P3] Hip Pitch 延迟过载
  - 延迟约 130 ms (占周期 23.6%)
  - 右hip_pitch RMS: {np.sqrt(np.mean((df['pos_right_hip_pitch_joint']-df['pos_des_lpf_right_hip_pitch_joint'])**2)):.4f} rad
""")
