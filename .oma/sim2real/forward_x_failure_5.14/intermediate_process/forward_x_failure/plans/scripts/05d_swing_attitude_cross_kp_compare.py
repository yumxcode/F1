import csv
import importlib.util
import math
import os
from collections import Counter, defaultdict


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
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
EARLY_TOUCHDOWN_LIMIT = 4
SWING_START_BEFORE_TOUCH_SEC = 0.35
SWING_END_BEFORE_TOUCH_SEC = 0.02
AIRBORNE_REL_HEIGHT_MIN_M = 0.02
PROFILE_BINS = 21

DATASETS = [
    ("baseline_35_0p5", "t26_round3_diag_20260427_170011.csv"),
    ("high_kp_right_roll_50_0p8", "t27_tracking_lag_b1_diag_20260428_161322.csv"),
    ("low_kp_right_roll_25_0p5", "t27_tracking_lag_b1_diag_20260428_163825.csv"),
    ("low_kp_all_ankles_25_0p5", "t27_tracking_lag_b1_diag_20260428_164817.csv"),
]


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

os.makedirs(OUT_DIR, exist_ok=True)


def mean(values):
    valid = [value for value in values if not math.isnan(value)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def stddev(values):
    valid = [value for value in values if not math.isnan(value)]
    if len(valid) < 2:
        return 0.0 if valid else math.nan
    mu = sum(valid) / len(valid)
    return math.sqrt(sum((value - mu) ** 2 for value in valid) / (len(valid) - 1))


def format_float(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def sign_label(value):
    if math.isnan(value):
        return "nan"
    return "negative" if value < 0.0 else "positive"


def load_rows(diag_filename):
    diag_path = os.path.join(BASE_DIR, "test_logs", "data_csv", diag_filename)
    if not os.path.isfile(diag_path):
        raise FileNotFoundError(f"Missing diag file: {diag_path}")
    rows = ROUND3A.load_csv(diag_path)
    ROUND3A.attach_fk_metrics(rows)
    events = ROUND3A.detect_touchdowns(rows)
    events = sorted(events, key=lambda event: event.timestamp_sec)[:EARLY_TOUCHDOWN_LIMIT]
    return diag_path, rows, events


def row_at_or_before(rows, target_time):
    return rows[ROUND3A.find_index_at_or_before(rows, target_time)]


def swing_rows_for_event(rows, event):
    swing_side = event.side
    stance_side = "right" if swing_side == "left" else "left"
    t_touch = event.timestamp_sec
    start_idx = ROUND3A.find_index_at_or_before(rows, t_touch - SWING_START_BEFORE_TOUCH_SEC)
    end_idx = ROUND3A.find_index_at_or_before(rows, t_touch - SWING_END_BEFORE_TOUCH_SEC)
    candidate_rows = rows[start_idx : max(end_idx + 1, start_idx + 1)]
    airborne_rows = [
        row for row in candidate_rows if row[f"{swing_side}_rel_height"] >= AIRBORNE_REL_HEIGHT_MIN_M
    ]
    if len(airborne_rows) >= 3:
        return airborne_rows, swing_side, stance_side
    return candidate_rows, swing_side, stance_side


def profile_sample(rows, field_name, phase):
    if not rows:
        return math.nan
    if len(rows) == 1:
        return rows[0][field_name]
    phase = min(max(phase, 0.0), 1.0)
    idx = phase * (len(rows) - 1)
    low = int(math.floor(idx))
    high = int(math.ceil(idx))
    if low == high:
        return rows[low][field_name]
    alpha = idx - low
    return rows[low][field_name] * (1.0 - alpha) + rows[high][field_name] * alpha


def summarize_event(dataset_name, diag_filename, rows, event):
    swing_rows, swing_side, stance_side = swing_rows_for_event(rows, event)
    touchdown_row = row_at_or_before(rows, event.timestamp_sec)
    peak_clearance_row = max(swing_rows, key=lambda row: row[f"{swing_side}_rel_height"])
    pre100_row = row_at_or_before(rows, event.timestamp_sec - 0.10)
    pre50_row = row_at_or_before(rows, event.timestamp_sec - 0.05)
    pre20_row = row_at_or_before(rows, event.timestamp_sec - 0.02)

    roll_series = [row[f"{swing_side}_sole_roll"] for row in swing_rows]
    pitch_series = [row[f"{swing_side}_sole_pitch"] for row in swing_rows]
    abs_roll_series = [abs(value) for value in roll_series]
    abs_pitch_series = [abs(value) for value in pitch_series]
    rel_height_series = [row[f"{swing_side}_rel_height"] for row in swing_rows]

    return {
        "dataset": dataset_name,
        "diag_filename": diag_filename,
        "side": swing_side,
        "touchdown_time_sec": event.timestamp_sec,
        "swing_row_count": len(swing_rows),
        "swing_duration_sec": swing_rows[-1]["time_sec"] - swing_rows[0]["time_sec"],
        "mean_sole_roll_rad": mean(roll_series),
        "mean_abs_sole_roll_rad": mean(abs_roll_series),
        "std_sole_roll_rad": stddev(roll_series),
        "max_abs_sole_roll_rad": max(abs_roll_series),
        "min_sole_roll_rad": min(roll_series),
        "max_sole_roll_rad": max(roll_series),
        "mean_sole_pitch_rad": mean(pitch_series),
        "mean_abs_sole_pitch_rad": mean(abs_pitch_series),
        "std_sole_pitch_rad": stddev(pitch_series),
        "max_abs_sole_pitch_rad": max(abs_pitch_series),
        "min_sole_pitch_rad": min(pitch_series),
        "max_sole_pitch_rad": max(pitch_series),
        "mean_rel_height_m": mean(rel_height_series),
        "max_rel_height_m": max(rel_height_series),
        "peak_clearance_time_sec": peak_clearance_row["time_sec"],
        "peak_clearance_phase_fraction": ROUND3A.phase_fraction(peak_clearance_row),
        "roll_at_peak_clearance_rad": peak_clearance_row[f"{swing_side}_sole_roll"],
        "pitch_at_peak_clearance_rad": peak_clearance_row[f"{swing_side}_sole_pitch"],
        "roll_at_minus_100ms_rad": pre100_row[f"{swing_side}_sole_roll"],
        "pitch_at_minus_100ms_rad": pre100_row[f"{swing_side}_sole_pitch"],
        "roll_at_minus_50ms_rad": pre50_row[f"{swing_side}_sole_roll"],
        "pitch_at_minus_50ms_rad": pre50_row[f"{swing_side}_sole_pitch"],
        "roll_at_minus_20ms_rad": pre20_row[f"{swing_side}_sole_roll"],
        "pitch_at_minus_20ms_rad": pre20_row[f"{swing_side}_sole_pitch"],
        "roll_at_touch_rad": touchdown_row[f"{swing_side}_sole_roll"],
        "pitch_at_touch_rad": touchdown_row[f"{swing_side}_sole_pitch"],
        "roll_sign_at_touch": sign_label(touchdown_row[f"{swing_side}_sole_roll"]),
    }, swing_rows


def build_profiles(dataset_name, diag_filename, side, swing_rows):
    profiles = []
    for bin_idx in range(PROFILE_BINS):
        phase = bin_idx / (PROFILE_BINS - 1)
        sole_roll = profile_sample(swing_rows, f"{side}_sole_roll", phase)
        sole_pitch = profile_sample(swing_rows, f"{side}_sole_pitch", phase)
        rel_height = profile_sample(swing_rows, f"{side}_rel_height", phase)
        profiles.append(
            {
                "dataset": dataset_name,
                "diag_filename": diag_filename,
                "side": side,
                "phase_bin": bin_idx,
                "norm_phase": phase,
                "sole_roll_rad": sole_roll,
                "sole_pitch_rad": sole_pitch,
                "abs_sole_roll_rad": abs(sole_roll),
                "abs_sole_pitch_rad": abs(sole_pitch),
                "rel_height_m": rel_height,
            }
        )
    return profiles


def aggregate_profiles(profile_rows):
    buckets = defaultdict(list)
    for row in profile_rows:
        key = (row["dataset"], row["side"], row["phase_bin"])
        buckets[key].append(row)
    aggregated = []
    for (dataset, side, phase_bin), rows in sorted(buckets.items()):
        aggregated.append(
            {
                "dataset": dataset,
                "side": side,
                "phase_bin": phase_bin,
                "norm_phase": rows[0]["norm_phase"],
                "mean_sole_roll_rad": mean([row["sole_roll_rad"] for row in rows]),
                "mean_abs_sole_roll_rad": mean([row["abs_sole_roll_rad"] for row in rows]),
                "mean_sole_pitch_rad": mean([row["sole_pitch_rad"] for row in rows]),
                "mean_abs_sole_pitch_rad": mean([row["abs_sole_pitch_rad"] for row in rows]),
                "mean_rel_height_m": mean([row["rel_height_m"] for row in rows]),
            }
        )
    return aggregated


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, event_rows, profile_rows):
    event_by_dataset = defaultdict(list)
    profile_by_dataset = defaultdict(list)
    for row in event_rows:
        event_by_dataset[row["dataset"]].append(row)
    for row in profile_rows:
        profile_by_dataset[row["dataset"]].append(row)

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Swing Attitude Cross-Kp Compare\n\n")
        handle.write("- Scope: first 4 touchdown-aligned swing phases only\n")
        handle.write(
            f"- Airborne window rule: touchdown前 `{SWING_START_BEFORE_TOUCH_SEC:.2f}s` 到 `{SWING_END_BEFORE_TOUCH_SEC:.2f}s`，优先使用 `rel_height >= {AIRBORNE_REL_HEIGHT_MIN_M:.2f} m` 的腾空行\n\n"
        )
        for dataset_name, rows in event_by_dataset.items():
            profile_dataset_rows = profile_by_dataset[dataset_name]
            handle.write(f"## {dataset_name}\n\n")
            handle.write(f"- Touchdowns analyzed: `{len(rows)}`\n")
            handle.write(f"- Mean abs sole roll during swing: `{format_float(mean([row['mean_abs_sole_roll_rad'] for row in rows]))}` rad\n")
            handle.write(f"- Mean abs sole pitch during swing: `{format_float(mean([row['mean_abs_sole_pitch_rad'] for row in rows]))}` rad\n")
            handle.write(f"- Mean max abs sole roll during swing: `{format_float(mean([row['max_abs_sole_roll_rad'] for row in rows]))}` rad\n")
            handle.write(f"- Mean max abs sole pitch during swing: `{format_float(mean([row['max_abs_sole_pitch_rad'] for row in rows]))}` rad\n")
            handle.write(f"- Mean roll at -50 ms: `{format_float(mean([row['roll_at_minus_50ms_rad'] for row in rows]))}` rad\n")
            handle.write(f"- Mean pitch at -50 ms: `{format_float(mean([row['pitch_at_minus_50ms_rad'] for row in rows]))}` rad\n")
            handle.write(f"- Mean roll at touchdown: `{format_float(mean([row['roll_at_touch_rad'] for row in rows]))}` rad\n")
            handle.write(f"- Mean pitch at touchdown: `{format_float(mean([row['pitch_at_touch_rad'] for row in rows]))}` rad\n")
            handle.write(f"- Touchdown roll sign counts: `{dict(Counter(row['roll_sign_at_touch'] for row in rows))}`\n\n")

            for side in ("left", "right"):
                side_rows = [row for row in rows if row["side"] == side]
                if not side_rows:
                    continue
                handle.write(f"### {side}\n\n")
                handle.write(f"- Mean abs swing roll: `{format_float(mean([row['mean_abs_sole_roll_rad'] for row in side_rows]))}` rad\n")
                handle.write(f"- Mean abs swing pitch: `{format_float(mean([row['mean_abs_sole_pitch_rad'] for row in side_rows]))}` rad\n")
                handle.write(f"- Mean peak-clearance roll: `{format_float(mean([row['roll_at_peak_clearance_rad'] for row in side_rows]))}` rad\n")
                handle.write(f"- Mean peak-clearance pitch: `{format_float(mean([row['pitch_at_peak_clearance_rad'] for row in side_rows]))}` rad\n")
                handle.write(f"- Mean roll at -20 ms: `{format_float(mean([row['roll_at_minus_20ms_rad'] for row in side_rows]))}` rad\n")
                handle.write(f"- Mean pitch at -20 ms: `{format_float(mean([row['pitch_at_minus_20ms_rad'] for row in side_rows]))}` rad\n\n")

            mid_rows = [row for row in profile_dataset_rows if row["phase_bin"] == (PROFILE_BINS - 1) // 2]
            if mid_rows:
                handle.write("### Mid-Swing Snapshot\n\n")
                for row in sorted(mid_rows, key=lambda item: item["side"]):
                    handle.write(
                        f"- `{row['side']}` phase `{format_float(row['norm_phase'], 2)}`: "
                        f"roll `{format_float(row['mean_sole_roll_rad'])}` rad, "
                        f"pitch `{format_float(row['mean_sole_pitch_rad'])}` rad, "
                        f"rel_height `{format_float(row['mean_rel_height_m'])}` m\n"
                    )
                handle.write("\n")


def main():
    event_rows = []
    profile_rows = []
    for dataset_name, diag_filename in DATASETS:
        _, rows, events = load_rows(diag_filename)
        for event in events:
            event_row, swing_rows = summarize_event(dataset_name, diag_filename, rows, event)
            event_rows.append(event_row)
            profile_rows.extend(build_profiles(dataset_name, diag_filename, event_row["side"], swing_rows))

    aggregated_profile_rows = aggregate_profiles(profile_rows)

    event_csv = os.path.join(OUT_DIR, "round3_swing_attitude_cross_kp_compare_event.csv")
    profile_csv = os.path.join(OUT_DIR, "round3_swing_attitude_cross_kp_compare_profile.csv")
    summary_md = os.path.join(OUT_DIR, "round3_swing_attitude_cross_kp_compare.md")

    write_csv(event_csv, event_rows)
    write_csv(profile_csv, aggregated_profile_rows)
    write_summary(summary_md, event_rows, aggregated_profile_rows)

    print(event_csv)
    print(profile_csv)
    print(summary_md)


if __name__ == "__main__":
    main()
