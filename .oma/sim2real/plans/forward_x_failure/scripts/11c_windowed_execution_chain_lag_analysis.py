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


def latest_t27_with_actuator_path():
    import glob

    matches = sorted(glob.glob(os.path.join(LOG_DIR, "t27_tracking_lag_b1_diag_*.csv")))
    for path in reversed(matches):
        with open(path, "r", newline="") as handle:
            header = next(csv.reader(handle))
        if any(name.startswith("actuator_state_pos_") for name in header):
            return path
    raise FileNotFoundError("No t27 log with actuator-state fields found")


def actuator_names(side):
    return [f"{side}_ankle_left_actuator", f"{side}_ankle_right_actuator"]


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


def classify_window(rows, event, window_name):
    window_rows = select_window_rows(rows, event.timestamp_sec, window_name)
    if len(window_rows) < 2:
        return None

    dt = rows[1]["time_sec"] - rows[0]["time_sec"] if len(rows) >= 2 else 1e-3
    max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt, 1e-6))))
    side = event.side
    act_left, act_right = actuator_names(side)

    joint_pos = [row[f"pos_{side}_ankle_roll_joint"] for row in window_rows]
    sole_roll = [row[f"{side}_sole_roll"] for row in window_rows]
    cmd_left = [row[f"actuator_cmd_pos_{act_left}"] for row in window_rows]
    cmd_right = [row[f"actuator_cmd_pos_{act_right}"] for row in window_rows]
    state_left = [row[f"actuator_state_pos_{act_left}"] for row in window_rows]
    state_right = [row[f"actuator_state_pos_{act_right}"] for row in window_rows]

    cmd_state_left = best_lag_samples(cmd_left, state_left, max_lag_samples)
    cmd_state_right = best_lag_samples(cmd_right, state_right, max_lag_samples)
    state_joint_left = best_lag_samples(state_left, joint_pos, max_lag_samples)
    state_joint_right = best_lag_samples(state_right, joint_pos, max_lag_samples)
    joint_sole = best_lag_samples(joint_pos, sole_roll, max_lag_samples)

    left_lag_ms = cmd_state_left[0] * dt * 1000.0 if not math.isnan(cmd_state_left[0]) else math.nan
    right_lag_ms = cmd_state_right[0] * dt * 1000.0 if not math.isnan(cmd_state_right[0]) else math.nan
    state_joint_left_ms = state_joint_left[0] * dt * 1000.0 if not math.isnan(state_joint_left[0]) else math.nan
    state_joint_right_ms = state_joint_right[0] * dt * 1000.0 if not math.isnan(state_joint_right[0]) else math.nan
    joint_sole_ms = joint_sole[0] * dt * 1000.0 if not math.isnan(joint_sole[0]) else math.nan

    return {
        "window": window_name,
        "side": side,
        "touchdown_time_sec": event.timestamp_sec,
        "sample_count": len(window_rows),
        "duration_sec": window_rows[-1]["time_sec"] - window_rows[0]["time_sec"],
        "cmd_state_left_lag_ms": left_lag_ms,
        "cmd_state_left_corr": cmd_state_left[1],
        "cmd_state_right_lag_ms": right_lag_ms,
        "cmd_state_right_corr": cmd_state_right[1],
        "state_joint_left_lag_ms": state_joint_left_ms,
        "state_joint_left_corr": state_joint_left[1],
        "state_joint_right_lag_ms": state_joint_right_ms,
        "state_joint_right_corr": state_joint_right[1],
        "state_joint_mean_lag_ms": mean([state_joint_left_ms, state_joint_right_ms]),
        "joint_sole_lag_ms": joint_sole_ms,
        "joint_sole_corr": joint_sole[1],
        "mean_abs_sole_roll": mean([abs(v) for v in sole_roll]),
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


def fmt(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def main():
    diag_path = latest_t27_with_actuator_path()
    rows = load_csv(diag_path)
    ROUND3A.attach_fk_metrics(rows)
    events = sorted(ROUND3A.detect_touchdowns(rows), key=lambda e: e.timestamp_sec)[:4]

    event_rows = []
    for event in events:
        for window_name in ("swing", "touchdown"):
            row = classify_window(rows, event, window_name)
            if row is not None:
                row["source"] = event.source
                event_rows.append(row)

    summary_rows = []
    grouped = defaultdict(list)
    for row in event_rows:
        grouped[row["window"]].append(row)

    for window_name, items in grouped.items():
        summary_rows.append(
            {
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

    summary_map = {row["window"]: row for row in summary_rows}
    swing = summary_map.get("swing", {})
    touchdown = summary_map.get("touchdown", {})
    delta_state_joint = (
        touchdown.get("mean_state_joint_lag_ms", math.nan) - swing.get("mean_state_joint_lag_ms", math.nan)
        if swing and touchdown
        else math.nan
    )
    delta_joint_sole = (
        touchdown.get("mean_joint_sole_lag_ms", math.nan) - swing.get("mean_joint_sole_lag_ms", math.nan)
        if swing and touchdown
        else math.nan
    )

    suffix = os.path.basename(diag_path).replace("t27_tracking_lag_b1_diag_", "").replace(".csv", "")
    out_csv = os.path.join(OUT_DIR, f"round3_execution_chain_lag_windowed_{suffix}.csv")
    out_md = os.path.join(OUT_DIR, f"round3_execution_chain_lag_windowed_{suffix}.md")
    write_csv(out_csv, event_rows)

    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("# 11C Windowed Execution Chain Lag Analysis\n\n")
        handle.write(f"- Source diag csv: `{os.path.basename(diag_path)}`\n")
        handle.write("- Scope: first 4 touchdown events only.\n")
        handle.write("- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.\n\n")

        handle.write("## Window Summary\n\n")
        handle.write("| window | events | mean left state->joint lag (ms) | mean right state->joint lag (ms) | mean state->joint lag (ms) | mean joint->sole lag (ms) | mean left cmd->state lag (ms) | mean right cmd->state lag (ms) | mean_abs_sole_roll |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in summary_rows:
            handle.write(
                f"| {row['window']} | {int(row['events'])} | {fmt(row['mean_state_joint_left_lag_ms'])} | {fmt(row['mean_state_joint_right_lag_ms'])} | "
                f"{fmt(row['mean_state_joint_lag_ms'])} | {fmt(row['mean_joint_sole_lag_ms'])} | "
                f"{fmt(row['mean_cmd_state_left_lag_ms'])} | {fmt(row['mean_cmd_state_right_lag_ms'])} | {fmt(row['mean_abs_sole_roll'])} |\n"
            )

        handle.write("\n## Window Delta\n\n")
        handle.write("| metric | delta touchdown - swing (ms) |\n")
        handle.write("|---|---:|\n")
        handle.write(f"| state->joint lag delta | {fmt(delta_state_joint)} |\n")
        handle.write(f"| joint->sole lag delta | {fmt(delta_joint_sole)} |\n")

        handle.write("\n## Event Table\n\n")
        handle.write("| window | side | t_touch(s) | left cmd->state (ms) | right cmd->state (ms) | left state->joint (ms) | right state->joint (ms) | mean state->joint (ms) | joint->sole (ms) |\n")
        handle.write("|---|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in event_rows:
            handle.write(
                f"| {row['window']} | {row['side']} | {fmt(row['touchdown_time_sec'], 3)} | {fmt(row['cmd_state_left_lag_ms'])} | "
                f"{fmt(row['cmd_state_right_lag_ms'])} | {fmt(row['state_joint_left_lag_ms'])} | {fmt(row['state_joint_right_lag_ms'])} | "
                f"{fmt(row['state_joint_mean_lag_ms'])} | {fmt(row['joint_sole_lag_ms'])} |\n"
            )

        handle.write("\n## Interpretation\n\n")
        handle.write("- If `cmd->state` stays near zero in both windows, the main lag is not in command acceptance.\n")
        handle.write("- If `state->joint` is already large in `swing`, the lag is pre-contact and not only a touchdown effect.\n")
        handle.write("- If `state->joint` grows further in `touchdown`, contact is amplifying the execution-chain lag.\n")
        handle.write("- Left/right asymmetry should be judged from `left/right state->joint lag`, not from `cmd->state`.\n")

    print(out_csv)
    print(out_md)


if __name__ == "__main__":
    main()
