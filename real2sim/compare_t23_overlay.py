import os
import mujoco
import time
import csv
import yaml
import numpy as np
import cv2
from datetime import datetime
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ===============================
# 配置参数 (用户可调)
# ===============================
USE_TARGET      = False    # True: target 轨迹 | False: pos 实际轨迹
FIX_IN_AIR      = True     # True: 固定在空中 | False: 地面动力学
RECORD_VIDEO    = False     # True: 同时录制视频
MAX_RECORD_TIME = 10.0     # 播放/录制时长 (秒)
ALPHA_OVERLAY   = 0.55     # Robot-2 叠加透明度 (0=全透明, 1=不透明)
PLAYBACK_SPEED  = 0.5      # 播放速度倍率 (0.5=慢放, 1.0=正常, 2.0=快放)
CYCLE_ALIGN     = True     # True: 自动对齐两段 CSV 的步态周期起始相位
ALIGN_JOINT     = "left_knee_pitch_joint"  # 用于周期检测的参考关节（膝关节峰值清晰）
ALIGN_SKIP_SEC  = 0.5      # 跳过开头 N 秒的过渡段再开始检测

VIDEO_DIR  = os.path.join(BASE_DIR, "video")
CSV_DIR    = os.path.join(BASE_DIR, "test_logs", "data_csv")
XML_PATH   = os.path.join(BASE_DIR, "src", "module", "sim_module", "model", "mjcf", "xyber_x1_flat.xml")
YAML_PATH  = os.path.join(BASE_DIR, "src", "module", "control_module", "cfg", "rl_x1.yaml")

# VIDEO_W, VIDEO_H = 1280, 720
VIDEO_W, VIDEO_H = 1920, 1080

# Robot-2 蓝色叠加色 (BGR)
COLOR_R2 = np.array([0.25, 0.50, 1.0, 1.0], dtype=np.float64)  # RGBA for MuJoCo geom
# ===============================


def load_csv(csv_path, joint_names):
    frames = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ft, fp = {}, {}
            for name in joint_names:
                ft[name] = float(row["target_" + name])
                fp[name] = float(row["pos_"    + name])
            frames.append({
                "time":   float(row["timestamp_ns"]) / 1e9,
                "target": ft,
                "pos":    fp,
            })
    return frames


def apply_pd(model, data, actuator_names,
             current_frame, data_key,
             kp_map, kd_map,
             fallback_target, fallback_kp, fallback_kd):
    for i, motor_name in enumerate(actuator_names):
        j_name = motor_name.replace("motor_", "")
        if "_joint" not in j_name:
            j_name += "_joint"
        j_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, j_name)
        if j_id == -1:
            continue
        qpos_adr = model.jnt_qposadr[j_id]
        dof_adr  = model.jnt_dofadr[j_id]
        cur_pos  = data.qpos[qpos_adr]
        cur_vel  = data.qvel[dof_adr]
        if j_name in current_frame[data_key]:
            target = current_frame[data_key][j_name]
            Kp = kp_map.get(j_name, 30.0)
            Kd = kd_map.get(j_name, 1.0)
        else:
            target = fallback_target.get(j_name, 0.0)
            Kp = fallback_kp.get(j_name, 150.0)
            Kd = fallback_kd.get(j_name, 5.0)
        data.ctrl[i] = Kp * (target - cur_pos) - Kd * cur_vel


def find_cycle_start(frames, joint_name, data_key="pos", skip_sec=0.5, smooth_n=5):
    """在 frames 中找到 joint_name 的第一个局部极小值帧索引（步态周期起点）。"""
    t0 = frames[0]["time"]
    # 提取关节角度序列
    vals = np.array([f[data_key].get(joint_name, 0.0) for f in frames])
    # 简单滑动平均平滑
    if smooth_n > 1:
        kernel = np.ones(smooth_n) / smooth_n
        vals = np.convolve(vals, kernel, mode='same')
    # 跳过开头过渡段
    skip_idx = next((i for i, f in enumerate(frames) if f["time"] - t0 >= skip_sec), 0)
    # 找第一个局部极小值（膝关节最伸直 = 角度最小）
    for i in range(skip_idx + 1, len(frames) - 1):
        if vals[i] < vals[i - 1] and vals[i] < vals[i + 1]:
            return i
    return skip_idx  # 找不到时回退到 skip 起点


def put_label(img, text, pos, color_bgr):
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0),     3, cv2.LINE_AA)
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.62, color_bgr,     2, cv2.LINE_AA)


