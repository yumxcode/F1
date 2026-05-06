#!/usr/bin/env python3
from __future__ import annotations

import csv
import glob
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
SMALL_SIGNAL_THRESH_RAD = 0.10
BIN_WIDTH_RAD = 0.05


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


def select_window_rows(rows, event_time):
    start_t = event_time - SWING_PRE_SEC
    end_t = event_time - SWING_POST_SEC
    return [row for row in rows if start_t <= row["time_sec"] <= end_t]


def fmt(value, digits=4):
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


def detect_right_touchdowns(rows):
    events = []
    prev = 0
    for row in rows:
        curr = int(row.get("right_contact", 0) or 0)
        if curr == 1 and prev == 0:
            events.append(row["time_sec"])
        prev = curr
    return events


def classify_right_event(rows, event_time_sec):
    window_rows = select_window_rows(rows, event_time_sec)
    if len(window_rows) < 2:
        return None
    values = [row["pos_des_raw_right_ankle_roll_joint"] for row in window_rows]
    abs_values = [abs(v) for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not abs_values:
        return None
    return {
        "touchdown_time_sec": event_time_sec,
        "sample_count": len(window_rows),
        "mean_pos_des_raw": mean(values),
        "mean_abs_pos_des_raw": mean(abs_values),
        "std_pos_des_raw": stddev(values),
        "min_pos_des_raw": min(abs_values),
        "max_pos_des_raw": max(abs_values),
        "small_signal_ratio": sum(1 for v in abs_values if v <= SMALL_SIGNAL_THRESH_RAD) / len(abs_values),
        "abs_values": abs_values,
    }


def bin_label(value):
    lower = math.floor(value / BIN_WIDTH_RAD) * BIN_WIDTH_RAD
    upper = lower + BIN_WIDTH_RAD
    return lower, upper


def accumulate_bins(abs_values, rows):
    bins = defaultdict(int)
    for value in abs_values:
        lower, upper = bin_label(value)
        bins[(lower, upper)] += 1
    total = sum(bins.values())
    out = []
    for (lower, upper), count in sorted(bins.items()):
        out.append(
            {
                "bin_start_rad": lower,
                "bin_end_rad": upper,
                "count": count,
                "ratio": count / total if total else math.nan,
            }
        )
    return out


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
    bin_rows = []
    skipped_rows = []

    for path in files:
        filename = os.path.basename(path)
        case_label = infer_case_label(filename)
        rows = load_csv(path)
        events = detect_right_touchdowns(rows)[:4]
        if not events:
            skipped_rows.append({"case_label": case_label, "diag_csv": filename, "reason": "no_right_touchdown_events"})
            continue

        event_rows = []
        case_abs_values = []
        for event in events:
            row = classify_right_event(rows, event)
            if row is None:
                continue
            row["case_label"] = case_label
            row["diag_csv"] = filename
            event_rows.append(row)
            detail_rows.append(row)
            case_abs_values.extend(row.pop("abs_values"))

        if not event_rows:
            skipped_rows.append({"case_label": case_label, "diag_csv": filename, "reason": "no_valid_swing_rows"})
            continue

        summary_rows.append(
            {
                "case_label": case_label,
                "diag_csv": filename,
                "events": len(event_rows),
                "mean_pos_des_raw": mean([r["mean_pos_des_raw"] for r in event_rows]),
                "mean_abs_pos_des_raw": mean([r["mean_abs_pos_des_raw"] for r in event_rows]),
                "mean_small_signal_ratio": mean([r["small_signal_ratio"] for r in event_rows]),
                "min_abs_pos_des_raw": min(r["min_pos_des_raw"] for r in event_rows),
                "max_abs_pos_des_raw": max(r["max_pos_des_raw"] for r in event_rows),
            }
        )

        for row in accumulate_bins(case_abs_values, event_rows):
            row["case_label"] = case_label
            row["diag_csv"] = filename
            bin_rows.append(row)

    out_csv = os.path.join(OUT_DIR, "round3_dead_zone_swing_pos_des_raw_summary.csv")
    out_detail_csv = os.path.join(OUT_DIR, "round3_dead_zone_swing_pos_des_raw_detail.csv")
    out_bin_csv = os.path.join(OUT_DIR, "round3_dead_zone_swing_pos_des_raw_bins_005.csv")
    out_md = os.path.join(OUT_DIR, "round3_dead_zone_swing_pos_des_raw_summary.md")
    out_skip_csv = os.path.join(OUT_DIR, "round3_dead_zone_swing_pos_des_raw_skipped.csv")
    write_csv(out_csv, summary_rows)
    write_csv(out_detail_csv, detail_rows)
    write_csv(out_bin_csv, bin_rows)
    write_csv(out_skip_csv, skipped_rows)

    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("# Swing Dead-Zone Audit on pos_des_raw\n\n")
        handle.write("- Scope: all local `t27_tracking_lag_b1_diag_*.csv` samples.\n")
        handle.write("- Signal: `pos_des_raw_right_ankle_roll_joint` only.\n")
        handle.write("- Event selection: first 4 `right` touchdown events per file.\n")
        handle.write("- Window: `swing = touchdown-350ms .. touchdown-20ms`.\n")
        handle.write(f"- Small-signal threshold: `|pos_des_raw| <= {SMALL_SIGNAL_THRESH_RAD:.2f} rad`.\n\n")
        handle.write("## Summary\n\n")
        handle.write("| case | csv | events | mean pos_des_raw | mean_abs_pos_des_raw | mean small-signal ratio | min_abs_pos_des_raw | max_abs_pos_des_raw |\n")
        handle.write("|---|---|---:|---:|---:|---:|---:|---:|\n")
        for row in summary_rows:
            handle.write(
                f"| {row['case_label']} | {row['diag_csv']} | {int(row['events'])} | "
                f"{fmt(row['mean_pos_des_raw'])} | {fmt(row['mean_abs_pos_des_raw'])} | "
                f"{fmt(row['mean_small_signal_ratio'])} | {fmt(row['min_abs_pos_des_raw'])} | {fmt(row['max_abs_pos_des_raw'])} |\n"
            )

        handle.write("\n## 0.05 Bin Histogram on |pos_des_raw|\n\n")
        handle.write(f"| case | bin start (rad) | bin end (rad) | count | ratio |\n")
        handle.write(f"|---|---:|---:|---:|---:|\n")
        for row in bin_rows:
            handle.write(
                f"| {row['case_label']} | {fmt(row['bin_start_rad'], 2)} | {fmt(row['bin_end_rad'], 2)} | "
                f"{int(row['count'])} | {fmt(row['ratio'], 4)} |\n"
            )

        handle.write("\n## Skipped\n\n")
        if skipped_rows:
            for row in skipped_rows:
                handle.write(f"- `{row['diag_csv']}`: {row['reason']}\n")
        else:
            handle.write("- none\n")

    print(out_csv)
    print(out_detail_csv)
    print(out_bin_csv)
    print(out_skip_csv)
    print(out_md)


if __name__ == "__main__":
    main()
