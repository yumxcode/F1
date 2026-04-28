import csv
import glob
import math
import os
import tempfile
from dataclasses import dataclass

import numpy as np

try:
    import mujoco
except ImportError as exc:  # pragma: no cover
    raise SystemExit("mujoco is required for Round 3 analysis") from exc


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_repo_root(start_dir: str) -> str:
    cursor = start_dir
    while True:
        if os.path.isdir(os.path.join(cursor, "real2sim")) and os.path.isdir(os.path.join(cursor, "src")):
            return cursor
        parent = os.path.dirname(cursor)
        if parent == cursor:
            raise RuntimeError("Failed to locate repository root from plan script path")
        cursor = parent


BASE_DIR = find_repo_root(SCRIPT_DIR)
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
MESH_DIR = os.path.join(
    BASE_DIR,
    "src",
    "module",
    "sim_module",
    "model",
    "meshes",
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
# FK currently uses a fixed floating-base height. Absolute foot_z is therefore not
# treated as physical truth; touchdown logic only relies on left/right relative height,
# foot velocities, and foot attitude.
BASE_Z = 0.82
SWING_WINDOW_SEC = 0.35
LANDING_WINDOW_SEC = 0.10
SWING_END_BEFORE_TOUCHDOWN_SEC = 0.08
CLEARANCE_MIN_METERS = 0.04
CONTACT_PRE_MARGIN_METERS = 0.01
TRACKING_ERR_RAD = 0.03
HIP_KNEE_TRACKING_ERR_RAD = 0.08
TOUCHDOWN_SEARCH_WINDOW_SEC = 0.04
TOUCHDOWN_MAX_REL_HEIGHT_M = 0.03
TOUCHDOWN_DESCENT_VEL_MPS = 0.02
TOUCHDOWN_SETTLE_VEL_MPS = 0.05
TOUCHDOWN_CONTACT_HOLD_FRAMES = 3
GEOM_TOUCHDOWN_REFRACTORY_SEC = 0.12
FIRST_CONTACT_CONTACT_HOLD_FRAMES = 2
STABLE_TOUCHDOWN_SEARCH_SEC = 0.08
STABLE_TOUCHDOWN_HOLD_FRAMES = 4
STABLE_TOUCHDOWN_MAX_REL_HEIGHT_M = 0.025
STABLE_TOUCHDOWN_MAX_VEL_MPS = 0.08
# Real touchdown usually still carries noticeable residual descent velocity. Keep this
# threshold loose enough that geometry scoring remains discriminative on hardware logs.
STABLE_TOUCHDOWN_MAX_DESCENT_MPS = 0.05
STABLE_TOUCHDOWN_MAX_FLAT_ERR_RATE = 1.2
STABLE_TOUCHDOWN_MAX_FOOT_X_RATE = 0.20
TOUCHDOWN_DEDUP_SEC = 0.08
SEVERE_FOOT_FLAT_ERROR_RAD = 1.0


@dataclass
class TouchdownEvent:
    side: str
    index: int
    timestamp_sec: float
    source: str
    first_contact_index: int
    first_contact_time_sec: float


def latest_round3_diag() -> str:
    patterns = [
        "t27_tracking_lag_b1_diag_*.csv",
        "t26_round3_diag_*.csv",
    ]
    matches = []
    for pattern in patterns:
        matches.extend(glob.glob(os.path.join(LOG_DIR, pattern)))
    matches = sorted(set(matches))
    if not matches:
        raise FileNotFoundError("No Round 3 diagnostic csv files found")
    return matches[-1]


def parse_csv_scalar(key: str, value):
    if key is None:
        return None
    if value is None or value == "":
        return math.nan if key != "timestamp_ns" else None
    if key == "timestamp_ns":
        return int(value)
    return float(value)


def load_csv(path: str):
    rows = []
    with open(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {}
            for key, value in raw.items():
                parsed = parse_csv_scalar(key, value)
                if key is None:
                    continue
                row[key] = parsed
            if row.get("timestamp_ns") is None:
                continue
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


def resolved_analysis_xml_path():
    with open(XML_PATH, "r", encoding="utf-8") as handle:
        xml_text = handle.read()
    meshdir_attr = 'meshdir="../meshes"'
    corrected_meshdir = f'meshdir="{MESH_DIR}"'
    if meshdir_attr in xml_text:
        xml_text = xml_text.replace(meshdir_attr, corrected_meshdir, 1)
    temp_handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix="_round3_xyber_x1.xml",
        delete=False,
        encoding="utf-8",
    )
    with temp_handle:
        temp_handle.write(xml_text)
    return temp_handle.name


def attach_fk_metrics(rows):
    analysis_xml_path = resolved_analysis_xml_path()
    model = mujoco.MjModel.from_xml_path(analysis_xml_path)
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

    for side in ("left", "right"):
        prev_z = rows[0][f"{side}_foot_z"]
        prev_x = rows[0][f"{side}_foot_x"]
        prev_t = rows[0]["time_sec"]
        rows[0][f"{side}_foot_vz"] = 0.0
        rows[0][f"{side}_foot_vx"] = 0.0
        rows[0][f"{side}_rel_height"] = rows[0][f"{side}_foot_z"] - rows[0][f"{'right' if side == 'left' else 'left'}_foot_z"]
        rows[0][f"{side}_flat_error_rate"] = 0.0
        for idx in range(1, len(rows)):
            prev_flat_err = rows[idx - 1][f"{side}_foot_flat_error"]
            curr_flat_err = rows[idx][f"{side}_foot_flat_error"]
            curr_x = rows[idx][f"{side}_foot_x"]
            curr_z = rows[idx][f"{side}_foot_z"]
            curr_t = rows[idx]["time_sec"]
            dt = max(curr_t - prev_t, 1e-6)
            rows[idx][f"{side}_foot_vx"] = (curr_x - prev_x) / dt
            rows[idx][f"{side}_foot_vz"] = (curr_z - prev_z) / dt
            rows[idx][f"{side}_rel_height"] = rows[idx][f"{side}_foot_z"] - rows[idx][f"{'right' if side == 'left' else 'left'}_foot_z"]
            rows[idx][f"{side}_flat_error_rate"] = (curr_flat_err - prev_flat_err) / dt
            prev_x = curr_x
            prev_z = curr_z
            prev_t = curr_t


def has_pre_swing_clearance(rows, idx, side):
    start_idx = find_index_at_or_before(rows, rows[idx]["time_sec"] - SWING_WINDOW_SEC)
    max_rel_height = max(row[f"{side}_rel_height"] for row in rows[start_idx : idx + 1])
    return max_rel_height >= CLEARANCE_MIN_METERS


def holds_contact(rows, idx, side):
    contact_key = f"{side}_contact"
    end_idx = min(len(rows), idx + TOUCHDOWN_CONTACT_HOLD_FRAMES)
    return all(int(rows[ii][contact_key]) == 1 for ii in range(idx, end_idx))


def holds_contact_for_frames(rows, idx, side, hold_frames):
    contact_key = f"{side}_contact"
    end_idx = min(len(rows), idx + hold_frames)
    if end_idx <= idx:
        return False
    return all(int(rows[ii][contact_key]) == 1 for ii in range(idx, end_idx))


def touchdown_geom_ok(rows, idx, side):
    row = rows[idx]
    prev_vz = rows[max(idx - 1, 0)][f"{side}_foot_vz"]
    curr_vz = row[f"{side}_foot_vz"]
    rel_height = row[f"{side}_rel_height"]
    return (
        rel_height <= TOUCHDOWN_MAX_REL_HEIGHT_M
        and prev_vz <= -TOUCHDOWN_DESCENT_VEL_MPS
        and abs(curr_vz) <= TOUCHDOWN_SETTLE_VEL_MPS
        and has_pre_swing_clearance(rows, idx, side)
    )


def first_contact_geom_ok(rows, idx, side):
    row = rows[idx]
    prev_vz = rows[max(idx - 1, 0)][f"{side}_foot_vz"]
    rel_height = row[f"{side}_rel_height"]
    return (
        rel_height <= TOUCHDOWN_MAX_REL_HEIGHT_M
        and prev_vz <= -TOUCHDOWN_DESCENT_VEL_MPS
        and has_pre_swing_clearance(rows, idx, side)
    )


def stable_touchdown_geom_ok(rows, idx, side):
    row = rows[idx]
    rel_height = row[f"{side}_rel_height"]
    vz = row[f"{side}_foot_vz"]
    vx = row[f"{side}_foot_vx"]
    flat_err_rate = row[f"{side}_flat_error_rate"]
    return (
        rel_height <= STABLE_TOUCHDOWN_MAX_REL_HEIGHT_M
        and abs(vz) <= STABLE_TOUCHDOWN_MAX_VEL_MPS
        and vz >= -STABLE_TOUCHDOWN_MAX_DESCENT_MPS
        and abs(vx) <= STABLE_TOUCHDOWN_MAX_FOOT_X_RATE
        and abs(flat_err_rate) <= STABLE_TOUCHDOWN_MAX_FLAT_ERR_RATE
    )


def refine_touchdown_index(rows, candidate_idx, side):
    candidate_time = rows[candidate_idx]["time_sec"]
    win_start_idx = find_index_at_or_before(rows, candidate_time - TOUCHDOWN_SEARCH_WINDOW_SEC)
    win_end_time = candidate_time + TOUCHDOWN_SEARCH_WINDOW_SEC
    win_end_idx = candidate_idx
    while win_end_idx + 1 < len(rows) and rows[win_end_idx + 1]["time_sec"] <= win_end_time:
        win_end_idx += 1

    best_idx = candidate_idx
    best_score = None
    for idx in range(win_start_idx, win_end_idx + 1):
        row = rows[idx]
        contact = int(row[f"{side}_contact"])
        contact_hold = holds_contact(rows, idx, side)
        geom_ok = touchdown_geom_ok(rows, idx, side)
        rel_height = row[f"{side}_rel_height"]
        curr_abs_vz = abs(row[f"{side}_foot_vz"])
        score = (
            0 if geom_ok else 1,
            0 if contact and contact_hold else 1,
            abs(rel_height),
            curr_abs_vz,
            abs(idx - candidate_idx),
        )
        if best_score is None or score < best_score:
            best_score = score
            best_idx = idx
    return best_idx


def find_first_contact_index(rows, candidate_idx, side):
    candidate_time = rows[candidate_idx]["time_sec"]
    win_start_idx = find_index_at_or_before(rows, candidate_time - TOUCHDOWN_SEARCH_WINDOW_SEC)
    earliest_geom_and_hold = None
    earliest_geom_and_contact = None
    earliest_geom_only = None
    for idx in range(win_start_idx, candidate_idx + 1):
        row = rows[idx]
        contact = int(row[f"{side}_contact"])
        geom_ok = first_contact_geom_ok(rows, idx, side)
        if not geom_ok:
            continue
        if earliest_geom_only is None:
            earliest_geom_only = idx
        if holds_contact_for_frames(rows, idx, side, FIRST_CONTACT_CONTACT_HOLD_FRAMES):
            earliest_geom_and_hold = idx
            break
        if contact == 1 and earliest_geom_and_contact is None:
            earliest_geom_and_contact = idx
    if earliest_geom_and_hold is not None:
        return earliest_geom_and_hold
    if earliest_geom_and_contact is not None:
        return earliest_geom_and_contact
    if earliest_geom_only is not None:
        return earliest_geom_only
    return candidate_idx


def find_stable_touchdown_index(rows, first_contact_idx, candidate_idx, side):
    start_time = rows[first_contact_idx]["time_sec"]
    end_time = rows[candidate_idx]["time_sec"] + STABLE_TOUCHDOWN_SEARCH_SEC
    start_idx = first_contact_idx
    end_idx = candidate_idx
    while end_idx + 1 < len(rows) and rows[end_idx + 1]["time_sec"] <= end_time:
        end_idx += 1

    best_idx = candidate_idx
    best_score = None
    for idx in range(start_idx, end_idx + 1):
        row = rows[idx]
        geom_ok = stable_touchdown_geom_ok(rows, idx, side)
        contact_hold = holds_contact_for_frames(rows, idx, side, STABLE_TOUCHDOWN_HOLD_FRAMES)
        rel_height = abs(row[f"{side}_rel_height"])
        vz = abs(row[f"{side}_foot_vz"])
        flat_rate = abs(row[f"{side}_flat_error_rate"])
        score = (
            0 if geom_ok else 1,
            0 if contact_hold else 1,
            rel_height,
            vz,
            flat_rate,
            idx,
        )
        if best_score is None or score < best_score:
            best_score = score
            best_idx = idx
        if geom_ok and contact_hold:
            return idx
    return best_idx


def detect_touchdowns_from_contact(rows, side):
    contact_key = f"{side}_contact"
    prev_contact = 0
    events = []
    for idx, row in enumerate(rows):
        contact = int(row[contact_key])
        if contact == 1 and prev_contact == 0:
            refined_idx = refine_touchdown_index(rows, idx, side)
            first_contact_idx = find_first_contact_index(rows, refined_idx, side)
            stable_idx = find_stable_touchdown_index(rows, first_contact_idx, refined_idx, side)
            if holds_contact(rows, stable_idx, side) and has_pre_swing_clearance(rows, stable_idx, side):
                events.append(
                    TouchdownEvent(
                        side,
                        stable_idx,
                        rows[stable_idx]["time_sec"],
                        "contact_refined",
                        first_contact_idx,
                        rows[first_contact_idx]["time_sec"],
                    )
                )
        prev_contact = contact
    return events


def detect_touchdowns_from_geometry(rows, side):
    events = []
    last_event_time = -1e9
    for idx in range(1, len(rows)):
        if rows[idx]["time_sec"] - last_event_time < GEOM_TOUCHDOWN_REFRACTORY_SEC:
            continue
        if not first_contact_geom_ok(rows, idx, side):
            continue
        prev_vz = rows[idx - 1][f"{side}_foot_vz"]
        curr_vz = rows[idx][f"{side}_foot_vz"]
        if prev_vz <= -TOUCHDOWN_DESCENT_VEL_MPS and curr_vz >= -TOUCHDOWN_SETTLE_VEL_MPS:
            stable_idx = find_stable_touchdown_index(rows, idx, idx, side)
            events.append(
                TouchdownEvent(
                    side,
                    stable_idx,
                    rows[stable_idx]["time_sec"],
                    "geometry_fallback",
                    idx,
                    rows[idx]["time_sec"],
                )
            )
            last_event_time = rows[stable_idx]["time_sec"]
    return events


def detect_touchdowns(rows):
    events = []
    for side in ("left", "right"):
        side_events = detect_touchdowns_from_contact(rows, side)
        if not side_events:
            side_events = detect_touchdowns_from_geometry(rows, side)
        events.extend(side_events)
    events = sorted(events, key=lambda event: event.timestamp_sec)
    deduped = []
    for event in events:
        if not deduped:
            deduped.append(event)
            continue
        last_event = deduped[-1]
        same_side = event.side == last_event.side
        near_same_touch = abs(event.timestamp_sec - last_event.timestamp_sec) <= TOUCHDOWN_DEDUP_SEC
        same_index = event.index == last_event.index
        if same_side and (same_index or near_same_touch):
            if event.first_contact_time_sec < last_event.first_contact_time_sec:
                deduped[-1] = event
            continue
        deduped.append(event)
    return deduped


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

    all_flags = []
    if flat_error_touch >= SEVERE_FOOT_FLAT_ERROR_RAD:
        all_flags.append("severe_foot_flat_touchdown")
    if max_clearance < CLEARANCE_MIN_METERS or clearance_pre50 < CONTACT_PRE_MARGIN_METERS:
        all_flags.append("foot_clearance_deficit")
    if abs(hip_err_pre50) > HIP_KNEE_TRACKING_ERR_RAD or abs(knee_err_pre50) > HIP_KNEE_TRACKING_ERR_RAD:
        all_flags.append("hip_knee_tracking_lag")
    if knee_peak_to_touchdown > 0.20:
        all_flags.append("early_knee_extension")
    if flat_error_touch > 0.05 and (
        abs(ankle_pitch_err_touch) > TRACKING_ERR_RAD or abs(ankle_roll_err_touch) > TRACKING_ERR_RAD
    ):
        all_flags.append("tracking_lag")
    elif flat_error_touch > 0.05:
        all_flags.append("command_not_flat")
    if not all_flags:
        all_flags.append("no_clear_blocker_detected")

    primary_flag = all_flags[0]

    return {
        "side": swing_side,
        "first_contact_time_sec": event.first_contact_time_sec,
        "first_contact_index": event.first_contact_index,
        "touchdown_time_sec": t_touch,
        "touchdown_index": touch_idx,
        "touchdown_source": event.source,
        "primary_flag": primary_flag,
        "all_flags": "|".join(all_flags),
        "has_severe_foot_flat_touchdown": int("severe_foot_flat_touchdown" in all_flags),
        "has_foot_clearance_deficit": int("foot_clearance_deficit" in all_flags),
        "has_hip_knee_tracking_lag": int("hip_knee_tracking_lag" in all_flags),
        "has_early_knee_extension": int("early_knee_extension" in all_flags),
        "has_tracking_lag": int("tracking_lag" in all_flags),
        "has_command_not_flat": int("command_not_flat" in all_flags),
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
        handle.write("| side | touchdown_time_sec | primary_flag | all_flags | max_swing_clearance_m | clearance_at_minus_50ms_m | foot_flat_error_touch_rad |\n")
        handle.write("|---|---:|---|---|---:|---:|---:|\n")
        for row in summaries:
            handle.write(
                f"| {row['side']} | {row['touchdown_time_sec']:.3f} | {row['primary_flag']} | {row['all_flags']} | "
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
