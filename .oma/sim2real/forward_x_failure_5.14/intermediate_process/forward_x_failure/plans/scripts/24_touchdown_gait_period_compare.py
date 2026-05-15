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
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "compare")
RESULT_DIR = os.path.join(BASE_DIR, ".oma", "sim2real", "results", "forward_x_failure")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


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


CASES = [
    ("real", "25/0.4 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100024.csv"),
    ("real", "30/0.4 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100314.csv"),
    ("real", "35/0.5 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100705.csv"),
    ("real", "40/0.8 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv"),
    ("sim", "25/0.4", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133905_2504.csv"),
    ("sim", "35/0.5", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133024_3505.csv"),
    ("sim", "40/0.5", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134153_4005.csv"),
    ("sim", "50/0.8", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134417_5008.csv"),
]


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def stddev(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if len(valid) < 2:
        return math.nan
    avg = mean(valid)
    return math.sqrt(sum((v - avg) ** 2 for v in valid) / (len(valid) - 1))


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


def intervals(values):
    return [values[idx + 1] - values[idx] for idx in range(len(values) - 1)]


def analyze_case(stage, case_label, rel_path):
    csv_path = os.path.join(BASE_DIR, rel_path)
    rows = ROUND3A.load_csv(csv_path)
    ROUND3A.attach_fk_metrics(rows)
    events = sorted(ROUND3A.detect_touchdowns(rows), key=lambda event: event.timestamp_sec)

    event_rows = []
    for idx, event in enumerate(events):
        event_rows.append(
            {
                "stage": stage,
                "case_label": case_label,
                "diag_csv": os.path.basename(csv_path),
                "event_seq": idx,
                "side": event.side,
                "touchdown_time_sec": event.timestamp_sec,
                "touchdown_source": event.source,
                "first_contact_time_sec": event.first_contact_time_sec,
                "stable_minus_first_contact_sec": event.timestamp_sec - event.first_contact_time_sec,
            }
        )

    by_side = defaultdict(list)
    for event in events:
        by_side[event.side].append(event.timestamp_sec)

    same_side_periods = []
    side_period_rows = []
    for side in ("left", "right"):
        side_intervals = intervals(by_side[side])
        same_side_periods.extend(side_intervals)
        side_period_rows.append(
            {
                "stage": stage,
                "case_label": case_label,
                "side": side,
                "touchdown_count": len(by_side[side]),
                "same_side_period_count": len(side_intervals),
                "same_side_period_mean_sec": mean(side_intervals),
                "same_side_period_std_sec": stddev(side_intervals),
            }
        )

    adjacent_intervals = intervals([event.timestamp_sec for event in events])
    summary = {
        "stage": stage,
        "case_label": case_label,
        "diag_csv": os.path.basename(csv_path),
        "event_count": len(events),
        "left_event_count": len(by_side["left"]),
        "right_event_count": len(by_side["right"]),
        "same_side_period_count": len(same_side_periods),
        "same_side_period_mean_sec": mean(same_side_periods),
        "same_side_period_std_sec": stddev(same_side_periods),
        "same_side_period_hz": 1.0 / mean(same_side_periods) if mean(same_side_periods) else math.nan,
        "adjacent_step_interval_count": len(adjacent_intervals),
        "adjacent_step_interval_mean_sec": mean(adjacent_intervals),
        "adjacent_step_interval_std_sec": stddev(adjacent_intervals),
        "adjacent_step_interval_hz": 1.0 / mean(adjacent_intervals) if mean(adjacent_intervals) else math.nan,
    }
    return event_rows, side_period_rows, summary


def build_markdown(path, summaries, side_rows):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# 24 Touchdown-based Gait Period Compare\n\n")
        handle.write("- Touchdown source: current `ROUND3A.detect_touchdowns()` logic.\n")
        handle.write("- Current detector: FK foot relative height / vertical velocity first, with hip-pitch motion as phase sanity check; `left_contact/right_contact` are fallback only.\n")
        handle.write("- Full gait period: same-side touchdown-to-touchdown interval.\n")
        handle.write("- Adjacent step interval: consecutive left/right touchdown interval, approximately half gait period when gait alternates cleanly.\n\n")

        handle.write("## Case Summary\n\n")
        handle.write("| stage | case | events L/R | same-side period mean±std (s) | gait freq (Hz) | adjacent step mean±std (s) | step freq (Hz) |\n")
        handle.write("|---|---|---:|---:|---:|---:|---:|\n")
        for row in summaries:
            handle.write(
                f"| {row['stage']} | {row['case_label']} | {int(row['left_event_count'])}/{int(row['right_event_count'])} | "
                f"{fmt(row['same_side_period_mean_sec'])} ± {fmt(row['same_side_period_std_sec'])} | "
                f"{fmt(row['same_side_period_hz'])} | "
                f"{fmt(row['adjacent_step_interval_mean_sec'])} ± {fmt(row['adjacent_step_interval_std_sec'])} | "
                f"{fmt(row['adjacent_step_interval_hz'])} |\n"
            )

        handle.write("\n## Side Summary\n\n")
        handle.write("| stage | case | side | touchdowns | same-side periods | period mean±std (s) |\n")
        handle.write("|---|---|---|---:|---:|---:|\n")
        for row in side_rows:
            handle.write(
                f"| {row['stage']} | {row['case_label']} | {row['side']} | "
                f"{int(row['touchdown_count'])} | {int(row['same_side_period_count'])} | "
                f"{fmt(row['same_side_period_mean_sec'])} ± {fmt(row['same_side_period_std_sec'])} |\n"
            )

        real_periods = [row["same_side_period_mean_sec"] for row in summaries if row["stage"] == "real"]
        sim_periods = [row["same_side_period_mean_sec"] for row in summaries if row["stage"] == "sim"]
        real_steps = [row["adjacent_step_interval_mean_sec"] for row in summaries if row["stage"] == "real"]
        sim_steps = [row["adjacent_step_interval_mean_sec"] for row in summaries if row["stage"] == "sim"]

        handle.write("\n## Reading\n\n")
        handle.write(
            f"- Real same-side gait period mean across cases: `{fmt(mean(real_periods))} s`; "
            f"sim: `{fmt(mean(sim_periods))} s`.\n"
        )
        handle.write(
            f"- Real adjacent step interval mean across cases: `{fmt(mean(real_steps))} s`; "
            f"sim: `{fmt(mean(sim_steps))} s`.\n"
        )
        handle.write("- Interpret this as FK-kinematic touchdown-detector period, not force-plate ground-truth contact period.\n")


def main():
    all_events = []
    all_side_rows = []
    summaries = []
    for stage, case_label, rel_path in CASES:
        event_rows, side_rows, summary = analyze_case(stage, case_label, rel_path)
        all_events.extend(event_rows)
        all_side_rows.extend(side_rows)
        summaries.append(summary)

    events_csv = os.path.join(OUT_DIR, "touchdown_gait_period_events.csv")
    side_csv = os.path.join(OUT_DIR, "touchdown_gait_period_side_summary.csv")
    summary_csv = os.path.join(OUT_DIR, "touchdown_gait_period_case_summary.csv")
    result_md = os.path.join(RESULT_DIR, "24_touchdown_gait_period_compare.md")

    write_csv(events_csv, all_events)
    write_csv(side_csv, all_side_rows)
    write_csv(summary_csv, summaries)
    build_markdown(result_md, summaries, all_side_rows)

    print(events_csv)
    print(side_csv)
    print(summary_csv)
    print(result_md)


if __name__ == "__main__":
    main()
