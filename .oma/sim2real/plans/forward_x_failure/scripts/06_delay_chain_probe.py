import csv
import glob
import math
import os
import re
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
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
LOG_DIR = os.path.join(BASE_DIR, "test_logs", "data_csv")
MAX_LAG_SEC = 0.25
MIN_SAMPLE_POINTS = 16
AUTOCORR_MIN_PERIOD_SEC = 0.08
AUTOCORR_MAX_PERIOD_SEC = 2.5


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


def find_latest_triplet():
    action_files = glob.glob(os.path.join(LOG_DIR, "t25_action_*.csv"))
    joint_files = glob.glob(os.path.join(LOG_DIR, "t23_joint_*.csv"))
    current_files = glob.glob(os.path.join(LOG_DIR, "t3_current_*.csv"))

    action_map = {extract_suffix(path, "t25_action_"): path for path in action_files}
    joint_map = {extract_suffix(path, "t23_joint_"): path for path in joint_files}
    current_map = {extract_suffix(path, "t3_current_"): path for path in current_files}

    common_suffixes = sorted(set(action_map) & set(joint_map) & set(current_map))
    if not common_suffixes:
        raise FileNotFoundError("No matching t25_action / t23_joint / t3_current triplet found")
    suffix = common_suffixes[-1]
    return suffix, action_map[suffix], joint_map[suffix], current_map[suffix]


def median(values):
    values = sorted(values)
    if not values:
        return math.nan
    mid = len(values) // 2
    if len(values) % 2 == 1:
        return values[mid]
    return 0.5 * (values[mid - 1] + values[mid])


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


