"""
Gait cycle analysis: compare 5 cycles from real_origin / real_new / sim.
Output: 4 figures (3 joints each) saved to real2sim/table/
"""

import os
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# ── 路径 ──────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "t23_compare", "data")
OUT_DIR   = os.path.join(BASE_DIR, "table")
os.makedirs(OUT_DIR, exist_ok=True)

FILES = {
    "real_origin": os.path.join(DATA_DIR, "t23_joint_real_origin.csv"),
    "real_new":    os.path.join(DATA_DIR, "t23_joint_real_new.csv"),
    "sim":         os.path.join(DATA_DIR, "t23_joint_sim.csv"),
}

COLORS = {
    "real_origin": "#e41a1c",   # red
    "real_new":    "#4daf4a",   # green
    "sim":         "#377eb8",   # blue
}

LABELS = {
    "real_origin": "Real Origin",
    "real_new":    "Real New",
    "sim":         "Sim",
}

# 用于检测步态周期的参考关节（膝关节峰值明显）
CYCLE_REF_JOINT = "left_knee_pitch_joint"
SKIP_SEC        = 0.5    # 跳过开头不稳定段
N_CYCLES        = 5      # 目标周期数（自适应降级）
INTERP_N        = 200    # 每个周期插值点数
PAD_THRESH      = 0.02   # 信号范围低于此视为常量段（截断尾部）

# 12 关节分为 4 组，每组 3 个关节，对应 4 张图
JOINT_GROUPS = [
    ["left_hip_pitch_joint",   "left_hip_roll_joint",   "left_hip_yaw_joint"],
    ["left_knee_pitch_joint",  "left_ankle_pitch_joint","left_ankle_roll_joint"],
    ["right_hip_pitch_joint",  "right_hip_roll_joint",  "right_hip_yaw_joint"],
    ["right_knee_pitch_joint", "right_ankle_pitch_joint","right_ankle_roll_joint"],
]

GROUP_NAMES = [
    "left_hip",
    "left_knee_ankle",
    "right_hip",
    "right_knee_ankle",
]

# ── CSV 加载 ──────────────────────────────────────────────────────────────────
def load_csv(path):
    ts, data = [], {}
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for col in fieldnames:
            if col != "timestamp_ns":
                data[col] = []
        for row in reader:
            ts.append(float(row["timestamp_ns"]) / 1e9)
            for col in fieldnames:
                if col != "timestamp_ns":
                    data[col].append(float(row[col]))
    ts = np.array(ts)
    for k in data:
        data[k] = np.array(data[k])
    return ts, data

# ── 常量尾部截断 ─────────────────────────────────────────────────────────────
def trim_active(pos_ref, window=50, thresh=PAD_THRESH):
    """返回有效运动段的末尾索引（去除常量填充尾部）"""
    total = len(pos_ref)
    for end in range(total - window, window, -window):
        seg = pos_ref[end:end + window]
        if seg.max() - seg.min() > thresh:
            return end + window
    return total

# ── 步态周期检测 ──────────────────────────────────────────────────────────────
def detect_cycles(ts, pos_ref, skip_sec=SKIP_SEC, n_cycles=N_CYCLES):
    """返回最多 n_cycles 个周期的起止帧索引列表 [(s0,e0), ...]"""
    skip_idx = np.searchsorted(ts, ts[0] + skip_sec)
    active_end = trim_active(pos_ref)
    pos_seg = pos_ref[skip_idx:active_end]

    if len(pos_seg) < 20:
        return []

    # 估算采样率与最小峰间距（0.5s 以上）
    dt       = float(np.median(np.diff(ts)))
    min_dist = max(10, int(0.5 / dt))

    # 归一化后找峰值，逐步降低阈值
    p_min, p_max = pos_seg.min(), pos_seg.max()
    p_norm = (pos_seg - p_min) / (p_max - p_min + 1e-9)
    peaks = np.array([], dtype=int)
    for height in [0.4, 0.3, 0.2, 0.1]:
        peaks, _ = find_peaks(p_norm, height=height, distance=min_dist)
        if len(peaks) >= 2:
            break

    peaks = peaks[:n_cycles + 1]
    cycles = []
    for i in range(min(n_cycles, len(peaks) - 1)):
        s = int(peaks[i])   + skip_idx
        e = int(peaks[i+1]) + skip_idx
        cycles.append((s, e))
    return cycles

