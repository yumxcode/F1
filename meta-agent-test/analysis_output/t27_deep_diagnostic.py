#!/usr/bin/env python3
"""t27 深度诊断分析 — hip_roll collapse → contact asymmetry → yaw drift 级联"""
import pandas as pd
import numpy as np
import json, os, sys

# ── 加载数据 ──
df = pd.read_csv("/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t27_joint_20260518_1_real.csv")
t0 = df["timestamp_ns"].iloc[0]
df["t_s"] = (df["timestamp_ns"] - t0) / 1e9
dt = np.diff(df["t_s"])
print(f"== 基本信息 ==")
print(f"行数: {len(df)}")
print(f"时长: {df['t_s'].iloc[-1]:.3f} s")
print(f"采样间隔: min={dt.min()*1000:.2f} ms, mean={dt.mean()*1000:.2f} ms, max={dt.max()*1000:.2f} ms")
print(f"cycle_time=0.55s, 预期每周期: {0.55*100:.0f} 帧 ({0.55*1000:.0f} ms)\n")

# ── 1. 接触不对称时序分析 ──
lc = df["left_contact"].values
rc = df["right_contact"].values
# 找到接触切换点
lc_sw = np.diff(lc.astype(int), prepend=lc[0])
rc_sw = np.diff(rc.astype(int), prepend=rc[0])
lc_on = np.where(lc_sw == 1)[0]
lc_off = np.where(lc_sw == -1)[0]
rc_on = np.where(rc_sw == 1)[0]
rc_off = np.where(rc_sw == -1)[0]

print(f"== 接触统计 ==")
print(f"左接触 fraction: {lc.mean():.3f}, transitions: {len(lc_on)+len(lc_off)}")
print(f"右接触 fraction: {rc.mean():.3f}, transitions: {len(rc_on)+len(rc_off)}")
print(f"左接触 on/off: {len(lc_on)}/{len(lc_off)}")
print(f"右接触 on/off: {len(rc_on)}/{len(rc_off)}")

# 左右同时接触的帧
both_contact = ((lc == 1) & (rc == 1)).mean()
no_contact = ((lc == 0) & (rc == 0)).mean()
only_left = ((lc == 1) & (rc == 0)).mean()
only_right = ((lc == 0) & (rc == 1)).mean()
print(f"双足同时接触: {both_contact:.3f}")
print(f"无接触: {no_contact:.3f}")
print(f"仅左足接触: {only_left:.3f}")
print(f"仅右足接触: {only_right:.3f}")
print()

# ── 2. Yaw 漂移分析 ──
yaw = df["base_euler_z"].values
roll = df["base_euler_x"].values
pitch = df["base_euler_y"].values
gyro_z = df["base_ang_vel_z"].values
print(f"== 机身姿态 (命令: 零yaw) ==")
print(f"Yaw range: {yaw.max()-yaw.min():.4f} rad = {(yaw.max()-yaw.min())*180/np.pi:.2f} deg")
print(f"Yaw std: {yaw.std():.4f} rad")
print(f"Roll abs p95: {np.percentile(np.abs(roll), 95):.4f} rad")
print(f"Pitch abs p95: {np.percentile(np.abs(pitch), 95):.4f} rad")
print(f"Gyro Z abs p95: {np.percentile(np.abs(gyro_z), 95):.4f} rad/s")
print()

