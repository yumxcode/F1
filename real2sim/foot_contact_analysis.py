"""
Foot contact detection and pose visualization.

Primary method: MuJoCo FK ankle z position (link_*_ankle_roll body)
  foot z reaches minimum during stance → IC = descend through threshold
                                       → TO = ascend through threshold
Fallback (no MuJoCo): knee pitch auto-threshold (swing/stance midpoint)

Outputs in real2sim/table/foot_contact/:
  01_contact_timeline.png   — foot z (or knee) + IC/TO markers + stance bands
  02_left/right_contact_poses.png  — joint angle windows around each IC
  03_left/right_mujoco_poses.png   — rendered lower-body pose at each IC
"""

import os
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

try:
    import mujoco
    import yaml
    _HAS_MUJOCO = True
except ImportError:
    _HAS_MUJOCO = False

# ── 路径 ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))          # real2sim/
BASE_DIR   = os.path.dirname(SCRIPT_DIR)                          # project root

DATA_FILES = {
    "real_new":    os.path.join(SCRIPT_DIR, "t23_compare", "data", "t23_joint_real_new.csv"),
    "real_origin": os.path.join(SCRIPT_DIR, "t23_compare", "data", "t23_joint_real_origin.csv"),
    "sim":         os.path.join(SCRIPT_DIR, "t23_compare", "data", "t23_joint_sim.csv"),
}
DATASET_STYLE = {
    "real_new":    {"color": "#e41a1c", "ls": "-",  "lw": 1.6, "label": "Real New"},
    "real_origin": {"color": "#377eb8", "ls": "--", "lw": 1.4, "label": "Real Origin"},
    "sim":         {"color": "#4daf4a", "ls": ":",  "lw": 1.8, "label": "Sim"},
}
OUT_DIR   = os.path.join(SCRIPT_DIR, "table", "foot_contact")
XML_PATH  = os.path.join(BASE_DIR, "src", "module", "sim_module", "model", "mjcf", "xyber_x1_flat.xml")
YAML_PATH = os.path.join(BASE_DIR, "src", "module", "control_module", "cfg", "rl_x1.yaml")

os.makedirs(OUT_DIR, exist_ok=True)

# ── 参数 ─────────────────────────────────────────────────────────────────────
SKIP_SEC          = 0.3   # 跳过开头过渡段
ACTIVE_END_SEC    = 8.0   # 只分析前 8s 有效行走段
FK_CONTACT_MARGIN = 0.04  # FK 法：min_z + margin 作为接地阈值 (m)
SWING_MIN_DIST_S  = 0.30  # 膝关节法：swing 峰最小间距 (s)
WINDOW_FRAMES     = 35    # IC 事件前后各显示多少帧（关节角图）
BASE_Z            = 0.82  # FK 计算时固定躯干高度 (m)
STANCE_OUTLIER_K  = 1.5   # 支撑时长离群值过滤：median ± K * IQR

KNEE = {
    "left":  "left_knee_pitch_joint",
    "right": "right_knee_pitch_joint",
}
FOOT_BODIES = {
    "left":  "link_left_ankle_roll",
    "right": "link_right_ankle_roll",
}
LEG_JOINTS = {
    "left":  ["left_hip_pitch_joint",  "left_hip_roll_joint",  "left_hip_yaw_joint",
              "left_knee_pitch_joint",  "left_ankle_pitch_joint", "left_ankle_roll_joint"],
    "right": ["right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
              "right_knee_pitch_joint", "right_ankle_pitch_joint","right_ankle_roll_joint"],
}
SIDE_COLOR = {"left": "#e41a1c", "right": "#377eb8"}   # red / blue


# ── 支撑时长离群值过滤 ────────────────────────────────────────────────────────
def filter_stance_outliers(ts, ic_frames, to_frames, k=STANCE_OUTLIER_K):
    """移除支撑时长异常的步（减速/停步），返回过滤后的 ic_frames, to_frames。"""
    if len(ic_frames) < 3:
        return ic_frames, to_frames
    durs = np.array([(ts[min(to, len(ts)-1)] - ts[ic]) for ic, to in zip(ic_frames, to_frames)])
    q1, q3 = np.percentile(durs, 25), np.percentile(durs, 75)
    iqr = q3 - q1
    upper = q3 + k * iqr
    keep = durs <= upper
    return [ic for ic, m in zip(ic_frames, keep) if m], \
           [to for to, m in zip(to_frames, keep) if m]


