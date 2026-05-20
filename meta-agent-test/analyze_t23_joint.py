#!/usr/bin/env python3
"""
t23 真机关节数据分析
数据: t23_joint_20260519_1_real.csv (40s, 100Hz)
可用列: timestamp_ns, pos_*, vel_*, target_*, target_lpf_*

关键发现: 踝关节 target_lpf 数据严重异常 (range 30-44 rad),
         因此本分析使用 target (raw) 作为跟踪基准.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import signal

data_dir = Path("/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv")
out_dir = Path("/Users/yumx/code/X1/agibot_x1_infer/meta-agent-test/analysis_output")

df = pd.read_csv(data_dir / "t23_joint_20260519_1_real.csv")

joint_names = [
    'left_hip_pitch_joint', 'left_hip_roll_joint', 'left_hip_yaw_joint',
    'left_knee_pitch_joint', 'left_ankle_pitch_joint', 'left_ankle_roll_joint',
    'right_hip_pitch_joint', 'right_hip_roll_joint', 'right_hip_yaw_joint',
    'right_knee_pitch_joint', 'right_ankle_pitch_joint', 'right_ankle_roll_joint',
]
short_names = ['L_HipP','L_HipR','L_HipY','L_Knee','L_AnkP','L_AnkR',
               'R_HipP','R_HipR','R_HipY','R_Knee','R_AnkP','R_AnkR']

t0 = df['timestamp_ns'].iloc[0]
t = (df['timestamp_ns'] - t0) / 1e9
dt_arr = np.diff(t)
fs = 1.0 / np.mean(dt_arr)

print("=" * 70)
print("T23 JOINT DATA ANALYSIS")
print("=" * 70)
print(f"Rows: {len(df)}")
print(f"Duration: {t.iloc[-1]:.2f}s")
print(f"Mean dt: {np.mean(dt_arr)*1000:.2f}ms, std: {np.std(dt_arr)*1000:.4f}ms")
print(f"Min/Max dt: {dt_arr.min()*1000:.2f}/{dt_arr.max()*1000:.2f}ms")
print(f"Effective freq: {fs:.1f}Hz")

# ═══════════════════════════════════════════════════════════
# 0. target_lpf 数据质量检查
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("0. TARGET_LPF DATA QUALITY CHECK")
print("=" * 70)

ankle_joints = [j for j in joint_names if 'ankle' in j]
hip_knee_joints = [j for j in joint_names if 'ankle' not in j]

for jname, sname in zip(joint_names, short_names):
    raw = df[f'target_{jname}'].values
    lpf = df[f'target_lpf_{jname}'].values
    raw_range = raw.max() - raw.min()
    lpf_range = lpf.max() - lpf.min()
    divergence_ratio = lpf_range / raw_range if raw_range > 1e-6 else 0

    flag = ''
    if divergence_ratio > 5:
        flag = ' ❌LPF_DIVERGED'
    print(f"  {sname:12s}: raw_range={raw_range:8.4f}, lpf_range={lpf_range:8.4f}, lpf/raw={divergence_ratio:8.1f}x{flag}")

# ═══════════════════════════════════════════════════════════
# 1. 关节跟踪误差: pos vs target (raw) — 以 raw target 为准
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("1. JOINT TRACKING: pos vs target (raw)")
print("=" * 70)

tracking_data = []
for jname, sname in zip(joint_names, short_names):
    pos = df[f'pos_{jname}'].values
    # 使用 raw target 作为参考 (lpf 对踝关节已发散)
    tgt = df[f'target_{jname}'].values

    err = pos - tgt
    rms = np.sqrt(np.mean(err**2))
    max_err = np.max(np.abs(err))
    mean_err = np.mean(err)
    std_err = np.std(err)

    corr = np.corrcoef(pos, tgt)[0, 1] if len(pos) > 1 else 0

    pos_range = pos.max() - pos.min()
    tgt_range = tgt.max() - tgt.min()
    tracking_ratio = pos_range / tgt_range if tgt_range > 1e-6 else 0

    # 延迟估计
    tgt_ac = tgt - np.mean(tgt)
    pos_ac = pos - np.mean(pos)
    corr_full = signal.correlate(pos_ac, tgt_ac, mode='same')
    lag = np.argmax(corr_full) - len(tgt_ac) // 2
    delay_ms = lag / fs * 1000
    corr_max = np.max(corr_full) / np.sqrt(np.sum(pos_ac**2) * np.sum(tgt_ac**2))

    tracking_data.append({
        'name': sname, 'jname': jname,
        'rms': rms, 'max_err': max_err, 'mean_err': mean_err,
        'std_err': std_err, 'corr': corr, 'tracking_ratio': tracking_ratio,
        'pos_range': pos_range, 'tgt_range': tgt_range,
        'delay_ms': delay_ms, 'corr_max': corr_max,
    })

tracking_data.sort(key=lambda x: x['rms'], reverse=True)

print(f"\n{'Joint':12s} {'RMS':>8s} {'max|err|':>8s} {'corr':>7s} {'corr_max':>9s} {'delay_ms':>8s} {'track%':>7s} {'Status'}")
print("-" * 85)
for d in tracking_data:
    status = 'OK'
    if abs(d['corr']) < 0.5:
        status = '⚠WEAK_TRACK'
    if abs(d['corr']) < 0.2:
        status = '❌NO_TRACK'
    if d['tracking_ratio'] < 0.3:
        status = '❌LOW_GAIN' if status == 'OK' else status
    print(f"  {d['name']:12s} {d['rms']:8.4f} {d['max_err']:8.4f} {d['corr']:7.3f} {d['corr_max']:9.3f} {d['delay_ms']:+8.1f} {d['tracking_ratio']:6.1%} {status}")

# ═══════════════════════════════════════════════════════════
# 2. 按关节组汇总
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("2. JOINT GROUP SUMMARY")
print("=" * 70)

groups = {
    'Hip Pitch':  ['left_hip_pitch_joint', 'right_hip_pitch_joint'],
    'Hip Roll':   ['left_hip_roll_joint', 'right_hip_roll_joint'],
    'Hip Yaw':    ['left_hip_yaw_joint', 'right_hip_yaw_joint'],
    'Knee':       ['left_knee_pitch_joint', 'right_knee_pitch_joint'],
    'Ankle Pitch':['left_ankle_pitch_joint', 'right_ankle_pitch_joint'],
    'Ankle Roll': ['left_ankle_roll_joint', 'right_ankle_roll_joint'],
}

for gname, gjoints in groups.items():
    gdata = [d for d in tracking_data if d['jname'] in gjoints]
    if len(gdata) == 2:
        mean_rms = np.mean([d['rms'] for d in gdata])
        mean_corr = np.mean([abs(d['corr']) for d in gdata])
        mean_track = np.mean([d['tracking_ratio'] for d in gdata])
        print(f"  {gname:15s}: mean_RMS={mean_rms:.4f}, mean|corr|={mean_corr:.3f}, mean_track%={mean_track:.1%}")

# ═══════════════════════════════════════════════════════════
# 3. 左右对称性
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("3. BILATERAL SYMMETRY (L vs R position)")
print("=" * 70)

pairs = [
    ('left_hip_pitch_joint', 'right_hip_pitch_joint', 'HipP'),
    ('left_hip_roll_joint', 'right_hip_roll_joint', 'HipR'),
    ('left_hip_yaw_joint', 'right_hip_yaw_joint', 'HipY'),
    ('left_knee_pitch_joint', 'right_knee_pitch_joint', 'Knee'),
    ('left_ankle_pitch_joint', 'right_ankle_pitch_joint', 'AnkP'),
    ('left_ankle_roll_joint', 'right_ankle_roll_joint', 'AnkR'),
]

for l_j, r_j, name in pairs:
    l_pos = df[f'pos_{l_j}'].values
    r_pos = df[f'pos_{r_j}'].values
    l_tgt = df[f'target_{l_j}'].values
    r_tgt = df[f'target_{r_j}'].values

    pos_corr = np.corrcoef(l_pos, r_pos)[0, 1]
    tgt_corr = np.corrcoef(l_tgt, r_tgt)[0, 1]
    mean_diff = np.mean(l_pos - r_pos)
    rms_diff = np.sqrt(np.mean((l_pos - r_pos)**2))
    l_range = l_pos.max() - l_pos.min()
    r_range = r_pos.max() - r_pos.min()

    # 跟踪误差对称性
    l_err = np.sqrt(np.mean((l_pos - l_tgt)**2))
    r_err = np.sqrt(np.mean((r_pos - r_tgt)**2))

    print(f"  {name:12s}: pos_corr={pos_corr:+.3f}, tgt_corr={tgt_corr:+.3f}, mean_diff(L-R)={mean_diff:+.4f}, "
          f"L_range={l_range:.4f}, R_range={r_range:.4f}, tracking L={l_err:.4f}/R={r_err:.4f}")

# ═══════════════════════════════════════════════════════════
# 4. 目标值限幅分析 (使用 raw target)
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("4. TARGET (raw) SATURATION vs POSITION LIMITS")
print("=" * 70)

limit_map = {
    'left_hip_roll_joint': 0.2, 'right_hip_roll_joint': 0.2,
    'left_hip_pitch_joint': 1.0, 'right_hip_pitch_joint': 1.0,
    'left_hip_yaw_joint': 0.8, 'right_hip_yaw_joint': 0.8,
    'left_knee_pitch_joint': 1.5, 'right_knee_pitch_joint': 1.5,
    'left_ankle_pitch_joint': 0.38, 'right_ankle_pitch_joint': 0.38,
    'left_ankle_roll_joint': 0.38, 'right_ankle_roll_joint': 0.38,
}

for jname, sname in zip(joint_names, short_names):
    tgt = df[f'target_{jname}'].values
    pos = df[f'pos_{jname}'].values

    if jname in limit_map:
        limit = limit_map[jname]
        tgt_upper = np.sum(tgt >= limit * 0.95) / len(tgt) * 100
        tgt_lower = np.sum(tgt <= -limit * 0.95) / len(tgt) * 100
        pos_upper = np.sum(pos >= limit * 0.95) / len(pos) * 100
        pos_lower = np.sum(pos <= -limit * 0.95) / len(pos) * 100
        print(f"  {sname:12s}: limit=±{limit:.2f}, tgt_sat↑{tgt_upper:5.1f}%/↓{tgt_lower:5.1f}%, pos_sat↑{pos_upper:5.1f}%/↓{pos_lower:5.1f}%")

# ═══════════════════════════════════════════════════════════
# 5. 关节速度分析
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("5. JOINT VELOCITY STATS")
print("=" * 70)
for jname, sname in zip(joint_names, short_names):
    vel = df[f'vel_{jname}'].values
    mean_abs = np.mean(np.abs(vel))
    peak = np.max(np.abs(vel))
    std_v = np.std(vel)
    high_vel_pct = np.sum(np.abs(vel) > 5.0) / len(vel) * 100
    flags = ''
    if high_vel_pct > 10:
        flags = f' ⚠HIGH_VEL({high_vel_pct:.0f}%)'
    if peak > 10:
        flags += f' ⚠PEAK({peak:.1f})'
    print(f"  {sname:12s}: mean|vel|={mean_abs:.3f}, σ={std_v:.3f}, peak|vel|={peak:.3f}{flags}")

# ═══════════════════════════════════════════════════════════
# 6. PLOTS
# ═══════════════════════════════════════════════════════════

# 6a. target_lpf 异常可视化: 散点图 target vs target_lpf
fig, axes = plt.subplots(6, 2, figsize=(14, 18))
for i, (jname, sname) in enumerate(zip(joint_names, short_names)):
    raw = df[f'target_{jname}'].values
    lpf = df[f'target_lpf_{jname}'].values
    row, col = i % 6, i // 6
    ax = axes[row, col]
    ax.scatter(raw, lpf, s=1, alpha=0.3)
    ax.plot([raw.min(), raw.max()], [raw.min(), raw.max()], 'k--', linewidth=0.5)
    ax.set_xlabel('target raw')
    ax.set_ylabel('target_lpf')
    # detect divergence
    lpf_range = lpf.max() - lpf.min()
    raw_range = raw.max() - raw.min()
    ratio = lpf_range / raw_range if raw_range > 1e-6 else 0
    status_str = '❌DIVERGED' if ratio > 5 else 'OK'
    ax.set_title(f'{sname}: lpf/raw range={ratio:.1f}x {status_str}', fontsize=9)
    ax.grid(True, alpha=0.2)
plt.tight_layout()
plt.savefig(out_dir / 't23_00_target_lpf_quality.png', dpi=150)
plt.close()
print("\n✅ t23_00_target_lpf_quality.png saved.")

# 6b. Joint tracking: pos vs target (raw)
fig, axes = plt.subplots(6, 2, figsize=(16, 18), sharex=True)
for i, d in enumerate(tracking_data):
    jname = d['jname']
    pos = df[f'pos_{jname}'].values
    tgt = df[f'target_{jname}'].values

    row, col = i % 6, i // 6
    ax = axes[row, col]
    ax.plot(t, pos, label='actual pos', linewidth=0.4, alpha=0.8)
    ax.plot(t, tgt, label='target', linewidth=0.4, alpha=0.6, linestyle='--')
    ax.fill_between(t, pos, tgt, alpha=0.10, color='red')
    ax.set_ylabel(f'{d["name"]} [rad]')
    ax.set_title(f'{d["name"]}: RMS={d["rms"]:.4f}, corr={d["corr"]:.3f}, delay={d["delay_ms"]:+.0f}ms', fontsize=9)
    ax.legend(fontsize=6)
    ax.grid(True, alpha=0.3)

axes[5, 0].set_xlabel('Time [s]')
axes[5, 1].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(out_dir / 't23_01_joint_tracking.png', dpi=150)
plt.close()
print("✅ t23_01_joint_tracking.png saved.")

# 6c. pos vs target scatter (raw target)
fig, axes = plt.subplots(6, 2, figsize=(14, 18))
for i, d in enumerate(tracking_data):
    jname = d['jname']
    pos = df[f'pos_{jname}'].values
    tgt = df[f'target_{jname}'].values
    vel = df[f'vel_{jname}'].values

    row, col = i % 6, i // 6
    ax = axes[row, col]
    scatter = ax.scatter(tgt, pos, c=np.abs(vel), cmap='plasma', s=1, alpha=0.5)
    lims = [min(tgt.min(), pos.min()), max(tgt.max(), pos.max())]
    ax.plot(lims, lims, 'k--', linewidth=0.5, alpha=0.3)
    ax.set_xlabel('Target [rad]')
    ax.set_ylabel('Actual Pos [rad]')
    ax.set_title(f'{d["name"]}: corr={d["corr"]:.3f}, track%={d["tracking_ratio"]:.1%}', fontsize=9)
    ax.grid(True, alpha=0.2)
    ax.axhline(y=0, color='gray', linewidth=0.3)
    ax.axvline(x=0, color='gray', linewidth=0.3)

plt.tight_layout()
plt.savefig(out_dir / 't23_02_scatter_target_vs_pos.png', dpi=150)
plt.close()
print("✅ t23_02_scatter_target_vs_pos.png saved.")

# 6d. Joint velocities
fig, axes = plt.subplots(6, 2, figsize=(16, 14), sharex=True)
for i, (jname, sname) in enumerate(zip(joint_names, short_names)):
    vel = df[f'vel_{jname}'].values
    row, col = i % 6, i // 6
    ax = axes[row, col]
    ax.plot(t, vel, linewidth=0.4)
    ax.axhline(y=0, color='k', linewidth=0.3)
    ax.set_ylabel(f'{sname} [rad/s]')
    ax.set_title(f'{sname}: mean|vel|={np.mean(np.abs(vel)):.2f}, peak={np.max(np.abs(vel)):.2f}', fontsize=9)
    ax.grid(True, alpha=0.3)

axes[5, 0].set_xlabel('Time [s]')
axes[5, 1].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(out_dir / 't23_03_joint_velocities.png', dpi=150)
plt.close()
print("✅ t23_03_joint_velocities.png saved.")

# 6e. Bilateral comparison
pairs_plot = [
    ('left_hip_pitch_joint', 'right_hip_pitch_joint', 'Hip Pitch'),
    ('left_hip_roll_joint', 'right_hip_roll_joint', 'Hip Roll'),
    ('left_hip_yaw_joint', 'right_hip_yaw_joint', 'Hip Yaw'),
    ('left_knee_pitch_joint', 'right_knee_pitch_joint', 'Knee'),
    ('left_ankle_pitch_joint', 'right_ankle_pitch_joint', 'Ankle Pitch'),
    ('left_ankle_roll_joint', 'right_ankle_roll_joint', 'Ankle Roll'),
]

fig, axes = plt.subplots(3, 2, figsize=(14, 12), sharex=True)
for i, (l_j, r_j, name) in enumerate(pairs_plot):
    l_pos = df[f'pos_{l_j}'].values
    r_pos = df[f'pos_{r_j}'].values
    l_tgt = df[f'target_{l_j}'].values
    r_tgt = df[f'target_{r_j}'].values

    row, col = i % 3, i // 3
    ax = axes[row, col]
    ax.plot(t, l_pos, label='L actual', linewidth=0.5)
    ax.plot(t, r_pos, label='R actual', linewidth=0.5, alpha=0.7)
    # target as dashed lines (only plot if not corrupted)
    ax.plot(t, l_tgt, label='L target', linewidth=0.3, alpha=0.35, linestyle=':')
    ax.plot(t, r_tgt, label='R target', linewidth=0.3, alpha=0.35, linestyle=':')

    pos_corr = np.corrcoef(l_pos, r_pos)[0, 1]
    ax.set_ylabel(f'{name} [rad]')
    ax.set_title(f'{name}: L-R corr={pos_corr:+.3f}')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

axes[2, 1].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(out_dir / 't23_04_bilateral.png', dpi=150)
plt.close()
print("✅ t23_04_bilateral.png saved.")

# 6f. Tracking error bar chart
fig, ax = plt.subplots(figsize=(10, 6))
names_sorted = [d['name'] for d in reversed(tracking_data)]
rms_vals = [d['rms'] for d in reversed(tracking_data)]
corrs = [d['corr'] for d in reversed(tracking_data)]
colors = ['#d32f2f' if abs(c) < 0.2 else '#ff9800' if abs(c) < 0.5 else '#4caf50' for c in corrs]
ax.barh(names_sorted, rms_vals, color=colors)
ax.set_xlabel('RMS Tracking Error [rad] (pos vs target raw)')
ax.set_title('T23 Joint Tracking Error Ranking')
for i, (v, d) in enumerate(zip(rms_vals, reversed(tracking_data))):
    ax.text(v + 0.005, i, f'{v:.3f} (corr={d["corr"]:.2f})', va='center', fontsize=8)
plt.tight_layout()
plt.savefig(out_dir / 't23_05_error_ranking.png', dpi=150)
plt.close()
print("✅ t23_05_error_ranking.png saved.")

# 6g. delay vs corr scatter
fig, ax = plt.subplots(figsize=(10, 6))
for d in tracking_data:
    ax.scatter(d['delay_ms'], abs(d['corr']), s=80, label=d['name'])
    ax.annotate(d['name'], (d['delay_ms'], abs(d['corr'])), fontsize=7,
                textcoords="offset points", xytext=(5, 5))
ax.axhline(y=0.5, color='green', linestyle='--', alpha=0.3, label='good tracking threshold')
ax.axvline(x=0, color='gray', linewidth=0.5)
ax.set_xlabel('Delay [ms] (target→pos)')
ax.set_ylabel('|Zero-lag Correlation|')
ax.set_title('T23: Delay vs Tracking Quality')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(out_dir / 't23_06_delay_vs_corr.png', dpi=150)
plt.close()
print("✅ t23_06_delay_vs_corr.png saved.")

# ═══════════════════════════════════════════════════════════
# 7. SUMMARY
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("7. SUMMARY")
print("=" * 70)

# Top-3 worst tracking
print("\n  Top 3 Worst Tracking (by RMS vs raw target):")
for i, d in enumerate(tracking_data[:3]):
    print(f"    {i+1}. {d['name']}: RMS={d['rms']:.4f} rad, corr={d['corr']:.3f}, delay={d['delay_ms']:+.0f}ms")

# Top-3 best tracking
print("\n  Top 3 Best Tracking (by RMS vs raw target):")
for i, d in enumerate(tracking_data[-3:]):
    print(f"    {i+1}. {d['name']}: RMS={d['rms']:.4f} rad, corr={d['corr']:.3f}, delay={d['delay_ms']:+.0f}ms")

# Key finding: target_lpf divergence
ankle_lpf_diverged = []
for jname, sname in zip(joint_names, short_names):
    if 'ankle' in jname:
        raw = df[f'target_{jname}'].values
        lpf = df[f'target_lpf_{jname}'].values
        ratio = (lpf.max() - lpf.min()) / (raw.max() - raw.min()) if raw.max() - raw.min() > 1e-6 else 0
        if ratio > 5:
            ankle_lpf_diverged.append(sname)

print(f"\n  ❌ CRITICAL: Ankle target_lpf DIVERGED for: {', '.join(ankle_lpf_diverged)}")
print(f"     lpf/raw range ratio exceeds 5x for these joints.")
print(f"     Possible cause: LPF initial state (denormal values → integrator windup)")

# Overall stats
mean_corr = np.mean([abs(d['corr']) for d in tracking_data])
mean_track = np.mean([d['tracking_ratio'] for d in tracking_data])
mean_delay = np.mean([abs(d['delay_ms']) for d in tracking_data])

# Separate hip/knee vs ankle
hk_data = [d for d in tracking_data if 'Ank' not in d['name']]
ank_data = [d for d in tracking_data if 'Ank' in d['name']]
hk_mean_corr = np.mean([abs(d['corr']) for d in hk_data])
ank_mean_corr = np.mean([abs(d['corr']) for d in ank_data])

print(f"\n  Hip/Knee mean |corr|: {hk_mean_corr:.3f}")
print(f"  Ankle mean |corr|: {ank_mean_corr:.3f}")
print(f"  Overall mean |corr|: {mean_corr:.3f}")
print(f"  Overall mean tracking%: {mean_track:.1%}")

if mean_corr < 0.5:
    print(f"  ⚠ Overall tracking is WEAK (mean |corr| < 0.5)")
if hk_mean_corr < 0.5:
    print(f"  ⚠ Hip/Knee tracking is WEAK — PD gains likely insufficient")

print(f"\nAll plots saved to: {out_dir}")
print("=" * 70)
