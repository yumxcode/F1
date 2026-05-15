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
OUT_CSV = os.path.join(OUT_DIR, "round3_coupled_geometry_cross_kp_compare.csv")
OUT_MD = os.path.join(OUT_DIR, "round3_coupled_geometry_cross_kp_compare.md")

os.makedirs(OUT_DIR, exist_ok=True)


def load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROBE = load_module(
    "round3_05a_probe",
    os.path.join(SCRIPT_DIR, "05a_coupled_geometry_probe.py"),
)


DATASETS = [
    {
        "label": "35_0.5_baseline",
        "group": "baseline",
        "desc": "all ankles baseline",
        "diag": "t26_round3_diag_20260427_170011.csv",
    },
    {
        "label": "35_0.5_retest",
        "group": "baseline",
        "desc": "all ankles baseline retest",
        "diag": "t26复测.csv",
    },
    {
        "label": "50_0.8_right_roll",
        "group": "high_kp",
        "desc": "right_ankle_roll only",
        "diag": "t27_tracking_lag_b1_diag_20260428_161322.csv",
    },
    {
        "label": "40_0.8_right_roll",
        "group": "high_kp",
        "desc": "right_ankle_roll only",
        "diag": "t27_tracking_lag_b1_diag_20260428_162312.csv",
    },
    {
        "label": "25_0.5_right_roll",
        "group": "low_kp",
        "desc": "right_ankle_roll only",
        "diag": "t27_tracking_lag_b1_diag_20260428_163825.csv",
    },
    {
        "label": "25_0.5_all_ankles",
        "group": "low_kp",
        "desc": "all ankles softened",
        "diag": "t27_tracking_lag_b1_diag_20260428_164817.csv",
    },
]


def mean(values):
    valid = [value for value in values if not math.isnan(value)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def format_float(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def analyze_dataset(item):
    diag_path = os.path.join(LOG_DIR, item["diag"])
    diag_path, diag_rows, touchdown_rows = PROBE.build_touchdown_rows_for_diag(diag_path)
    rows = PROBE.enrich_rows(diag_rows, touchdown_rows)
    side_majority, cross_side_pattern = PROBE.annotate_side_majority(rows)
    rows = [PROBE.classify_suspected_geometry_mode(row) for row in rows]

    mode_counts = Counter(row["suspected_geometry_mode"] for row in rows)
    root_counts = Counter(row["three_layer_root_cause"] for row in rows)
    attitude_counts = Counter(row["touchdown_attitude_type"] for row in rows)

    summary = {
        "label": item["label"],
        "group": item["group"],
        "desc": item["desc"],
        "diag": item["diag"],
        "touchdowns_first4": len(rows),
        "side_roll_sign_majority": str(side_majority),
        "cross_side_roll_pattern": cross_side_pattern,
        "mode_counts": str(dict(mode_counts)),
        "root_counts": str(dict(root_counts)),
        "attitude_counts": str(dict(attitude_counts)),
        "mean_sole_roll_abs_rad": mean([abs(row["sole_roll_touch_rad"]) for row in rows]),
        "mean_sole_pitch_abs_rad": mean([abs(row["sole_pitch_touch_rad"]) for row in rows]),
        "mean_ankle_roll_q_abs_rad": mean([abs(row["ankle_roll_q_touch_rad"]) for row in rows]),
        "mean_ankle_pitch_q_abs_rad": mean([abs(row["ankle_pitch_q_touch_rad"]) for row in rows]),
        "mean_roll_to_joint_gain_ratio": mean([row["roll_to_joint_gain_ratio"] for row in rows]),
        "mean_ankle_roll_err_abs_rad": mean([abs(row["ankle_roll_err_touch_rad"]) for row in rows]),
        "mean_ankle_pitch_err_abs_rad": mean([abs(row["ankle_pitch_err_touch_rad"]) for row in rows]),
        "dominant_mode": mode_counts.most_common(1)[0][0] if mode_counts else "none",
        "dominant_root": root_counts.most_common(1)[0][0] if root_counts else "none",
    }
    return summary


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_md(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Coupled Geometry Cross-Kp Comparison\n\n")
        handle.write("- Scope: first 4 touchdowns only\n")
        handle.write("- Purpose: compare whether `coupled_geometry` under high-kp and low-kp settings keeps the same structural signature or changes category.\n\n")

        handle.write("## Summary Table\n\n")
        handle.write("| label | group | cross_side_roll_pattern | dominant_mode | dominant_root | mean_sole_roll_abs_rad | mean_ankle_roll_q_abs_rad | mean_roll_to_joint_gain_ratio | side_roll_sign_majority |\n")
        handle.write("|---|---|---|---|---|---:|---:|---:|---|\n")
        for row in rows:
            handle.write(
                f"| {row['label']} | {row['group']} | {row['cross_side_roll_pattern']} | "
                f"{row['dominant_mode']} | {row['dominant_root']} | "
                f"{format_float(row['mean_sole_roll_abs_rad'])} | {format_float(row['mean_ankle_roll_q_abs_rad'])} | "
                f"{format_float(row['mean_roll_to_joint_gain_ratio'])} | {row['side_roll_sign_majority']} |\n"
            )

        handle.write("\n## Interpretation\n\n")
        high_rows = [row for row in rows if row["group"] == "high_kp"]
        low_rows = [row for row in rows if row["group"] == "low_kp"]

        handle.write("### High-kp set\n\n")
        for row in high_rows:
            handle.write(
                f"- `{row['label']}`: mode=`{row['dominant_mode']}`, root=`{row['dominant_root']}`, "
                f"`cross_side_roll_pattern={row['cross_side_roll_pattern']}`, "
                f"`mean_roll_to_joint_gain_ratio={format_float(row['mean_roll_to_joint_gain_ratio'])}`\n"
            )

        handle.write("\n### Low-kp set\n\n")
        for row in low_rows:
            handle.write(
                f"- `{row['label']}`: mode=`{row['dominant_mode']}`, root=`{row['dominant_root']}`, "
                f"`cross_side_roll_pattern={row['cross_side_roll_pattern']}`, "
                f"`mean_roll_to_joint_gain_ratio={format_float(row['mean_roll_to_joint_gain_ratio'])}`\n"
            )

        handle.write("\n## Current Read\n\n")
        handle.write("1. If both high-kp and low-kp datasets keep `bilateral_mirror_stable` plus a high `roll_to_joint_gain_ratio`, then `coupled_geometry` is not just a low-kp artifact.\n")
        handle.write("2. If high-kp mainly changes `dominant_root` but keeps the same mirror geometry signature, then gain changes are modulating expression rather than replacing the underlying geometry issue.\n")
        handle.write("3. If low-kp suppresses shaking but retains the same mirror sign pattern, that supports the interpretation that controller gain is not the root source of the mirror roll bias.\n")


def main():
    rows = [analyze_dataset(item) for item in DATASETS]
    write_csv(OUT_CSV, rows)
    write_md(OUT_MD, rows)
    print(f"Coupled geometry cross-kp compare csv: {OUT_CSV}")
    print(f"Coupled geometry cross-kp compare md: {OUT_MD}")


if __name__ == "__main__":
    main()