# ── 3. Hip Roll 通道分析 ──
joints_roll = [
    ("left_hip_roll_joint",  "pos_des_lpf_left_hip_roll_joint",  "pos_left_hip_roll_joint",  "effort_left_hip_roll_joint"),
    ("right_hip_roll_joint", "pos_des_lpf_right_hip_roll_joint", "pos_right_hip_roll_joint", "effort_right_hip_roll_joint"),
]
print(f"== Hip Roll 通道 ==")
for name, tgt_col, pos_col, eff_col in joints_roll:
    tgt = df[tgt_col].values
    pos = df[pos_col].values
    eff = df[eff_col].values
    limit = 0.2  # hip_roll position limit from config
    upper_hit = (pos >= limit * 0.95).mean() * 100
    lower_hit = (pos <= -limit * 0.95).mean() * 100
    print(f"{name}:")
    print(f"  target range: [{tgt.min():.4f}, {tgt.max():.4f}]")
    print(f"  pos range: [{pos.min():.4f}, {pos.max():.4f}]")
    print(f"  pos/target range ratio: {(pos.max()-pos.min())/(tgt.max()-tgt.min()):.4f}")
    print(f"  upper hit(>{limit*0.95}): {upper_hit:.1f}%, lower hit(<{-limit*0.95}): {lower_hit:.1f}%")
    print(f"  effort p95: {np.percentile(np.abs(eff), 95):.3f}")
print()

# ── 4. Hip Pitch 执行延迟分析（互相关法） ──
from scipy import signal

joints_pitch = [
    ("left_hip_pitch_joint",  "pos_des_lpf_left_hip_pitch_joint",  "pos_left_hip_pitch_joint"),
    ("right_hip_pitch_joint", "pos_des_lpf_right_hip_pitch_joint", "pos_right_hip_pitch_joint"),
]
print(f"== Hip Pitch 执行延迟 ==")
fs = 100.0  # Hz
for name, tgt_col, pos_col in joints_pitch:
    tgt = df[tgt_col].values
    pos = df[pos_col].values
    # 去直流
    tgt_ac = tgt - np.mean(tgt)
    pos_ac = pos - np.mean(pos)
    corr = signal.correlate(pos_ac, tgt_ac, mode="same")
    lag = np.argmax(corr) - len(tgt_ac)//2
    delay_ms = lag / fs * 1000
    rms = np.sqrt(np.mean((pos - tgt)**2))
    print(f"{name}: delay={delay_ms:.0f} ms, RMS={rms:.4f} rad, corr_max={np.max(corr)/np.sqrt(np.sum(pos_ac**2)*np.sum(tgt_ac**2)):.3f}")
print()

# ── 5. Phase 和接触对齐分析 ──
print(f"== Phase 对齐分析 ==")
phase_sin = df["phase_sin"].values
phase_cos = df["phase_cos"].values
phase = np.arctan2(phase_sin, phase_cos)  # [-pi, pi]

# 用 phase 过零检测周期边界
phase_unwrap = np.unwrap(phase)
# 期望周期 = 0.55s * 100Hz = 55 帧
expected_period_frames = 55
print(f"Phase range: [{phase.min():.3f}, {phase.max():.3f}]")
print(f"Phase unwrapped range: [{phase_unwrap.min():.3f}, {phase_unwrap.max():.3f}]")

# 找相位过零点（步态周期分界）
zero_crossings = np.where(np.diff(np.signbit(phase_sin)))[0]
print(f"Phase sin 过零次数: {len(zero_crossings)}")
print(f"平均帧数/半周期: {np.mean(np.diff(zero_crossings)):.1f} 帧")
print(f"平均半周期时间: {np.mean(np.diff(zero_crossings))/100:.3f} s")
print(f"实际平均周期(2个半周期): {np.mean(np.diff(zero_crossings))/100*2:.3f} s (预期: 0.55 s)")
print()

# ── 6. 分割左右接触状态下的各关节表现 ──
print(f"== 按接触状态分割的跟踪误差 ==")
# 定义四种接触状态
states = {
    "双足接触": (lc == 1) & (rc == 1),
    "仅右足": (lc == 0) & (rc == 1),
    "仅左足": (lc == 1) & (rc == 0),
    "无接触": (lc == 0) & (rc == 0),
}
for sname, mask in states.items():
    n = mask.sum()
    if n < 5:
        continue
    print(f"\n  --- {sname} (n={n}, {n/len(df)*100:.1f}%) ---")
    for jname, tgt_col, pos_col, _ in joints_roll:
        tgt = df[tgt_col].values[mask]
        pos = df[pos_col].values[mask]
        rms = np.sqrt(np.mean((pos - tgt)**2))
        print(f"    {jname}: RMS={rms:.4f}")

