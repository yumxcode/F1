import csv
import glob
import math
import os
from dataclasses import dataclass

import numpy as np

try:
    import mujoco
except ImportError as exc:  # pragma: no cover
    raise SystemExit("mujoco is required for Round 3 analysis") from exc


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(BASE_DIR, "test_logs", "data_csv")
OUT_DIR = os.path.join(SCRIPT_DIR, "table", "round3")
XML_PATH = os.path.join(
    BASE_DIR,
    "src",
    "module",
    "sim_module",
    "model",
    "mjcf",
    "robot",
    "xyber_x1",
    "xyber_x1_serial.xml",
)

os.makedirs(OUT_DIR, exist_ok=True)

LEFT_JOINTS = [
    "left_hip_pitch_joint",
    "left_hip_roll_joint",
    "left_hip_yaw_joint",
    "left_knee_pitch_joint",
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
]
RIGHT_JOINTS = [
    "right_hip_pitch_joint",
    "right_hip_roll_joint",
    "right_hip_yaw_joint",
    "right_knee_pitch_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
]
FOOT_BODIES = {
    "left": "link_left_ankle_roll",
    "right": "link_right_ankle_roll",
}
BASE_Z = 0.82
SWING_WINDOW_SEC = 0.35
LANDING_WINDOW_SEC = 0.10
SWING_END_BEFORE_TOUCHDOWN_SEC = 0.08
CLEARANCE_MIN_METERS = 0.04
CONTACT_PRE_MARGIN_METERS = 0.01
TRACKING_ERR_RAD = 0.03
HIP_KNEE_TRACKING_ERR_RAD = 0.08


@dataclass
class TouchdownEvent:
    side: str
    index: int
    timestamp_sec: float


def latest_round3_diag() -> str:
    matches = sorted(glob.glob(os.path.join(LOG_DIR, "t26_round3_diag_*.csv")))
    if not matches:
        raise FileNotFoundError("No t26_round3_diag_*.csv files found")
    return matches[-1]


def load_csv(path: str):
    rows = []
    with open(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {}
            for key, value in raw.items():
                row[key] = float(value) if key != "timestamp_ns" else int(value)
            row["time_sec"] = row["timestamp_ns"] / 1e9
            rows.append(row)
    if not rows:
        raise RuntimeError(f"No rows loaded from {path}")
    return rows


def euler_xyz_to_quat(roll: float, pitch: float, yaw: float):
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    return np.array(
        [
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        ]
    )


def matrix_to_roll_pitch_yaw(rot: np.ndarray):
    sy = math.sqrt(rot[0, 0] * rot[0, 0] + rot[1, 0] * rot[1, 0])
    singular = sy < 1e-6
    if not singular:
        roll = math.atan2(rot[2, 1], rot[2, 2])
        pitch = math.atan2(-rot[2, 0], sy)
        yaw = math.atan2(rot[1, 0], rot[0, 0])
    else:
        roll = math.atan2(-rot[1, 2], rot[1, 1])
        pitch = math.atan2(-rot[2, 0], sy)
        yaw = 0.0
    return roll, pitch, yaw


def phase_fraction(row) -> float:
    return (math.atan2(row["phase_sin"], row["phase_cos"]) / (2.0 * math.pi)) % 1.0


def attach_fk_metrics(rows):
    model = mujoco.MjModel.from_xml_path(XML_PATH)
    data = mujoco.MjData(model)
    body_ids = {
        side: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        for side, body_name in FOOT_BODIES.items()
    }
    joint_ids = {}
    for joint_name in LEFT_JOINTS + RIGHT_JOINTS:
        joint_ids[joint_name] = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)

    for row in rows:
        mujoco.mj_resetData(model, data)
        data.qpos[2] = BASE_Z
        quat = euler_xyz_to_quat(row["base_euler_x"], row["base_euler_y"], row["base_euler_z"])
        data.qpos[3:7] = quat
        for joint_name, joint_id in joint_ids.items():
            qpos_adr = model.jnt_qposadr[joint_id]
            data.qpos[qpos_adr] = row[f"pos_{joint_name}"]
        mujoco.mj_forward(model, data)

        for side, body_id in body_ids.items():
            row[f"{side}_foot_x"] = float(data.xpos[body_id, 0])
            row[f"{side}_foot_z"] = float(data.xpos[body_id, 2])
            rot = np.array(data.xmat[body_id]).reshape(3, 3)
            roll, pitch, _ = matrix_to_roll_pitch_yaw(rot)
            row[f"{side}_sole_roll"] = roll
            row[f"{side}_sole_pitch"] = pitch
            row[f"{side}_sole_normal_z"] = float(rot[2, 2])

        row["left_foot_flat_error"] = math.sqrt(
            row["left_sole_pitch"] ** 2 + row["left_sole_roll"] ** 2
        )
        row["right_foot_flat_error"] = math.sqrt(
            row["right_sole_pitch"] ** 2 + row["right_sole_roll"] ** 2
        )


