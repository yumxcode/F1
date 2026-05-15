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
            raise RuntimeError("Failed to locate repository root")
        cursor = parent


BASE_DIR = find_repo_root(SCRIPT_DIR)
TABLE_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
SEPARATION_CSV = os.path.join(TABLE_DIR, "round3_realization_vs_geometry_separation.csv")
OUT_CSV = os.path.join(TABLE_DIR, "round3_touchdown_geometry_residual_collection.csv")
OUT_MD = os.path.join(TABLE_DIR, "round3_touchdown_geometry_residual_collection.md")


def load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROUND3_05A = load_module(
    "round3_05a_collection",
    os.path.join(SCRIPT_DIR, "05a_coupled_geometry_probe.py"),
)


def read_csv(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mean(values):
    valid = [v for v in values if not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def fmt(value, digits=4):
    if isinstance(value, str):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def collect_case(case_label: str, diag_csv: str, separation_label: str, rationale: str,
                 mean_state_joint_lag_ms: str, mean_joint_sole_lag_ms: str):
    diag_path = os.path.join(BASE_DIR, "test_logs", "data_csv", diag_csv)
    _, diag_rows, touchdown_rows = ROUND3_05A.build_touchdown_rows_for_diag(diag_path)
    rows = ROUND3_05A.enrich_rows(diag_rows, touchdown_rows)
    side_majority, cross_side_pattern = ROUND3_05A.annotate_side_majority(rows)
    rows = [ROUND3_05A.classify_suspected_geometry_mode(row) for row in rows]

    mode_counts = Counter(row["suspected_geometry_mode"] for row in rows)
    three_layer_counts = Counter(row["three_layer_root_cause"] for row in rows)
    dominant_mode = mode_counts.most_common(1)[0][0]
    dominant_three_layer = three_layer_counts.most_common(1)[0][0]

    return {
        "case_label": case_label,
        "diag_csv": diag_csv,
        "touchdown_events": len(rows),
        "mean_state_joint_lag_ms": float(mean_state_joint_lag_ms),
        "mean_joint_sole_lag_ms": float(mean_joint_sole_lag_ms),
        "separation_label": separation_label,
        "separation_rationale": rationale,
        "mean_abs_sole_roll": mean([abs(row["sole_roll_touch_rad"]) for row in rows]),
        "mean_abs_sole_pitch": mean([abs(row["sole_pitch_touch_rad"]) for row in rows]),
        "mean_abs_ankle_roll_q": mean([abs(row["ankle_roll_q_touch_rad"]) for row in rows]),
        "mean_roll_to_joint_gain_ratio": mean([row["roll_to_joint_gain_ratio"] for row in rows]),
        "mean_pitch_to_joint_gain_ratio": mean([row["pitch_to_joint_gain_ratio"] for row in rows]),
        "side_roll_sign_majority": str(side_majority),
        "cross_side_roll_pattern": cross_side_pattern,
        "dominant_geometry_mode": dominant_mode,
        "geometry_mode_counts": str(dict(mode_counts)),
        "dominant_three_layer_root": dominant_three_layer,
        "three_layer_counts": str(dict(three_layer_counts)),
        "foot_contact_residual_reading": summarize_residual(
            separation_label=separation_label,
            cross_side_roll_pattern=cross_side_pattern,
            dominant_mode=dominant_mode,
            mean_roll_gain=mean([row["roll_to_joint_gain_ratio"] for row in rows]),
        ),
    }


def summarize_residual(separation_label: str, cross_side_roll_pattern: str,
                       dominant_mode: str, mean_roll_gain: float) -> str:
    if separation_label == "geometry_residual_dominant":
        if cross_side_roll_pattern == "bilateral_mirror_stable" and dominant_mode == "parallel_mapping_mismatch":
            return "foot_space_or_contact_residual_dominant"
        return "geometry_residual_dominant_but_not_mirror_stable"
    if separation_label == "mixed_with_geometry_residual":
        if cross_side_roll_pattern == "bilateral_mirror_stable" and mean_roll_gain >= 10.0:
            return "mixed_with_strong_foot_space_residual"
        return "mixed_residual"
    return "realization_dominant"


def main():
    rows = read_csv(SEPARATION_CSV)
    touchdown_rows = [row for row in rows if row["window"] == "touchdown"]
    out_rows = []
    for row in touchdown_rows:
        out_rows.append(
            collect_case(
                case_label=row["case_label"],
                diag_csv=row["diag_csv"],
                separation_label=row["separation_label"],
                rationale=row["rationale"],
                mean_state_joint_lag_ms=row["mean_state_joint_lag_ms"],
                mean_joint_sole_lag_ms=row["mean_joint_sole_lag_ms"],
            )
        )

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    lines = [
        "# Touchdown Foot-Space / Contact Residual Collection",
        "",
        "## Rule",
        "",
        "- Fix `12C` first: use its touchdown-side `state->joint` vs `joint->sole` separation as the upstream boundary.",
        "- Then collect touchdown-only geometry signatures from `05` on the same cases.",
        "- If `12C` says `geometry_residual_dominant` and `05` still shows `bilateral_mirror_stable + parallel_mapping_mismatch`, the remaining residual is treated as foot-space / contact residual rather than upstream realization lag.",
        "",
        "## Per Case",
        "",
    ]

    for row in out_rows:
        lines.append(
            f"- `{row['case_label']}` -> `{row['foot_contact_residual_reading']}`: "
            f"`state->joint={fmt(row['mean_state_joint_lag_ms'], 1)}ms`, "
            f"`joint->sole={fmt(row['mean_joint_sole_lag_ms'], 1)}ms`, "
            f"`abs_sole_roll={fmt(row['mean_abs_sole_roll'])}`, "
            f"`roll_gain={fmt(row['mean_roll_to_joint_gain_ratio'])}`, "
            f"`pattern={row['cross_side_roll_pattern']}`, "
            f"`geometry={row['dominant_geometry_mode']}`"
        )

    lines.extend(
        [
            "",
            "## Current Reading",
            "",
        ]
    )

    reading_counts = Counter(row["foot_contact_residual_reading"] for row in out_rows)
    lines.append(f"- residual counts: `{dict(reading_counts)}`")

    OUT_MD = os.path.join(TABLE_DIR, "round3_touchdown_geometry_residual_collection.md")
    with open(OUT_MD, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    print(OUT_CSV)
    print(OUT_MD)


if __name__ == "__main__":
    main()
