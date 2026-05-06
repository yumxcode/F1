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


def align_series(x, y, lag_samples):
    if math.isnan(lag_samples):
        return [], []
    lag = int(lag_samples)
    if lag > 0:
        xs = x[: len(x) - lag]
        ys = y[lag:]
    else:
        xs = x
        ys = y
    n = min(len(xs), len(ys))
    return xs[:n], ys[:n]


def corr(xs, ys):
    if len(xs) < 3:
        return math.nan
    mx = mean(xs)
    my = mean(ys)
    vx = sum((v - mx) ** 2 for v in xs)
    vy = sum((v - my) ** 2 for v in ys)
    if vx <= 1e-12 or vy <= 1e-12:
        return math.nan
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    return cov / math.sqrt(vx * vy)


def slope_gain(xs, ys):
    if len(xs) < 3:
        return math.nan
    mx = mean(xs)
    my = mean(ys)
    vx = sum((v - mx) ** 2 for v in xs)
    if vx <= 1e-12:
        return math.nan
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    return cov / vx


def hysteresis_area(xs, ys):
    if len(xs) < 3:
        return math.nan
    area = 0.0
    for i in range(len(xs) - 1):
        area += 0.5 * (ys[i + 1] + ys[i]) * (xs[i + 1] - xs[i])
    xr = max(xs) - min(xs)
    yr = max(ys) - min(ys)
    denom = xr * yr
    if denom <= 1e-12:
        return 0.0
    return abs(area) / denom


