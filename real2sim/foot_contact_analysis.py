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

DATA_FILE = os.path.join(SCRIPT_DIR, "t23_compare", "data", "t23_joint_real_new.csv")
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

    model   = mujoco.MjModel.from_xml_path(XML_PATH)
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

    return ic_frames, to_frames, threshold, swing_peaks


# ── 图1：时序总览图 ────────────────────────────────────────────────────────────
def plot_timeline(ts, data, contacts_dict, output_path, foot_z=None):
    """
    foot_z: dict {"left": array, "right": array}，FK 法时传入；None 则退化为膝关节图。
    """
    t0    = ts[0]
    t_rel = ts - t0
    use_fk = foot_z is not None

    fig, axes = plt.subplots(2, 1, figsize=(15, 7), sharex=True)
    method_label = "FK ankle z" if use_fk else "knee pitch threshold"
    fig.suptitle(f"Foot Contact Detection ({method_label}) — real_new",
                 fontsize=13, fontweight="bold")

    for ax, side in zip(axes, ["left", "right"]):
        c = SIDE_COLOR[side]
        ic_frames, to_frames, threshold = contacts_dict[side][:3]
        swing_peaks = contacts_dict[side][3] if len(contacts_dict[side]) > 3 else []

        if use_fk:
            sig = foot_z[side]
            sig_label  = f"{side} ankle z (FK)"
            thresh_label = f"contact z < {threshold:.3f} m"
            y_label = f"{side}\nankle z (m)"
        else:
            sig = data[f"pos_{KNEE[side]}"]
            sig_label  = f"{side} knee pitch"
            thresh_label = f"threshold = {threshold:.3f} rad"
            y_label = f"{side}\nknee pitch (rad)"

        ax.plot(t_rel, sig, color=c, lw=1.4, label=sig_label)

        # 支撑相色带
        for ic, to in zip(ic_frames, to_frames):
            ax.axvspan(t_rel[ic], t_rel[min(to, len(t_rel)-1)],
                       alpha=0.20, color=c)

        # swing 峰（仅膝关节法有）
        if len(swing_peaks):
            ax.scatter(t_rel[swing_peaks], sig[swing_peaks],
                       marker="^", s=55, color=c, zorder=6,
                       label=f"swing peak ({len(swing_peaks)})")

        # IC 事件
        ic_t = [t_rel[i] for i in ic_frames]
        ic_v = [sig[i]   for i in ic_frames]
        ax.scatter(ic_t, ic_v, marker="v", s=75, color="k", zorder=7,
                   label=f"Initial Contact ({len(ic_frames)} events)")

        ax.axhline(threshold, color=c, lw=1.0, ls="--", alpha=0.65,
                   label=thresh_label)
        ax.set_ylabel(y_label, fontsize=9)
        ax.legend(fontsize=8, loc="upper right", ncol=2)
        ax.grid(True, lw=0.4, alpha=0.5)

    axes[-1].set_xlabel("Time (s)", fontsize=10)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
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


# ── 图3：MuJoCo 渲染姿态网格 ──────────────────────────────────────────────────
def render_mujoco_poses(ts, data, ic_frames, side, joint_names, output_path,
                        cam_azimuth=None, view_label=""):
    try:
        import mujoco
    except ImportError:
        print("  [skip] mujoco 未安装，跳过渲染")
        return
    if not os.path.exists(XML_PATH):
        print(f"  [skip] XML 不存在: {XML_PATH}")
        return

    t0  = ts[0]
    n   = len(ic_frames)
    if n == 0:
        return

    model   = mujoco.MjModel.from_xml_path(XML_PATH)
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

    frames = []
    for ic in ic_frames:
        mujoco.mj_resetData(model, mj_data)
        for j in joint_names:
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, j)
            if jid == -1:
                continue
            col = f"pos_{j}"
            if col in data:
                mj_data.qpos[model.jnt_qposadr[jid]] = data[col][ic]
        mj_data.qpos[2] = 0.82   # 近似站立高度
        mujoco.mj_forward(model, mj_data)
        renderer.update_scene(mj_data, camera=cam)
        frames.append(renderer.render().copy())

    ncols = 5
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(ncols * 4.8, nrows * 4.0),
                             squeeze=False)
    view_tag = f" [{view_label}]" if view_label else ""
    title = f"{side.capitalize()} Foot — {n} IC Poses{view_tag}"
    fig.suptitle(title, fontsize=13, fontweight="bold")

    for idx, (frame, ic) in enumerate(zip(frames, ic_frames)):
        ax = axes[idx // ncols][idx % ncols]
        ax.imshow(frame, interpolation="lanczos")
        ax.set_title(f"#{idx + 1}  t={ts[ic] - t0:.2f}s", fontsize=10)
        ax.axis("off")

    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)

    fig.patch.set_facecolor("#111111")
    for ax_row in axes:
        for ax in ax_row:
            ax.set_facecolor("#111111")
            ax.title.set_color("white")
    fig.suptitle(title, fontsize=13, fontweight="bold", color="white")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output_path, dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  保存: {output_path}")


