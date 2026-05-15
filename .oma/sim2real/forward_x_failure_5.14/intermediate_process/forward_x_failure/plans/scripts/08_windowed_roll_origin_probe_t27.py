import csv
import importlib.util
import math
import os
from bisect import bisect_left
from collections import Counter


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
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
SWING_WINDOW_SEC = 0.35
SWING_END_BEFORE_TOUCHDOWN_SEC = 0.02
TOUCHDOWN_PRE_SEC = 0.05
TOUCHDOWN_POST_SEC = 0.10
AIRBORNE_REL_HEIGHT_MIN_M = 0.02
MAX_LAG_SEC = 0.20
MIN_SAMPLE_POINTS = 10


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


def glob_sorted(pattern):
    import glob

    return sorted(glob.glob(os.path.join(LOG_DIR, pattern)))


def latest_t27_path():
    matches = glob_sorted("t27_tracking_lag_b1_diag_*.csv")
    if not matches:
        raise FileNotFoundError("No t27_tracking_lag_b1_diag files found")
    return matches[-1]


def extract_suffix(path, prefix):
    basename = os.path.basename(path)
    if not basename.startswith(prefix):
        return None
    return basename[len(prefix) :].replace(".csv", "")


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


def row_at_or_before(rows, target_time):
    for idx in range(len(rows) - 1, -1, -1):
        if rows[idx]["time_sec"] <= target_time:
            return rows[idx]
    return rows[0]


def interpolate_series(source_times, source_values, target_times):
    if not source_times:
        return [math.nan for _ in target_times]
    if len(source_times) == 1:
        return [source_values[0] for _ in target_times]
    out = []
    for t in target_times:
        if t <= source_times[0]:
            out.append(source_values[0])
            continue
        if t >= source_times[-1]:
            out.append(source_values[-1])
            continue
        right = bisect_left(source_times, t)
        left = right - 1
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


def first_differences(values):
    return [values[i + 1] - values[i] for i in range(len(values) - 1)]


def zscore(values):
    valid = [v for v in values if not math.isnan(v)]
    if not valid:
        return values
    mu = mean(valid)
    sigma = stddev(valid)
    if sigma == 0.0 or math.isnan(sigma):
        return [0.0 for _ in values]
    return [(v - mu) / sigma for v in values]


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


def label_source(lag_map):
    ranked = sorted(lag_map.items(), key=lambda item: (-item[1][1], item[1][0]))
    best_source, (best_lag, best_corr) = ranked[0]
    if best_source in ("action", "target"):
        if best_corr >= 0.30:
            return "output_chain_dominant"
    if best_source in ("current", "pos"):
        if best_corr >= 0.30:
            return "execution_chain_dominant"
    return "mixed_or_uncertain"


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


def format_float(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def add_time_window_stats(prefix, rows, series_map, out):
    for signal_name, values in series_map.items():
        valid = [v for v in values if not math.isnan(v)]
        out[f"{prefix}_{signal_name}_mean"] = mean(values)
        out[f"{prefix}_{signal_name}_mean_abs"] = mean([abs(v) for v in values])
        out[f"{prefix}_{signal_name}_std"] = stddev(values)
        out[f"{prefix}_{signal_name}_min"] = min(valid) if valid else math.nan
        out[f"{prefix}_{signal_name}_max"] = max(valid) if valid else math.nan
    out[f"{prefix}_sample_count"] = len(rows)
    out[f"{prefix}_duration_sec"] = rows[-1]["time_sec"] - rows[0]["time_sec"] if len(rows) >= 2 else 0.0


def classify_event(rows, event, side):
    swing_start = event.timestamp_sec - SWING_WINDOW_SEC
    swing_end = event.timestamp_sec - SWING_END_BEFORE_TOUCHDOWN_SEC
    touchdown_start = event.timestamp_sec - TOUCHDOWN_PRE_SEC
    touchdown_end = event.timestamp_sec + TOUCHDOWN_POST_SEC

    swing_rows = [
        row
        for row in rows
        if swing_start <= row["time_sec"] <= swing_end
        and row[f"{side}_contact"] == 0
        and row[f"{side}_rel_height"] >= AIRBORNE_REL_HEIGHT_MIN_M
    ]
    touchdown_rows = [row for row in rows if touchdown_start <= row["time_sec"] <= touchdown_end]
    if not swing_rows:
        swing_rows = [row_at_or_before(rows, 0.5 * (swing_start + swing_end))]
    if not touchdown_rows:
        touchdown_rows = [row_at_or_before(rows, 0.5 * (touchdown_start + touchdown_end))]

    series_names = [
        f"action_{side}_ankle_roll_joint",
        f"pos_des_raw_{side}_ankle_roll_joint",
        f"pos_des_lpf_{side}_ankle_roll_joint",
        f"pos_{side}_ankle_roll_joint",
        f"{side}_sole_roll",
    ]

    window_outs = {}
    for window_name, window_rows in (("swing", swing_rows), ("touchdown", touchdown_rows)):
        series_map = {name: [row[name] for row in window_rows] for name in series_names}
        row_out = {}
        add_time_window_stats(window_name, window_rows, series_map, row_out)
        sole = series_map[f"{side}_sole_roll"]
        lag_sources = {}
        dt = rows[1]["time_sec"] - rows[0]["time_sec"] if len(rows) >= 2 else 1e-3
        max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt, 1e-6))))
        for source in ("action", "pos_des_raw", "pos_des_lpf", "pos"):
            src_series = series_map[f"{source}_{side}_ankle_roll_joint"]
            lag, corr = best_lag_samples(src_series, sole, max_lag_samples=max_lag_samples)
            row_out[f"{window_name}_{source}_to_sole_lag_samples"] = lag
            row_out[f"{window_name}_{source}_to_sole_lag_ms"] = lag * dt * 1000.0 if not math.isnan(lag) else math.nan
            row_out[f"{window_name}_{source}_to_sole_corr"] = corr
            lag_sources[source] = (lag, corr)
        row_out[f"{window_name}_sole_source_guess"] = label_source(lag_sources)
        row_out[f"{window_name}_sole_roll_sign"] = "negative" if mean(sole) < 0 else "positive"
        row_out[f"{window_name}_sole_roll_mean_abs"] = mean([abs(v) for v in sole])
        row_out[f"{window_name}_sole_roll_std"] = stddev(sole)
        row_out[f"{window_name}_sole_roll_min"] = min(sole)
        row_out[f"{window_name}_sole_roll_max"] = max(sole)
        window_outs[window_name] = row_out

    return {
        "side": side,
        "touchdown_time_sec": event.timestamp_sec,
        "first_contact_time_sec": event.first_contact_time_sec,
        "touchdown_source": event.source,
        **window_outs["swing"],
        **window_outs["touchdown"],
    }