def safe_float(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return math.nan
    return float(value)


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


def dominant_period_sec(values, dt):
    if len(values) < MIN_SAMPLE_POINTS:
        return math.nan, math.nan
    x = zscore([v - mean(values) for v in values])
    n = len(x)
    min_lag = max(1, int(round(AUTOCORR_MIN_PERIOD_SEC / dt)))
    max_lag = min(n // 2, int(round(AUTOCORR_MAX_PERIOD_SEC / dt)))
    if max_lag <= min_lag:
        return math.nan, math.nan
    best_lag = None
    best_corr = -1e9
    for lag in range(min_lag, max_lag + 1):
        xs = x[:-lag]
        ys = x[lag:]
        if len(xs) < MIN_SAMPLE_POINTS:
            continue
        corr = sum(a * b for a, b in zip(xs, ys)) / len(xs)
        if corr > best_corr:
            best_corr = corr
            best_lag = lag
    if best_lag is None or best_corr < 0.2:
        return math.nan, best_corr
    return best_lag * dt, best_corr


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


def format_float(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def main():
    suffix, action_path, joint_path, current_path = find_latest_triplet()

    action_rows = load_csv(action_path)
    joint_rows = load_csv(joint_path)
    current_rows = load_csv(current_path)

    joint_times = [row["time_sec"] for row in joint_rows]
    action_times = [row["time_sec"] for row in action_rows]
    current_times = [row["time_sec"] for row in current_rows]

    dt_joint = median([joint_times[i + 1] - joint_times[i] for i in range(len(joint_times) - 1)])
    dt_action = median([action_times[i + 1] - action_times[i] for i in range(len(action_times) - 1)])
    dt_current = median([current_times[i + 1] - current_times[i] for i in range(len(current_times) - 1)])
    max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt_joint, 1e-6))))

    action_header = load_header(action_path)
    joint_names = sorted(
        key[len("action_") :]
        for key in action_header
        if key.startswith("action_") and key != "clip_count"
    )

    rows = []
    for joint_name in joint_names:
        action_series = interpolate_series(
            action_times,
            [safe_float(row[f"action_{joint_name}"]) for row in action_rows],
            joint_times,
        )
        target_series = [safe_float(row[f"target_{joint_name}"]) for row in joint_rows]
        pos_series = [safe_float(row[f"pos_{joint_name}"]) for row in joint_rows]
        vel_series = [safe_float(row[f"vel_{joint_name}"]) for row in joint_rows]
        current_series = interpolate_series(
            current_times,
            [safe_float(row[f"current_{joint_name}"]) for row in current_rows],
            joint_times,
        )

        action_target_lag, action_target_corr = best_lag_samples(action_series, target_series, max_lag_samples)
        target_pos_lag, target_pos_corr = best_lag_samples(target_series, pos_series, max_lag_samples)
        target_current_lag, target_current_corr = best_lag_samples(target_series, current_series, max_lag_samples)
        current_pos_lag, current_pos_corr = best_lag_samples(current_series, pos_series, max_lag_samples)

        target_period, target_period_corr = dominant_period_sec(target_series, dt_joint)
        current_period, current_period_corr = dominant_period_sec(current_series, dt_joint)
        pos_period, pos_period_corr = dominant_period_sec(pos_series, dt_joint)

        rows.append(
            {
                "joint": joint_name,
                "group": joint_group(joint_name),
                "action_to_target_lag_samples": action_target_lag,
                "action_to_target_lag_ms": action_target_lag * dt_joint * 1000.0 if not math.isnan(action_target_lag) else math.nan,
                "action_to_target_corr": action_target_corr,
                "target_to_pos_lag_samples": target_pos_lag,
                "target_to_pos_lag_ms": target_pos_lag * dt_joint * 1000.0 if not math.isnan(target_pos_lag) else math.nan,
                "target_to_pos_corr": target_pos_corr,
                "target_to_current_lag_samples": target_current_lag,
                "target_to_current_lag_ms": target_current_lag * dt_joint * 1000.0 if not math.isnan(target_current_lag) else math.nan,
                "target_to_current_corr": target_current_corr,
                "current_to_pos_lag_samples": current_pos_lag,
                "current_to_pos_lag_ms": current_pos_lag * dt_joint * 1000.0 if not math.isnan(current_pos_lag) else math.nan,
                "current_to_pos_corr": current_pos_corr,
                "target_dominant_period_sec": target_period,
                "target_dominant_freq_hz": 1.0 / target_period if not math.isnan(target_period) and target_period > 0 else math.nan,
                "target_dominant_corr": target_period_corr,
                "current_dominant_period_sec": current_period,
                "current_dominant_freq_hz": 1.0 / current_period if not math.isnan(current_period) and current_period > 0 else math.nan,
                "current_dominant_corr": current_period_corr,
                "pos_dominant_period_sec": pos_period,
                "pos_dominant_freq_hz": 1.0 / pos_period if not math.isnan(pos_period) and pos_period > 0 else math.nan,
                "pos_dominant_corr": pos_period_corr,
                "target_pos_rms_err": math.sqrt(mean([(t - p) ** 2 for t, p in zip(target_series, pos_series)])),
                "target_current_rms_err": math.sqrt(mean([(t - c) ** 2 for t, c in zip(target_series, current_series)])),
                "current_pos_rms_err": math.sqrt(mean([(c - p) ** 2 for c, p in zip(current_series, pos_series)])),
                "sample_dt_sec": dt_joint,
                "sample_dt_action_sec": dt_action,
                "sample_dt_current_sec": dt_current,
                "window_samples": len(joint_times),
            }
        )

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["group"]].append(row)

    summary_rows = []
    for group, group_rows in grouped.items():
        summary_rows.append(
            {
                "group": group,
                "joint_count": len(group_rows),
                "mean_action_to_target_lag_ms": mean([row["action_to_target_lag_ms"] for row in group_rows]),
                "mean_target_to_pos_lag_ms": mean([row["target_to_pos_lag_ms"] for row in group_rows]),
                "mean_target_to_current_lag_ms": mean([row["target_to_current_lag_ms"] for row in group_rows]),
                "mean_current_to_pos_lag_ms": mean([row["current_to_pos_lag_ms"] for row in group_rows]),
                "mean_target_dominant_freq_hz": mean([row["target_dominant_freq_hz"] for row in group_rows]),
                "mean_current_dominant_freq_hz": mean([row["current_dominant_freq_hz"] for row in group_rows]),
                "mean_pos_dominant_freq_hz": mean([row["pos_dominant_freq_hz"] for row in group_rows]),
            }
        )

    event_csv = os.path.join(OUT_DIR, f"round3_delay_chain_probe_{suffix}.csv")
    summary_csv = os.path.join(OUT_DIR, f"round3_delay_chain_probe_{suffix}_summary.csv")
    summary_md = os.path.join(OUT_DIR, f"round3_delay_chain_probe_{suffix}.md")

    write_csv(event_csv, rows)
    write_csv(summary_csv, summary_rows)

    with open(summary_md, "w", encoding="utf-8") as handle:
        handle.write("# Delay Chain Probe\n\n")
        handle.write(f"- Source action log: `{action_path}`\n")
        handle.write(f"- Source joint log: `{joint_path}`\n")
        handle.write(f"- Source current log: `{current_path}`\n")
        handle.write(f"- Shared suffix: `{suffix}`\n")
        handle.write(f"- Joint sample dt: `{format_float(dt_joint * 1000.0, 3)} ms`\n")
        handle.write(f"- Action sample dt: `{format_float(dt_action * 1000.0, 3)} ms`\n")
        handle.write(f"- Current sample dt: `{format_float(dt_current * 1000.0, 3)} ms`\n")
        handle.write(f"- Max lag search window: `{format_float(MAX_LAG_SEC * 1000.0, 0)} ms`\n\n")

        handle.write("## Per-Joint Summary\n\n")
        handle.write("| joint | group | action->target ms | target->pos ms | target->current ms | current->pos ms | target freq Hz | current freq Hz | pos freq Hz |\n")
        handle.write("|---|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in rows:
            handle.write(
                f"| {row['joint']} | {row['group']} | {format_float(row['action_to_target_lag_ms'])} | "
                f"{format_float(row['target_to_pos_lag_ms'])} | {format_float(row['target_to_current_lag_ms'])} | "
                f"{format_float(row['current_to_pos_lag_ms'])} | {format_float(row['target_dominant_freq_hz'])} | "
                f"{format_float(row['current_dominant_freq_hz'])} | {format_float(row['pos_dominant_freq_hz'])} |\n"
            )

        handle.write("\n## Group Summary\n\n")
        handle.write("| group | joint_count | mean action->target ms | mean target->pos ms | mean target->current ms | mean current->pos ms |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for row in sorted(summary_rows, key=lambda item: item["group"]):
            handle.write(
                f"| {row['group']} | {row['joint_count']} | {format_float(row['mean_action_to_target_lag_ms'])} | "
                f"{format_float(row['mean_target_to_pos_lag_ms'])} | {format_float(row['mean_target_to_current_lag_ms'])} | "
                f"{format_float(row['mean_current_to_pos_lag_ms'])} |\n"
            )

        handle.write("\n## Interpretation\n\n")
        handle.write("- `action->target` 主要看模型输出到关节目标的链路延迟。如果这里明显大于 0，优先查控制模块输出和记录时序。\n")
        handle.write("- `target->current` 主要看关节目标到电机电流响应的延迟。如果这里大于 `action->target`，更像执行器/通信/驱动链问题。\n")
        handle.write("- `current->pos` 主要看电机侧输出到实际关节位姿的机械响应。如果这里比 `target->current` 更慢，更像并联踝机械/接触/摩擦问题。\n")
        handle.write("- `target->pos` 是总体现象，包含控制、驱动、机构三层延迟，适合和前两段一起看。\n")
        handle.write("- `target/current/pos` 的 dominant freq 只作为节律参考，不作为主因；主因仍看各段 lag 是否在 ankle 上显著高于 knee/hip。\n")

    print(event_csv)
    print(summary_csv)
    print(summary_md)


if __name__ == "__main__":
    main()