# ── CSV 加载 ──────────────────────────────────────────────────────────────────
def load_csv(path):
    ts, data = [], {}
    with open(path) as f:
        rd = csv.DictReader(f)
        for col in rd.fieldnames:
            if col != "timestamp_ns":
                data[col] = []
        for row in rd:
            ts.append(float(row["timestamp_ns"]) / 1e9)
            for col in data:
                data[col].append(float(row[col]))
    ts = np.array(ts)
    for k in data:
        data[k] = np.array(data[k])
    return ts, data


# ── FK：批量计算脚踝 z 高度 ──────────────────────────────────────────────────
def compute_foot_z_fk(ts, data, joint_names,
                      skip_sec=SKIP_SEC, active_end=ACTIVE_END_SEC):
    """
    对有效行走段每帧跑 mj_forward，返回两侧脚踝 z 高度数组（全长，非活跃帧为 NaN）。
    """
    if not _HAS_MUJOCO or not os.path.exists(XML_PATH):
        return None

    try:
        model = mujoco.MjModel.from_xml_path(XML_PATH)
    except (ValueError, Exception) as e:
        print(f"  [warn] MuJoCo XML 加载失败，跳过 FK: {e}")
        return None
    mj_data = mujoco.MjData(model)
    bid = {s: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, FOOT_BODIES[s])
           for s in ["left", "right"]}

    t0 = ts[0]
    start_idx = int(np.searchsorted(ts, t0 + skip_sec))
    end_idx   = min(int(np.searchsorted(ts, t0 + active_end)), len(ts) - 1)

    foot_z = {"left": np.full(len(ts), np.nan),
              "right": np.full(len(ts), np.nan)}

    for i in range(start_idx, end_idx):
        mujoco.mj_resetData(model, mj_data)
        mj_data.qpos[2]   = BASE_Z
        mj_data.qpos[3:7] = [1, 0, 0, 0]
        for j in joint_names:
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, j)
            if jid == -1:
                continue
            col = f"pos_{j}"
            if col in data:
                mj_data.qpos[model.jnt_qposadr[jid]] = data[col][i]
        mujoco.mj_forward(model, mj_data)
        for s in ["left", "right"]:
            foot_z[s][i] = mj_data.xpos[bid[s], 2]

    return foot_z


# ── 主检测：FK ankle z 阈值穿越法 ────────────────────────────────────────────
def detect_contacts_fk(ts, foot_z,
                       skip_sec=SKIP_SEC, active_end=ACTIVE_END_SEC,
                       margin=FK_CONTACT_MARGIN):
    """
    foot_z: 全帧脚踝 z 数组（非活跃帧为 NaN）
    Returns: ic_frames, to_frames, threshold
    """
    t0 = ts[0]
    start_idx = int(np.searchsorted(ts, t0 + skip_sec))
    end_idx   = min(int(np.searchsorted(ts, t0 + active_end)), len(ts) - 1)

    seg = foot_z[start_idx:end_idx]
    threshold = np.nanmin(seg) + margin

    ic_frames, to_frames = [], []
    in_stance  = False
    ic_start   = None

    for i, z in enumerate(seg):
        gi = i + start_idx
        if np.isnan(z):
            continue
        if z < threshold and not in_stance:
            ic_start  = gi
            in_stance = True
        elif z >= threshold and in_stance:
            ic_frames.append(ic_start)
            to_frames.append(gi)
            in_stance = False

    if in_stance and ic_start is not None:   # 最后一段未结束
        ic_frames.append(ic_start)
        to_frames.append(end_idx)

    ic_frames, to_frames = filter_stance_outliers(ts, ic_frames, to_frames)
    return ic_frames, to_frames, threshold


