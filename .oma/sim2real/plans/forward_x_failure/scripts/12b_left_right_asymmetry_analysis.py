import csv
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
ROUND3_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
CASE_CSV = os.path.join(ROUND3_DIR, "round3_parallel_realization_shape_case_summary.csv")
SIDE_CSV = os.path.join(ROUND3_DIR, "round3_parallel_realization_shape_side_summary.csv")
OUT_CSV = os.path.join(ROUND3_DIR, "round3_left_right_asymmetry_summary.csv")
OUT_MD = os.path.join(ROUND3_DIR, "round3_left_right_asymmetry_summary.md")


def load_csv(path):
    rows = []
    with open(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {}
            for key, value in raw.items():
                if value is None or value == "":
                    row[key] = math.nan
                    continue
                try:
                    row[key] = float(value)
                except ValueError:
                    row[key] = value
            rows.append(row)
    return rows


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def fmt(value, digits=4):
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return "nan"
        return f"{value:.{digits}f}"
    return str(value)


def write_csv(path, rows):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sign_label(value, tol=1e-6):
    if math.isnan(value):
        return "nan"
    if value > tol:
        return "left_worse"
    if value < -tol:
        return "right_worse"
    return "balanced"


def shape_severity(shape_label):
    if not isinstance(shape_label, str):
        return 0
    score = 0
    if "overall_slow" in shape_label:
        score += 3
    if "stick_slip_like" in shape_label:
        score += 3
    if "backlash_like" in shape_label:
        score += 2
    if "low_realization_gain" in shape_label:
        score += 2
    if "mostly_linear" in shape_label:
        score += 0
    return score


def main():
    case_rows = load_csv(CASE_CSV)
    side_rows = load_csv(SIDE_CSV)

    summary_rows = []
    by_window = defaultdict(list)

    for row in case_rows:
        lag_side = sign_label(row["lag_gap_ms"])
        gain_side = sign_label(row["gain_gap"])
        left_shape_score = shape_severity(row["left_shape"])
        right_shape_score = shape_severity(row["right_shape"])
        shape_gap = left_shape_score - right_shape_score
        shape_side = sign_label(shape_gap)
        enriched = {
            **row,
            "lag_worse_side": lag_side,
            "gain_worse_side": gain_side,
            "left_shape_score": left_shape_score,
            "right_shape_score": right_shape_score,
            "shape_score_gap": shape_gap,
            "shape_worse_side": shape_side,
        }
        summary_rows.append(enriched)
        by_window[row["window"]].append(enriched)

    out_rows = []
    for window, items in by_window.items():
        lag_counter = Counter(r["lag_worse_side"] for r in items)
        gain_counter = Counter(r["gain_worse_side"] for r in items)
        shape_counter = Counter(r["shape_worse_side"] for r in items)
        out_rows.append(
            {
                "window": window,
                "cases": len(items),
                "mean_abs_lag_gap_ms": mean([abs(r["lag_gap_ms"]) for r in items]),
                "mean_abs_gain_gap": mean([abs(r["gain_gap"]) for r in items]),
                "lag_left_worse_count": lag_counter.get("left_worse", 0),
                "lag_right_worse_count": lag_counter.get("right_worse", 0),
                "lag_balanced_count": lag_counter.get("balanced", 0),
                "gain_left_worse_count": gain_counter.get("left_worse", 0),
                "gain_right_worse_count": gain_counter.get("right_worse", 0),
                "gain_balanced_count": gain_counter.get("balanced", 0),
                "shape_left_worse_count": shape_counter.get("left_worse", 0),
                "shape_right_worse_count": shape_counter.get("right_worse", 0),
                "shape_balanced_count": shape_counter.get("balanced", 0),
                "dominant_lag_side": lag_counter.most_common(1)[0][0] if lag_counter else "n/a",
                "dominant_gain_side": gain_counter.most_common(1)[0][0] if gain_counter else "n/a",
                "dominant_shape_side": shape_counter.most_common(1)[0][0] if shape_counter else "n/a",
            }
        )

    write_csv(OUT_CSV, out_rows)

    with open(OUT_MD, "w", encoding="utf-8") as handle:
        handle.write("# 12B Left-Right Asymmetry Analysis\n\n")
        handle.write("- Source case summary: `round3_parallel_realization_shape_case_summary.csv`\n")
        handle.write("- Scope: 4 all-ankle actuator-state cases, swing/touchdown windows.\n")
        handle.write("- Asymmetry is judged along 3 axes: lag gap, gain gap, and shape severity gap.\n\n")

        handle.write("## Window-level Summary\n\n")
        handle.write("| window | cases | mean_abs_lag_gap_ms | mean_abs_gain_gap | dominant lag side | dominant gain side | dominant shape side |\n")
        handle.write("|---|---:|---:|---:|---|---|---|\n")
        for row in out_rows:
            handle.write(
                f"| {row['window']} | {int(row['cases'])} | {fmt(row['mean_abs_lag_gap_ms'])} | {fmt(row['mean_abs_gain_gap'])} | "
                f"{row['dominant_lag_side']} | {row['dominant_gain_side']} | {row['dominant_shape_side']} |\n"
            )

        handle.write("\n## Per-case View\n\n")
        handle.write("| case | window | lag gap (ms) | lag worse side | gain gap | gain worse side | shape gap | shape worse side |\n")
        handle.write("|---|---|---:|---|---:|---|---:|---|\n")
        for row in summary_rows:
            handle.write(
                f"| {row['case_label']} | {row['window']} | {fmt(row['lag_gap_ms'])} | {row['lag_worse_side']} | {fmt(row['gain_gap'])} | "
                f"{row['gain_worse_side']} | {fmt(row['shape_score_gap'])} | {row['shape_worse_side']} |\n"
            )

        handle.write("\n## Interpretation\n\n")
        handle.write("- If dominant worse side flips across windows or metrics, asymmetry exists but is not a fixed single-side failure.\n")
        handle.write("- If one side were consistently worse in lag, gain, and shape severity, that would support a fixed unilateral fault hypothesis.\n")
        handle.write("- Current output is intended to answer exactly whether `left/right asymmetry` should be interpreted as fixed-side or mode-dependent.\n")

    print(OUT_CSV)
    print(OUT_MD)


if __name__ == "__main__":
    main()
