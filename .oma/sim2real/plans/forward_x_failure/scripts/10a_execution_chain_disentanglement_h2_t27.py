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
    if best_source in ("action", "pos_des_raw"):
        if best_corr >= 0.30:
            return "output_chain_dominant"
    if best_source in ("pos_des_lpf", "pos"):
        if best_corr >= 0.30:
            return "execution_chain_dominant"
    return "mixed_or_uncertain"


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


def classify_event(rows, event):
    touchdown_start = event.timestamp_sec - TOUCHDOWN_PRE_SEC
    touchdown_end = event.timestamp_sec + TOUCHDOWN_POST_SEC
    window_rows = [row for row in rows if touchdown_start <= row["time_sec"] <= touchdown_end]
    if not window_rows:
        window_rows = [row_at_or_before(rows, event.timestamp_sec)]

    side = event.side
    dt = rows[1]["time_sec"] - rows[0]["time_sec"] if len(rows) >= 2 else 1e-3
    max_lag_samples = max(1, int(round(MAX_LAG_SEC / max(dt, 1e-6))))

    action = [row[f"action_{side}_ankle_roll_joint"] for row in window_rows]
    raw = [row[f"pos_des_raw_{side}_ankle_roll_joint"] for row in window_rows]
    lpf = [row[f"pos_des_lpf_{side}_ankle_roll_joint"] for row in window_rows]
    pos = [row[f"pos_{side}_ankle_roll_joint"] for row in window_rows]
    sole = [row[f"{side}_sole_roll"] for row in window_rows]

    action_lag, action_corr = best_lag_samples(action, sole, max_lag_samples)
    raw_lag, raw_corr = best_lag_samples(raw, sole, max_lag_samples)
    lpf_lag, lpf_corr = best_lag_samples(lpf, sole, max_lag_samples)
    pos_lag, pos_corr = best_lag_samples(pos, sole, max_lag_samples)
    lpf_pos_lag, lpf_pos_corr = best_lag_samples(lpf, pos, max_lag_samples)

    return {
        "side": side,
        "touchdown_time_sec": event.timestamp_sec,
        "sample_count": len(window_rows),
        "duration_sec": window_rows[-1]["time_sec"] - window_rows[0]["time_sec"] if len(window_rows) >= 2 else 0.0,
        "sole_mean_abs": mean([abs(v) for v in sole]),
        "sole_std": stddev(sole),
        "action_to_sole_lag_ms": action_lag * dt * 1000.0 if not math.isnan(action_lag) else math.nan,
        "raw_to_sole_lag_ms": raw_lag * dt * 1000.0 if not math.isnan(raw_lag) else math.nan,
        "lpf_to_sole_lag_ms": lpf_lag * dt * 1000.0 if not math.isnan(lpf_lag) else math.nan,
        "pos_to_sole_lag_ms": pos_lag * dt * 1000.0 if not math.isnan(pos_lag) else math.nan,
        "lpf_to_pos_lag_ms": lpf_pos_lag * dt * 1000.0 if not math.isnan(lpf_pos_lag) else math.nan,
        "action_to_sole_corr": action_corr,
        "raw_to_sole_corr": raw_corr,
        "lpf_to_sole_corr": lpf_corr,
        "pos_to_sole_corr": pos_corr,
        "lpf_to_pos_corr": lpf_pos_corr,
        "sole_source_guess": label_source(
            {
                "action": (action_lag, action_corr),
                "pos_des_raw": (raw_lag, raw_corr),
                "pos_des_lpf": (lpf_lag, lpf_corr),
                "pos": (pos_lag, pos_corr),
            }
        ),
        "h2_proxy_supported": 1
        if (not math.isnan(lpf_pos_lag) and lpf_pos_lag >= 1 and label_source({"pos_des_lpf": (lpf_pos_lag, lpf_pos_corr), "pos": (pos_lag, pos_corr)}) == "execution_chain_dominant")
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
    event_rows = []
    summary_rows = []

    for label, suffix, path in case_paths():
        rows = load_csv(path)
        ROUND3A.attach_fk_metrics(rows)
        events = sorted(ROUND3A.detect_touchdowns(rows), key=lambda e: e.timestamp_sec)[:4]
        case_event_rows = [classify_event(rows, event) for event in events]
        for row in case_event_rows:
            row["case_label"] = label
            row["suffix"] = suffix
        event_rows.extend(case_event_rows)
        summary_rows.append(
            {
                "case_label": label,
                "suffix": suffix,
                "event_count": len(case_event_rows),
                "mean_sole_mean_abs": mean([r["sole_mean_abs"] for r in case_event_rows]),
                "mean_lpf_to_pos_lag_ms": mean([r["lpf_to_pos_lag_ms"] for r in case_event_rows]),
                "mean_pos_to_sole_lag_ms": mean([r["pos_to_sole_lag_ms"] for r in case_event_rows]),
                "mean_h2_proxy_supported": mean([r["h2_proxy_supported"] for r in case_event_rows]),
                "dominant_source": Counter(r["sole_source_guess"] for r in case_event_rows).most_common(1)[0][0] if case_event_rows else "n/a",
            }
        )

    out_csv = os.path.join(OUT_DIR, "round3_t27_execution_chain_disentanglement_h2.csv")
    out_md = os.path.join(OUT_DIR, "round3_t27_execution_chain_disentanglement_h2.md")
    write_csv(out_csv, event_rows)

    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("# 10 Execution Chain Disentanglement H2 on t27\n\n")
        handle.write("## 口径\n\n")
        handle.write("- 这份分析把 `pos_des_lpf -> pos` 当成当前可用的执行链代理量。\n")
        handle.write("- 由于仓库里还没有补录 `/actuator_states`，当前不能把 `lpf -> actuator` 和 `actuator -> pos` 真正拆开，只能先做代理判定。\n")
        handle.write("- 目标是判断：`sole_roll` 是否仍然主要跟随执行链，而不是即时 output。\n\n")

        handle.write("## 摘要\n\n")
        handle.write("| case | events | mean |sole_roll| | mean lpf->pos lag (ms) | mean pos->sole lag (ms) | H2 proxy support | dominant source |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---|\n")
        for row in summary_rows:
            handle.write(
                f"| {row['case_label']} | {row['event_count']} | {format_float(row['mean_sole_mean_abs'])} | "
                f"{format_float(row['mean_lpf_to_pos_lag_ms'])} | {format_float(row['mean_pos_to_sole_lag_ms'])} | "
                f"{format_float(row['mean_h2_proxy_supported'])} | {row['dominant_source']} |\n"
            )

        handle.write("\n## 解释\n\n")
        handle.write("- 若 `lpf->pos` 代理滞后明显，而 `sole_roll` 仍主要判为 `execution_chain_dominant`，则 H2 代理成立。\n")
        handle.write("- 这表示当前问题不是 output 直接把姿态做坏，而是目标到执行到位之间的响应迟滞在接触阶段占主导。\n")
        handle.write("- 但这仍不是严格的 actuator-state 分解，因此只能作为 H2 的代理判定。\n\n")

        handle.write("## 下一步\n\n")
        handle.write("- 补录 `/actuator_states`，把 `lpf -> actuator` 与 `actuator -> pos` 真正拆开。\n")
        handle.write("- 在同一批 kp 条件下重复前 4 步 touchdown，确认高 kp 下迟滞是否主要出现在执行链前段还是后段。\n")
        handle.write("- 若补录后仍然保持左右镜像 `roll` 偏置，则继续往 `parallel_mapping / sign-convention / hard-ware degradation` 方向查。\n")

    print(out_csv)
    print(out_md)


if __name__ == "__main__":
    main()