# ── 备用检测：膝关节自动阈值（swing/stance 均值中点）────────────────────────
def detect_contacts_knee(ts, knee_pos,
                         skip_sec=SKIP_SEC, active_end=ACTIVE_END_SEC):
    """
    Returns: ic_frames, to_frames, threshold, swing_peaks
    """
    t0 = ts[0]
    start_idx = int(np.searchsorted(ts, t0 + skip_sec))
    end_idx   = min(int(np.searchsorted(ts, t0 + active_end)), len(ts) - 1)

    seg      = knee_pos[start_idx:end_idx]
    dt       = float(np.median(np.diff(ts)))
    min_dist = int(SWING_MIN_DIST_S / dt)

    # swing 峰
    norm = (seg - seg.min()) / (seg.max() - seg.min() + 1e-9)
    peaks = np.array([], dtype=int)
    for h in [0.55, 0.45, 0.35, 0.25]:
        peaks, _ = find_peaks(norm, height=h, distance=min_dist)
        if len(peaks) >= 2:
            break
    swing_peaks = peaks + start_idx

    # stance 谷
    neg = 1 - norm
    valleys = np.array([], dtype=int)
    for h in [0.5, 0.4, 0.3, 0.2]:
        valleys, _ = find_peaks(neg, height=h, distance=min_dist)
        if len(valleys) >= 2:
            break
    stance_peaks = valleys + start_idx

    # 阈值 = swing 均值与 stance 均值的中点
    sw_mean = knee_pos[swing_peaks].mean() if len(swing_peaks) else seg.max()
    st_mean = knee_pos[stance_peaks].mean() if len(stance_peaks) else seg.min()
    threshold = (sw_mean + st_mean) / 2.0

    ic_frames, to_frames = [], []
    search_limit = int(0.8 / dt)
    min_stance   = int(0.1 / dt)

    for pk in swing_peaks:
        ic = None
        for i in range(pk, min(pk + search_limit, end_idx)):
            if knee_pos[i] <= threshold:
                ic = i
                break
        if ic is None:
            continue
        ic_frames.append(ic)
        to = None
        for i in range(ic + min_stance, min(ic + search_limit, end_idx)):
            if knee_pos[i] >= threshold:
                to = i
                break
        to_frames.append(to if to is not None else min(ic + search_limit, end_idx - 1))

    ic_frames, to_frames = filter_stance_outliers(ts, ic_frames, to_frames)
    return ic_frames, to_frames, threshold, swing_peaks


# ── 图1：多数据集时序对比图 ────────────────────────────────────────────────────
def plot_timeline_comparison(all_results, output_path):
    """
    all_results: OrderedDict { dataset_key: {
        "ts", "data", "foot_z", "contacts", "use_fk"
    }}
    Overlays foot_z (or knee pitch) from all datasets on two subplots (left/right).
    """
    fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=False)
    any_fk = any(r["use_fk"] for r in all_results.values())
    method_label = "FK ankle z" if any_fk else "knee pitch threshold"
    fig.suptitle(f"Foot Contact Detection Comparison — {method_label}",
                 fontsize=14, fontweight="bold")

    for ax, side in zip(axes, ["left", "right"]):
        for key, res in all_results.items():
            style = DATASET_STYLE[key]
            ts    = res["ts"]
            t_rel = ts - ts[0]

            if res["use_fk"] and res["foot_z"] is not None:
                sig = res["foot_z"][side]
                y_label = f"{side} ankle z (m)"
            else:
                sig = res["data"][f"pos_{KNEE[side]}"]
                y_label = f"{side} knee pitch (rad)"

            ax.plot(t_rel, sig, color=style["color"], ls=style["ls"],
                    lw=style["lw"], label=style["label"], alpha=0.85)

            # IC markers
            ic_frames = res["contacts"][side][0]
            ic_t = [t_rel[i] for i in ic_frames]
            ic_v = [sig[i]   for i in ic_frames]
            ax.scatter(ic_t, ic_v, marker="v", s=55, color=style["color"],
                       zorder=7, edgecolors="k", linewidths=0.5)

            # stance shading (light, only for first dataset to avoid clutter)
            if key == list(all_results.keys())[0]:
                to_frames = res["contacts"][side][1]
                for ic, to in zip(ic_frames, to_frames):
                    ax.axvspan(t_rel[ic], t_rel[min(to, len(t_rel)-1)],
                               alpha=0.10, color=style["color"])

        ax.set_ylabel(y_label, fontsize=10)
        ax.legend(fontsize=9, loc="upper right", ncol=3)
        ax.grid(True, lw=0.4, alpha=0.5)
        ax.set_title(f"{side.capitalize()} foot", fontsize=11, fontweight="bold")

    axes[-1].set_xlabel("Time (s)", fontsize=10)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  保存: {output_path}")


