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
            raise RuntimeError("Failed to locate repository root from frequency script path")
        cursor = parent


BASE_DIR = find_repo_root(SCRIPT_DIR)
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "forward_x_failure_first6")
RESULT_DIR = os.path.join(BASE_DIR, ".oma", "sim2real", "results", "forward_x_failure")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

STEP_LIMIT = 6
DIFF_EPS_RAD = 5e-4
JOINTS = ("ankle_pitch", "ankle_roll", "knee_pitch", "hip_pitch", "hip_roll")
WINDOW_ROLES = {
    "swing": (("event_leg", "event"), ("opposite_leg", "opposite")),
    "touchdown": (("landing_leg", "event"), ("stance_leg", "opposite")),
}
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


ANALYSIS28 = load_module(
    "analysis28",
    os.path.join(SCRIPT_DIR, "28_forward_x_failure_first6_step_stage_analysis.py"),
)


def mean(values):
    valid = [value for value in values if isinstance(value, (int, float)) and not math.isnan(value)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def stddev(values):
    valid = [value for value in values if isinstance(value, (int, float)) and not math.isnan(value)]
    if len(valid) < 2:
        return 0.0 if valid else math.nan
    avg = mean(valid)
    return math.sqrt(sum((value - avg) ** 2 for value in valid) / len(valid))


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


def parse_kp_kd(dataset, case_label):
    if dataset == "sim" and case_label in SIM_KP_KD:
        kp, kd = SIM_KP_KD[case_label]
        return kp, kd
    token = case_label.split()[0]
    if "/" in token:
        kp_text, kd_text = token.split("/", 1)
        return float(kp_text), float(kd_text)
    return math.nan, math.nan


def kp_case_label(kp, kd):
    if math.isnan(kp) or math.isnan(kd):
        return "unknown"
    kp_text = str(int(kp)) if float(kp).is_integer() else f"{kp:g}"
    kd_text = f"{kd:g}"
    return f"kp{kp_text}_kd{kd_text}"


def side_for_role(event_side, role_side):
    if role_side == "event":
        return event_side
    return "right" if event_side == "left" else "left"


def direction_change_rate_hz(signal, dt_sec):
    if len(signal) < 3:
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
    duration_sec = max((len(signal) - 1) * dt_sec, 1e-6)
    return flips / duration_sec


def dominant_frequency_hz(signal, dt_sec):
    if len(signal) < 6 or dt_sec <= 0:
        return math.nan
    avg = mean(signal)
    centered = [float(value) - avg for value in signal]
    n = len(centered)
    best_freq = math.nan
    best_power = 0.0
    for k in range(1, n // 2 + 1):
        real = 0.0
        imag = 0.0
        for idx, value in enumerate(centered):
            angle = 2.0 * math.pi * k * idx / n
            real += value * math.cos(angle)
            imag -= value * math.sin(angle)
        power = real * real + imag * imag
        if power > best_power:
            best_power = power
            best_freq = k / (n * dt_sec)
    return best_freq


def signal_metrics(values, dt_sec):
    if len(values) < 3:
        return {
            "range_rad": math.nan,
            "path_rad": math.nan,
            "direction_change_rate_hz": math.nan,
            "dominant_freq_hz": math.nan,
        }
    diffs = [curr - prev for prev, curr in zip(values[:-1], values[1:])]
    duration_sec = max((len(values) - 1) * dt_sec, 1e-6)
    extrema = local_extrema_count(values)
    return {
        "range_rad": max(values) - min(values),
        "path_rad": sum(abs(value) for value in diffs),
        "path_rate_radps": sum(abs(value) for value in diffs) / duration_sec,
        "direction_change_rate_hz": direction_change_rate_hz(values, dt_sec),
        "extrema_rate_hz": extrema / duration_sec,
        "dominant_freq_hz": dominant_frequency_hz(values, dt_sec),
    }


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


def build_detail_rows():
    detail_rows = []
    for dataset, case_label, rel_path in ANALYSIS28.REAL_CASES + ANALYSIS28.SIM_CASES:
        ankle_kp, ankle_kd = parse_kp_kd(dataset, case_label)
        csv_path = os.path.join(BASE_DIR, rel_path)
        rows = ANALYSIS28.ROUND3A.load_csv(csv_path)
        ANALYSIS28.ROUND3A.attach_fk_metrics(rows)
        events = sorted(ANALYSIS28.ROUND3A.detect_touchdowns(rows), key=lambda event: event.timestamp_sec)[:STEP_LIMIT]
        dt_sec = ANALYSIS28.median([rows[idx + 1]["time_sec"] - rows[idx]["time_sec"] for idx in range(len(rows) - 1)])

        for step_idx, event in enumerate(events, start=1):
            for window_name in ("swing", "touchdown"):
                window_rows = ANALYSIS28.select_window_rows(rows, event.timestamp_sec, window_name)
                if len(window_rows) < 6:
                    continue
                for role, role_side in WINDOW_ROLES[window_name]:
                    side = side_for_role(event.side, role_side)
                    for joint in JOINTS:
                        target_key = f"pos_des_raw_{side}_{joint}_joint"
                        joint_key = f"pos_{side}_{joint}_joint"
                        target_values = [row[target_key] for row in window_rows]
                        joint_values = [row[joint_key] for row in window_rows]
                        target_metrics = signal_metrics(target_values, dt_sec)
                        joint_metrics = signal_metrics(joint_values, dt_sec)
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
                                "window": window_name,
                                "role": role,
                                "side": side,
                                "joint": joint,
                                "sample_count": len(window_rows),
                                "duration_sec": window_rows[-1]["time_sec"] - window_rows[0]["time_sec"],
                                "target_direction_change_rate_hz": target_metrics["direction_change_rate_hz"],
                                "joint_direction_change_rate_hz": joint_metrics["direction_change_rate_hz"],
                                "target_dominant_freq_hz": target_metrics["dominant_freq_hz"],
                                "joint_dominant_freq_hz": joint_metrics["dominant_freq_hz"],
                                "target_extrema_rate_hz": target_metrics["extrema_rate_hz"],
                                "joint_extrema_rate_hz": joint_metrics["extrema_rate_hz"],
                                "target_range_rad": target_metrics["range_rad"],
                                "joint_range_rad": joint_metrics["range_rad"],
                                "target_path_rad": target_metrics["path_rad"],
                                "joint_path_rad": joint_metrics["path_rad"],
                                "target_path_rate_radps": target_metrics["path_rate_radps"],
                                "joint_path_rate_radps": joint_metrics["path_rate_radps"],
                                "tracking_err_rms_rad": rms(track_err),
                            }
                        )
    return detail_rows


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
                "mean_target_direction_change_rate_hz": mean([item["target_direction_change_rate_hz"] for item in items]),
                "mean_joint_direction_change_rate_hz": mean([item["joint_direction_change_rate_hz"] for item in items]),
                "mean_target_dominant_freq_hz": mean([item["target_dominant_freq_hz"] for item in items]),
                "mean_joint_dominant_freq_hz": mean([item["joint_dominant_freq_hz"] for item in items]),
                "mean_target_extrema_rate_hz": mean([item["target_extrema_rate_hz"] for item in items]),
                "mean_joint_extrema_rate_hz": mean([item["joint_extrema_rate_hz"] for item in items]),
                "mean_target_range_rad": mean([item["target_range_rad"] for item in items]),
                "mean_joint_range_rad": mean([item["joint_range_rad"] for item in items]),
                "mean_target_path_rate_radps": mean([item["target_path_rate_radps"] for item in items]),
                "mean_joint_path_rate_radps": mean([item["joint_path_rate_radps"] for item in items]),
                "mean_tracking_err_rms_rad": mean([item["tracking_err_rms_rad"] for item in items]),
            }
        )
        out.append(row)
    return out


