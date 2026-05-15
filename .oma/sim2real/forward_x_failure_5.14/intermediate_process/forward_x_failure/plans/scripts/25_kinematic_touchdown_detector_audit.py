import csv
import importlib.util
import math
import os
from collections import defaultdict


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
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "compare")
RESULT_DIR = os.path.join(BASE_DIR, ".oma", "sim2real", "results", "forward_x_failure")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


def load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROUND3A = load_module(
    "round3a_plan",
    os.path.join(SCRIPT_DIR, "03a_round3_landing_window_analysis.py"),
)


CASES = [
    ("real", "25/0.4 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100024.csv"),
    ("real", "30/0.4 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100314.csv"),
    ("real", "35/0.5 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100705.csv"),
    ("real", "40/0.8 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv"),
    ("sim", "25/0.4", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133905_2504.csv"),
    ("sim", "35/0.5", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133024_3505.csv"),
    ("sim", "40/0.5", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134153_4005.csv"),
    ("sim", "50/0.8", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134417_5008.csv"),
]

EARLY_TOUCHDOWN_LIMIT = 4
KIN_SWING_CLEARANCE_M = 0.04
KIN_TOUCHDOWN_REL_HEIGHT_M = 0.025
KIN_DESCENT_VEL_MPS = 0.015
KIN_SETTLE_VEL_MPS = 0.08
KIN_SIDE_REFRACTORY_SEC = 0.30
KIN_STABLE_SEARCH_SEC = 0.08
KIN_POST_STABLE_SEC = 0.05
KIN_POST_REL_HEIGHT_M = 0.035
KIN_HIP_DELTA_MIN_RAD = 0.02


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def stddev(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if len(valid) < 2:
        return math.nan
    avg = mean(valid)
    return math.sqrt(sum((v - avg) ** 2 for v in valid) / (len(valid) - 1))


def fmt(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def write_csv(path, rows):
    if not rows:
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def find_index_at_or_after(rows, target_time):
    for idx, row in enumerate(rows):
        if row["time_sec"] >= target_time:
            return idx
    return len(rows) - 1


def hip_motion_ok(rows, swing_start_idx, touchdown_idx, side):
    hip_key = f"pos_{side}_hip_pitch_joint"
    values = [row[hip_key] for row in rows[swing_start_idx : touchdown_idx + 1] if hip_key in row]
    if len(values) < 3:
        return False, math.nan
    delta = max(values) - min(values)
    return delta >= KIN_HIP_DELTA_MIN_RAD, delta


def post_stable_ok(rows, touchdown_idx, side):
    end_idx = find_index_at_or_after(rows, rows[touchdown_idx]["time_sec"] + KIN_POST_STABLE_SEC)
    if end_idx <= touchdown_idx:
        return False
    post_rows = rows[touchdown_idx : end_idx + 1]
    low_rows = [row for row in post_rows if row[f"{side}_rel_height"] <= KIN_POST_REL_HEIGHT_M]
    return len(low_rows) >= max(2, int(0.6 * len(post_rows)))


def choose_stable_kinematic_idx(rows, candidate_idx, side):
    end_idx = find_index_at_or_after(rows, rows[candidate_idx]["time_sec"] + KIN_STABLE_SEARCH_SEC)
    best_idx = candidate_idx
    best_score = None
    for idx in range(candidate_idx, end_idx + 1):
        row = rows[idx]
        rel_height = row[f"{side}_rel_height"]
        vz = row[f"{side}_foot_vz"]
        vx = row[f"{side}_foot_vx"]
        flat_rate = row[f"{side}_flat_error_rate"]
        stable = (
            rel_height <= KIN_TOUCHDOWN_REL_HEIGHT_M
            and abs(vz) <= KIN_SETTLE_VEL_MPS
            and post_stable_ok(rows, idx, side)
        )
        score = (
            0 if stable else 1,
            max(rel_height, 0.0),
            abs(vz),
            abs(vx),
            abs(flat_rate),
            idx,
        )
        if best_score is None or score < best_score:
            best_score = score
            best_idx = idx
        if stable:
            return idx
    return best_idx


def detect_touchdowns_kinematic(rows):
    events = []
    for side in ("left", "right"):
        state = "wait_swing"
        swing_start_idx = None
        peak_idx = None
        last_event_time = -1e9
        for idx in range(2, len(rows) - 2):
            row = rows[idx]
            rel_height = row[f"{side}_rel_height"]
            prev_rel = rows[idx - 1][f"{side}_rel_height"]
            vz = row[f"{side}_foot_vz"]
            prev_vz = rows[idx - 1][f"{side}_foot_vz"]

            if row["time_sec"] - last_event_time < KIN_SIDE_REFRACTORY_SEC:
                continue

            if state == "wait_swing":
                if rel_height >= KIN_SWING_CLEARANCE_M:
                    state = "in_swing"
                    swing_start_idx = idx
                    peak_idx = idx
                continue

            if state == "in_swing":
                if rel_height > rows[peak_idx][f"{side}_rel_height"]:
                    peak_idx = idx
                descending = prev_vz <= -KIN_DESCENT_VEL_MPS or rel_height < prev_rel
                low_enough = rel_height <= KIN_TOUCHDOWN_REL_HEIGHT_M
                settling = abs(vz) <= KIN_SETTLE_VEL_MPS or (prev_vz < -KIN_DESCENT_VEL_MPS and vz >= -KIN_SETTLE_VEL_MPS)
                if descending and low_enough and settling:
                    stable_idx = choose_stable_kinematic_idx(rows, idx, side)
                    hip_ok, hip_delta = hip_motion_ok(rows, swing_start_idx, stable_idx, side)
                    if hip_ok and post_stable_ok(rows, stable_idx, side):
                        events.append(
                            ROUND3A.TouchdownEvent(
                                side,
                                stable_idx,
                                rows[stable_idx]["time_sec"],
                                "kinematic_fk_hip",
                                idx,
                                rows[idx]["time_sec"],
                            )
                        )
                        last_event_time = rows[stable_idx]["time_sec"]
                    state = "wait_swing"
                    swing_start_idx = None
                    peak_idx = None
    return sorted(events, key=lambda event: event.timestamp_sec)


def intervals(times):
    return [times[idx + 1] - times[idx] for idx in range(len(times) - 1)]


def summarize_events(events):
    first4 = events[:EARLY_TOUCHDOWN_LIMIT]
    times = [event.timestamp_sec for event in first4]
    sides = [event.side for event in first4]
    adjacent = intervals(times)
    same_side = []
    for side in ("left", "right"):
        side_times = [event.timestamp_sec for event in first4 if event.side == side]
        same_side.extend(intervals(side_times))
    return {
        "first4_sides": "-".join(sides),
        "first4_left_count": sides.count("left"),
        "first4_right_count": sides.count("right"),
        "first4_adjacent_mean_sec": mean(adjacent),
        "first4_adjacent_std_sec": stddev(adjacent),
        "first4_same_side_mean_sec": mean(same_side),
        "first4_same_side_std_sec": stddev(same_side),
        "all_event_count": len(events),
    }


def analyze_case(stage, case_label, rel_path):
    csv_path = os.path.join(BASE_DIR, rel_path)
    rows = ROUND3A.load_csv(csv_path)
    ROUND3A.attach_fk_metrics(rows)
    old_events = []
    for side in ("left", "right"):
        side_events = ROUND3A.detect_touchdowns_from_contact(rows, side)
        if not side_events:
            side_events = ROUND3A.detect_touchdowns_from_geometry(rows, side)
        old_events.extend(side_events)
    old_events = sorted(old_events, key=lambda event: event.timestamp_sec)
    new_events = detect_touchdowns_kinematic(rows)
    old_summary = summarize_events(old_events)
    new_summary = summarize_events(new_events)
    out = {
        "stage": stage,
        "case_label": case_label,
        "diag_csv": os.path.basename(csv_path),
    }
    for key, value in old_summary.items():
        out[f"old_{key}"] = value
    for key, value in new_summary.items():
        out[f"new_{key}"] = value
    detail = []
    for detector_name, events in (("old", old_events), ("new", new_events)):
        for seq, event in enumerate(events[:8]):
            row = rows[event.index]
            detail.append(
                {
                    "stage": stage,
                    "case_label": case_label,
                    "detector": detector_name,
                    "seq": seq,
                    "side": event.side,
                    "time_sec": event.timestamp_sec,
                    "source": event.source,
                    "rel_height_m": row[f"{event.side}_rel_height"],
                    "foot_vz_mps": row[f"{event.side}_foot_vz"],
                    "hip_pitch_rad": row[f"pos_{event.side}_hip_pitch_joint"],
                }
            )
    return out, detail


def build_markdown(path, summaries):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# 25 Kinematic Touchdown Detector Audit\n\n")
        handle.write("- Old detector: `ankle_pitch` low-velocity contact proxy plus FK refine.\n")
        handle.write("- New/current detector: FK foot relative height/vertical velocity first, hip pitch motion as phase sanity check.\n")
        handle.write("- Validation target from visual fact: real first 4 touchdowns should look like normal stepping, with early adjacent intervals near the observed gait rhythm instead of repeated spurious same-side triggers.\n\n")
        handle.write("## First-4 Comparison\n\n")
        handle.write("| stage | case | old sides | old adj mean±std | old same-side mean±std | new sides | new adj mean±std | new same-side mean±std | old/new events |\n")
        handle.write("|---|---|---|---:|---:|---|---:|---:|---:|\n")
        for row in summaries:
            handle.write(
                f"| {row['stage']} | {row['case_label']} | {row['old_first4_sides']} | "
                f"{fmt(row['old_first4_adjacent_mean_sec'])} ± {fmt(row['old_first4_adjacent_std_sec'])} | "
                f"{fmt(row['old_first4_same_side_mean_sec'])} ± {fmt(row['old_first4_same_side_std_sec'])} | "
                f"{row['new_first4_sides']} | "
                f"{fmt(row['new_first4_adjacent_mean_sec'])} ± {fmt(row['new_first4_adjacent_std_sec'])} | "
                f"{fmt(row['new_first4_same_side_mean_sec'])} ± {fmt(row['new_first4_same_side_std_sec'])} | "
                f"{int(row['old_all_event_count'])}/{int(row['new_all_event_count'])} |\n"
            )

        handle.write("\n## Reading\n\n")
        real_rows = [row for row in summaries if row["stage"] == "real"]
        old_adj = [row["old_first4_adjacent_mean_sec"] for row in real_rows]
        new_adj = [row["new_first4_adjacent_mean_sec"] for row in real_rows]
        old_same = [row["old_first4_same_side_mean_sec"] for row in real_rows]
        new_same = [row["new_first4_same_side_mean_sec"] for row in real_rows]
        handle.write(f"- Real old first-4 adjacent mean across cases: `{fmt(mean(old_adj))} s`; new: `{fmt(mean(new_adj))} s`.\n")
        handle.write(f"- Real old first-4 same-side mean across cases: `{fmt(mean(old_same))} s`; new: `{fmt(mean(new_same))} s`.\n")
        handle.write("- If the new detector restores alternating side sequence and period close to visual gait rhythm, downstream jitter/residual windows should be regenerated from this detector.\n")


def main():
    summaries = []
    details = []
    for stage, case_label, rel_path in CASES:
        summary, detail = analyze_case(stage, case_label, rel_path)
        summaries.append(summary)
        details.extend(detail)

    summary_csv = os.path.join(OUT_DIR, "kinematic_touchdown_detector_audit_summary.csv")
    detail_csv = os.path.join(OUT_DIR, "kinematic_touchdown_detector_audit_detail.csv")
    result_md = os.path.join(RESULT_DIR, "25_kinematic_touchdown_detector_audit.md")
    write_csv(summary_csv, summaries)
    write_csv(detail_csv, details)
    build_markdown(result_md, summaries)
    print(summary_csv)
    print(detail_csv)
    print(result_md)


if __name__ == "__main__":
    main()