# ── 图1b：着地统计对比 ─────────────────────────────────────────────────────────
def plot_contact_summary(all_results, output_path):
    """Bar chart: IC count + mean stance duration per dataset/side."""
    datasets = list(all_results.keys())
    sides    = ["left", "right"]
    n_ds     = len(datasets)
    x        = np.arange(len(sides))
    width    = 0.22

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    fig.suptitle("Contact Event Statistics Comparison", fontsize=13, fontweight="bold")

    for i, key in enumerate(datasets):
        style = DATASET_STYLE[key]
        res   = all_results[key]
        counts, durations = [], []
        for side in sides:
            ic = res["contacts"][side][0]
            to = res["contacts"][side][1]
            ts = res["ts"]
            counts.append(len(ic))
            durs = [(ts[min(t, len(ts)-1)] - ts[c]) * 1000 for c, t in zip(ic, to)]
            durations.append(np.mean(durs) if durs else 0)

        offset = (i - (n_ds - 1) / 2) * width
        ax1.bar(x + offset, counts, width, label=style["label"],
                color=style["color"], alpha=0.8)
        ax2.bar(x + offset, durations, width, label=style["label"],
                color=style["color"], alpha=0.8)

    for ax, ylabel, title in [
        (ax1, "IC count", "Number of Initial Contacts"),
        (ax2, "mean stance (ms)", "Mean Stance Duration"),
    ]:
        ax.set_xticks(x)
        ax.set_xticklabels([s.capitalize() for s in sides])
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(axis="y", lw=0.4, alpha=0.5)

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  保存: {output_path}")