def main():
    path = latest_t27_path()
    suffix = extract_suffix(path, "t27_tracking_lag_b1_diag_")
    rows = load_csv(path)
    ROUND3A.attach_fk_metrics(rows)
    events = ROUND3A.detect_touchdowns(rows)
    events = sorted(events, key=lambda event: event.timestamp_sec)[:4]

    event_rows = [classify_event(rows, event, event.side) for event in events]

    out_csv = os.path.join(OUT_DIR, f"round3_windowed_roll_origin_probe_t27_{suffix}.csv")
    out_md = os.path.join(OUT_DIR, f"round3_windowed_roll_origin_probe_t27_{suffix}.md")
    write_csv(out_csv, event_rows)

    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("# Windowed Roll Origin Probe on t27\n\n")
        handle.write(f"- Source log: `{path}`\n")
        handle.write(f"- Shared suffix: `{suffix}`\n\n")

        handle.write("## Summary\n\n")
        for window_name in ("swing", "touchdown"):
            labels = Counter(row[f"{window_name}_sole_source_guess"] for row in event_rows)
            handle.write(f"- `{window_name}` source guesses: `{dict(labels)}`\n")
        handle.write("\n")

        handle.write("## Per Event\n\n")
        handle.write("| side | touchdown_time_sec | swing sole mean abs | touchdown sole mean abs | swing source guess | touchdown source guess | swing action->sole lag ms | swing raw->sole lag ms | swing lpf->sole lag ms | swing pos->sole lag ms | touchdown action->sole lag ms | touchdown raw->sole lag ms | touchdown lpf->sole lag ms | touchdown pos->sole lag ms |\n")
        handle.write("|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in event_rows:
            handle.write(
                f"| {row['side']} | {format_float(row['touchdown_time_sec'], 3)} | {format_float(row['swing_sole_roll_mean_abs'])} | "
                f"{format_float(row['touchdown_sole_roll_mean_abs'])} | {row['swing_sole_source_guess']} | {row['touchdown_sole_source_guess']} | "
                f"{format_float(row['swing_action_to_sole_lag_ms'])} | {format_float(row['swing_pos_des_raw_to_sole_lag_ms'])} | "
                f"{format_float(row['swing_pos_des_lpf_to_sole_lag_ms'])} | {format_float(row['swing_pos_to_sole_lag_ms'])} | "
                f"{format_float(row['touchdown_action_to_sole_lag_ms'])} | {format_float(row['touchdown_pos_des_raw_to_sole_lag_ms'])} | "
                f"{format_float(row['touchdown_pos_des_lpf_to_sole_lag_ms'])} | {format_float(row['touchdown_pos_to_sole_lag_ms'])} |\n"
            )

        handle.write("\n## Interpretation\n\n")
        handle.write("- 若 swing 窗口里 `sole_roll` 更接近 `action/target`，说明问题更早出现在输出链或映射链。\n")
        handle.write("- 若 touchdown 窗口里 `sole_roll` 更接近 `current/pos`，说明接触阶段更受执行链/机械响应影响。\n")
        handle.write("- 两个窗口若都保留同样的左右镜像 roll 偏置，则底层几何/映射问题仍然存在，延迟只是在放大表现。\n")

    print(out_csv)
    print(out_md)


if __name__ == "__main__":
    main()
