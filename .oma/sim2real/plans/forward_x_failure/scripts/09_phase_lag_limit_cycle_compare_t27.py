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
TOUCHDOWN_PRE_SEC = 0.05
TOUCHDOWN_POST_SEC = 0.10
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


def infer_case_label(suffix: str) -> str:
    mapping = {
        "20260428_152240": "35/0.5 baseline",
        "20260428_161322": "50/0.8 right_roll",
        "20260428_162312": "40/0.8 right_roll",
        "20260428_163825": "25/0.5 right_roll",
        "20260428_164817": "25/0.5 all_ankles",
    }
    return mapping.get(suffix, suffix)


def latest_case_paths():
    files = {}
    for path in glob_sorted("t27_tracking_lag_b1_diag_*.csv"):
        suffix = os.path.basename(path).replace("t27_tracking_lag_b1_diag_", "").replace(".csv", "")
        if suffix in {"20260428_155015", "20260428_155055"}:
            continue
        files[suffix] = path
    return [(infer_case_label(sfx), sfx, path) for sfx, path in sorted(files.items())]


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


def dominant_period_sec(values, dt):
    valid = [v for v in values if not math.isnan(v)]
    if len(valid) < MIN_SAMPLE_POINTS:
        return math.nan, math.nan
    x = [v - mean(valid) for v in values]
    x = zscore(x)
    n = len(x)
    min_lag = max(1, int(round(0.05 / dt)))
    max_lag = min(n // 2, int(round(2.0 / dt)))
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


def phase_loop_area(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if not math.isnan(a) and not math.isnan(b)]
    if len(pairs) < 3:
        return math.nan
    xs_raw = [a for a, _ in pairs]
    ys_raw = [b for _, b in pairs]
    xm = mean(xs_raw)
    ym = mean(ys_raw)
    xs = [v - xm for v in xs_raw]
    ys = [v - ym for v in ys_raw]
    area = 0.0
    for i in range(len(xs) - 1):
        area += xs[i] * ys[i + 1] - xs[i + 1] * ys[i]
    return 0.5 * area


def zero_crossings(values):
    valid = [v for v in values if not math.isnan(v)]
    if len(valid) < 2:
        return 0
    crossings = 0
    prev = valid[0]
    for v in valid[1:]:
        if prev == 0.0:
            prev = v
            continue
        if (prev > 0 and v < 0) or (prev < 0 and v > 0):
            crossings += 1
        prev = v
    return crossings


def classify_event(rows, event, side):
    touchdown_start = event.timestamp_sec - TOUCHDOWN_PRE_SEC
    touchdown_end = event.timestamp_sec + TOUCHDOWN_POST_SEC
    window_rows = [row for row in rows if touchdown_start <= row["time_sec"] <= touchdown_end]
    if not window_rows:
        window_rows = [row_at_or_before(rows, event.timestamp_sec)]

    dt = rows[1]["time_sec"] - rows[0]["time_sec"] if len(rows) >= 2 else 1e-3
    max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt, 1e-6))))
    sole = [row[f"{side}_sole_roll"] for row in window_rows]
    action = [row[f"action_{side}_ankle_roll_joint"] for row in window_rows]
    raw = [row[f"pos_des_raw_{side}_ankle_roll_joint"] for row in window_rows]
    lpf = [row[f"pos_des_lpf_{side}_ankle_roll_joint"] for row in window_rows]
    pos = [row[f"pos_{side}_ankle_roll_joint"] for row in window_rows]

    lag_action, corr_action = best_lag_samples(action, sole, max_lag_samples)
    lag_raw, corr_raw = best_lag_samples(raw, sole, max_lag_samples)
    lag_lpf, corr_lpf = best_lag_samples(lpf, sole, max_lag_samples)
    lag_pos, corr_pos = best_lag_samples(pos, sole, max_lag_samples)
    lag_lpf_to_pos, corr_lpf_to_pos = best_lag_samples(lpf, pos, max_lag_samples)
    lag_pos_to_sole, corr_pos_to_sole = best_lag_samples(pos, sole, max_lag_samples)

    period_sec, period_corr = dominant_period_sec(sole, dt)
    return {
        "case_label": infer_case_label(event.case_suffix) if hasattr(event, "case_suffix") else "unknown",
        "side": side,
        "touchdown_time_sec": event.timestamp_sec,
        "sample_count": len(window_rows),
        "duration_sec": window_rows[-1]["time_sec"] - window_rows[0]["time_sec"] if len(window_rows) >= 2 else 0.0,
        "sole_mean_abs": mean([abs(v) for v in sole]),
        "sole_std": stddev(sole),
        "sole_zero_crossings": zero_crossings(sole),
        "sole_dominant_period_sec": period_sec,
        "sole_dominant_period_corr": period_corr,
        "loop_area_lpf_pos": phase_loop_area(lpf, pos),
        "loop_area_pos_sole": phase_loop_area(pos, sole),
        "action_to_sole_lag_ms": lag_action * dt * 1000.0 if not math.isnan(lag_action) else math.nan,
        "raw_to_sole_lag_ms": lag_raw * dt * 1000.0 if not math.isnan(lag_raw) else math.nan,
        "lpf_to_sole_lag_ms": lag_lpf * dt * 1000.0 if not math.isnan(lag_lpf) else math.nan,
        "pos_to_sole_lag_ms": lag_pos * dt * 1000.0 if not math.isnan(lag_pos) else math.nan,
        "lpf_to_pos_lag_ms": lag_lpf_to_pos * dt * 1000.0 if not math.isnan(lag_lpf_to_pos) else math.nan,
        "pos_to_sole_corr": corr_pos_to_sole,
        "lpf_to_pos_corr": corr_lpf_to_pos,
        "source_guess": label_source({
            "action": (lag_action, corr_action),
            "pos_des_raw": (lag_raw, corr_raw),
            "pos_des_lpf": (lag_lpf, corr_lpf),
            "pos": (lag_pos, corr_pos),
        }),
    }


