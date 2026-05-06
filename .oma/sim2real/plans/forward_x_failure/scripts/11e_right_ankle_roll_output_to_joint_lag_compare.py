#!/usr/bin/env python3
from __future__ import annotations

import csv
import glob
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
LOG_DIR = os.path.join(BASE_DIR, "test_logs", "data_csv")
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
SWING_PRE_SEC = 0.35
SWING_POST_SEC = 0.02
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


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def stddev(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if len(valid) < 2:
        return 0.0 if valid else math.nan
    mu = mean(valid)
    return math.sqrt(sum((v - mu) ** 2 for v in valid) / (len(valid) - 1))


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
    return [(v - mu) / sigma if not math.isnan(v) else 0.0 for v in values]


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


def select_window_rows(rows, event_time, window_name):
    if window_name == "swing":
        start_t = event_time - SWING_PRE_SEC
        end_t = event_time - SWING_POST_SEC
    elif window_name == "touchdown":
        start_t = event_time - TOUCHDOWN_PRE_SEC
        end_t = event_time + TOUCHDOWN_POST_SEC
    else:
        raise ValueError(window_name)
    return [row for row in rows if start_t <= row["time_sec"] <= end_t]


def fmt(value, digits=3):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def infer_case_label(filename: str) -> str:
    mapping = {
        "t27_tracking_lag_b1_diag_20260428_152240.csv": "35/0.5 retest_copy",
        "t27_tracking_lag_b1_diag_20260428_155015.csv": "40/0.5 part1_invalid",
        "t27_tracking_lag_b1_diag_20260428_155055.csv": "40/0.5 part2_invalid",
        "t27_tracking_lag_b1_diag_20260428_161322.csv": "50/0.8 right_roll",
        "t27_tracking_lag_b1_diag_20260428_162312.csv": "40/0.8 right_roll",
        "t27_tracking_lag_b1_diag_20260428_163825.csv": "25/0.5 right_roll",
        "t27_tracking_lag_b1_diag_20260428_164817.csv": "25/0.5 all_ankles",
        "t27_tracking_lag_b1_diag_20260429_161248.csv": "25/0.5 all_ankles actuator",
        "t27_tracking_lag_b1_diag_20260430_100024.csv": "25/0.4 all_ankles",
        "t27_tracking_lag_b1_diag_20260430_100314.csv": "30/0.4 all_ankles",
        "t27_tracking_lag_b1_diag_20260430_100705.csv": "35/0.5 all_ankles",
        "t27_tracking_lag_b1_diag_20260430_101404.csv": "40/0.8 all_ankles",
    }
    return mapping.get(filename, "unknown")


def classify_right_event(rows, event, window_name):
    window_rows = select_window_rows(rows, event.timestamp_sec, window_name)
    if len(window_rows) < 2:
        return None
    dt = rows[1]["time_sec"] - rows[0]["time_sec"] if len(rows) >= 2 else 1e-3
    max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt, 1e-6))))
    action = [row["action_right_ankle_roll_joint"] for row in window_rows]
    joint = [row["pos_right_ankle_roll_joint"] for row in window_rows]
    lag, corr = best_lag_samples(action, joint, max_lag_samples)
    lag_ms = lag * dt * 1000.0 if not math.isnan(lag) else math.nan
    return {
        "window": window_name,
        "touchdown_time_sec": event.timestamp_sec,
        "sample_count": len(window_rows),
        "mean_action_abs": mean([abs(v) for v in action]),
        "mean_action_signed": mean(action),
        "action_joint_lag_ms": lag_ms,
        "action_joint_corr": corr,
    }


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


def main():
    files = sorted(glob.glob(os.path.join(LOG_DIR, "t27_tracking_lag_b1_diag_*.csv")))
    detail_rows = []
    summary_rows = []
    skipped_rows = []

    for path in files:
        filename = os.path.basename(path)
        case_label = infer_case_label(filename)
        rows = load_csv(path)
        ROUND3A.attach_fk_metrics(rows)
        events = [e for e in sorted(ROUND3A.detect_touchdowns(rows), key=lambda e: e.timestamp_sec) if e.side == "right"][:4]
        if not events:
            skipped_rows.append({"case_label": case_label, "diag_csv": filename, "reason": "no_right_touchdown_events"})
            continue

        event_rows = []
        for event in events:
            for window_name in ("swing", "touchdown"):
                row = classify_right_event(rows, event, window_name)
                if row is None:
                    continue
                row["case_label"] = case_label
                row["diag_csv"] = filename
                event_rows.append(row)
                detail_rows.append(row)

        grouped = defaultdict(list)
        for row in event_rows:
            grouped[row["window"]].append(row)
        for window_name, items in grouped.items():
            summary_rows.append(
                {
                    "case_label": case_label,
                    "diag_csv": filename,
                    "window": window_name,
                    "events": len(items),
                    "mean_action_abs": mean([r["mean_action_abs"] for r in items]),
                    "mean_action_signed": mean([r["mean_action_signed"] for r in items]),
                    "mean_action_joint_lag_ms": mean([r["action_joint_lag_ms"] for r in items]),
                    "mean_action_joint_corr": mean([r["action_joint_corr"] for r in items]),
                }
            )

    out_csv = os.path.join(OUT_DIR, "round3_right_ankle_roll_action_to_joint_lag_summary.csv")
    out_detail_csv = os.path.join(OUT_DIR, "round3_right_ankle_roll_action_to_joint_lag_detail.csv")
    out_md = os.path.join(OUT_DIR, "round3_right_ankle_roll_action_to_joint_lag_summary.md")
    out_skip_csv = os.path.join(OUT_DIR, "round3_right_ankle_roll_action_to_joint_lag_skipped.csv")
    write_csv(out_csv, summary_rows)
    write_csv(out_detail_csv, detail_rows)
    write_csv(out_skip_csv, skipped_rows)

    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("# Right Ankle Roll Action-to-Joint Lag Summary\n\n")
        handle.write("- Scope: all local `t27_tracking_lag_b1_diag_*.csv` samples.\n")
        handle.write("- Signal pair: `action_right_ankle_roll_joint -> pos_right_ankle_roll_joint`.\n")
        handle.write("- Event selection: first 4 `right` touchdown events per file.\n")
        handle.write("- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.\n\n")
        handle.write("## Summary\n\n")
        handle.write("| case | csv | window | events | mean_abs_action | mean signed action | mean lag (ms) | mean corr |\n")
        handle.write("|---|---|---|---:|---:|---:|---:|---:|\n")
        for row in summary_rows:
            handle.write(
                f"| {row['case_label']} | {row['diag_csv']} | {row['window']} | {int(row['events'])} | "
                f"{fmt(row['mean_action_abs'])} | {fmt(row['mean_action_signed'])} | "
                f"{fmt(row['mean_action_joint_lag_ms'])} | {fmt(row['mean_action_joint_corr'])} |\n"
            )
        handle.write("\n## Skipped\n\n")
        if skipped_rows:
            for row in skipped_rows:
                handle.write(f"- `{row['diag_csv']}`: {row['reason']}\n")
        else:
            handle.write("- none\n")

    print(out_csv)
    print(out_detail_csv)
    print(out_skip_csv)
    print(out_md)


if __name__ == "__main__":
    main()
