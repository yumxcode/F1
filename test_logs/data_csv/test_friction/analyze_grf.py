#!/usr/bin/env python3
"""
GRF (Ground Reaction Force) 分析脚本
读取 sim_module 记录的 grf_*.csv，生成以下图表并保存到 analyze/ 目录：
  1. GRF 法向力时序图 (Fn)，标注 IC/TO 事件
  2. 摩擦力时序图 (Fx, Fy, Ft)
  3. 摩擦锥散点图 (Ft vs Fn)
  4. 单步态周期叠加 GRF 曲线 (均值±std)
  5. 左右对称性统计柱状图
  6. 接触点数时序图
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── 路径配置 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "grf_20260427_163437.csv")
OUT_DIR = os.path.join(SCRIPT_DIR, "analyze")
os.makedirs(OUT_DIR, exist_ok=True)

# ── 参数 ──
FN_THRESHOLD = 5.0    # 法向力阈值 (N)，低于此值视为摆动相
FRICTION_COEFF = 1.0  # 地面摩擦系数 (flat.xml friction="1")
CYCLE_TIME = 0.7      # 步态周期 (s)
MIN_SWING_MS = 50     # 短于此值的摆动相视为弹跳，合并到相邻支撑相
MIN_STANCE_MS = 50    # 短于此值的支撑相视为噪声，丢弃

# ──────────────────────────────────────────────────────────────────────────────
# 1. 加载数据 (pure numpy, no pandas)
# ──────────────────────────────────────────────────────────────────────────────
print(f"Loading {CSV_PATH} ...")
with open(CSV_PATH, "r") as f:
    header = f.readline().strip().split(",")
col = {name: idx for idx, name in enumerate(header)}
raw = np.loadtxt(CSV_PATH, delimiter=",", skiprows=1)

t = raw[:, col["sim_time"]]
t0 = t[0]
t_rel = t - t0  # 相对时间 (s)
N = len(t)
dt = np.median(np.diff(t))
print(f"  Frames: {N}, dt={dt*1000:.1f} ms, duration={t_rel[-1]:.1f} s")

# ──────────────────────────────────────────────────────────────────────────────
# 2. IC/TO 事件检测（鲁棒版：合并短时弹跳，过滤噪声接触）
# ──────────────────────────────────────────────────────────────────────────────
def detect_events_robust(Fn, t_arr, threshold=FN_THRESHOLD,
                         min_swing_ms=MIN_SWING_MS, min_stance_ms=MIN_STANCE_MS):
    """鲁棒 IC/TO 检测：合并间隔 < min_swing_ms 的相邻支撑段，
    过滤持续 < min_stance_ms 的短支撑段。返回 IC/TO 帧索引。"""
    contact = Fn > threshold
    # Step 1: 找到所有原始接触段 (start_idx, end_idx)
    segments = []
    start = None
    for i in range(len(contact)):
        if contact[i] and start is None:
            start = i
        elif not contact[i] and start is not None:
            segments.append([start, i - 1])
            start = None
    if start is not None:
        segments.append([start, len(contact) - 1])

    # Step 2: 合并间隔 < min_swing_ms 的相邻段（消除弹跳）
    if not segments:
        return np.array([]), np.array([])
    merged = [list(segments[0])]
    for s, e in segments[1:]:
        prev_s, prev_e = merged[-1]
        gap_ms = (t_arr[s] - t_arr[prev_e]) * 1000
        if gap_ms < min_swing_ms:
            merged[-1][1] = e  # 合并
        else:
            merged.append([s, e])

    # Step 3: 过滤持续 < min_stance_ms 的段
    filtered = [(s, e) for s, e in merged
                if (t_arr[e] - t_arr[s]) * 1000 >= min_stance_ms]

    ic_indices = np.array([s for s, e in filtered])
    to_indices = np.array([e for s, e in filtered])
    return ic_indices, to_indices

left_Fn = raw[:, col["left_Fn"]]
right_Fn = raw[:, col["right_Fn"]]
left_Ft = raw[:, col["left_Ft"]]
right_Ft = raw[:, col["right_Ft"]]

left_ic, left_to = detect_events_robust(left_Fn, t_rel)
right_ic, right_to = detect_events_robust(right_Fn, t_rel)

print(f"  Left  IC={len(left_ic)}, TO={len(left_to)}")
print(f"  Right IC={len(right_ic)}, TO={len(right_to)}")

# ──────────────────────────────────────────────────────────────────────────────
# 3. 步态周期提取 (IC-to-IC)
# ──────────────────────────────────────────────────────────────────────────────
def extract_strides(Fn, Ft, ic_indices, t_rel):
    """按 IC 切分步态周期，返回归一化时间下的 Fn/Ft 列表。"""
    strides_Fn, strides_Ft, durations = [], [], []
    for k in range(len(ic_indices) - 1):
        i0, i1 = ic_indices[k], ic_indices[k + 1]
        dur = t_rel[i1] - t_rel[i0]
        if dur < 0.3 or dur > 1.5:  # 过滤异常步
            continue
        seg_Fn = Fn[i0:i1]
        seg_Ft = Ft[i0:i1]
        # 重采样到 100 点
        x_old = np.linspace(0, 1, len(seg_Fn))
        x_new = np.linspace(0, 1, 100)
        strides_Fn.append(np.interp(x_new, x_old, seg_Fn))
        strides_Ft.append(np.interp(x_new, x_old, seg_Ft))
        durations.append(dur)
    return strides_Fn, strides_Ft, durations

left_strides_Fn, left_strides_Ft, left_durs = extract_strides(left_Fn, left_Ft, left_ic, t_rel)
right_strides_Fn, right_strides_Ft, right_durs = extract_strides(right_Fn, right_Ft, right_ic, t_rel)

print(f"  Left  valid strides: {len(left_durs)}, mean duration: {np.mean(left_durs):.3f} s")
print(f"  Right valid strides: {len(right_durs)}, mean duration: {np.mean(right_durs):.3f} s")

# ──────────────────────────────────────────────────────────────────────────────
# Plot 1: GRF 法向力时序 + IC/TO 标注
# ──────────────────────────────────────────────────────────────────────────────
print("Generating plot 1: GRF normal force time series ...")
fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
for ax, Fn, ic, to, side in zip(axes,
                                 [left_Fn, right_Fn],
                                 [left_ic, right_ic],
                                 [left_to, right_to],
                                 ["Left", "Right"]):
    ax.plot(t_rel, Fn, linewidth=0.5, color="steelblue", label="Fn (N)")
    ax.axhline(FN_THRESHOLD, color="gray", linestyle="--", linewidth=0.5, label=f"threshold={FN_THRESHOLD}N")
    if len(ic) > 0:
        ax.plot(t_rel[ic], Fn[ic], "g^", markersize=4, label=f"IC ({len(ic)})")
    if len(to) > 0:
        ax.plot(t_rel[to], Fn[to], "rv", markersize=4, label=f"TO ({len(to)})")
    ax.set_ylabel(f"{side} Fn (N)")
    ax.legend(fontsize=7, loc="upper right")
    ax.grid(True, alpha=0.3)

axes[-1].set_xlabel("Time (s)")
fig.suptitle("Ground Reaction Force — Normal Component (Fn)", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "01_grf_normal_force.png"), dpi=150)
plt.close(fig)

# ──────────────────────────────────────────────────────────────────────────────
# Plot 2: 摩擦力时序 (Fx, Fy, Ft)
# ──────────────────────────────────────────────────────────────────────────────
print("Generating plot 2: Friction force time series ...")
fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
for ax, side in zip(axes, ["left", "right"]):
    Fx = raw[:, col[f"{side}_Fx"]]
    Fy = raw[:, col[f"{side}_Fy"]]
    Ft = raw[:, col[f"{side}_Ft"]]
    ax.plot(t_rel, Fx, linewidth=0.4, alpha=0.7, label="Fx (tangent1)")
    ax.plot(t_rel, Fy, linewidth=0.4, alpha=0.7, label="Fy (tangent2)")
    ax.plot(t_rel, Ft, linewidth=0.6, color="black", label="Ft (magnitude)")
    ax.set_ylabel(f"{side.capitalize()} Friction (N)")
    ax.legend(fontsize=7, loc="upper right")
    ax.grid(True, alpha=0.3)

axes[-1].set_xlabel("Time (s)")
fig.suptitle("Friction Forces (Fx, Fy, Ft)", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "02_friction_force.png"), dpi=150)
plt.close(fig)

# ──────────────────────────────────────────────────────────────────────────────
# Plot 3: 摩擦锥散点图 (Ft vs Fn)
# ──────────────────────────────────────────────────────────────────────────────
print("Generating plot 3: Friction cone check ...")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
for ax, Fn, Ft, side in zip(axes,
                             [left_Fn, right_Fn],
                             [left_Ft, right_Ft],
                             ["Left", "Right"]):
    # 只画有接触的帧
    mask = Fn > FN_THRESHOLD
    ax.scatter(Fn[mask], Ft[mask], s=1, alpha=0.3, color="steelblue")
    # 摩擦锥边界
    fn_range = np.linspace(0, Fn[mask].max() * 1.1, 100)
    ax.plot(fn_range, FRICTION_COEFF * fn_range, "r--", linewidth=1, label=f"μ·Fn (μ={FRICTION_COEFF})")
    # 统计超出摩擦锥的比例
    n_exceed = np.sum(Ft[mask] > FRICTION_COEFF * Fn[mask])
    pct = 100.0 * n_exceed / mask.sum() if mask.sum() > 0 else 0
    ax.set_title(f"{side} foot — exceed cone: {n_exceed}/{mask.sum()} ({pct:.1f}%)")
    ax.set_xlabel("Fn (N)")
    ax.set_ylabel("Ft (N)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal", adjustable="datalim")

fig.suptitle("Friction Cone Check: Ft vs Fn", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "03_friction_cone.png"), dpi=150)
plt.close(fig)

# ──────────────────────────────────────────────────────────────────────────────
# Plot 4: 单步态周期叠加 (mean ± std)
# ──────────────────────────────────────────────────────────────────────────────
print("Generating plot 4: Stride-overlaid GRF ...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
phase = np.linspace(0, 100, 100)  # 归一化 0-100%

for ci, (strides_Fn, strides_Ft, durs, side) in enumerate([
    (left_strides_Fn, left_strides_Ft, left_durs, "Left"),
    (right_strides_Fn, right_strides_Ft, right_durs, "Right"),
]):
    if len(strides_Fn) == 0:
        for r in range(2):
            axes[r, ci].text(0.5, 0.5, "No valid strides", ha="center", va="center")
        continue

    arr_Fn = np.array(strides_Fn)
    arr_Ft = np.array(strides_Ft)
    mean_Fn, std_Fn = arr_Fn.mean(axis=0), arr_Fn.std(axis=0)
    mean_Ft, std_Ft = arr_Ft.mean(axis=0), arr_Ft.std(axis=0)

    # Fn
    ax = axes[0, ci]
    for s in arr_Fn:
        ax.plot(phase, s, linewidth=0.3, alpha=0.2, color="steelblue")
    ax.plot(phase, mean_Fn, linewidth=1.5, color="navy", label="mean")
    ax.fill_between(phase, mean_Fn - std_Fn, mean_Fn + std_Fn, alpha=0.2, color="navy")
    ax.set_ylabel("Fn (N)")
    ax.set_title(f"{side} — Normal Force ({len(strides_Fn)} strides, dur={np.mean(durs):.3f}±{np.std(durs):.3f}s)")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # Ft
    ax = axes[1, ci]
    for s in arr_Ft:
        ax.plot(phase, s, linewidth=0.3, alpha=0.2, color="coral")
    ax.plot(phase, mean_Ft, linewidth=1.5, color="darkred", label="mean")
    ax.fill_between(phase, mean_Ft - std_Ft, mean_Ft + std_Ft, alpha=0.2, color="darkred")
    ax.set_ylabel("Ft (N)")
    ax.set_xlabel("Gait cycle (%)")
    ax.set_title(f"{side} — Tangential Friction")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

fig.suptitle("Stride-Overlaid GRF Curves (IC-to-IC, normalized)", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "04_stride_overlay.png"), dpi=150)
plt.close(fig)

# ──────────────────────────────────────────────────────────────────────────────
# Plot 5: 左右对称性统计
# ──────────────────────────────────────────────────────────────────────────────
print("Generating plot 5: Left/right symmetry ...")
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# 5a: peak Fn per stride
left_peak_Fn  = [np.max(s) for s in left_strides_Fn]  if left_strides_Fn  else [0]
right_peak_Fn = [np.max(s) for s in right_strides_Fn] if right_strides_Fn else [0]

ax = axes[0]
x = np.arange(2)
means = [np.mean(left_peak_Fn), np.mean(right_peak_Fn)]
stds  = [np.std(left_peak_Fn),  np.std(right_peak_Fn)]
bars = ax.bar(x, means, yerr=stds, capsize=5, color=["steelblue", "coral"], width=0.5)
ax.set_xticks(x)
ax.set_xticklabels(["Left", "Right"])
ax.set_ylabel("Peak Fn (N)")
ax.set_title("Peak Normal Force per Stride")
for bar, m in zip(bars, means):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{m:.1f}", ha="center", fontsize=9)
ax.grid(True, alpha=0.3, axis="y")

# 5b: stride duration
ax = axes[1]
ld = left_durs if left_durs else [0]
rd = right_durs if right_durs else [0]
means_d = [np.mean(ld), np.mean(rd)]
stds_d  = [np.std(ld),  np.std(rd)]
bars = ax.bar(x, means_d, yerr=stds_d, capsize=5, color=["steelblue", "coral"], width=0.5)
ax.set_xticks(x)
ax.set_xticklabels(["Left", "Right"])
ax.set_ylabel("Duration (s)")
ax.set_title("Stride Duration (IC-to-IC)")
for bar, m in zip(bars, means_d):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005, f"{m:.3f}", ha="center", fontsize=9)
ax.grid(True, alpha=0.3, axis="y")

# 5c: peak Ft per stride
left_peak_Ft  = [np.max(s) for s in left_strides_Ft]  if left_strides_Ft  else [0]
right_peak_Ft = [np.max(s) for s in right_strides_Ft] if right_strides_Ft else [0]

ax = axes[2]
means_ft = [np.mean(left_peak_Ft), np.mean(right_peak_Ft)]
stds_ft  = [np.std(left_peak_Ft),  np.std(right_peak_Ft)]
bars = ax.bar(x, means_ft, yerr=stds_ft, capsize=5, color=["steelblue", "coral"], width=0.5)
ax.set_xticks(x)
ax.set_xticklabels(["Left", "Right"])
ax.set_ylabel("Peak Ft (N)")
ax.set_title("Peak Friction Force per Stride")
for bar, m in zip(bars, means_ft):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f"{m:.1f}", ha="center", fontsize=9)
ax.grid(True, alpha=0.3, axis="y")

fig.suptitle("Left / Right Symmetry Comparison", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "05_symmetry.png"), dpi=150)
plt.close(fig)

# ──────────────────────────────────────────────────────────────────────────────
# Plot 6: 接触点数时序
# ──────────────────────────────────────────────────────────────────────────────
print("Generating plot 6: Contact count time series ...")
fig, ax = plt.subplots(figsize=(16, 4))
ax.plot(t_rel, raw[:, col["left_contact_count"]], linewidth=0.5, label="Left", color="steelblue")
ax.plot(t_rel, raw[:, col["right_contact_count"]], linewidth=0.5, label="Right", color="coral")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Contact count")
ax.set_title("Active Contact Points per Foot")
ax.set_yticks([0, 1, 2, 3, 4])
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "06_contact_count.png"), dpi=150)
plt.close(fig)

# ──────────────────────────────────────────────────────────────────────────────
# 统计摘要
# ──────────────────────────────────────────────────────────────────────────────
summary_lines = []
summary_lines.append("=" * 60)
summary_lines.append("GRF Analysis Summary")
summary_lines.append("=" * 60)
summary_lines.append(f"CSV: {os.path.basename(CSV_PATH)}")
summary_lines.append(f"Frames: {N}, dt={dt*1000:.1f} ms, duration={t_rel[-1]:.1f} s")
summary_lines.append("")

for side, Fn, Ft, ic, to, durs, strides_Fn_list, strides_Ft_list in [
    ("Left",  left_Fn,  left_Ft,  left_ic,  left_to,  left_durs,  left_strides_Fn,  left_strides_Ft),
    ("Right", right_Fn, right_Ft, right_ic, right_to, right_durs, right_strides_Fn, right_strides_Ft),
]:
    summary_lines.append(f"--- {side} foot ---")
    summary_lines.append(f"  IC events: {len(ic)}, TO events: {len(to)}  (robust: min_swing={MIN_SWING_MS}ms, min_stance={MIN_STANCE_MS}ms)")
    contact_mask = Fn > FN_THRESHOLD
    stance_pct = 100.0 * contact_mask.sum() / N
    summary_lines.append(f"  Stance phase: {stance_pct:.1f}% of total")
    summary_lines.append(f"  Fn — max: {Fn.max():.1f} N, mean (stance): {Fn[contact_mask].mean():.1f} N")
    summary_lines.append(f"  Ft — max: {Ft.max():.1f} N, mean (stance): {Ft[contact_mask].mean():.1f} N")
    if len(durs) > 0:
        summary_lines.append(f"  Stride duration: {np.mean(durs):.3f} ± {np.std(durs):.3f} s (n={len(durs)})")
        peaks_fn = [np.max(s) for s in strides_Fn_list]
        peaks_ft = [np.max(s) for s in strides_Ft_list]
        summary_lines.append(f"  Peak Fn/stride: {np.mean(peaks_fn):.1f} ± {np.std(peaks_fn):.1f} N")
        summary_lines.append(f"  Peak Ft/stride: {np.mean(peaks_ft):.1f} ± {np.std(peaks_ft):.1f} N")
        # 摩擦系数利用率
        mu_util = np.array(peaks_ft) / np.array(peaks_fn)
        summary_lines.append(f"  Friction utilization (peak Ft/Fn): {np.mean(mu_util):.3f} ± {np.std(mu_util):.3f} (μ={FRICTION_COEFF})")
    summary_lines.append("")

summary_text = "\n".join(summary_lines)
print(summary_text)

summary_path = os.path.join(OUT_DIR, "summary.txt")
with open(summary_path, "w") as f:
    f.write(summary_text)

print(f"\nAll outputs saved to: {OUT_DIR}")
print("  01_grf_normal_force.png")
print("  02_friction_force.png")
print("  03_friction_cone.png")
print("  04_stride_overlay.png")
print("  05_symmetry.png")
print("  06_contact_count.png")
print("  summary.txt")