# ── 单周期插值 ────────────────────────────────────────────────────────────────
def interp_cycle(ts, values, s, e, n=INTERP_N):
    t_seg = ts[s:e+1] - ts[s]
    v_seg = values[s:e+1]
    t_norm = t_seg / t_seg[-1]
    xi = np.linspace(0, 1, n)
    return np.interp(xi, t_norm, v_seg)

# ── 主逻辑 ────────────────────────────────────────────────────────────────────
def main():
    print("加载数据...")
    datasets = {}
    for name, path in FILES.items():
        print(f"  {name}: {path}")
        ts, data = load_csv(path)
        datasets[name] = (ts, data)

    # 检测各数据集周期
    print("检测步态周期...")
    cycles_map = {}
    for name, (ts, data) in datasets.items():
        ref_col = f"pos_{CYCLE_REF_JOINT}"
        cycles = detect_cycles(ts, data[ref_col])
        cycles_map[name] = cycles
        if cycles:
            durations = [(ts[e] - ts[s]) for s, e in cycles]
            print(f"  {name}: {len(cycles)} 个周期, "
                  f"平均时长 {np.mean(durations):.3f}s ± {np.std(durations):.3f}s")
        else:
            print(f"  {name}: [ERROR] 未检测到有效周期")

    # 生成 4 张图
    print("生成图表...")
    for fig_idx, (group, gname) in enumerate(zip(JOINT_GROUPS, GROUP_NAMES)):
        fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        n_used = min(len(c) for c in cycles_map.values() if c)
        fig.suptitle(f"Gait Cycle Comparison — {gname}  ({n_used} cycles)",
                     fontsize=14, fontweight="bold")

        for ax, joint in zip(axes, group):
            col_pos    = f"pos_{joint}"
            col_target = f"target_{joint}"

            for name, (ts, data) in datasets.items():
                cycles = cycles_map[name][:n_used]
                if not cycles:
                    continue
                # 串联 n_used 个周期，X 轴 0 ~ n_used
                segs_pos, segs_tgt, xi_all = [], [], []
                for ci, (s, e) in enumerate(cycles):
                    seg_p = interp_cycle(ts, data[col_pos], s, e)
                    seg_t = interp_cycle(ts, data[col_target], s, e)
                    xi_seg = np.linspace(ci, ci + 1, INTERP_N, endpoint=False)
                    segs_pos.append(seg_p)
                    segs_tgt.append(seg_t)
                    xi_all.append(xi_seg)
                xi_cat  = np.concatenate(xi_all)
                pos_cat = np.concatenate(segs_pos)
                tgt_cat = np.concatenate(segs_tgt)
                c = COLORS[name]

                ax.plot(xi_cat, pos_cat, color=c, lw=1.5,
                        label=f"{LABELS[name]} pos")
                ax.plot(xi_cat, tgt_cat, color=c, lw=0.9, ls="--", alpha=0.55,
                        label=f"{LABELS[name]} target")

            # 周期分隔线
            for ci in range(1, n_used):
                ax.axvline(ci, color="grey", lw=0.5, ls=":", alpha=0.6)

            short = joint.replace("_joint", "").replace("_", " ")
            ax.set_ylabel(f"{short}\n(rad)", fontsize=9)
            ax.grid(True, lw=0.4, alpha=0.5)
            ax.tick_params(labelsize=8)

            if ax is axes[0]:
                ax.legend(fontsize=7, ncol=3, loc="upper right")

        axes[-1].set_xlabel("Cycle", fontsize=10)
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        out_path = os.path.join(OUT_DIR, f"cycle_compare_{fig_idx+1:02d}_{gname}.png")
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  保存: {out_path}")

    print("完成。")

if __name__ == "__main__":
    main()
