import os
import mujoco
import mujoco.viewer
import time
import csv
import yaml
import numpy as np
import cv2  # 用于录制视频
from datetime import datetime
import glob

def replay_dynamic():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # ===============================
    # 配置参数 (用户可调)
    # ===============================
    USE_TARGET = False    # True: 使用 target_*_joint (控制器原始指令) | False: 使用 pos_*_joint (真机实际轨迹)
    FIX_IN_AIR = True   # True: 将机器人固定在空中 | False: 开启地面动力学仿真
    
    RECORD_VIDEO = True # True: 开启视频录制 | False: 仅实时查看
    MAX_RECORD_TIME = 10.0 # 录制时长 (秒)，最长不要超过 CSV 记录的时长
    VIDEO_DIR = os.path.join(BASE_DIR, "video")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    VIDEO_PATH = f"{VIDEO_DIR}/replay_result_{timestamp}.mp4"
    if not os.path.exists(VIDEO_DIR):
        os.makedirs(VIDEO_DIR)
        
    VIDEO_WIDTH = 1280
    VIDEO_HEIGHT = 720
    # ===============================

    xml_path  = os.path.join(BASE_DIR, "src", "module", "sim_module", "model", "mjcf", "xyber_x1_flat.xml")
    yaml_path = os.path.join(BASE_DIR, "src", "module", "control_module", "cfg", "rl_x1.yaml")

    # 查找特定的 csv 目录下最新的 t23 日志文件
    csv_dir = os.path.join(BASE_DIR, "test_logs", "data_csv")
    search_pattern = os.path.join(csv_dir, "t23*.csv")
    t23_files = glob.glob(search_pattern)
    if t23_files:
        # 按修改时间选取最新的文件
        csv_path = max(t23_files, key=os.path.getmtime)
        print(f"已自动选择最新的 t23 日志文件: {csv_path}")
    else:
        # 兜底文件路径
        csv_path = os.path.join(csv_dir, "t23_joint_20260326_102002.csv")

    # 加载模型
    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)

    # 读取真机配置文件参数
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    walk_conf = config['controllers']['rl_walk_leg']
    csv_joint_names = walk_conf['joint_list']
    joint_names = csv_joint_names # 保持原始名称，因为 MJCF 中带有 _joint 后缀
    
    kp_map = {name: kp for name, kp in zip(joint_names, walk_conf['stiffness'])}
    kd_map = {name: kd for name, kd in zip(joint_names, walk_conf['damping'])}

    # 构建上半身关节控制参数的真机还原 fallback
    pd_zero = config['controllers']['pd_zero']
    pd_stand = config['controllers']['pd_stand']
    fallback_target_map = {}
    fallback_kp_map = {}
    fallback_kd_map = {}
    for conf in [pd_zero, pd_stand]:
        for name, init_pos, kp, kd in zip(conf['joint_list'], conf['init_state'], conf['stiffness'], conf['damping']):
            fallback_target_map[name] = init_pos
            fallback_kp_map[name] = kp
            fallback_kd_map[name] = kd

    # 读取 CSV 数据
    frames = []
    data_mode_str = "target" if USE_TARGET else "pos"
    print(f"Loading CSV data ({data_mode_str} mode, fixed_air={FIX_IN_AIR})...")
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            frame_target = {}
            frame_pos = {}
            for mj_name, csv_name in zip(joint_names, csv_joint_names):
                frame_target[mj_name] = float(row["target_" + csv_name])
                frame_pos[mj_name] = float(row["pos_" + csv_name])
            frames.append({
                "time": float(row["timestamp_ns"]) / 1e9, 
                "target": frame_target, 
                "pos": frame_pos
            })
    print(f"Loaded {len(frames)} frames.")

    # 视频录制准备
    video_writer = None
    renderer = None
    # 预先定义一个录制专用摄像头视角 (侧前方、拉远)
    record_cam = mujoco.MjvCamera()
    record_cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    record_cam.fixedcamid = -1
    record_cam.distance = 4.0   # 拉远 (原来 MuJoCo 默认约 2.0-3.0)
    record_cam.azimuth = -135    # 转向：改为 -45 度以获得更清楚的侧前方视角
    record_cam.elevation = -15  # 俯视角度
    record_cam.lookat = [0.2, 0, 0.6] # 聚焦在机器人上半身稍微偏前一点
    
    try:
        if RECORD_VIDEO:
            # 强制覆盖离屏缓冲区大小，避免 1280 > 640 错误 (无需修改 XML)
            model.vis.global_.offwidth = VIDEO_WIDTH
            model.vis.global_.offheight = VIDEO_HEIGHT
            renderer = mujoco.Renderer(model, height=VIDEO_HEIGHT, width=VIDEO_WIDTH)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(VIDEO_PATH, fourcc, 30.0, (VIDEO_WIDTH, VIDEO_HEIGHT))
            print(f"Recording enabled, saving to {VIDEO_PATH}")

        # 启动控制循环
        with mujoco.viewer.launch_passive(model, data) as viewer:
            print(f"Starting dynamic replay (using {data_mode_str} data)...")
            
            # 这里是同步 viewer 的实时视角 (可选)
            viewer.cam.distance = record_cam.distance
            viewer.cam.azimuth = record_cam.azimuth
            viewer.cam.elevation = record_cam.elevation
            viewer.cam.lookat = record_cam.lookat
            
            mujoco.mj_resetData(model, data)
            for j_name in joint_names:
                j_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, j_name)
                if j_id != -1:
                    qpos_adr = model.jnt_qposadr[j_id]
                    data.qpos[qpos_adr] = frames[0]["pos"][j_name]
            
            data.qpos[2] = 1.0 if FIX_IN_AIR else 0.7
            mujoco.mj_forward(model, data)
            
            fixed_base_qpos = data.qpos[:7].copy()
            fixed_base_qvel = np.zeros(6)
            
            actuator_names = [model.actuator(i).name for i in range(model.nu)]
            start_data_time = frames[0]["time"]
            
            frame_idx = 0
            start_wall_time = time.time()
            last_sync_time = 0
            last_video_frame_time = 0
            
            while viewer.is_running() and data.time < MAX_RECORD_TIME:
                wall_elapsed = time.time() - start_wall_time
                
                while data.time < wall_elapsed and viewer.is_running() and data.time < MAX_RECORD_TIME:
                    current_target_time = start_data_time + data.time
                    
                    while frame_idx < len(frames) and frames[frame_idx]["time"] <= current_target_time:
                        frame_idx += 1
                    
                    if frame_idx >= len(frames):
                        # 一番播放结束，退出（视频长度在此处封顶 40s 左右）
                        print("Reached end of CSV data.")
                        viewer.close()
                        break
                        
                    current_frame = frames[frame_idx - 1] if frame_idx > 0 else frames[0]

                    # ==========================
                    # PD 闭环控制
                    # ==========================
                    data_key = "target" if USE_TARGET else "pos"
                    for i, motor_name in enumerate(actuator_names):
                        # 尝试多种匹配方式，确保能找到关联的关节
                        j_name = motor_name.replace("motor_", "")
                        if "_joint" not in j_name:
                            j_name += "_joint"
                            
                        j_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, j_name)
                        csv_data_name = j_name # 在我们的配置中直接使用 j_name 即可匹配 CSV 列名
                        if j_id != -1 and csv_data_name in current_frame[data_key]:
                            setpoint = current_frame[data_key][j_name]
                            qpos_adr = model.jnt_qposadr[j_id]
                            dof_adr = model.jnt_dofadr[j_id]
                            current_pos = data.qpos[qpos_adr]
                            current_vel = data.qvel[dof_adr]
                            Kp = kp_map.get(j_name, 30.0)
                            Kd = kd_map.get(j_name, 1.0)
                            tau = Kp * (setpoint - current_pos) - Kd * current_vel
                            data.ctrl[i] = tau
                        elif j_id != -1:
                            # 按照真机的 pd_zero -> pd_stand 状态机规则还原真机上半身控制
                            qpos_adr = model.jnt_qposadr[j_id]
                            dof_adr = model.jnt_dofadr[j_id]
                            current_pos = data.qpos[qpos_adr]
                            current_vel = data.qvel[dof_adr]
                            
                            target = fallback_target_map.get(j_name, 0.0)
                            Kp = fallback_kp_map.get(j_name, 150.0)
                            Kd = fallback_kd_map.get(j_name, 5.0)
                            
                            tau = Kp * (target - current_pos) - Kd * current_vel
                            data.ctrl[i] = tau
                            
                    # 物理步进
                    mujoco.mj_step(model, data)
                    
                    if FIX_IN_AIR:
                        data.qpos[:7] = fixed_base_qpos
                        data.qvel[:6] = fixed_base_qvel

                    # 录制逻辑
                    if RECORD_VIDEO and (data.time - last_video_frame_time) >= (1.0 / 30.0):
                        renderer.update_scene(data, camera=record_cam)
                        frame = renderer.render()
                        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        video_writer.write(bgr_frame)
                        last_video_frame_time = data.time
                    
                if not viewer.is_running():
                    break

                if time.time() - last_sync_time > 1.0 / 60.0:
                    viewer.sync()
                    last_sync_time = time.time()
                    
                time.sleep(0.001)
    finally:
        # 即使关闭窗口（发生异常或手动关闭），也在此释放资源确保视频成功录制保存
        if video_writer:
            video_writer.release()
            print(f"Video saved to {VIDEO_PATH}")

if __name__ == "__main__":
    replay_dynamic()
