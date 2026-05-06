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
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")


def load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


W = load_module("windowed_lag", os.path.join(SCRIPT_DIR, "11c_windowed_execution_chain_lag_analysis.py"))

FILES = [
    ("25/0.4 all_ankles", "t27_tracking_lag_b1_diag_20260430_100024.csv"),
    ("30/0.4 all_ankles", "t27_tracking_lag_b1_diag_20260430_100314.csv"),
    ("35/0.5 all_ankles", "t27_tracking_lag_b1_diag_20260430_100705.csv"),
    ("40/0.8 all_ankles", "t27_tracking_lag_b1_diag_20260430_101404.csv"),
]


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


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


def main():
    summary_rows = []
    detail_rows = []
    for case_label, filename in FILES:
        path = os.path.join(BASE_DIR, "test_logs", "data_csv", filename)
        rows = W.load_csv(path)
        W.ROUND3A.attach_fk_metrics(rows)
        events = sorted(W.ROUND3A.detect_touchdowns(rows), key=lambda e: e.timestamp_sec)[:4]
        event_rows = []
        for event in events:
            for window_name in ("swing", "touchdown"):
                row = W.classify_window(rows, event, window_name)
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
                    "mean_state_joint_left_lag_ms": mean([r["state_joint_left_lag_ms"] for r in items]),
                    "mean_state_joint_right_lag_ms": mean([r["state_joint_right_lag_ms"] for r in items]),
                    "mean_state_joint_lag_ms": mean([r["state_joint_mean_lag_ms"] for r in items]),
                    "mean_joint_sole_lag_ms": mean([r["joint_sole_lag_ms"] for r in items]),
                    "mean_cmd_state_left_lag_ms": mean([r["cmd_state_left_lag_ms"] for r in items]),
                    "mean_cmd_state_right_lag_ms": mean([r["cmd_state_right_lag_ms"] for r in items]),
                    "mean_abs_sole_roll": mean([r["mean_abs_sole_roll"] for r in items]),
                }
            )

    out_csv = os.path.join(OUT_DIR, "round3_execution_chain_lag_multi_sample_summary.csv")
    out_md = os.path.join(OUT_DIR, "round3_execution_chain_lag_multi_sample_summary.md")
    detail_csv = os.path.join(OUT_DIR, "round3_execution_chain_lag_multi_sample_detail.csv")
    write_csv(out_csv, summary_rows)
    write_csv(detail_csv, detail_rows)

    by_case = defaultdict(dict)
    for row in summary_rows:
        by_case[row["case_label"]][row["window"]] = row

    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("# 11D Multi-sample Execution Chain Lag Compare\n\n")
        handle.write("- Scope: 4 actuator-state t27 logs with all-ankle tuning.\n")
        handle.write("- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.\n")
        handle.write("- Focus: `cmd->state`, `state->joint`, `joint->sole`, and left/right asymmetry.\n\n")

        handle.write("## Window Summary\n\n")
        handle.write("| case | window | events | mean left state->joint (ms) | mean right state->joint (ms) | mean state->joint (ms) | mean joint->sole (ms) | mean left cmd->state (ms) | mean right cmd->state (ms) | mean_abs_sole_roll |\n")
        handle.write("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in summary_rows:
            handle.write(
                f"| {row['case_label']} | {row['window']} | {int(row['events'])} | {fmt(row['mean_state_joint_left_lag_ms'])} | {fmt(row['mean_state_joint_right_lag_ms'])} | "
                f"{fmt(row['mean_state_joint_lag_ms'])} | {fmt(row['mean_joint_sole_lag_ms'])} | {fmt(row['mean_cmd_state_left_lag_ms'])} | "
                f"{fmt(row['mean_cmd_state_right_lag_ms'])} | {fmt(row['mean_abs_sole_roll'])} |\n"
            )

        handle.write("\n## Per-case Delta\n\n")
        handle.write("| case | state->joint delta (touchdown-swing, ms) | joint->sole delta (touchdown-swing, ms) | left-right asymmetry in swing (ms) | left-right asymmetry in touchdown (ms) |\n")
        handle.write("|---|---:|---:|---:|---:|\n")
        for case_label, windows in by_case.items():
            swing = windows.get("swing")
            touch = windows.get("touchdown")
            if not swing or not touch:
                continue
            state_delta = touch["mean_state_joint_lag_ms"] - swing["mean_state_joint_lag_ms"]
            sole_delta = touch["mean_joint_sole_lag_ms"] - swing["mean_joint_sole_lag_ms"]
            asym_swing = swing["mean_state_joint_left_lag_ms"] - swing["mean_state_joint_right_lag_ms"]
            asym_touch = touch["mean_state_joint_left_lag_ms"] - touch["mean_state_joint_right_lag_ms"]
            handle.write(
                f"| {case_label} | {fmt(state_delta)} | {fmt(sole_delta)} | {fmt(asym_swing)} | {fmt(asym_touch)} |\n"
            )

        handle.write("\n## Interpretation\n\n")
        handle.write("- If `cmd->state` stays near zero across all 4 cases, command acceptance is not the main lag segment.\n")
        handle.write("- If `state->joint` is consistently large already in `swing`, the lag is pre-contact rather than touchdown-induced.\n")
        handle.write("- If left-right asymmetry is stable across cases, hardware/structure asymmetry priority rises.\n")
        handle.write("- Use `round3_execution_chain_lag_multi_sample_detail.csv` for event-level review.\n")

    print(out_csv)
    print(detail_csv)
    print(out_md)


if __name__ == "__main__":
    main()