# ── 7. 踝关节在 touchdown 前后的表现 ──
print(f"\n== 踝关节 Touchdown 分析 ==")
# 寻找接触切换点：从无接触→有接触
# 左足 touchdown
lc_arr = lc.astype(int)
rc_arr = rc.astype(int)
# 找左足着陆: 从0变1
ltouchdown = np.where(np.diff(lc_arr, prepend=0) == 1)[0]
# 找右足着陆
rtouchdown = np.where(np.diff(rc_arr, prepend=0) == 1)[0]

print(f"左足 touchdown 事件: {len(ltouchdown)} 次")
print(f"右足 touchdown 事件: {len(rtouchdown)} 次")

# 分析踝关节在 touchdown 前后 10 帧的表现
ankle_joints = [
    ("left_ankle_pitch_joint", "pos_des_raw_left_ankle_pitch_joint", "pos_left_ankle_pitch_joint", "effort_left_ankle_pitch_joint"),
    ("right_ankle_pitch_joint", "pos_des_raw_right_ankle_pitch_joint", "pos_right_ankle_pitch_joint", "effort_right_ankle_pitch_joint"),
    ("left_ankle_roll_joint", "pos_des_raw_left_ankle_roll_joint", "pos_left_ankle_roll_joint", "effort_left_ankle_roll_joint"),
    ("right_ankle_roll_joint", "pos_des_raw_right_ankle_roll_joint", "pos_right_ankle_roll_joint", "effort_right_ankle_roll_joint"),
]

for td_name, td_indices in [("左足", ltouchdown), ("右足", rtouchdown)]:
    print(f"\n  --- {td_name} touchdown 前后踝关节 ---")
    for aj_name, tgt_col, pos_col, eff_col in ankle_joints:
        pre_errs, post_errs = [], []
        pre_effs, post_effs = [], []
        for idx in td_indices[:20]:  # 最多20个事件
            # 前10帧
            i0, i1 = max(0, idx-10), idx
            if i1 > i0:
                pre_tgt = df[tgt_col].values[i0:i1]
                pre_pos = df[pos_col].values[i0:i1]
                pre_errs.append(np.sqrt(np.mean((pre_pos - pre_tgt)**2)))
                pre_effs.append(np.percentile(np.abs(df[eff_col].values[i0:i1]), 95))
            # 后10帧
            i0, i1 = idx, min(len(df), idx+10)
            if i1 > i0:
                post_tgt = df[tgt_col].values[i0:i1]
                post_pos = df[pos_col].values[i0:i1]
                post_errs.append(np.sqrt(np.mean((post_pos - post_tgt)**2)))
                post_effs.append(np.percentile(np.abs(df[eff_col].values[i0:i1]), 95))
        if pre_errs:
            print(f"    {aj_name}: 前RMS={np.mean(pre_errs):.4f} → 后RMS={np.mean(post_errs):.4f}, 前effort={np.mean(pre_effs):.1f} → 后effort={np.mean(post_effs):.1f}")

# ── 8. 特定滑动窗口分析 ──
print(f"\n== 滑动窗口 yaw 漂移 vs hip_roll 不对称 ==")
window = 50  # 0.5s窗口
left_roll_pos = df["pos_left_hip_roll_joint"].values
right_roll_pos = df["pos_right_hip_roll_joint"].values
roll_asym = left_roll_pos - right_roll_pos  # 正值=左边高

yaw = df["base_euler_z"].values
yaw_rate = np.gradient(yaw)