def stiction_ratio(xs, ys):
    if len(xs) < 3:
        return math.nan
    dx = [abs(xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
    dy = [abs(ys[i + 1] - ys[i]) for i in range(len(ys) - 1)]
    x_range = max(xs) - min(xs)
    y_range = max(ys) - min(ys)
    x_thr = max(1e-6, 0.05 * x_range)
    y_thr = max(1e-6, 0.05 * y_range)
    active = [1 for a, b in zip(dx, dy) if a >= x_thr]
    if not active:
        return 0.0
    stuck = [1 for a, b in zip(dx, dy) if a >= x_thr and b <= y_thr]
    return len(stuck) / len(active)


def classify_shape(corr_value, gain_value, hyst_value, stiction_value, lag_ms):
    flags = []
    if not math.isnan(lag_ms) and lag_ms >= 60.0:
        flags.append("overall_slow")
    if not math.isnan(stiction_value) and stiction_value >= 0.35:
        flags.append("stick_slip_like")
    if not math.isnan(hyst_value) and hyst_value >= 0.18:
        flags.append("backlash_like")
    if not math.isnan(gain_value) and abs(gain_value) <= 0.2:
        flags.append("low_realization_gain")
    if not flags:
        flags.append("mostly_linear")
    return ",".join(flags)


def analyze_window_rows(window_rows, side):
    if len(window_rows) < 3:
        return []
    dt = window_rows[1]["time_sec"] - window_rows[0]["time_sec"]
    max_lag_samples = max(1, int(round(W.MAX_LAG_SEC / max(dt, 1e-6))))
    joint = [row[f"pos_{side}_ankle_roll_joint"] for row in window_rows]
    results = []
    for actuator_name in W.actuator_names(side):
        state = [row[f"actuator_state_pos_{actuator_name}"] for row in window_rows]
        lag_samp, lag_corr = W.best_lag_samples(state, joint, max_lag_samples)
        xs, ys = align_series(state, joint, lag_samp if not math.isnan(lag_samp) else math.nan)
        gain = slope_gain(xs, ys)
        raw_corr = corr(xs, ys)
        hyst = hysteresis_area(xs, ys)
        stiction = stiction_ratio(xs, ys)
        lag_ms = lag_samp * dt * 1000.0 if not math.isnan(lag_samp) else math.nan
        results.append(
            {
                "actuator_name": actuator_name,
                "lag_ms": lag_ms,
                "lag_corr": lag_corr,
                "raw_corr": raw_corr,
                "gain": gain,
                "hysteresis_area": hyst,
                "stiction_ratio": stiction,
                "shape_flag": classify_shape(raw_corr, gain, hyst, stiction, lag_ms),
            }
        )
    return results


def main():
    detail_rows = []
    side_summary_rows = []
    case_summary_rows = []

    for case_label, filename in FILES:
        path = os.path.join(BASE_DIR, "test_logs", "data_csv", filename)
        rows = W.load_csv(path)
        W.ROUND3A.attach_fk_metrics(rows)
        events = sorted(W.ROUND3A.detect_touchdowns(rows), key=lambda e: e.timestamp_sec)[:4]

        grouped = defaultdict(list)

        for event in events:
            for window_name in ("swing", "touchdown"):
                window_rows = W.select_window_rows(rows, event.timestamp_sec, window_name)
                if len(window_rows) < 3:
                    continue
                side = event.side
                metrics = analyze_window_rows(window_rows, side)
                for metric in metrics:
                    row = {
                        "case_label": case_label,
                        "diag_csv": filename,
                        "window": window_name,
                        "side": side,
                        "touchdown_time_sec": event.timestamp_sec,
                        **metric,
                    }
                    detail_rows.append(row)
                    grouped[(window_name, side)].append(row)

        for (window_name, side), items in grouped.items():
            side_summary_rows.append(
                {
                    "case_label": case_label,
                    "diag_csv": filename,
                    "window": window_name,
                    "side": side,
                    "events": len(items),
                    "mean_lag_ms": mean([r["lag_ms"] for r in items]),
                    "mean_raw_corr": mean([r["raw_corr"] for r in items]),
                    "mean_gain": mean([r["gain"] for r in items]),
                    "mean_hysteresis_area": mean([r["hysteresis_area"] for r in items]),
                    "mean_stiction_ratio": mean([r["stiction_ratio"] for r in items]),
                    "dominant_shape": Counter(r["shape_flag"] for r in items).most_common(1)[0][0],
                }
            )

        for window_name in ("swing", "touchdown"):
            win_items = [r for r in side_summary_rows if r["case_label"] == case_label and r["window"] == window_name]
            left = next((r for r in win_items if r["side"] == "left"), None)
            right = next((r for r in win_items if r["side"] == "right"), None)
            if not left or not right:
                continue
            case_summary_rows.append(
                {
                    "case_label": case_label,
                    "diag_csv": filename,
                    "window": window_name,
                    "left_mean_lag_ms": left["mean_lag_ms"],
                    "right_mean_lag_ms": right["mean_lag_ms"],
                    "lag_gap_ms": left["mean_lag_ms"] - right["mean_lag_ms"],
                    "left_mean_gain": left["mean_gain"],
                    "right_mean_gain": right["mean_gain"],
                    "gain_gap": left["mean_gain"] - right["mean_gain"],
                    "left_mean_hysteresis_area": left["mean_hysteresis_area"],
                    "right_mean_hysteresis_area": right["mean_hysteresis_area"],
                    "left_mean_stiction_ratio": left["mean_stiction_ratio"],
                    "right_mean_stiction_ratio": right["mean_stiction_ratio"],
                    "left_shape": left["dominant_shape"],
                    "right_shape": right["dominant_shape"],
                }
            )

    detail_csv = os.path.join(OUT_DIR, "round3_parallel_realization_shape_detail.csv")
    side_csv = os.path.join(OUT_DIR, "round3_parallel_realization_shape_side_summary.csv")
    case_csv = os.path.join(OUT_DIR, "round3_parallel_realization_shape_case_summary.csv")
    out_md = os.path.join(OUT_DIR, "round3_parallel_realization_shape_summary.md")

    write_csv(detail_csv, detail_rows)
    write_csv(side_csv, side_summary_rows)
    write_csv(case_csv, case_summary_rows)

    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("# 12A Parallel Realization Shape Analysis\n\n")
        handle.write("- Scope: 4 actuator-state t27 logs, 4 first touchdown events, swing/touchdown windows.\n")
        handle.write("- Focus: `actuator_state -> joint_pos` realization shape.\n\n")

        handle.write("## Side Summary\n\n")
        handle.write("| case | window | side | events | mean lag (ms) | mean corr | mean gain | mean hysteresis area | mean stiction ratio | dominant shape |\n")
        handle.write("|---|---|---|---:|---:|---:|---:|---:|---:|---|\n")
        for row in side_summary_rows:
            handle.write(
                f"| {row['case_label']} | {row['window']} | {row['side']} | {int(row['events'])} | {fmt(row['mean_lag_ms'])} | {fmt(row['mean_raw_corr'])} | "
                f"{fmt(row['mean_gain'])} | {fmt(row['mean_hysteresis_area'])} | {fmt(row['mean_stiction_ratio'])} | {row['dominant_shape']} |\n"
            )

        handle.write("\n## Case Summary\n\n")
        handle.write("| case | window | lag gap left-right (ms) | gain gap | left shape | right shape |\n")
        handle.write("|---|---|---:|---:|---|---|\n")
        for row in case_summary_rows:
            handle.write(
                f"| {row['case_label']} | {row['window']} | {fmt(row['lag_gap_ms'])} | {fmt(row['gain_gap'])} | {row['left_shape']} | {row['right_shape']} |\n"
            )

        handle.write("\n## Interpretation\n\n")
        handle.write("- `overall_slow` means the lag itself is already large.\n")
        handle.write("- `stick_slip_like` means actuator state moves while joint response stays locally pinned for a noticeable fraction of the window.\n")
        handle.write("- `backlash_like` means the state-joint loop encloses a visible area, consistent with backlash / hysteresis.\n")
        handle.write("- `low_realization_gain` means the joint realizes only a small fraction of the actuator-state variation.\n")
        handle.write("- Use the detail csv for per-event/per-actuator review.\n")

    print(detail_csv)
    print(side_csv)
    print(case_csv)
    print(out_md)


if __name__ == "__main__":
    main()
