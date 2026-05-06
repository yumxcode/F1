import csv
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
IN_CSV = os.path.join(TABLE_DIR, "round3_touchdown_geometry_residual_collection.csv")
OUT_CSV = os.path.join(TABLE_DIR, "round3_touchdown_contact_residual_classification.csv")
OUT_MD = os.path.join(TABLE_DIR, "round3_touchdown_contact_residual_classification.md")


def read_csv(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_float(row, key):
    value = row.get(key, "")
    if value == "" or value == "nan":
        return math.nan
    return float(value)


def parse_counts(text: str):
    # The source uses Python dict repr with simple string keys. Avoid eval; parse only key:number pairs.
    out = {}
    cleaned = text.strip().strip("{}")
    if not cleaned:
        return out
    for item in cleaned.split(","):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip().strip("'\"")
        try:
            out[key] = int(value.strip())
        except ValueError:
            continue
    return out


def classify(row):
    state_joint = parse_float(row, "mean_state_joint_lag_ms")
    joint_sole = parse_float(row, "mean_joint_sole_lag_ms")
    abs_roll = parse_float(row, "mean_abs_sole_roll")
    abs_pitch = parse_float(row, "mean_abs_sole_pitch")
    abs_joint_roll = parse_float(row, "mean_abs_ankle_roll_q")
    roll_gain = parse_float(row, "mean_roll_to_joint_gain_ratio")
    pitch_gain = parse_float(row, "mean_pitch_to_joint_gain_ratio")
    geometry_counts = parse_counts(row["geometry_mode_counts"])

    pitch_roll_count = geometry_counts.get("pitch_roll_coupling_mismatch", 0)
    mapping_count = geometry_counts.get("parallel_mapping_mismatch", 0)
    mirror_stable = row["cross_side_roll_pattern"] == "bilateral_mirror_stable"
    foot_space_dominant = row["foot_contact_residual_reading"] in (
        "foot_space_or_contact_residual_dominant",
        "mixed_with_strong_foot_space_residual",
    )

    pitch_participates = abs_pitch >= 0.12 or pitch_roll_count >= 2 or pitch_gain >= 5.0
    joint_small_foot_large = abs_joint_roll <= 0.12 and abs_roll >= 1.0 and roll_gain >= 10.0
    joint_sole_dominates = joint_sole - state_joint >= 20.0

    if foot_space_dominant and mirror_stable and joint_small_foot_large and not pitch_participates:
        label = "fk_foot_frame_residual_candidate"
        rationale = (
            "mirror roll remains stable; ankle roll q is small while sole roll is large; "
            "pitch participation is low, but sole_roll is MuJoCo FK-derived, so treat this as a foot-frame/contact residual candidate until real sole contact is validated"
        )
    elif foot_space_dominant and pitch_participates:
        label = "pitch_roll_coupled_contact_residual"
        rationale = (
            "foot-space residual remains, but pitch participation is material; "
            "do not reduce this case to pure roll contact edge"
        )
    elif foot_space_dominant and mirror_stable and mapping_count >= 2:
        label = "mapping_workpoint_residual"
        rationale = (
            "mirror pattern and parallel_mapping_mismatch remain, but joint-space amplification is less extreme; "
            "focus on mapping table / real-mechanism workpoint consistency"
        )
    elif joint_sole_dominates:
        label = "contact_geometry_residual"
        rationale = "joint->sole lag dominates state->joint lag, but residual pattern is not clean enough for a narrower label"
    else:
        label = "mixed_or_uncertain_contact_residual"
        rationale = "foot-space residual exists but current aggregates are not decisive"

    row["contact_residual_label"] = label
    row["contact_residual_rationale"] = rationale
    row["pitch_participates"] = int(pitch_participates)
    row["joint_small_foot_large"] = int(joint_small_foot_large)
    row["joint_sole_dominates"] = int(joint_sole_dominates)
    return row


def fmt(value, digits=4):
    if isinstance(value, str):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def main():
    rows = [classify(dict(row)) for row in read_csv(IN_CSV)]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(row["contact_residual_label"] for row in rows)
    lines = [
        "# Touchdown Contact Residual Classification",
        "",
        "## Scope",
        "",
        "- This is `05C`: only touchdown-window foot-space / contact residual is classified.",
        "- `13` owns swing dead-zone / small-signal realization.",
        "- `12` owns `actuator_state -> joint_pos` realization residual.",
        "- This report only classifies what remains in `joint_pos -> sole_roll`.",
        "",
        "## Summary",
        "",
        f"- label counts: `{dict(counts)}`",
        "",
        "## Per Case",
        "",
    ]
    for row in rows:
        lines.append(
            f"- `{row['case_label']}` -> `{row['contact_residual_label']}`: "
            f"`abs_sole_roll={fmt(parse_float(row, 'mean_abs_sole_roll'))}`, "
            f"`abs_sole_pitch={fmt(parse_float(row, 'mean_abs_sole_pitch'))}`, "
            f"`abs_ankle_roll_q={fmt(parse_float(row, 'mean_abs_ankle_roll_q'))}`, "
            f"`roll_gain={fmt(parse_float(row, 'mean_roll_to_joint_gain_ratio'))}`, "
            f"`joint->sole={fmt(parse_float(row, 'mean_joint_sole_lag_ms'), 1)}ms`; "
            f"{row['contact_residual_rationale']}"
        )
    lines.extend(
        [
            "",
            "## Current 05C Reading",
            "",
            "- If `fk_foot_frame_residual_candidate` dominates, next test should first validate FK foot-frame alignment, then check real sole contact edge with synchronized video/contact evidence.",
            "- If `pitch_roll_coupled_contact_residual` appears, that case should not be treated as a pure roll residual.",
            "- If `mapping_workpoint_residual` dominates, next test should focus on mapping table / real mechanism consistency around touchdown operating points.",
        ]
    )
    with open(OUT_MD, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    print(OUT_CSV)
    print(OUT_MD)


if __name__ == "__main__":
    main()
