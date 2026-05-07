import csv
import glob
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
LOG_DIR = os.path.join(BASE_DIR, "test_logs", "data_csv", "sim")
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "sim")
MAX_LAG_SEC = 0.20
MIN_SAMPLE_POINTS = 10
EARLY_TOUCHDOWN_LIMIT = 4

os.makedirs(OUT_DIR, exist_ok=True)


def load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROUND3A = load_module(
    "sim_round3a",
    os.path.join(SCRIPT_DIR, "03a_round3_landing_window_analysis.py"),
)
ROUND3B = load_module(
    "sim_round3b",
    os.path.join(SCRIPT_DIR, "03b_round3_ankle_landing_attitude_classification.py"),
)


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def fmt(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def parse_case_code(path: str):
    stem = os.path.splitext(os.path.basename(path))[0]
    token = stem.rsplit("_", 1)[-1]
    if len(token) == 4 and token.isdigit():
        kp = int(token[:2])
        kd = int(token[2:]) / 10.0
        return token, f"{kp}/{kd:.1f}"
    return token, token


def sim_diag_paths():
    matches = sorted(glob.glob(os.path.join(LOG_DIR, "t27_tracking_lag_b1_diag_*.csv")))
    if not matches:
        raise FileNotFoundError(f"No sim t27 diag csv found under {LOG_DIR}")
    return matches


def first_differences(values):
    if len(values) < 2:
        return []
    return [values[i + 1] - values[i] for i in range(len(values) - 1)]


def stddev(values):
    valid = [v for v in values if not math.isnan(v)]
    if len(valid) < 2:
        return 0.0 if valid else math.nan
    mu = mean(valid)
    return math.sqrt(sum((v - mu) ** 2 for v in valid) / (len(valid) - 1))


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


def joint_group(joint_name: str):
    if "ankle" in joint_name:
        return "ankle"
    if "knee" in joint_name:
        return "knee"
    if "hip" in joint_name:
        return "hip"
    return "other"


def lower_body_joints(rows):
    sample = rows[0]
    return sorted(
        key[len("action_") :]
        for key in sample.keys()
        if key.startswith("action_") and "left_" in key or key.startswith("action_") and "right_" in key
    )


def classify_touchdowns(diag_path: str):
    rows = ROUND3A.load_csv(diag_path)
    ROUND3A.attach_fk_metrics(rows)
    events = sorted(ROUND3A.detect_touchdowns(rows), key=lambda e: e.timestamp_sec)[:EARLY_TOUCHDOWN_LIMIT]
    summaries = [ROUND3A.summarize_event(rows, event) for event in events]

    classified = []
    for summary in summaries:
        row = ROUND3B.classify_attitude_axis(dict(summary))
        row = ROUND3B.add_checkpoint_fields(row, rows)
        row = ROUND3B.classify_three_layer_cause(row)
        classified.append(row)
    return rows, summaries, classified


def lag_rows_for_case(diag_path: str, rows):
    case_code, case_label = parse_case_code(diag_path)
    joint_names = lower_body_joints(rows)
    if len(rows) < 2:
        return []
    dt = rows[1]["time_sec"] - rows[0]["time_sec"]
    max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt, 1e-6))))

    out = []
    for joint_name in joint_names:
        action_series = [row.get(f"action_{joint_name}", math.nan) for row in rows]
        raw_series = [row.get(f"pos_des_raw_{joint_name}", math.nan) for row in rows]
        lpf_series = [row.get(f"pos_des_lpf_{joint_name}", math.nan) for row in rows]
        tau_raw_series = [row.get(f"tau_des_raw_{joint_name}", math.nan) for row in rows]
        tau_lpf_series = [row.get(f"tau_des_lpf_{joint_name}", math.nan) for row in rows]
        pos_series = [row.get(f"pos_{joint_name}", math.nan) for row in rows]

        action_raw = best_lag_samples(action_series, raw_series, max_lag_samples)
        raw_lpf = best_lag_samples(raw_series, lpf_series, max_lag_samples)
        tau_raw_lpf = best_lag_samples(tau_raw_series, tau_lpf_series, max_lag_samples)
        raw_pos = best_lag_samples(raw_series, pos_series, max_lag_samples)

        out.append(
            {
                "case_code": case_code,
                "case_label": case_label,
                "joint": joint_name,
                "group": joint_group(joint_name),
                "sample_dt_ms": dt * 1000.0,
                "action_to_raw_lag_ms": action_raw[0] * dt * 1000.0 if not math.isnan(action_raw[0]) else math.nan,
                "action_to_raw_corr": action_raw[1],
                "raw_to_lpf_lag_ms": raw_lpf[0] * dt * 1000.0 if not math.isnan(raw_lpf[0]) else math.nan,
                "raw_to_lpf_corr": raw_lpf[1],
                "tau_raw_to_tau_lpf_lag_ms": tau_raw_lpf[0] * dt * 1000.0 if not math.isnan(tau_raw_lpf[0]) else math.nan,
                "tau_raw_to_tau_lpf_corr": tau_raw_lpf[1],
                "raw_to_pos_lag_ms": raw_pos[0] * dt * 1000.0 if not math.isnan(raw_pos[0]) else math.nan,
                "raw_to_pos_corr": raw_pos[1],
            }
        )
    return out


