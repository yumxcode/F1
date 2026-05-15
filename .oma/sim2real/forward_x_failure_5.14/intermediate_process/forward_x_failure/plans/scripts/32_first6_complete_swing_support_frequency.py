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
            raise RuntimeError("Failed to locate repository root from complete phase script path")
        cursor = parent


BASE_DIR = find_repo_root(SCRIPT_DIR)
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "forward_x_failure_first6")
RESULT_DIR = os.path.join(BASE_DIR, ".oma", "sim2real", "results", "forward_x_failure")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

STEP_LIMIT = 6
DIFF_EPS_RAD = 5e-4
JOINTS = ("ankle_pitch", "ankle_roll", "knee_pitch", "hip_pitch", "hip_roll")
SIM_KP_KD = {
    "2504": (25.0, 0.4),
    "3505": (35.0, 0.5),
    "4005": (40.0, 0.5),
    "5008": (50.0, 0.8),
}


def load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    ANALYSIS28 = load_module(
        "analysis28",
        os.path.join(SCRIPT_DIR, "28_forward_x_failure_first6_step_stage_analysis.py"),
    )
except (Exception, SystemExit) as exc:
    ANALYSIS28 = None
    ANALYSIS28_IMPORT_ERROR = exc
else:
    ANALYSIS28_IMPORT_ERROR = None


REAL_CASES = [
    ("real", "25/0.4 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100024.csv"),
    ("real", "30/0.4 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100314.csv"),
    ("real", "35/0.5 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100705.csv"),
    ("real", "40/0.8 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv"),
]

