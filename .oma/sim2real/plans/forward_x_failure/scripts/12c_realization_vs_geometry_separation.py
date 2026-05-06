#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
TABLE_DIR = REPO_ROOT / "real2sim" / "table" / "round3"

LAG_SUMMARY_CSV = TABLE_DIR / "round3_execution_chain_lag_multi_sample_summary.csv"
SHAPE_SUMMARY_CSV = TABLE_DIR / "round3_parallel_realization_shape_case_summary.csv"
OUT_CSV = TABLE_DIR / "round3_realization_vs_geometry_separation.csv"
OUT_MD = TABLE_DIR / "round3_realization_vs_geometry_separation.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def classify_case(lag_row: dict[str, str], shape_row: dict[str, str]) -> tuple[str, str]:
    state_joint = f(lag_row, "mean_state_joint_lag_ms")
    joint_sole = f(lag_row, "mean_joint_sole_lag_ms")
    abs_sole = f(lag_row, "mean_abs_sole_roll")
    cmd_state_left = f(lag_row, "mean_cmd_state_left_lag_ms")
    cmd_state_right = f(lag_row, "mean_cmd_state_right_lag_ms")
    gain_gap = abs(f(shape_row, "gain_gap"))
    lag_gap = abs(f(shape_row, "lag_gap_ms"))
    left_shape = shape_row["left_shape"]
    right_shape = shape_row["right_shape"]

    shape_flags = ",".join([left_shape, right_shape])
    cmd_state_small = max(cmd_state_left, cmd_state_right) <= 30.0
    state_joint_high = state_joint >= 50.0
    state_joint_risky = state_joint >= 30.0
    state_joint_healthy = state_joint < 20.0
    joint_sole_high = joint_sole >= 50.0
    joint_sole_risky = joint_sole >= 30.0
    geometry_jump = joint_sole - state_joint >= 20.0
    realization_gap_large = state_joint - joint_sole >= 20.0

    if state_joint_high and (joint_sole <= 30.0 or realization_gap_large):
        return (
            "realization_dominant",
            (
                f"state->joint={state_joint:.1f}ms already high while joint->sole="
                f"{joint_sole:.1f}ms is smaller; cmd->state small={cmd_state_small}; "
                f"shape={shape_flags}"
            ),
        )

    if state_joint_healthy and (joint_sole_high or geometry_jump):
        return (
            "geometry_residual_dominant",
            (
                f"state->joint={state_joint:.1f}ms is low but joint->sole="
                f"{joint_sole:.1f}ms remains high; abs_sole_roll={abs_sole:.3f}; "
                f"shape={shape_flags}"
            ),
        )

    if state_joint_risky and joint_sole_risky:
        return (
            "mixed_with_geometry_residual",
            (
                f"state->joint={state_joint:.1f}ms and joint->sole={joint_sole:.1f}ms "
                f"are both risky; abs_sole_roll={abs_sole:.3f}; lag_gap={lag_gap:.1f}ms; "
                f"gain_gap={gain_gap:.3f}"
            ),
        )

    if geometry_jump or joint_sole_high:
        return (
            "geometry_residual_dominant",
            (
                f"joint->sole={joint_sole:.1f}ms dominates over state->joint="
                f"{state_joint:.1f}ms; abs_sole_roll={abs_sole:.3f}; shape={shape_flags}"
            ),
        )

    return (
        "mixed_with_geometry_residual",
        (
            f"state->joint={state_joint:.1f}ms is not enough to fully explain "
            f"abs_sole_roll={abs_sole:.3f}; lag_gap={lag_gap:.1f}ms; "
            f"shape={shape_flags}"
        ),
    )


def main() -> None:
    lag_rows = read_csv(LAG_SUMMARY_CSV)
    shape_rows = read_csv(SHAPE_SUMMARY_CSV)
    shape_map = {(r["case_label"], r["window"]): r for r in shape_rows}

    out_rows: list[dict[str, str]] = []
    counter = Counter()
    by_window = {"swing": Counter(), "touchdown": Counter()}

    for lag_row in lag_rows:
        key = (lag_row["case_label"], lag_row["window"])
        shape_row = shape_map[key]
        label, rationale = classify_case(lag_row, shape_row)
        counter[label] += 1
        by_window[lag_row["window"]][label] += 1
        out_rows.append(
            {
                "case_label": lag_row["case_label"],
                "diag_csv": lag_row["diag_csv"],
                "window": lag_row["window"],
                "events": lag_row["events"],
                "mean_state_joint_lag_ms": lag_row["mean_state_joint_lag_ms"],
                "mean_joint_sole_lag_ms": lag_row["mean_joint_sole_lag_ms"],
                "mean_abs_sole_roll": lag_row["mean_abs_sole_roll"],
                "mean_cmd_state_left_lag_ms": lag_row["mean_cmd_state_left_lag_ms"],
                "mean_cmd_state_right_lag_ms": lag_row["mean_cmd_state_right_lag_ms"],
                "lag_gap_ms": shape_row["lag_gap_ms"],
                "gain_gap": shape_row["gain_gap"],
                "left_shape": shape_row["left_shape"],
                "right_shape": shape_row["right_shape"],
                "separation_label": label,
                "rationale": rationale,
            }
        )

    fieldnames = list(out_rows[0].keys())
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    lines = [
        "# Realization vs Geometry Separation",
        "",
        "## Rule",
        "",
        "- `realization_dominant`: `state->joint` already high-risk/unacceptable and dominates `joint->sole`.",
        "- `geometry_residual_dominant`: `state->joint` is low/tight but `joint->sole` remains high, or geometry jump is obvious.",
        "- `mixed_with_geometry_residual`: both segments are risky, or `state->joint` alone still cannot explain the final `sole_roll`.",
        "",
        "## Summary",
        "",
        f"- overall counts: {dict(counter)}",
        f"- swing counts: {dict(by_window['swing'])}",
        f"- touchdown counts: {dict(by_window['touchdown'])}",
        "",
        "## Per Case",
        "",
    ]
    for row in out_rows:
        lines.append(
            f"- `{row['case_label']} / {row['window']}` -> `{row['separation_label']}`: {row['rationale']}"
        )

    OUT_MD.write_text("\n".join(lines) + "\n")
    print(OUT_CSV)
    print(OUT_MD)


if __name__ == "__main__":
    main()