# ── 主逻辑 ────────────────────────────────────────────────────────────────────
def main():
    print("加载数据...")
    ts, data = load_csv(DATA_FILE)
    t0 = ts[0]
    dt = float(np.median(np.diff(ts)))
    print(f"  {len(ts)} 帧，{dt*1000:.1f}ms 间隔，总时长 {ts[-1]-t0:.1f}s")

    # ── 读取 joint_names ─────────────────────────────────────────────────────
    joint_names = list(LEG_JOINTS["left"]) + list(LEG_JOINTS["right"])
    if _HAS_MUJOCO and os.path.exists(YAML_PATH):
        try:
            with open(YAML_PATH) as f:
                joint_names = yaml.safe_load(f)["controllers"]["rl_walk_leg"]["joint_list"]
        except Exception:
            pass

    # ── FK：批量计算脚踝 z ───────────────────────────────────────────────────
    foot_z = None
    if _HAS_MUJOCO and os.path.exists(XML_PATH):
        print("\n运行 FK 计算脚踝高度...")
        foot_z = compute_foot_z_fk(ts, data, joint_names)
        if foot_z is not None:
            for s in ["left", "right"]:
                valid = ~np.isnan(foot_z[s])
                print(f"  {s} ankle z: min={foot_z[s][valid].min():.4f}  "
                      f"max={foot_z[s][valid].max():.4f} m  "
                      f"contact thresh={foot_z[s][valid].min()+FK_CONTACT_MARGIN:.4f} m")

    # ── 接地检测 ─────────────────────────────────────────────────────────────
    print("\n检测脚掌着地事件...")
    contacts = {}
    use_fk = foot_z is not None

    for side in ["left", "right"]:
        if use_fk:
            ic_frames, to_frames, thresh = detect_contacts_fk(ts, foot_z[side])
            contacts[side] = (ic_frames, to_frames, thresh)   # 无 swing_peaks
            unit = "m"
        else:
            ic_frames, to_frames, thresh, swing_peaks = detect_contacts_knee(
                ts, data[f"pos_{KNEE[side]}"])
            contacts[side] = (ic_frames, to_frames, thresh, swing_peaks)
            unit = "rad"

        durations = [(ts[min(to, len(ts)-1)] - ts[ic]) * 1000
                     for ic, to in zip(ic_frames, to_frames)]
        method_tag = "FK" if use_fk else "knee"
        print(f"  [{method_tag}] {side}: {len(ic_frames)} 次着地  "
              f"阈值={thresh:.4f} {unit}")
        print(f"    着地时刻(s): {[f'{ts[i]-t0:.2f}' for i in ic_frames]}")
        if durations:
            print(f"    支撑时长(ms): avg={np.mean(durations):.0f}  "
                  f"min={np.min(durations):.0f}  max={np.max(durations):.0f}")

    print("生成 MuJoCo 渲染姿态图...")
    views = [
        ("side",  None,   "Side"),     # None -> auto ±90° per foot
        ("front",  0.0,  "Front"),
        ("back",  180.0, "Back"),
    ]
    for side in ["left", "right"]:
        for view_name, azimuth, label in views:
            render_mujoco_poses(
                ts, data, contacts[side][0], side, joint_names,
                os.path.join(OUT_DIR, f"03_{side}_{view_name}.png"),
                cam_azimuth=azimuth,
                view_label=label,
            )

    print("\n完成！输出目录:", OUT_DIR)


if __name__ == "__main__":
    main()