SIM_CASES = [
    ("sim", "2504", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133905_2504.csv"),
    ("sim", "3505", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133024_3505.csv"),
    ("sim", "4005", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134153_4005.csv"),
    ("sim", "5008", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134417_5008.csv"),
]


def mean(values):
    valid = [value for value in values if isinstance(value, (int, float)) and not math.isnan(value)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def median(values):
    valid = sorted(value for value in values if isinstance(value, (int, float)) and not math.isnan(value))
    if not valid:
        return math.nan
    mid = len(valid) // 2
    if len(valid) % 2:
        return valid[mid]
    return 0.5 * (valid[mid - 1] + valid[mid])


def rms(values):
    valid = [float(value) for value in values if isinstance(value, (int, float)) and not math.isnan(value)]
    if not valid:
        return math.nan
    return math.sqrt(sum(value * value for value in valid) / len(valid))


def fmt(value, digits=3):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def write_csv(path, rows):
    if not rows:
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    rows = []
    with open(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {}
            for key, value in raw.items():
                if value == "":
                    row[key] = math.nan
                    continue
                if key == "timestamp_ns":
                    row[key] = int(value)
                else:
                    try:
                        row[key] = float(value)
                    except (TypeError, ValueError):
                        row[key] = value
            if "timestamp_ns" in row and "time_sec" not in row:
                row["time_sec"] = row["timestamp_ns"] / 1e9
            rows.append(row)
    return rows


def parse_kp_kd(dataset, case_label):
    if dataset == "sim" and case_label in SIM_KP_KD:
        return SIM_KP_KD[case_label]
    token = case_label.split()[0]
    if "/" in token:
        kp_text, kd_text = token.split("/", 1)
        return float(kp_text), float(kd_text)
    return math.nan, math.nan


def kp_case_label(kp, kd):
    if math.isnan(kp) or math.isnan(kd):
        return "unknown"
    kp_text = str(int(kp)) if float(kp).is_integer() else f"{kp:g}"
    return f"kp{kp_text}_kd{kd:g}"


def other_side(side):
    return "right" if side == "left" else "left"


def select_time_rows(rows, start_time, end_time):
    return [row for row in rows if start_time <= row["time_sec"] <= end_time]


def previous_opposite_event(events, event_index):
    side = events[event_index].side
    for idx in range(event_index - 1, -1, -1):
        if events[idx].side != side:
            return events[idx]
    return None


def next_opposite_event(events, event_index):
    side = events[event_index].side
    for idx in range(event_index + 1, len(events)):
        if events[idx].side != side:
            return events[idx]
    return None


def direction_change_rate_hz(signal, duration_sec):
    if len(signal) < 3 or duration_sec <= 0:
        return math.nan
    signs = []
    for prev, curr in zip(signal[:-1], signal[1:]):
        diff = curr - prev
        if abs(diff) <= DIFF_EPS_RAD:
            continue
        signs.append(1 if diff > 0.0 else -1)
    if len(signs) < 2:
        return 0.0
    flips = sum(1 for left, right in zip(signs[:-1], signs[1:]) if left != right)
    return flips / duration_sec


def local_extrema_count(signal):
    if len(signal) < 3:
        return 0
    count = 0
    for idx in range(1, len(signal) - 1):
        prev_delta = signal[idx] - signal[idx - 1]
        next_delta = signal[idx + 1] - signal[idx]
        if abs(prev_delta) <= DIFF_EPS_RAD or abs(next_delta) <= DIFF_EPS_RAD:
            continue
        if prev_delta * next_delta < 0:
            count += 1
    return count


def dominant_frequency_hz(signal, duration_sec):
    if len(signal) < 3 or duration_sec <= 0:
        return math.nan
    mean_value = sum(signal) / len(signal)
    centered = [value - mean_value for value in signal]
    if max(abs(value) for value in centered) <= DIFF_EPS_RAD:
        return 0.0
    dt_sec = duration_sec / max(len(signal) - 1, 1)
    n = len(centered)
    windowed = [
        value * (0.5 - 0.5 * math.cos(2.0 * math.pi * idx / (n - 1)))
        for idx, value in enumerate(centered)
    ]
    best_power = 0.0
    best_freq = 0.0
    # One-sided periodogram. k=0 is DC and is intentionally ignored.
    for k in range(1, n // 2 + 1):
        real = 0.0
        imag = 0.0
        for idx, value in enumerate(windowed):
            angle = -2.0 * math.pi * k * idx / n
            real += value * math.cos(angle)
            imag += value * math.sin(angle)
        power = real * real + imag * imag
        if power > best_power:
            best_power = power
            best_freq = k / (n * dt_sec)
    return best_freq


def signal_metrics(values, duration_sec):
    if len(values) < 3 or duration_sec <= 0:
        return {
            "range_rad": math.nan,
            "path_rad": math.nan,
            "path_rate_radps": math.nan,
            "direction_change_rate_hz": math.nan,
            "extrema_rate_hz": math.nan,
            "dominant_freq_hz": math.nan,
        }
    diffs = [curr - prev for prev, curr in zip(values[:-1], values[1:])]
    path = sum(abs(value) for value in diffs)
    return {
        "range_rad": max(values) - min(values),
        "path_rad": path,
        "path_rate_radps": path / duration_sec,
        "direction_change_rate_hz": direction_change_rate_hz(values, duration_sec),
        "extrema_rate_hz": local_extrema_count(values) / duration_sec,
        "dominant_freq_hz": dominant_frequency_hz(values, duration_sec),
    }


def build_phase_windows(events, event_index):
    event = events[event_index]
    prev_opp = previous_opposite_event(events, event_index)
    next_opp = next_opposite_event(events, event_index)
    windows = []
    if prev_opp is not None:
        windows.append(
            {
                "phase": "complete_swing",
                "role": "swing_leg",
                "side": event.side,
                "start_time_sec": prev_opp.timestamp_sec,
                "end_time_sec": event.timestamp_sec,
                "start_event_side": prev_opp.side,
                "end_event_side": event.side,
            }
        )
    if next_opp is not None:
        windows.append(
            {
                "phase": "complete_support",
                "role": "support_leg",
                "side": event.side,
                "start_time_sec": event.timestamp_sec,
                "end_time_sec": next_opp.timestamp_sec,
                "start_event_side": event.side,
                "end_event_side": next_opp.side,
            }
        )
    return windows


def build_detail_rows_from_existing_windows():
    detail_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_complete_phase_frequency_detail.csv")
    skipped_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_complete_phase_skipped.csv")
    if not os.path.exists(detail_csv):
        raise RuntimeError(
            "Cannot rebuild dominant-frequency tables without mujoco/numpy because "
            f"the existing window detail CSV is missing: {detail_csv}. "
            f"Import error: {ANALYSIS28_IMPORT_ERROR}"
        )

    rel_by_basename = {
        os.path.basename(rel_path): rel_path for _dataset, _case_label, rel_path in REAL_CASES + SIM_CASES
    }
    raw_cache = {}
    detail_rows = []
    for window in read_csv(detail_csv):
        diag_csv = str(window["diag_csv"])
        if diag_csv not in rel_by_basename:
            raise RuntimeError(f"No raw CSV mapping found for {diag_csv}")
        if diag_csv not in raw_cache:
            raw_cache[diag_csv] = read_csv(os.path.join(BASE_DIR, rel_by_basename[diag_csv]))
        window_rows = select_time_rows(
            raw_cache[diag_csv],
            float(window["start_time_sec"]),
            float(window["end_time_sec"]),
        )
        if len(window_rows) < 6:
            continue
        duration_sec = window_rows[-1]["time_sec"] - window_rows[0]["time_sec"]
        side = str(window["side"])
        joint = str(window["joint"])
        target_key = f"pos_des_raw_{side}_{joint}_joint"
        joint_key = f"pos_{side}_{joint}_joint"
        target_values = [row[target_key] for row in window_rows]
        joint_values = [row[joint_key] for row in window_rows]
        target_metrics = signal_metrics(target_values, duration_sec)
        joint_metrics = signal_metrics(joint_values, duration_sec)
        track_err = [target - joint_pos for target, joint_pos in zip(target_values, joint_values)]
        detail_rows.append(
            {
                "dataset": window["dataset"],
                "case_label": window["case_label"],
                "kp_case": window["kp_case"],
                "ankle_kp": window["ankle_kp"],
                "ankle_kd": window["ankle_kd"],
                "diag_csv": diag_csv,
                "step_index": int(float(window["step_index"])),
                "touchdown_side": window["touchdown_side"],
                "phase": window["phase"],
                "role": window["role"],
                "side": side,
                "start_time_sec": window["start_time_sec"],
                "end_time_sec": window["end_time_sec"],
                "duration_sec": duration_sec,
                "sample_count": len(window_rows),
                "start_event_side": window["start_event_side"],
                "end_event_side": window["end_event_side"],
                "joint": joint,
                "target_direction_change_rate_hz": target_metrics["direction_change_rate_hz"],
                "joint_direction_change_rate_hz": joint_metrics["direction_change_rate_hz"],
                "target_extrema_rate_hz": target_metrics["extrema_rate_hz"],
                "joint_extrema_rate_hz": joint_metrics["extrema_rate_hz"],
                "target_dominant_freq_hz": target_metrics["dominant_freq_hz"],
                "joint_dominant_freq_hz": joint_metrics["dominant_freq_hz"],
                "target_range_rad": target_metrics["range_rad"],
                "joint_range_rad": joint_metrics["range_rad"],
                "target_path_rad": target_metrics["path_rad"],
                "joint_path_rad": joint_metrics["path_rad"],
                "target_path_rate_radps": target_metrics["path_rate_radps"],
                "joint_path_rate_radps": joint_metrics["path_rate_radps"],
                "tracking_err_rms_rad": rms(track_err),
            }
        )
    skipped_rows = read_csv(skipped_csv) if os.path.exists(skipped_csv) else []
    return detail_rows, skipped_rows


def build_detail_rows():
    if ANALYSIS28 is None:
        return build_detail_rows_from_existing_windows()

    detail_rows = []
    skipped_rows = []
    for dataset, case_label, rel_path in REAL_CASES + SIM_CASES:
        ankle_kp, ankle_kd = parse_kp_kd(dataset, case_label)
        csv_path = os.path.join(BASE_DIR, rel_path)
        rows = ANALYSIS28.ROUND3A.load_csv(csv_path)
        ANALYSIS28.ROUND3A.attach_fk_metrics(rows)
        events = sorted(ANALYSIS28.ROUND3A.detect_touchdowns(rows), key=lambda event: event.timestamp_sec)
        first_events = events[:STEP_LIMIT]

        for event_index, event in enumerate(first_events):
            step_idx = event_index + 1
            windows = build_phase_windows(events, event_index)
            present_phases = {window["phase"] for window in windows}
            for phase in ("complete_swing", "complete_support"):
                if phase not in present_phases:
                    skipped_rows.append(
                        {
                            "dataset": dataset,
                            "case_label": case_label,
                            "kp_case": kp_case_label(ankle_kp, ankle_kd),
                            "step_index": step_idx,
                            "touchdown_side": event.side,
                            "phase": phase,
                            "reason": "missing_previous_opposite_touchdown" if phase == "complete_swing" else "missing_next_opposite_touchdown",
                        }
                    )

            for window in windows:
                window_rows = select_time_rows(rows, window["start_time_sec"], window["end_time_sec"])
                if len(window_rows) < 6:
                    skipped_rows.append(
                        {
                            "dataset": dataset,
                            "case_label": case_label,
                            "kp_case": kp_case_label(ankle_kp, ankle_kd),
                            "step_index": step_idx,
                            "touchdown_side": event.side,
                            "phase": window["phase"],
                            "reason": "too_few_samples",
                        }
                    )
                    continue
                duration_sec = window_rows[-1]["time_sec"] - window_rows[0]["time_sec"]
                for joint in JOINTS:
                    target_key = f"pos_des_raw_{window['side']}_{joint}_joint"
                    joint_key = f"pos_{window['side']}_{joint}_joint"
                    target_values = [row[target_key] for row in window_rows]
                    joint_values = [row[joint_key] for row in window_rows]
                    target_metrics = signal_metrics(target_values, duration_sec)
                    joint_metrics = signal_metrics(joint_values, duration_sec)
                    track_err = [target - joint_pos for target, joint_pos in zip(target_values, joint_values)]
                    detail_rows.append(
                        {
                            "dataset": dataset,
                            "case_label": case_label,
                            "kp_case": kp_case_label(ankle_kp, ankle_kd),
                            "ankle_kp": ankle_kp,
                            "ankle_kd": ankle_kd,
                            "diag_csv": os.path.basename(rel_path),
                            "step_index": step_idx,
                            "touchdown_side": event.side,
                            "phase": window["phase"],
                            "role": window["role"],
                            "side": window["side"],
                            "start_time_sec": window["start_time_sec"],
                            "end_time_sec": window["end_time_sec"],
                            "duration_sec": duration_sec,
                            "sample_count": len(window_rows),
                            "start_event_side": window["start_event_side"],
                            "end_event_side": window["end_event_side"],
                            "joint": joint,
                            "target_direction_change_rate_hz": target_metrics["direction_change_rate_hz"],
                            "joint_direction_change_rate_hz": joint_metrics["direction_change_rate_hz"],
                            "target_extrema_rate_hz": target_metrics["extrema_rate_hz"],
                            "joint_extrema_rate_hz": joint_metrics["extrema_rate_hz"],
                            "target_dominant_freq_hz": target_metrics["dominant_freq_hz"],
                            "joint_dominant_freq_hz": joint_metrics["dominant_freq_hz"],
                            "target_range_rad": target_metrics["range_rad"],
                            "joint_range_rad": joint_metrics["range_rad"],
                            "target_path_rad": target_metrics["path_rad"],
                            "joint_path_rad": joint_metrics["path_rad"],
                            "target_path_rate_radps": target_metrics["path_rate_radps"],
                            "joint_path_rate_radps": joint_metrics["path_rate_radps"],
                            "tracking_err_rms_rad": rms(track_err),
                        }
                    )
    return detail_rows, skipped_rows


def summarize(rows, keys):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    out = []
    for key_values, items in sorted(grouped.items()):
        row = {key: value for key, value in zip(keys, key_values)}
        row.update(
            {
                "case_count": len({item["case_label"] for item in items}),
                "curve_count": len(items),
                "mean_duration_sec": mean([item["duration_sec"] for item in items]),
                "mean_target_direction_change_rate_hz": mean([item["target_direction_change_rate_hz"] for item in items]),
                "mean_joint_direction_change_rate_hz": mean([item["joint_direction_change_rate_hz"] for item in items]),
                "mean_target_extrema_rate_hz": mean([item["target_extrema_rate_hz"] for item in items]),
                "mean_joint_extrema_rate_hz": mean([item["joint_extrema_rate_hz"] for item in items]),
                "mean_target_dominant_freq_hz": mean([item["target_dominant_freq_hz"] for item in items]),
                "mean_joint_dominant_freq_hz": mean([item["joint_dominant_freq_hz"] for item in items]),
                "mean_target_range_rad": mean([item["target_range_rad"] for item in items]),
                "mean_joint_range_rad": mean([item["joint_range_rad"] for item in items]),
                "mean_target_path_rate_radps": mean([item["target_path_rate_radps"] for item in items]),
                "mean_joint_path_rate_radps": mean([item["joint_path_rate_radps"] for item in items]),
                "mean_tracking_err_rms_rad": mean([item["tracking_err_rms_rad"] for item in items]),
            }
        )
        out.append(row)
    return out


def write_table(handle, rows, include_kp=False, include_side=False, include_step=False):
    prefix = []
    if include_kp:
        prefix.append("kp_case")
    prefix.extend(["dataset", "phase", "role"])
    if include_side:
        prefix.append("side")
    if include_step:
        prefix.append("step_index")
    prefix.append("joint")
    handle.write(
        "| "
        + " | ".join(prefix)
        + " | curves | duration | target dominant hz | joint dominant hz | target dir hz | joint dir hz | target extrema hz | joint extrema hz | target path rad/s | joint path rad/s | target range | joint range | err rms |\n"
    )
    handle.write(
        "|"
        + "|".join(["---"] * len(prefix))
        + "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    for row in rows:
        values = []
        for key in prefix:
            value = row[key]
            if key == "step_index":
                value = int(value)
            values.append(str(value))
        handle.write(
            "| "
            + " | ".join(values)
            + " | "
            + f"{int(row['curve_count'])} | {fmt(row['mean_duration_sec'])} | "
            + f"{fmt(row['mean_target_dominant_freq_hz'])} | {fmt(row['mean_joint_dominant_freq_hz'])} | "
            + f"{fmt(row['mean_target_direction_change_rate_hz'])} | {fmt(row['mean_joint_direction_change_rate_hz'])} | "
            + f"{fmt(row['mean_target_extrema_rate_hz'])} | {fmt(row['mean_joint_extrema_rate_hz'])} | "
            + f"{fmt(row['mean_target_path_rate_radps'])} | {fmt(row['mean_joint_path_rate_radps'])} | "
            + f"{fmt(row['mean_target_range_rad'], 4)} | {fmt(row['mean_joint_range_rad'], 4)} | {fmt(row['mean_tracking_err_rms_rad'], 4)} |\n"
        )


def write_markdown(path, overview_rows, kp_overview_rows, kp_side_rows, step_rows, skipped_rows):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# 32 Complete Swing / Support Frequency Tables\n\n")
        handle.write("Source: same touchdown detector and first-6 touchdown events as 28 report, but windows are now complete gait phases rather than short touchdown-centered windows.\n\n")
        handle.write("## Window Definition\n\n")
        handle.write("- `complete_swing`: previous opposite-side touchdown -> current touchdown of the same leg. This is the completed swing phase of the landing leg.\n")
        handle.write("- `complete_support`: current touchdown -> next opposite-side touchdown. This approximates the completed single-support phase for the touchdown leg using touchdown boundaries.\n")
        handle.write("- Step 1 often has no previous opposite touchdown, so its `complete_swing` is skipped. If a later boundary is missing, that phase is also skipped and recorded in the skipped CSV.\n\n")
        handle.write("## Metric Notes\n\n")
        handle.write("- `target_direction_change_rate_hz` / `joint_direction_change_rate_hz`: sign-reversal rate of first differences.\n")
        handle.write("- `target_dominant_freq_hz` / `joint_dominant_freq_hz`: FFT/PSD dominant frequency after demeaning and Hann-windowing each phase signal; DC is ignored.\n")
        handle.write("- `target_extrema_rate_hz` / `joint_extrema_rate_hz`: local extrema rate after epsilon filtering.\n")
        handle.write("- `target_path_rate_radps` / `joint_path_rate_radps`: cumulative absolute motion per second.\n")
        handle.write("- `target_range_rad` / `joint_range_rad`: max-min amplitude across the full phase window.\n")
        handle.write("- `tracking_err_rms_rad`: RMS of `pos_des_raw - joint_pos` in the full phase window.\n\n")

        handle.write("## Overview\n\n")
        write_table(handle, overview_rows)
        handle.write("\n## By KP/KD\n\n")
        write_table(handle, kp_overview_rows, include_kp=True)
        handle.write("\n## By KP/KD And Left/Right Side\n\n")
        write_table(handle, kp_side_rows, include_kp=True, include_side=True)
        handle.write("\n## Per Step\n\n")
        write_table(handle, step_rows, include_step=True)

        skipped_count = len(skipped_rows)
        handle.write(f"\n## Skipped Phase Windows\n\nSkipped rows: `{skipped_count}`. See `forward_x_failure_first6_complete_phase_skipped.csv` for details.\n")


def main():
    detail_rows, skipped_rows = build_detail_rows()
    overview_rows = summarize(detail_rows, ["dataset", "phase", "role", "joint"])
    kp_overview_rows = summarize(detail_rows, ["kp_case", "dataset", "phase", "role", "joint"])
    kp_side_rows = summarize(detail_rows, ["kp_case", "dataset", "phase", "role", "side", "joint"])
    step_rows = summarize(detail_rows, ["dataset", "phase", "role", "step_index", "joint"])

    detail_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_complete_phase_frequency_detail.csv")
    overview_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_complete_phase_frequency_overview.csv")
    kp_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_complete_phase_frequency_kp_overview.csv")
    kp_side_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_complete_phase_frequency_kp_side_overview.csv")
    step_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_complete_phase_frequency_step_summary.csv")
    skipped_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_complete_phase_skipped.csv")
    result_md = os.path.join(RESULT_DIR, "32_complete_swing_support_frequency_tables.md")

    write_csv(detail_csv, detail_rows)
    write_csv(overview_csv, overview_rows)
    write_csv(kp_csv, kp_overview_rows)
    write_csv(kp_side_csv, kp_side_rows)
    write_csv(step_csv, step_rows)
    write_csv(skipped_csv, skipped_rows)
    write_markdown(result_md, overview_rows, kp_overview_rows, kp_side_rows, step_rows, skipped_rows)

    print(detail_csv)
    print(overview_csv)
    print(kp_csv)
    print(kp_side_csv)
    print(step_csv)
    print(skipped_csv)
    print(result_md)


if __name__ == "__main__":
    main()