def label_source(lag_map):
    ranked = sorted(lag_map.items(), key=lambda item: (-item[1][1], item[1][0]))
    best_source, (best_lag, best_corr) = ranked[0]
    if best_source in ("action", "pos_des_raw"):
        if best_corr >= 0.30:
            return "output_chain_dominant"
    if best_source in ("pos_des_lpf", "pos"):
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


def case_paths():
    selected = []
    for label, suffix in [
        ("35/0.5 baseline", "20260428_152240"),
        ("50/0.8 right_roll", "20260428_161322"),
        ("40/0.8 right_roll", "20260428_162312"),
        ("25/0.5 right_roll", "20260428_163825"),
        ("25/0.5 all_ankles", "20260428_164817"),
    ]:
        path = os.path.join(LOG_DIR, f"t27_tracking_lag_b1_diag_{suffix}.csv")
        if os.path.exists(path):
            selected.append((label, suffix, path))
    return selected


def main():
    all_rows = []
    summary_rows = []
    for label, suffix, path in case_paths():
        rows = load_csv(path)
        ROUND3A.attach_fk_metrics(rows)
        events = sorted(ROUND3A.detect_touchdowns(rows), key=lambda e: e.timestamp_sec)[:4]
        event_rows = []
        for event in events:
            event.case_suffix = suffix
            event_rows.append(classify_event(rows, event, event.side))
        all_rows.extend(event_rows)
        summary_rows.append({
            "case_label": label,
            "suffix": suffix,
            "event_count": len(event_rows),
            "mean_sole_mean_abs": mean([r["sole_mean_abs"] for r in event_rows]),
            "mean_sole_zero_crossings": mean([r["sole_zero_crossings"] for r in event_rows]),
            "mean_sole_period_sec": mean([r["sole_dominant_period_sec"] for r in event_rows]),
            "mean_loop_area_lpf_pos": mean([abs(r["loop_area_lpf_pos"]) for r in event_rows]),
            "mean_loop_area_pos_sole": mean([abs(r["loop_area_pos_sole"]) for r in event_rows]),
            "mean_lpf_to_pos_lag_ms": mean([r["lpf_to_pos_lag_ms"] for r in event_rows]),
            "mean_pos_to_sole_lag_ms": mean([r["pos_to_sole_lag_ms"] for r in event_rows]),
            "dominant_source": Counter(r["source_guess"] for r in event_rows).most_common(1)[0][0] if event_rows else "n/a",
        })

    out_csv = os.path.join(OUT_DIR, "round3_t27_phase_lag_limit_cycle_compare.csv")
    out_md = os.path.join(OUT_DIR, "round3_t27_phase_lag_limit_cycle_compare.md")
    write_csv(out_csv, all_rows)

    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("# t27 Phase Lag / Limit Cycle Compare\n\n")
        handle.write("## Summary by case\n\n")
        handle.write("| case | events | mean |sole_roll| | mean zero crossings | mean dominant period (s) | mean |lpf-pos| loop area | mean |pos-sole| loop area | mean lpf->pos lag (ms) | mean pos->sole lag (ms) | dominant source |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
        for row in summary_rows:
            handle.write(
                f"| {row['case_label']} | {row['event_count']} | {format_float(row['mean_sole_mean_abs'])} | "
                f"{format_float(row['mean_sole_zero_crossings'])} | {format_float(row['mean_sole_period_sec'])} | "
                f"{format_float(row['mean_loop_area_lpf_pos'])} | {format_float(row['mean_loop_area_pos_sole'])} | "
                f"{format_float(row['mean_lpf_to_pos_lag_ms'])} | {format_float(row['mean_pos_to_sole_lag_ms'])} | {row['dominant_source']} |\n"
            )

        handle.write("\n## Interpretation\n\n")
        handle.write("- 若高 kp 组的 `lpf->pos` lag、`pos->sole` lag、loop area 和 zero crossings 同时更大，更符合局部相位滞后驱动的限环振荡。\n")
        handle.write("- 若低 kp 组这些指标显著减小，但前进变弱，说明低 kp 是把不稳定压住了，而不是根因消失。\n")
        handle.write("- `sole_roll` 若仍主要判为 `execution_chain_dominant`，说明问题仍主要在执行链/机构响应，不是 output 直接把姿态做坏。\n")

    print(out_csv)
    print(out_md)


if __name__ == "__main__":
    main()
