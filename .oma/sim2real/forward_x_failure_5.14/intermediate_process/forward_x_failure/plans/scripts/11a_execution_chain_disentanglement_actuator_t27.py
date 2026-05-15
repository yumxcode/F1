import csv
import importlib.util
import math
import os
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


def classify_source(scores):
    ranked = sorted(scores.items(), key=lambda item: (-item[1][1], item[1][0]))
    best_source, (best_lag, best_corr) = ranked[0]
    if best_source in ("action", "pos_des_raw", "tau_des_lpf"):
        if best_corr >= 0.30:
            return "output_chain_dominant"
    if best_source.startswith("actuator_cmd_pos") or best_source.startswith("actuator_state_pos") or best_source == "joint_pos":
        if best_corr >= 0.30:
            return "execution_chain_dominant"
    return "mixed_or_uncertain"


def latest_t27_path():
    matches = glob_sorted("t27_tracking_lag_b1_diag_*.csv")
    if not matches:
        raise FileNotFoundError("No t27_tracking_lag_b1_diag files found")
    return max(matches, key=lambda p: os.path.getmtime(p))


def actuator_names(side):
    return [f"{side}_ankle_left_actuator", f"{side}_ankle_right_actuator"]


def classify_event(rows, event):
    touchdown_start = event.timestamp_sec - TOUCHDOWN_PRE_SEC
    touchdown_end = event.timestamp_sec + TOUCHDOWN_POST_SEC
    window_rows = [row for row in rows if touchdown_start <= row["time_sec"] <= touchdown_end]
    if not window_rows:
        window_rows = [row_at_or_before(rows, event.timestamp_sec)]

    side = event.side
    dt = rows[1]["time_sec"] - rows[0]["time_sec"] if len(rows) >= 2 else 1e-3
    max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt, 1e-6))))

    sole = [row[f"{side}_sole_roll"] for row in window_rows]
    sigs = {
        "action": [row[f"action_{side}_ankle_roll_joint"] for row in window_rows],
        "pos_des_raw": [row[f"pos_des_raw_{side}_ankle_roll_joint"] for row in window_rows],
        "tau_des_lpf": [row[f"tau_des_lpf_{side}_ankle_roll_joint"] for row in window_rows],
        "joint_pos": [row[f"pos_{side}_ankle_roll_joint"] for row in window_rows],
    }

    act_names = actuator_names(side)
    for act in act_names:
        sigs[f"actuator_cmd_pos_{act}"] = [row[f"actuator_cmd_pos_{act}"] for row in window_rows]
        sigs[f"actuator_state_pos_{act}"] = [row[f"actuator_state_pos_{act}"] for row in window_rows]

    lag_scores = {}
    for name, sig in sigs.items():
        lag, corr = best_lag_samples(sig, sole, max_lag_samples)
        lag_scores[name] = (lag, corr)

    cmd_state_scores = {}
    state_joint_scores = {}
    for act in act_names:
        cmd = [row[f"actuator_cmd_pos_{act}"] for row in window_rows]
        state = [row[f"actuator_state_pos_{act}"] for row in window_rows]
        joint = [row[f"pos_{side}_ankle_roll_joint"] for row in window_rows]
        cmd_state_scores[act] = best_lag_samples(cmd, state, max_lag_samples)
        state_joint_scores[act] = best_lag_samples(state, joint, max_lag_samples)

    sole_source = classify_source(lag_scores)
    best_lag_name, (best_lag, best_corr) = max(lag_scores.items(), key=lambda item: (item[1][1], item[1][0]))

    return {
        "side": side,
        "touchdown_time_sec": event.timestamp_sec,
        "sample_count": len(window_rows),
        "duration_sec": window_rows[-1]["time_sec"] - window_rows[0]["time_sec"] if len(window_rows) >= 2 else 0.0,
        "sole_mean_abs": mean([abs(v) for v in sole]),
        "sole_std": stddev(sole),
        "best_match_signal": best_lag_name,
        "best_match_lag_ms": best_lag * dt * 1000.0 if not math.isnan(best_lag) else math.nan,
        "best_match_corr": best_corr,
        "sole_source_guess": sole_source,
        "action_to_sole_lag_ms": lag_scores["action"][0] * dt * 1000.0 if not math.isnan(lag_scores["action"][0]) else math.nan,
        "action_to_sole_corr": lag_scores["action"][1],
        "raw_to_sole_lag_ms": lag_scores["pos_des_raw"][0] * dt * 1000.0 if not math.isnan(lag_scores["pos_des_raw"][0]) else math.nan,
        "raw_to_sole_corr": lag_scores["pos_des_raw"][1],
        "tau_lpf_to_sole_lag_ms": lag_scores["tau_des_lpf"][0] * dt * 1000.0 if not math.isnan(lag_scores["tau_des_lpf"][0]) else math.nan,
        "tau_lpf_to_sole_corr": lag_scores["tau_des_lpf"][1],
        "joint_pos_to_sole_lag_ms": lag_scores["joint_pos"][0] * dt * 1000.0 if not math.isnan(lag_scores["joint_pos"][0]) else math.nan,
        "joint_pos_to_sole_corr": lag_scores["joint_pos"][1],
        "act_left_cmd_to_state_lag_ms": cmd_state_scores[act_names[0]][0] * dt * 1000.0 if not math.isnan(cmd_state_scores[act_names[0]][0]) else math.nan,
        "act_left_cmd_to_state_corr": cmd_state_scores[act_names[0]][1],
        "act_right_cmd_to_state_lag_ms": cmd_state_scores[act_names[1]][0] * dt * 1000.0 if not math.isnan(cmd_state_scores[act_names[1]][0]) else math.nan,
        "act_right_cmd_to_state_corr": cmd_state_scores[act_names[1]][1],
        "act_left_state_to_joint_lag_ms": state_joint_scores[act_names[0]][0] * dt * 1000.0 if not math.isnan(state_joint_scores[act_names[0]][0]) else math.nan,
        "act_left_state_to_joint_corr": state_joint_scores[act_names[0]][1],
        "act_right_state_to_joint_lag_ms": state_joint_scores[act_names[1]][0] * dt * 1000.0 if not math.isnan(state_joint_scores[act_names[1]][0]) else math.nan,
        "act_right_state_to_joint_corr": state_joint_scores[act_names[1]][1],
        "actuator_chain_support": 1
        if sole_source == "execution_chain_dominant"
        else 0,
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


def format_float(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def main():
    diag_path = latest_t27_path()
    rows = load_csv(diag_path)
    ROUND3A.attach_fk_metrics(rows)
    events = sorted(ROUND3A.detect_touchdowns(rows), key=lambda e: e.timestamp_sec)[:4]

    event_rows = []
    for event in events:
        row = classify_event(rows, event)
        row["source"] = event.source
        event_rows.append(row)

    summary = {
        "diag_path": os.path.basename(diag_path),
        "event_count": len(event_rows),
        "mean_sole_mean_abs": mean([r["sole_mean_abs"] for r in event_rows]),
        "mean_action_to_sole_lag_ms": mean([r["action_to_sole_lag_ms"] for r in event_rows]),
        "mean_raw_to_sole_lag_ms": mean([r["raw_to_sole_lag_ms"] for r in event_rows]),
        "mean_tau_lpf_to_sole_lag_ms": mean([r["tau_lpf_to_sole_lag_ms"] for r in event_rows]),
        "mean_joint_pos_to_sole_lag_ms": mean([r["joint_pos_to_sole_lag_ms"] for r in event_rows]),
        "mean_act_left_cmd_to_state_lag_ms": mean([r["act_left_cmd_to_state_lag_ms"] for r in event_rows]),
        "mean_act_right_cmd_to_state_lag_ms": mean([r["act_right_cmd_to_state_lag_ms"] for r in event_rows]),
        "mean_act_left_state_to_joint_lag_ms": mean([r["act_left_state_to_joint_lag_ms"] for r in event_rows]),
        "mean_act_right_state_to_joint_lag_ms": mean([r["act_right_state_to_joint_lag_ms"] for r in event_rows]),
        "dominant_source": Counter(r["sole_source_guess"] for r in event_rows).most_common(1)[0][0] if event_rows else "n/a",
        "actuator_chain_support_mean": mean([r["actuator_chain_support"] for r in event_rows]),
    }

    suffix = os.path.basename(diag_path).replace("t27_tracking_lag_b1_diag_", "").replace(".csv", "")
    out_csv = os.path.join(OUT_DIR, f"round3_execution_chain_disentanglement_actuator_{suffix}.csv")
    out_md = os.path.join(OUT_DIR, f"round3_execution_chain_disentanglement_actuator_{suffix}.md")
    write_csv(out_csv, event_rows)

    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("# 11 Execution Chain Disentanglement with Actuator States\n\n")
        handle.write(f"- Source diag csv: `{diag_path}`\n")
        handle.write("- This analysis uses the newly added `/actuator_cmd` and `/actuator_states` logs.\n")
        handle.write("- Window: first 4 touchdown events, touchdown-350ms to touchdown+100ms.\n\n")
        handle.write("## Summary\n\n")
        handle.write("| metric | value |\n|---|---:|\n")
        handle.write(f"| event_count | {summary['event_count']} |\n")
        handle.write(f"| mean_abs_sole_roll | {format_float(summary['mean_sole_mean_abs'])} |\n")
        handle.write(f"| mean action->sole lag (ms) | {format_float(summary['mean_action_to_sole_lag_ms'])} |\n")
        handle.write(f"| mean raw->sole lag (ms) | {format_float(summary['mean_raw_to_sole_lag_ms'])} |\n")
        handle.write(f"| mean tau_lpf->sole lag (ms) | {format_float(summary['mean_tau_lpf_to_sole_lag_ms'])} |\n")
        handle.write(f"| mean joint_pos->sole lag (ms) | {format_float(summary['mean_joint_pos_to_sole_lag_ms'])} |\n")
        handle.write(f"| mean left act cmd->state lag (ms) | {format_float(summary['mean_act_left_cmd_to_state_lag_ms'])} |\n")
        handle.write(f"| mean right act cmd->state lag (ms) | {format_float(summary['mean_act_right_cmd_to_state_lag_ms'])} |\n")
        handle.write(f"| mean left act state->joint lag (ms) | {format_float(summary['mean_act_left_state_to_joint_lag_ms'])} |\n")
        handle.write(f"| mean right act state->joint lag (ms) | {format_float(summary['mean_act_right_state_to_joint_lag_ms'])} |\n")
        handle.write(f"| dominant sole source | {summary['dominant_source']} |\n")
        handle.write(f"| actuator_chain_support_mean | {format_float(summary['actuator_chain_support_mean'])} |\n\n")

        handle.write("## Event table\n\n")
        handle.write("| side | t_touch(s) | sole_source_guess | best_match_signal | best_match_lag(ms) | best_match_corr | act_left_cmd->state(ms) | act_right_cmd->state(ms) | act_left_state->joint(ms) | act_right_state->joint(ms) |\n")
        handle.write("|---|---:|---|---|---:|---:|---:|---:|---:|---:|\n")
        for row in event_rows:
            handle.write(
                f"| {row['side']} | {format_float(row['touchdown_time_sec'], 3)} | {row['sole_source_guess']} | {row['best_match_signal']} | {format_float(row['best_match_lag_ms'])} | {format_float(row['best_match_corr'])} | {format_float(row['act_left_cmd_to_state_lag_ms'])} | {format_float(row['act_right_cmd_to_state_lag_ms'])} | {format_float(row['act_left_state_to_joint_lag_ms'])} | {format_float(row['act_right_state_to_joint_lag_ms'])} |\n"
            )

        handle.write("\n## Interpretation\n\n")
        handle.write("- If `sole_source_guess` remains `execution_chain_dominant`, the newly logged actuator path still supports the previous conclusion: `sole_roll` is not directly following the network output chain.\n")
        handle.write("- The new actuator logs let us split the execution chain into `actuator_cmd -> actuator_state` and `actuator_state -> joint_pos`, which was previously only a proxy.\n")
        handle.write("- Use this file as the baseline before changing `kp/kd` again.\n")

    print(out_csv)
    print(out_md)


if __name__ == "__main__":
    main()