def write_markdown(path, step_rows, overview_rows):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# 31 First-6-Step Joint Change Frequency Tables\n\n")
        handle.write("Source: 28 report canonical data scope, reusing the same first-6 touchdown events and `swing/touchdown` windows.\n\n")
        handle.write("## Metric Notes\n\n")
        handle.write("- `target_direction_change_rate_hz`: `pos_des_raw` first-difference sign reversal rate. It measures how often target direction changes.\n")
        handle.write("- `joint_direction_change_rate_hz`: `joint_pos` first-difference sign reversal rate. It measures how often the actual joint reverses direction.\n")
        handle.write("- `target_dominant_freq_hz` / `joint_dominant_freq_hz`: dominant frequency from a short-window DFT after mean removal. Because the windows are short, this column has low frequency resolution and often falls into the first DFT bin.\n")
        handle.write("- `target_extrema_rate_hz` / `joint_extrema_rate_hz`: local extrema rate after a small diff epsilon. This is a more direct short-window turning-frequency metric.\n")
        handle.write("- `target_path_rate_radps` / `joint_path_rate_radps`: cumulative absolute motion path per second. This measures movement intensity.\n")
        handle.write("- `target_range_rad` / `joint_range_rad`: max-min amplitude inside the window.\n")
        handle.write("- `tracking_err_rms_rad`: RMS of `pos_des_raw - joint_pos` without additional delay alignment in this table.\n")
        handle.write("- `swing/event_leg`: the leg that will touchdown at the event; `swing/opposite_leg`: support-side opposite leg.\n")
        handle.write("- `touchdown/landing_leg`: the leg that just touched down; `touchdown/stance_leg`: opposite support leg.\n\n")

        handle.write("## Overview By Dataset / Window / Role / Joint\n\n")
        handle.write("| dataset | window | role | joint | curves | target dir hz | joint dir hz | target extrema hz | joint extrema hz | target path rad/s | joint path rad/s | target range | joint range | err rms |\n")
        handle.write("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in overview_rows:
            handle.write(
                f"| {row['dataset']} | {row['window']} | {row['role']} | {row['joint']} | {int(row['curve_count'])} | "
                f"{fmt(row['mean_target_direction_change_rate_hz'])} | {fmt(row['mean_joint_direction_change_rate_hz'])} | "
                f"{fmt(row['mean_target_extrema_rate_hz'])} | {fmt(row['mean_joint_extrema_rate_hz'])} | "
                f"{fmt(row['mean_target_path_rate_radps'])} | {fmt(row['mean_joint_path_rate_radps'])} | "
                f"{fmt(row['mean_target_range_rad'], 4)} | {fmt(row['mean_joint_range_rad'], 4)} | {fmt(row['mean_tracking_err_rms_rad'], 4)} |\n"
            )


def write_kp_markdown(path, kp_overview_rows, kp_step_rows):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# 31B First-6-Step Joint Change Frequency By KP/KD\n\n")
        handle.write("Source: same detail table as `31_first6_joint_change_frequency_tables.md`, grouped by `kp_case`.\n\n")
        handle.write("## KP/KD Mapping\n\n")
        handle.write("| dataset | case label | kp_case |\n")
        handle.write("|---|---|---|\n")
        for dataset, case_label, _ in ANALYSIS28.REAL_CASES + ANALYSIS28.SIM_CASES:
            kp, kd = parse_kp_kd(dataset, case_label)
            handle.write(f"| {dataset} | {case_label} | {kp_case_label(kp, kd)} |\n")

        handle.write("\n## KP Overview By Dataset / Window / Role / Joint\n\n")
        handle.write("| dataset | kp_case | window | role | joint | curves | target dir hz | joint dir hz | target extrema hz | joint extrema hz | target path rad/s | joint path rad/s | target range | joint range | err rms |\n")
        handle.write("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in kp_overview_rows:
            handle.write(
                f"| {row['dataset']} | {row['kp_case']} | {row['window']} | {row['role']} | {row['joint']} | {int(row['curve_count'])} | "
                f"{fmt(row['mean_target_direction_change_rate_hz'])} | {fmt(row['mean_joint_direction_change_rate_hz'])} | "
                f"{fmt(row['mean_target_extrema_rate_hz'])} | {fmt(row['mean_joint_extrema_rate_hz'])} | "
                f"{fmt(row['mean_target_path_rate_radps'])} | {fmt(row['mean_joint_path_rate_radps'])} | "
                f"{fmt(row['mean_target_range_rad'], 4)} | {fmt(row['mean_joint_range_rad'], 4)} | {fmt(row['mean_tracking_err_rms_rad'], 4)} |\n"
            )

        handle.write("\n## KP Per-Step Table\n\n")
        handle.write("Each row is one dataset/kp/window/role/step/joint. Since each kp case has one log, `curve_count` is normally 1.\n\n")
        handle.write("| dataset | kp_case | window | role | step | joint | target dir hz | joint dir hz | target extrema hz | joint extrema hz | target path rad/s | joint path rad/s | target range | joint range | err rms |\n")
        handle.write("|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in kp_step_rows:
            handle.write(
                f"| {row['dataset']} | {row['kp_case']} | {row['window']} | {row['role']} | {int(row['step_index'])} | {row['joint']} | "
                f"{fmt(row['mean_target_direction_change_rate_hz'])} | {fmt(row['mean_joint_direction_change_rate_hz'])} | "
                f"{fmt(row['mean_target_extrema_rate_hz'])} | {fmt(row['mean_joint_extrema_rate_hz'])} | "
                f"{fmt(row['mean_target_path_rate_radps'])} | {fmt(row['mean_joint_path_rate_radps'])} | "
                f"{fmt(row['mean_target_range_rad'], 4)} | {fmt(row['mean_joint_range_rad'], 4)} | {fmt(row['mean_tracking_err_rms_rad'], 4)} |\n"
            )

def main():
    detail_rows = build_detail_rows()
    step_rows = summarize(detail_rows, ["dataset", "window", "role", "step_index", "joint"])
    overview_rows = summarize(detail_rows, ["dataset", "window", "role", "joint"])
    kp_overview_rows = summarize(detail_rows, ["dataset", "kp_case", "window", "role", "joint"])
    kp_step_rows = summarize(detail_rows, ["dataset", "kp_case", "window", "role", "step_index", "joint"])

    detail_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_joint_change_frequency_detail.csv")
    step_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_joint_change_frequency_step_summary.csv")
    overview_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_joint_change_frequency_overview.csv")
    kp_overview_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_joint_change_frequency_kp_overview.csv")
    kp_step_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_joint_change_frequency_kp_step_summary.csv")
    result_md = os.path.join(RESULT_DIR, "31_first6_joint_change_frequency_tables.md")
    kp_result_md = os.path.join(RESULT_DIR, "31b_first6_joint_change_frequency_by_kp.md")
    write_csv(detail_csv, detail_rows)
    write_csv(step_csv, step_rows)
    write_csv(overview_csv, overview_rows)
    write_csv(kp_overview_csv, kp_overview_rows)
    write_csv(kp_step_csv, kp_step_rows)
    write_markdown(result_md, step_rows, overview_rows)
    write_kp_markdown(kp_result_md, kp_overview_rows, kp_step_rows)

    print(detail_csv)
    print(step_csv)
    print(overview_csv)
    print(kp_overview_csv)
    print(kp_step_csv)
    print(result_md)
    print(kp_result_md)


if __name__ == "__main__":
    main()