# ── 图2：每次着地的关节角度窗口 ───────────────────────────────────────────────
def plot_contact_poses(ts, data, ic_frames, side, output_path,
                       window=WINDOW_FRAMES):
    joints = LEG_JOINTS[side]
    t0 = ts[0]
    n  = len(ic_frames)
    if n == 0:
        print(f"  [skip] {side}: 无 IC 事件")
        return

    ncols = 5
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, nrows * 3.2), squeeze=False)
    fig.suptitle(f"{side.capitalize()} Foot — {n} Initial Contact Events\n"
                 f"(gray band = stance phase, dashed line = IC moment)",
                 fontsize=11, fontweight="bold")

    short_names = [j.replace(f"{side}_", "").replace("_joint", "") for j in joints]
    colors = plt.cm.tab10(np.linspace(0, 0.8, len(joints)))

    for idx, ic in enumerate(ic_frames):
        ax = axes[idx // ncols][idx % ncols]
        s  = max(0, ic - window)
        e  = min(len(ts) - 1, ic + window)
        t_seg = (ts[s:e] - ts[ic]) * 1000  # ms，以 IC 为零点

        for j, name, col in zip(joints, short_names, colors):
            ax.plot(t_seg, data[f"pos_{j}"][s:e], lw=1.3, color=col, label=name)

        # 支撑相区域（仅着地侧）：IC 到数据末
        ax.axvspan(0, t_seg[-1], alpha=0.08, color=SIDE_COLOR[side])
        ax.axvline(0, color="k", lw=1.2, ls="--")
        ax.set_title(f"#{idx + 1}  t={ts[ic] - t0:.2f}s", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, lw=0.3, alpha=0.4)
        ax.set_xlabel("ms", fontsize=7)
        if idx == 0:
            ax.legend(fontsize=6, ncol=2, loc="upper left")

    # 隐藏多余子图
    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  保存: {output_path}")


# ── 图3：三数据集 MuJoCo 对比渲染（3行，每行独立 IC）──────────────────────────
# 行顺序：Sim → Real Origin → Real New
ROW_ORDER = ["sim", "real_origin", "real_new"]

def render_mujoco_comparison(all_results, side, joint_names, output_path,
                             cam_azimuth=None, view_label=""):
    """
    三行对比渲染：每行一个数据集。
    列数 = real_new 的 IC 数（基准），多的截断，少的留空。
    每张图保证是该脚（left/right）的真实着地时刻，数据集间时间戳独立。
    """
    try:
        import mujoco
    except ImportError:
        print("  [skip] mujoco 未安装，跳过渲染")
        return
    if not os.path.exists(XML_PATH):
        print(f"  [skip] XML 不存在: {XML_PATH}")
        return

    available = [k for k in ROW_ORDER if k in all_results]
    if not available:
        return

    # 列数以 real_new 为基准，多的截断，少的留空
    REF_KEY = "real_new"
    ic_per_ds = {k: all_results[k]["contacts"][side][0] for k in available}
    if REF_KEY not in ic_per_ds or len(ic_per_ds[REF_KEY]) == 0:
        print(f"  [skip] {side}: 基准数据集 {REF_KEY} 无 IC 事件")
        return
    n_cols = len(ic_per_ds[REF_KEY])

    # 加载模型
    try:
        model = mujoco.MjModel.from_xml_path(XML_PATH)
    except (ValueError, Exception) as e:
        print(f"  [skip] MuJoCo XML 加载失败: {e}")
        return
    mj_data = mujoco.MjData(model)
    model.vis.global_.offwidth  = 1280
    model.vis.global_.offheight = 960
    renderer = mujoco.Renderer(model, height=960, width=1280)

    cam = mujoco.MjvCamera()
    cam.type       = mujoco.mjtCamera.mjCAMERA_FREE
    cam.fixedcamid = -1
    if cam_azimuth is None:
        cam_azimuth = 90.0 if side == "left" else -90.0
    cam.distance   = 1.1
    cam.azimuth    = cam_azimuth
    cam.elevation  = -3.0
    cam.lookat     = np.array([0.0, 0.0, 0.10])

    # 逐数据集渲染（每行渲染自己的全部 IC）
    rendered = {}   # key -> [image, ...]
    ic_times = {}   # key -> [relative seconds, ...]

    for key in available:
        res  = all_results[key]
        ts   = res["ts"]
        data = res["data"]
        ics  = ic_per_ds[key][:n_cols]  # 截断到基准列数

        frames = []
        times  = []
        for ic in ics:
            mujoco.mj_resetData(model, mj_data)
            for j in joint_names:
                jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, j)
                if jid == -1:
                    continue
                col = f"pos_{j}"
                if col in data:
                    mj_data.qpos[model.jnt_qposadr[jid]] = data[col][ic]
            mj_data.qpos[2] = 0.82
            mujoco.mj_forward(model, mj_data)
            renderer.update_scene(mj_data, camera=cam)
            frames.append(renderer.render().copy())
            times.append(ts[ic] - ts[0])

        rendered[key] = frames
        ic_times[key] = times

    # ── 绘图：3行 × n_cols列 ─────────────────────────────────────────────────
    n_rows = len(available)
    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(n_cols * 4.0, n_rows * 3.8),
                             squeeze=False)
    fig.patch.set_facecolor("#111111")

    view_tag = f" [{view_label}]" if view_label else ""
    title = f"{side.capitalize()} Foot IC Comparison{view_tag}"
    fig.suptitle(title, fontsize=14, fontweight="bold", color="white")

    for row, key in enumerate(available):
        style  = DATASET_STYLE[key]
        n_ic   = len(rendered[key])

        for col in range(n_cols):
            ax = axes[row][col]
            ax.set_facecolor("#111111")
            ax.axis("off")

            if col < n_ic:
                ax.imshow(rendered[key][col], interpolation="lanczos")

                # 右下角：该数据集自己的时间戳
                ax.text(0.97, 0.03, f"t={ic_times[key][col]:.2f}s",
                        transform=ax.transAxes, fontsize=8, color="white",
                        ha="right", va="bottom",
                        bbox=dict(facecolor="black", alpha=0.6,
                                  pad=2, edgecolor="none"))

                # 列标题：仅顶行，显示该行的第 col+1 次 IC
                if row == 0:
                    ax.set_title(f"#{col + 1}", fontsize=10, color="white",
                                 fontweight="bold", pad=6)
            else:
                # 该数据集无此周期，留空
                ax.set_visible(False)

        # 行标签（第一列左侧）
        axes[row][0].text(-0.08, 0.5,
                          f"{style['label']}\n({n_ic} IC)",
                          transform=axes[row][0].transAxes,
                          fontsize=12, fontweight="bold", color=style["color"],
                          ha="right", va="center", rotation=90)

    plt.tight_layout(rect=[0.07, 0, 1, 0.94])
    fig.savefig(output_path, dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  保存: {output_path}")


# ── 主逻辑 ────────────────────────────────────────────────────────────────────
def process_dataset(key, path, joint_names):
    """加载一个数据集并运行 FK + 接地检测，返回结果 dict。"""
    label = DATASET_STYLE[key]["label"]
    print(f"\n{'='*60}")
    print(f"  [{label}]  {os.path.basename(path)}")
    print(f"{'='*60}")

    ts, data = load_csv(path)
    t0 = ts[0]
    dt = float(np.median(np.diff(ts)))
    print(f"  {len(ts)} 帧，{dt*1000:.1f}ms 间隔，总时长 {ts[-1]-t0:.1f}s")

    # FK
    foot_z = None
    if _HAS_MUJOCO and os.path.exists(XML_PATH):
        foot_z = compute_foot_z_fk(ts, data, joint_names)
        if foot_z is not None:
            for s in ["left", "right"]:
                valid = ~np.isnan(foot_z[s])
                if valid.any():
                    print(f"  {s} ankle z: min={foot_z[s][valid].min():.4f}  "
                          f"max={foot_z[s][valid].max():.4f} m")

    # 接地检测
    use_fk = foot_z is not None
    contacts = {}
    for side in ["left", "right"]:
        if use_fk:
            ic_frames, to_frames, thresh = detect_contacts_fk(ts, foot_z[side])
            contacts[side] = (ic_frames, to_frames, thresh)
            unit = "m"
        else:
            ic_frames, to_frames, thresh, swing_peaks = detect_contacts_knee(
                ts, data[f"pos_{KNEE[side]}"])
            contacts[side] = (ic_frames, to_frames, thresh, swing_peaks)
            unit = "rad"

        durations = [(ts[min(to, len(ts)-1)] - ts[ic]) * 1000
                     for ic, to in zip(ic_frames, to_frames)]
        method_tag = "FK" if use_fk else "knee"
        print(f"  [{method_tag}] {side}: {len(ic_frames)} IC  "
              f"thresh={thresh:.4f} {unit}  "
              f"stance_ms={'%.0f' % np.mean(durations) if durations else 'N/A'}")

    return {"ts": ts, "data": data, "foot_z": foot_z,
            "contacts": contacts, "use_fk": use_fk}


def main():
    # ── 读取 joint_names ─────────────────────────────────────────────────────
    joint_names = list(LEG_JOINTS["left"]) + list(LEG_JOINTS["right"])
    if _HAS_MUJOCO and os.path.exists(YAML_PATH):
        try:
            with open(YAML_PATH) as f:
                joint_names = yaml.safe_load(f)["controllers"]["rl_walk_leg"]["joint_list"]
        except Exception:
            pass

    # ── 加载并处理所有数据集 ─────────────────────────────────────────────────
    from collections import OrderedDict
    all_results = OrderedDict()
    for key, path in DATA_FILES.items():
        if not os.path.exists(path):
            print(f"  [skip] {DATASET_STYLE[key]['label']}: 文件不存在 {path}")
            continue
        all_results[key] = process_dataset(key, path, joint_names)

    if not all_results:
        print("无可用数据集，退出。")
        return

    # ── 三数据集对比渲染（3行 × N列，按最小周期数对齐）──────────────────────
    print("\n生成三数据集对比 MuJoCo 渲染...")
    views = [
        ("side",  None,   "Side"),
        ("front",  0.0,  "Front"),
        ("back",  180.0, "Back"),
    ]
    for side in ["left", "right"]:
        for view_name, azimuth, label in views:
            render_mujoco_comparison(
                all_results, side, joint_names,
                os.path.join(OUT_DIR, f"03_{side}_{view_name}.png"),
                cam_azimuth=azimuth,
                view_label=label,
            )

    print(f"\n完成！输出目录: {OUT_DIR}")
    print(f"  数据集: {', '.join(DATASET_STYLE[k]['label'] for k in all_results)}")


if __name__ == "__main__":
    main()
