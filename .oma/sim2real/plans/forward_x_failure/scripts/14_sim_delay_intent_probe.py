import csv
import glob
import math
import os
from bisect import bisect_left
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
SIM_LOG_DIR = os.path.join(BASE_DIR, "test_logs", "data_csv", "sim")
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "sim")

MAX_LAG_SEC = 0.25
MIN_SAMPLE_POINTS = 16
RAW_FLATTEN_MARGIN_RAD = 0.02
EFFECTIVE_DELAY_SEC = 0.020
HIGH_TRACKING_ERR_RAD = 0.12


def mean(values):
    valid = [v for v in values if not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def stddev(values):
    valid = [v for v in values if not math.isnan(v)]
    if len(valid) < 2:
        return 0.0 if valid else math.nan
    mu = mean(valid)
    return math.sqrt(sum((v - mu) ** 2 for v in valid) / (len(valid) - 1))


def median(values):
    values = sorted(values)
    if not values:
        return math.nan
    mid = len(values) // 2
    if len(values) % 2 == 1:
        return values[mid]
    return 0.5 * (values[mid - 1] + values[mid])


def format_float(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def parse_scalar(key, value):
    if value is None or value == "":
        return math.nan if key != "timestamp_ns" else None
    if key == "timestamp_ns":
        return int(value)
    return float(value)


def load_csv(path):
    rows = []
    with open(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {}
            for key, value in raw.items():
                if key is None:
                    continue
                row[key] = parse_scalar(key, value)
            if row.get("timestamp_ns") is None:
                continue
            row["time_sec"] = row["timestamp_ns"] / 1e9
            rows.append(row)
    if not rows:
        raise RuntimeError(f"No rows loaded from {path}")
    return rows


def load_header(path):
    with open(path, "r", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader)


def extract_suffix(path, prefix):
    basename = os.path.basename(path)
    if not basename.startswith(prefix):
        return None
    return basename[len(prefix) :].replace(".csv", "")


def find_latest_pair():
    joint_files = glob.glob(os.path.join(SIM_LOG_DIR, "t23_joint_*.csv"))
    current_files = glob.glob(os.path.join(SIM_LOG_DIR, "tm_raw_motor_current_*.csv"))

    joint_map = {extract_suffix(path, "t23_joint_"): path for path in joint_files}
    current_map = {extract_suffix(path, "tm_raw_motor_current_"): path for path in current_files}

    common_suffixes = sorted(set(joint_map) & set(current_map))
    if not common_suffixes:
        raise FileNotFoundError("No matching t23_joint / tm_raw_motor_current pair found under sim/")
    suffix = common_suffixes[-1]
    return suffix, joint_map[suffix], current_map[suffix]


def interpolate_series(source_times, source_values, target_times):
    if len(source_times) != len(source_values):
        raise ValueError("Source time/value length mismatch")
    if not source_times:
        return []
    if len(source_times) == 1:
        return [source_values[0] for _ in target_times]

    out = []
    left = 0
    for t in target_times:
        while left + 1 < len(source_times) and source_times[left + 1] < t:
            left += 1
        if t <= source_times[0]:
            out.append(source_values[0])
            continue
        if t >= source_times[-1]:
            out.append(source_values[-1])
            continue
        right = bisect_left(source_times, t, lo=left, hi=len(source_times))
        if right <= left:
            out.append(source_values[left])
            continue
        t0 = source_times[left]
        t1 = source_times[right]
        v0 = source_values[left]
        v1 = source_values[right]
        if t1 == t0:
            out.append(v0)
        else:
            alpha = (t - t0) / (t1 - t0)
            out.append(v0 * (1.0 - alpha) + v1 * alpha)
    return out


def zscore(values):
    valid = [v for v in values if not math.isnan(v)]
    if not valid:
        return values
    mu = mean(valid)
    sigma = stddev(valid)
    if sigma == 0.0 or math.isnan(sigma):
        return [0.0 for _ in values]
    return [(v - mu) / sigma for v in values]


def first_differences(values):
    if len(values) < 2:
        return []
    return [values[i + 1] - values[i] for i in range(len(values) - 1)]


def best_lag_samples(x, y, max_lag_samples):
    x = zscore(first_differences(x))
    y = zscore(first_differences(y))
    n = min(len(x), len(y))
    if n < MIN_SAMPLE_POINTS:
        return math.nan, math.nan
    x = x[:n]
    y = y[:n]

    best_lag = 0
    best_corr = -1e9
    for lag in range(0, max_lag_samples + 1):
        if lag > 0:
            xs = x[: len(x) - lag]
            ys = y[lag:]
        else:
            xs = x
            ys = y
        if len(xs) < MIN_SAMPLE_POINTS:
            continue
        corr = sum(a * b for a, b in zip(xs, ys)) / len(xs)
        if corr > best_corr:
            best_corr = corr
            best_lag = lag
    return best_lag, best_corr


def flattening_intent(raw_value: float, q_value: float) -> bool:
    if math.isnan(raw_value) or math.isnan(q_value):
        return False
    if raw_value * q_value <= 0.0:
        return True
    return abs(raw_value) + RAW_FLATTEN_MARGIN_RAD < abs(q_value)


def joint_group(joint_name):
    if "ankle" in joint_name:
        return "ankle"
    if "knee" in joint_name:
        return "knee"
    if "hip" in joint_name:
        return "hip"
    return "other"


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    suffix, joint_path, current_path = find_latest_pair()

    joint_rows = load_csv(joint_path)
    current_rows = load_csv(current_path)

    joint_times = [row["time_sec"] for row in joint_rows]
    current_times = [row["time_sec"] for row in current_rows]
    dt_joint = median([joint_times[i + 1] - joint_times[i] for i in range(len(joint_times) - 1)])
    dt_current = median([current_times[i + 1] - current_times[i] for i in range(len(current_times) - 1)])
    delay_frames = max(1, int(round(EFFECTIVE_DELAY_SEC / dt_joint)))
    max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt_joint, 1e-6))))

    header = load_header(joint_path)
    joint_names = sorted(
        key[len("target_") :]
        for key in header
        if key.startswith("target_") and not key.startswith("target_lpf_")
    )

    per_joint_rows = []
    for joint_name in joint_names:
        target_series = [row[f"target_{joint_name}"] for row in joint_rows]
        pos_series = [row[f"pos_{joint_name}"] for row in joint_rows]
        current_series = interpolate_series(
            current_times,
            [row[joint_name] for row in current_rows],
            joint_times,
        )

        target_pos_lag, target_pos_corr = best_lag_samples(target_series, pos_series, max_lag_samples)
        current_pos_lag, current_pos_corr = best_lag_samples(current_series, pos_series, max_lag_samples)
        target_current_lag, target_current_corr = best_lag_samples(target_series, current_series, max_lag_samples)

        flatten_flags = []
        delayed_errs = []
        high_err_flatten_flags = []
        for idx in range(delay_frames, len(joint_rows)):
            delayed_target = target_series[idx - delay_frames]
            delayed_pos = pos_series[idx - delay_frames]
            touch_pos = pos_series[idx]
            flatten_flag = 1 if flattening_intent(delayed_target, delayed_pos) else 0
            flatten_flags.append(flatten_flag)
            delayed_err = abs(delayed_target - touch_pos)
            delayed_errs.append(delayed_err)
            if delayed_err >= HIGH_TRACKING_ERR_RAD:
                high_err_flatten_flags.append(flatten_flag)

        per_joint_rows.append(
            {
                "joint": joint_name,
                "group": joint_group(joint_name),
                "target_to_pos_lag_ms": target_pos_lag * dt_joint * 1000.0 if not math.isnan(target_pos_lag) else math.nan,
                "target_to_pos_corr": target_pos_corr,
                "target_to_current_lag_ms": target_current_lag * dt_joint * 1000.0 if not math.isnan(target_current_lag) else math.nan,
                "target_to_current_corr": target_current_corr,
                "current_to_pos_lag_ms": current_pos_lag * dt_joint * 1000.0 if not math.isnan(current_pos_lag) else math.nan,
                "current_to_pos_corr": current_pos_corr,
                "target_pos_rms_err_rad": math.sqrt(mean([(t - p) ** 2 for t, p in zip(target_series, pos_series)])),
                "target_abs_mean_rad": mean([abs(v) for v in target_series]),
                "pos_abs_mean_rad": mean([abs(v) for v in pos_series]),
                "effective_delay_flattening_intent_ratio": mean(flatten_flags),
                "effective_delay_tracking_err_mean_rad": mean(delayed_errs),
                "high_err_sample_count": len(high_err_flatten_flags),
                "high_err_flattening_intent_ratio": mean(high_err_flatten_flags),
                "sample_dt_ms": dt_joint * 1000.0,
            }
        )

    grouped = defaultdict(list)
    for row in per_joint_rows:
        grouped[row["group"]].append(row)

    summary_rows = []
    for group, rows in grouped.items():
        summary_rows.append(
            {
                "group": group,
                "joint_count": len(rows),
                "mean_target_to_pos_lag_ms": mean([row["target_to_pos_lag_ms"] for row in rows]),
                "mean_target_to_current_lag_ms": mean([row["target_to_current_lag_ms"] for row in rows]),
                "mean_current_to_pos_lag_ms": mean([row["current_to_pos_lag_ms"] for row in rows]),
                "mean_target_pos_rms_err_rad": mean([row["target_pos_rms_err_rad"] for row in rows]),
                "mean_effective_delay_flattening_intent_ratio": mean([row["effective_delay_flattening_intent_ratio"] for row in rows]),
                "mean_high_err_flattening_intent_ratio": mean([row["high_err_flattening_intent_ratio"] for row in rows]),
            }
        )

    per_joint_csv = os.path.join(OUT_DIR, f"sim_delay_intent_probe_{suffix}.csv")
    summary_csv = os.path.join(OUT_DIR, f"sim_delay_intent_probe_{suffix}_summary.csv")
    summary_md = os.path.join(OUT_DIR, f"sim_delay_intent_probe_{suffix}.md")

    write_csv(per_joint_csv, per_joint_rows)
    write_csv(summary_csv, summary_rows)

    with open(summary_md, "w", encoding="utf-8") as handle:
        handle.write("# Sim Delay And Intent Probe\n\n")
        handle.write(f"- Source joint log: `{joint_path}`\n")
        handle.write(f"- Source motor-current log: `{current_path}`\n")
        handle.write(f"- Shared suffix: `{suffix}`\n")
        handle.write(f"- Joint sample dt: `{format_float(dt_joint * 1000.0, 3)} ms`\n")
        handle.write(f"- Current sample dt: `{format_float(dt_current * 1000.0, 3)} ms`\n")
        handle.write(f"- Delay compensation proxy: `{format_float(EFFECTIVE_DELAY_SEC * 1000.0, 0)} ms`\n")
        handle.write(f"- High tracking error threshold: `{format_float(HIGH_TRACKING_ERR_RAD, 2)} rad`\n\n")

        handle.write("## Scope And Limits\n\n")
        handle.write("- This reuses the `06` lag-reading style on sim logs, but only `target / pos / motor current` are available.\n")
        handle.write("- This does **not** reproduce the full `03` touchdown foot-flat analysis, because sim logs here do not contain `base_euler`, contact state, or FK-derived sole attitude.\n")
        handle.write("- The `03` reference used here is only the joint-space `flattening_intent(target, pos)` logic, as a simplified command-sufficiency proxy.\n\n")

        handle.write("## Per-Joint Summary\n\n")
        handle.write("| joint | group | target->pos ms | target->current ms | current->pos ms | target-pos rms rad | flatten intent ratio | high-err flatten ratio |\n")
        handle.write("|---|---|---:|---:|---:|---:|---:|---:|\n")
        for row in per_joint_rows:
            handle.write(
                f"| {row['joint']} | {row['group']} | {format_float(row['target_to_pos_lag_ms'])} | "
                f"{format_float(row['target_to_current_lag_ms'])} | {format_float(row['current_to_pos_lag_ms'])} | "
                f"{format_float(row['target_pos_rms_err_rad'])} | {format_float(row['effective_delay_flattening_intent_ratio'])} | "
                f"{format_float(row['high_err_flattening_intent_ratio'])} |\n"
            )

        handle.write("\n## Group Summary\n\n")
        handle.write("| group | joints | mean target->pos ms | mean target->current ms | mean current->pos ms | mean rms err rad | mean flatten intent ratio | mean high-err flatten ratio |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in sorted(summary_rows, key=lambda item: item["group"]):
            handle.write(
                f"| {row['group']} | {row['joint_count']} | {format_float(row['mean_target_to_pos_lag_ms'])} | "
                f"{format_float(row['mean_target_to_current_lag_ms'])} | {format_float(row['mean_current_to_pos_lag_ms'])} | "
                f"{format_float(row['mean_target_pos_rms_err_rad'])} | {format_float(row['mean_effective_delay_flattening_intent_ratio'])} | "
                f"{format_float(row['mean_high_err_flattening_intent_ratio'])} |\n"
            )

        handle.write("\n## Reading Guide\n\n")
        handle.write("- `target->pos` is the closest sim counterpart to `06`'s total execution lag.\n")
        handle.write("- `target->current` and `current->pos` are only rough proxies here, because the second file is motor current, not actuator position/state.\n")
        handle.write("- `flatten intent ratio` means how often the delayed target is trying to pull the joint back toward zero / the opposite side, following `03`'s `flattening_intent` rule.\n")
        handle.write("- `high-err flatten ratio` restricts that same check to samples whose delayed tracking error is already large, which is the closer proxy to asking whether `command_not_flat` is still happening when error is nontrivial.\n")

    print(per_joint_csv)
    print(summary_csv)
    print(summary_md)


if __name__ == "__main__":
    main()