def compare_t23():
    # ---- 查找最新两个 t23 文件 ----
    def _fname_ts(p):
        base = os.path.basename(p)
        parts = base.replace(".csv", "").split("_")
        try:
            return datetime.strptime(parts[-2] + parts[-1], "%Y%m%d%H%M%S")
        except Exception:
            return datetime.fromtimestamp(os.path.getmtime(p))
    t23_files = sorted(glob.glob(os.path.join(CSV_DIR, "t23*.csv")), key=_fname_ts)
    if len(t23_files) < 2:
        print(f"[ERROR] 需要至少 2 个 t23 CSV 文件，当前仅找到 {len(t23_files)} 个")
        return
    csv_path1 = t23_files[-2]   # 次新（对比基准）
    csv_path2 = t23_files[-1]   # 最新
    print(f"[比较对象]")
    print(f"  Robot-1 (灰色, 基准): {csv_path1}")
    print(f"  Robot-2 (蓝色, 最新): {csv_path2}")

    # ---- 读取 YAML ----
    with open(YAML_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    walk_conf  = config['controllers']['rl_walk_leg']
    joint_names = walk_conf['joint_list']
    kp_map = {n: kp for n, kp in zip(joint_names, walk_conf['stiffness'])}
    kd_map = {n: kd for n, kd in zip(joint_names, walk_conf['damping'])}

    fallback_target, fallback_kp, fallback_kd = {}, {}, {}
    for conf in [config['controllers']['pd_zero'], config['controllers']['pd_stand']]:
        for name, ip, kp, kd in zip(conf['joint_list'], conf['init_state'],
                                    conf['stiffness'], conf['damping']):
            fallback_target[name] = ip
            fallback_kp[name]     = kp
            fallback_kd[name]     = kd

    # ---- 加载 CSV ----
    frames1 = load_csv(csv_path1, joint_names)
    frames2 = load_csv(csv_path2, joint_names)
    n1, n2  = len(frames1), len(frames2)
    n_min   = min(n1, n2)
    print(f"  CSV1: {n1} 帧  |  CSV2: {n2} 帧  |  播放取较短: {n_min} 帧")

    # ---- 加载两份 MuJoCo 模型 ----
    model1 = mujoco.MjModel.from_xml_path(XML_PATH)
    data1  = mujoco.MjData(model1)
    model2 = mujoco.MjModel.from_xml_path(XML_PATH)
    data2  = mujoco.MjData(model2)

    # Robot-2: 全身几何体着蓝色（视觉区分）
    for i in range(model2.ngeom):
        model2.geom_rgba[i] = COLOR_R2

    # ---- 设置渲染器（两个共享同一摄像头参数）----
    for m in [model1, model2]:
        m.vis.global_.offwidth  = VIDEO_W
        m.vis.global_.offheight = VIDEO_H

    renderer1 = mujoco.Renderer(model1, height=VIDEO_H, width=VIDEO_W)
    renderer2 = mujoco.Renderer(model2, height=VIDEO_H, width=VIDEO_W)

    cam = mujoco.MjvCamera()
    cam.type       = mujoco.mjtCamera.mjCAMERA_FREE
    cam.fixedcamid = -1
    cam.distance   = 3.2
    cam.azimuth    = -120.0
    cam.elevation  = -18.0
    cam.lookat     = np.array([0.0, 0.0, 0.65])

    # ---- 初始化仿真状态 ----
    def reset(model, data, frames):
        mujoco.mj_resetData(model, data)
        for j in joint_names:
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, j)
            if jid != -1:
                data.qpos[model.jnt_qposadr[jid]] = frames[0]["pos"][j]
        data.qpos[2] = 1.0 if FIX_IN_AIR else 0.7
        mujoco.mj_forward(model, data)
        return data.qpos[:7].copy()

    fixed_qpos1 = reset(model1, data1, frames1)
    fixed_qpos2 = reset(model2, data2, frames2)   # 上半身重合：与 robot1 同位置
    fixed_qpos2[:3] = fixed_qpos1[:3]             # 确保 xyz 完全一致

    act1 = [model1.actuator(i).name for i in range(model1.nu)]
    act2 = [model2.actuator(i).name for i in range(model2.nu)]

    data_key = "target" if USE_TARGET else "pos"

    # ---- 视频录制准备 ----
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(VIDEO_DIR, f"compare_t23_{timestamp}.mp4")
    os.makedirs(VIDEO_DIR, exist_ok=True)
    video_writer = None
    if RECORD_VIDEO:
        fourcc       = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(video_path, fourcc, 30.0, (VIDEO_W, VIDEO_H))
        print(f"  录制输出: {video_path}")

    # ---- 周期对齐 ----
    if CYCLE_ALIGN:
        data_key_align = "target" if USE_TARGET else "pos"
        offset1 = find_cycle_start(frames1, ALIGN_JOINT, data_key_align, ALIGN_SKIP_SEC)
        offset2 = find_cycle_start(frames2, ALIGN_JOINT, data_key_align, ALIGN_SKIP_SEC)
        phase1  = frames1[offset1]["time"] - frames1[0]["time"]
        phase2  = frames2[offset2]["time"] - frames2[0]["time"]
        print(f"[Cycle align] CSV1 start @ frame {offset1} (t+{phase1:.3f}s)")
        print(f"[Cycle align] CSV2 start @ frame {offset2} (t+{phase2:.3f}s)")
    else:
        offset1 = offset2 = 0

    # ---- 主循环 ----
    fi1 = offset1
    fi2 = offset2
    start_t1   = frames1[offset1]["time"]
    start_t2   = frames2[offset2]["time"]
    start_wall = time.time()
    last_video_t   = -1.0
    last_display_t = -1.0
    sim_time = 0.0

    label1 = os.path.basename(csv_path1)
    label2 = os.path.basename(csv_path2)

    print("[提示] 按 ESC 或 Q 退出；空格暂停/继续")
    cv2.namedWindow("T23 Compare | Gray=Baseline  Blue=Latest", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("T23 Compare | Gray=Baseline  Blue=Latest", VIDEO_W, VIDEO_H)

    paused     = False
    step_dt    = model1.opt.timestep   # 通常 0.001 s

    try:
        while sim_time < MAX_RECORD_TIME:
            if not paused:
                wall_elapsed = (time.time() - start_wall) * PLAYBACK_SPEED

                # 仿真推进到与真实时间同步
                while sim_time < wall_elapsed and sim_time < MAX_RECORD_TIME:
                    cur_t = sim_time

                    # 推进帧索引
                    while fi1 < n1 - 1 and frames1[fi1]["time"] <= start_t1 + cur_t:
                        fi1 += 1
                    while fi2 < n2 - 1 and frames2[fi2]["time"] <= start_t2 + cur_t:
                        fi2 += 1

                    if fi1 - offset1 >= n_min - max(offset1, offset2) or fi2 - offset2 >= n_min - max(offset1, offset2):
                        print("[完成] CSV 数据已全部播放")
                        sim_time = MAX_RECORD_TIME
                        break

                    cf1 = frames1[fi1]
                    cf2 = frames2[fi2]

                    # 上半身重合：两个仿真 base 固定到同一位置
                    # 下半身：各自按各自 CSV 运行
                    apply_pd(model1, data1, act1, cf1, data_key,
                             kp_map, kd_map, fallback_target, fallback_kp, fallback_kd)
                    apply_pd(model2, data2, act2, cf2, data_key,
                             kp_map, kd_map, fallback_target, fallback_kp, fallback_kd)

                    mujoco.mj_step(model1, data1)
                    mujoco.mj_step(model2, data2)

                    if FIX_IN_AIR:
                        data1.qpos[:7] = fixed_qpos1
                        data1.qvel[:6] = np.zeros(6)
                        data2.qpos[:7] = fixed_qpos2   # 上半身完全重合
                        data2.qvel[:6] = np.zeros(6)

                    sim_time += step_dt

            # ---- 渲染与显示 (30 fps) ----
            if sim_time - last_display_t >= 1.0 / 30.0:
                renderer1.update_scene(data1, camera=cam)
                frame1 = renderer1.render().copy()  # RGB

                renderer2.update_scene(data2, camera=cam)
                frame2 = renderer2.render().copy()  # RGB

                # Alpha 叠加：Robot-1 正常 + Robot-2 蓝色半透明
                blended = cv2.addWeighted(frame1, 1.0, frame2, ALPHA_OVERLAY, 0)
                bgr     = cv2.cvtColor(blended, cv2.COLOR_RGB2BGR)

                # ---- 图例 ----
                put_label(bgr, f"[Gray] {label1}", (20, 40),  (180, 180, 180))
                put_label(bgr, f"[Blue] {label2}", (20, 75),  (255, 140,   0))
                put_label(bgr, f"t={sim_time:5.2f}s  mode={'target' if USE_TARGET else 'pos'}  "
                               f"{'[PAUSED]' if paused else ''}",
                          (20, VIDEO_H - 20), (200, 200, 200))
                align_str = f"Cycle aligned [{ALIGN_JOINT}]" if CYCLE_ALIGN else "No cycle align"
                put_label(bgr, f"Upper aligned | Lower body compare | {align_str}", (VIDEO_W // 2 - 320, 40), (100, 255, 100))

                cv2.imshow("T23 Compare | Gray=Baseline  Blue=Latest", bgr)

                if RECORD_VIDEO and sim_time - last_video_t >= 1.0 / 30.0:
                    video_writer.write(bgr)
                    last_video_t = sim_time

                last_display_t = sim_time

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):   # ESC / Q
                print("[退出] 用户中断")
                break
            if key == ord(' '):                    # 空格：暂停/继续
                paused = not paused
                if not paused:
                    start_wall = time.time() - sim_time

            if not paused:
                time.sleep(max(0.0, step_dt - 0.0005))

    finally:
        cv2.destroyAllWindows()
        if video_writer:
            video_writer.release()
            print(f"[保存] 视频已写入: {video_path}")


if __name__ == "__main__":
    compare_t23()