def summarize_lag_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["case_code"], row["group"])].append(row)
    out = []
    for (case_code, group), items in sorted(grouped.items()):
        out.append(
            {
                "case_code": case_code,
                "case_label": items[0]["case_label"],
                "group": group,
                "joint_count": len(items),
                "mean_action_to_raw_lag_ms": mean([r["action_to_raw_lag_ms"] for r in items]),
                "mean_raw_to_lpf_lag_ms": mean([r["raw_to_lpf_lag_ms"] for r in items]),
                "mean_tau_raw_to_tau_lpf_lag_ms": mean([r["tau_raw_to_tau_lpf_lag_ms"] for r in items]),
                "mean_raw_to_pos_lag_ms": mean([r["raw_to_pos_lag_ms"] for r in items]),
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


def write_summary_md(path, case_rows, lag_group_rows):
    lag_map = {(row["case_code"], row["group"]): row for row in lag_group_rows}
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Sim T27 03/06 Analysis Summary\n\n")
        handle.write(f"- Source directory: `{LOG_DIR}`\n")
        handle.write(f"- Cases analyzed: `{len(case_rows)}`\n")
        handle.write(f"- Touchdown slice per case: first `{EARLY_TOUCHDOWN_LIMIT}` touchdown events\n")
        handle.write("- Case code rule: filename suffix last 4 digits, e.g. `3505 -> kp=35, kd=0.5`.\n\n")

        handle.write("## Metric Table\n\n")
        handle.write("| metric | meaning |\n")
        handle.write("|---|---|\n")
        handle.write("| `mean_flat_error_rad` | `03` touchdown baseline-corrected foot-frame residual mean over first 4 touchdown events |\n")
        handle.write("| `dominant_axis_counts` | touchdown dominant axis count from `sole_pitch/sole_roll` |\n")
        handle.write("| `root_cause_counts` | `03b` three-layer root cause count |\n")
        handle.write("| `mean_action_to_raw_lag_ms` | sim `06` proxy: policy action to raw joint target lag |\n")
        handle.write("| `mean_raw_to_lpf_lag_ms` | sim `06` proxy: raw joint target to lpf joint target lag |\n")
        handle.write("| `mean_tau_raw_to_tau_lpf_lag_ms` | sim `06` proxy: raw torque to filtered torque lag |\n")
        handle.write("| `mean_raw_to_pos_lag_ms` | sim `06` proxy: raw joint target to actual joint position lag |\n\n")

        handle.write("## Per-Case Summary\n\n")
        handle.write("| case | kp/kd | touchdowns | mean_flat_error_rad | large_residual_count | dominant_axis_counts | root_cause_counts | ankle action->raw ms | ankle raw->lpf ms | ankle tau_raw->tau_lpf ms | ankle raw->pos ms |\n")
        handle.write("|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|\n")
        for row in sorted(case_rows, key=lambda item: item["case_code"]):
            ankle_lag = lag_map.get((row["case_code"], "ankle"), {})
            handle.write(
                f"| {row['case_code']} | {row['case_label']} | {row['touchdown_count']} | "
                f"{fmt(row['mean_flat_error_rad'])} | {row['large_residual_count']} | "
                f"{row['dominant_axis_counts']} | {row['root_cause_counts']} | "
                f"{fmt(ankle_lag.get('mean_action_to_raw_lag_ms', math.nan))} | "
                f"{fmt(ankle_lag.get('mean_raw_to_lpf_lag_ms', math.nan))} | "
                f"{fmt(ankle_lag.get('mean_tau_raw_to_tau_lpf_lag_ms', math.nan))} | "
                f"{fmt(ankle_lag.get('mean_raw_to_pos_lag_ms', math.nan))} |\n"
            )

        handle.write("\n## 03 Readout\n\n")
        handle.write("- `03` here fully reuses touchdown detection + baseline-corrected FK foot-frame residual + three-layer classification logic on sim `t27`.\n")
        handle.write("- Interpretation still follows real-data rules: `command_not_flat`, `filter_delay`, `tracking_lag`, `coupled_geometry`.\n\n")

        handle.write("## 06 Readout\n\n")
        handle.write("- Sim `t27` does not contain actuator cmd/state, so this is a degraded `06`.\n")
        handle.write("- The usable chain is `action -> pos_des_raw -> pos_des_lpf / tau_des_lpf -> pos`.\n")
        handle.write("- Therefore `raw->pos` should be read as the sim-side total execution lag proxy, not the full hardware execution chain.\n")


def main():
    case_summary_rows = []
    touchdown_rows = []
    lag_joint_rows = []

    for diag_path in sim_diag_paths():
        case_code, case_label = parse_case_code(diag_path)
        rows, summaries, classified = classify_touchdowns(diag_path)
        lag_joint_rows.extend(lag_rows_for_case(diag_path, rows))

        dominant_axis_counts = Counter(row["attitude_dominant_axis"] for row in classified)
        root_cause_counts = Counter(row["three_layer_root_cause"] for row in classified)
        touchdown_type_counts = Counter(row["touchdown_attitude_type"] for row in classified)

        case_summary_rows.append(
            {
                "case_code": case_code,
                "case_label": case_label,
                "source_diag_csv": os.path.basename(diag_path),
                "touchdown_count": len(classified),
                "mean_flat_error_rad": mean([row["foot_flat_error_touch_rad"] for row in classified]),
                "mean_clearance_m": mean([row["max_swing_clearance_m"] for row in classified]),
                "large_residual_count": sum(int(row["has_large_foot_frame_residual_touchdown"]) for row in classified),
                "command_not_flat_flag_count": sum(int(row["has_command_not_flat"]) for row in classified),
                "tracking_lag_flag_count": sum(int(row["has_tracking_lag"]) for row in classified),
                "dominant_axis_counts": dict(dominant_axis_counts),
                "touchdown_type_counts": dict(touchdown_type_counts),
                "root_cause_counts": dict(root_cause_counts),
            }
        )

        for row in classified:
            out = dict(row)
            out["case_code"] = case_code
            out["case_label"] = case_label
            out["source_diag_csv"] = os.path.basename(diag_path)
            touchdown_rows.append(out)

    lag_group_rows = summarize_lag_rows(lag_joint_rows)

    case_csv = os.path.join(OUT_DIR, "sim_t27_03_06_case_summary.csv")
    touchdown_csv = os.path.join(OUT_DIR, "sim_t27_03_touchdown_classification.csv")
    lag_joint_csv = os.path.join(OUT_DIR, "sim_t27_06_joint_lag_table.csv")
    lag_group_csv = os.path.join(OUT_DIR, "sim_t27_06_group_lag_summary.csv")
    summary_md = os.path.join(OUT_DIR, "sim_t27_03_06_summary.md")

    write_csv(case_csv, case_summary_rows)
    write_csv(touchdown_csv, touchdown_rows)
    write_csv(lag_joint_csv, lag_joint_rows)
    write_csv(lag_group_csv, lag_group_rows)
    write_summary_md(summary_md, case_summary_rows, lag_group_rows)

    print(case_csv)
    print(touchdown_csv)
    print(lag_joint_csv)
    print(lag_group_csv)
    print(summary_md)


if __name__ == "__main__":
    main()