def detect_touchdowns(rows):
    events = []
    prev_left = 0
    prev_right = 0
    for idx, row in enumerate(rows):
        left = int(row["left_contact"])
        right = int(row["right_contact"])
        if left == 1 and prev_left == 0:
            events.append(TouchdownEvent("left", idx, row["time_sec"]))
        if right == 1 and prev_right == 0:
            events.append(TouchdownEvent("right", idx, row["time_sec"]))
        prev_left = left
        prev_right = right
    return events


def find_index_at_or_before(rows, target_time):
    for idx in range(len(rows) - 1, -1, -1):
        if rows[idx]["time_sec"] <= target_time:
            return idx
    return 0


def summarize_event(rows, event: TouchdownEvent):
    swing_side = event.side
    stance_side = "right" if swing_side == "left" else "left"
    touch_idx = event.index
    touch_row = rows[touch_idx]
    t_touch = touch_row["time_sec"]

    swing_start = t_touch - SWING_WINDOW_SEC
    swing_end = t_touch - SWING_END_BEFORE_TOUCHDOWN_SEC
    win_start_idx = find_index_at_or_before(rows, swing_start)
    win_end_idx = find_index_at_or_before(rows, swing_end)
    pre50_idx = find_index_at_or_before(rows, t_touch - 0.05)
    pre20_idx = find_index_at_or_before(rows, t_touch - 0.02)
    pre100_idx = find_index_at_or_before(rows, t_touch - 0.10)

    swing_rows = rows[win_start_idx : max(win_end_idx + 1, win_start_idx + 1)]
    max_clearance = max(
        row[f"{swing_side}_foot_z"] - row[f"{stance_side}_foot_z"] for row in swing_rows
    )
    peak_row = max(
        swing_rows,
        key=lambda row: row[f"{swing_side}_foot_z"] - row[f"{stance_side}_foot_z"],
    )
    pre50_row = rows[pre50_idx]
    pre20_row = rows[pre20_idx]
    pre100_row = rows[pre100_idx]

    hip_joint = f"{swing_side}_hip_pitch_joint"
    knee_joint = f"{swing_side}_knee_pitch_joint"
    ankle_pitch_joint = f"{swing_side}_ankle_pitch_joint"
    ankle_roll_joint = f"{swing_side}_ankle_roll_joint"

    knee_peak_row = max(swing_rows, key=lambda row: row[f"pos_{knee_joint}"])
    knee_peak_to_touchdown = t_touch - knee_peak_row["time_sec"]

    hip_err_pre50 = pre50_row[f"pos_des_raw_{hip_joint}"] - pre50_row[f"pos_{hip_joint}"]
    knee_err_pre50 = pre50_row[f"pos_des_raw_{knee_joint}"] - pre50_row[f"pos_{knee_joint}"]
    ankle_pitch_err_touch = touch_row[f"pos_des_raw_{ankle_pitch_joint}"] - touch_row[f"pos_{ankle_pitch_joint}"]
    ankle_roll_err_touch = touch_row[f"pos_des_raw_{ankle_roll_joint}"] - touch_row[f"pos_{ankle_roll_joint}"]

    clearance_pre50 = pre50_row[f"{swing_side}_foot_z"] - pre50_row[f"{stance_side}_foot_z"]
    flat_error_touch = touch_row[f"{swing_side}_foot_flat_error"]

    if max_clearance < CLEARANCE_MIN_METERS or clearance_pre50 < CONTACT_PRE_MARGIN_METERS:
        primary_flag = "foot_clearance_deficit"
    elif abs(hip_err_pre50) > HIP_KNEE_TRACKING_ERR_RAD or abs(knee_err_pre50) > HIP_KNEE_TRACKING_ERR_RAD:
        primary_flag = "hip_knee_tracking_lag"
    elif knee_peak_to_touchdown > 0.20:
        primary_flag = "early_knee_extension"
    elif flat_error_touch > 0.05 and (
        abs(ankle_pitch_err_touch) > TRACKING_ERR_RAD or abs(ankle_roll_err_touch) > TRACKING_ERR_RAD
    ):
        primary_flag = "tracking_lag"
    elif flat_error_touch > 0.05:
        primary_flag = "command_not_flat"
    else:
        primary_flag = "no_clear_blocker_detected"

    return {
        "side": swing_side,
        "touchdown_time_sec": t_touch,
        "touchdown_index": touch_idx,
        "primary_flag": primary_flag,
        "max_swing_clearance_m": max_clearance,
        "clearance_at_minus_50ms_m": clearance_pre50,
        "clearance_peak_phase": phase_fraction(peak_row),
        "foot_flat_error_touch_rad": flat_error_touch,
        "sole_pitch_touch_rad": touch_row[f"{swing_side}_sole_pitch"],
        "sole_roll_touch_rad": touch_row[f"{swing_side}_sole_roll"],
        "hip_err_minus_50ms_rad": hip_err_pre50,
        "knee_err_minus_50ms_rad": knee_err_pre50,
        "ankle_pitch_err_touch_rad": ankle_pitch_err_touch,
        "ankle_roll_err_touch_rad": ankle_roll_err_touch,
        "knee_peak_to_touchdown_sec": knee_peak_to_touchdown,
        "cmd_linear_x": touch_row["cmd_linear_x"],
        "cmd_linear_y": touch_row["cmd_linear_y"],
        "cmd_angular_z": touch_row["cmd_angular_z"],
        "clearance_at_minus_100ms_m": pre100_row[f"{swing_side}_foot_z"] - pre100_row[f"{stance_side}_foot_z"],
        "clearance_at_minus_20ms_m": pre20_row[f"{swing_side}_foot_z"] - pre20_row[f"{stance_side}_foot_z"],
    }


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary_md(path, diag_path, summaries):
    mean_clearance = np.mean([row["max_swing_clearance_m"] for row in summaries]) if summaries else float("nan")
    mean_flat_error = np.mean([row["foot_flat_error_touch_rad"] for row in summaries]) if summaries else float("nan")
    with open(path, "w") as handle:
        handle.write("# Round 3 Landing Window Summary\n\n")
        handle.write(f"- Source log: `{diag_path}`\n")
        handle.write(f"- Touchdowns analyzed: `{len(summaries)}`\n")
        handle.write(f"- Mean max swing clearance: `{mean_clearance:.4f} m`\n")
        handle.write(f"- Mean touchdown foot-flat error: `{mean_flat_error:.4f} rad`\n\n")
        handle.write("| side | touchdown_time_sec | primary_flag | max_swing_clearance_m | clearance_at_minus_50ms_m | foot_flat_error_touch_rad |\n")
        handle.write("|---|---:|---|---:|---:|---:|\n")
        for row in summaries:
            handle.write(
                f"| {row['side']} | {row['touchdown_time_sec']:.3f} | {row['primary_flag']} | "
                f"{row['max_swing_clearance_m']:.4f} | {row['clearance_at_minus_50ms_m']:.4f} | "
                f"{row['foot_flat_error_touch_rad']:.4f} |\n"
            )


def main():
    diag_path = latest_round3_diag()
    rows = load_csv(diag_path)
    attach_fk_metrics(rows)
    events = detect_touchdowns(rows)
    summaries = [summarize_event(rows, event) for event in events]

    base_name = os.path.splitext(os.path.basename(diag_path))[0]
    per_frame_path = os.path.join(OUT_DIR, f"{base_name}_fk_metrics.csv")
    touchdown_path = os.path.join(OUT_DIR, f"{base_name}_touchdown_summary.csv")
    summary_md_path = os.path.join(OUT_DIR, f"{base_name}_summary.md")

    write_csv(per_frame_path, rows)
    write_csv(touchdown_path, summaries)
    write_summary_md(summary_md_path, diag_path, summaries)

    print(f"Round 3 per-frame metrics: {per_frame_path}")
    print(f"Round 3 touchdown summary: {touchdown_path}")
    print(f"Round 3 markdown summary: {summary_md_path}")


if __name__ == "__main__":
    main()