# 计算滚动窗口 yaw 漂移率
window_samples = 50
yaw_drift_per_window = []
roll_asym_per_window = []
for i in range(0, len(df)-window_samples, 10):
    yaw_drift = yaw[i+window_samples] - yaw[i]
    roll_asym_mean = np.mean(roll_asym[i:i+window_samples])
    yaw_drift_per_window.append(yaw_drift)
    roll_asym_per_window.append(roll_asym_mean)

corr_roll_yaw = np.corrcoef(roll_asym_per_window, yaw_drift_per_window)[0, 1]
print(f"Roll asymmetry vs yaw drift (滑动窗口) 相关系数: {corr_roll_yaw:.3f}")

# ── 9. 时间序列关键片段 ──
print(f"\n== 时间序列关键片段 ==")
# 取第一个5秒片段详细看
seg = df.iloc[:500]
t = seg["t_s"].values
print("前5秒数据摘要:")
print(f"  左接触 fraction: {seg['left_contact'].mean():.3f}")
print(f"  右接触 fraction: {seg['right_contact'].mean():.3f}")
print(f"  Yaw range: {(seg['base_euler_z'].max()-seg['base_euler_z'].min())*180/np.pi:.2f} deg")
print(f"  左hip_roll upper hit: {(seg['pos_left_hip_roll_joint']>0.19).mean()*100:.1f}%")
print(f"  右hip_roll pos/target: {((seg['pos_right_hip_roll_joint'].max()-seg['pos_right_hip_roll_joint'].min())/(seg['pos_des_lpf_right_hip_roll_joint'].max()-seg['pos_des_lpf_right_hip_roll_joint'].min())):.3f}")

# ── 10. Cycle time 实际 vs 期望 ──
print(f"\n== 周期一致性验证 ==")
# 用 phase 计算实际周期
phase_unwrap = np.unwrap(phase)
# 拟合斜率 = 2*pi/T
from numpy.polynomial import polynomial as P
t_sec = df["t_s"].values
coeffs = P.polyfit(t_sec, phase_unwrap, 1)
actual_freq = coeffs[1] / (2*np.pi)
actual_period = 1.0 / actual_freq
print(f"Phase 拟合频率: {actual_freq:.3f} Hz")
print(f"Phase 拟合周期: {actual_period:.3f} s (配置: 0.55 s)")
print(f"周期偏差: {(actual_period-0.55)/0.55*100:.1f}%")
print()

# ── 11. 关键关节 target 整体饱和分析 ──
print(f"== Target 饱和/限幅分析 ==")
limit_map = {
    "left_hip_roll_joint": 0.2,
    "right_hip_roll_joint": 0.2,
    "left_ankle_pitch_joint": 0.38,
    "right_ankle_pitch_joint": 0.38,
}
for jname, limit in limit_map.items():
    tgt_col = f"pos_des_lpf_{jname}"
    if jname not in tgt_col:
        # try raw for ankle
        tgt_col = f"pos_des_raw_{jname}"
    if tgt_col not in df.columns:
        continue
    tgt = df[tgt_col].values
    upper_sat = (tgt >= limit*0.95).mean()*100
    lower_sat = (tgt <= -limit*0.95).mean()*100
    print(f"  {jname} (limit=±{limit}): upper饱和={upper_sat:.1f}%, lower饱和={lower_sat:.1f}%")

# ── 12. 髋关节组整体负载分析 ──
print(f"\n== 髋关节组负载 (effort p95) ==")
hip_groups = {
    "hip_roll":  ["left_hip_roll_joint", "right_hip_roll_joint"],
    "hip_pitch": ["left_hip_pitch_joint", "right_hip_pitch_joint"],
    "hip_yaw":   ["left_hip_yaw_joint", "right_hip_yaw_joint"],
}
for gname, joints in hip_groups.items():
    efforts = []
    for j in joints:
        efforts.extend(np.abs(df[f"effort_{j}"].values))
    print(f"  {gname}: effort p95={np.percentile(efforts, 95):.2f}, p99={np.percentile(efforts, 99):.2f}")

print("\n== 分析完成 ==")
