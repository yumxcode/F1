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
ROUND3_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
OUT_DIR = ROUND3_DIR
EARLY_TOUCHDOWN_LIMIT = 4
SMALL_JOINT_BIAS_RAD = 0.10
LARGE_SOLE_ROLL_RAD = 0.15
LARGE_SOLE_PITCH_RAD = 0.12
FOOT_TO_JOINT_GAIN_RATIO = 2.5
SMALL_TRACKING_ERR_RAD = 0.10

os.makedirs(OUT_DIR, exist_ok=True)


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
ROUND3B = load_module(
    "round3b_plan",
    os.path.join(SCRIPT_DIR, "03b_round3_ankle_landing_attitude_classification.py"),
)


def mean(values):
    valid = [value for value in values if not math.isnan(value)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def format_float(value, digits=4):
    if isinstance(value, str):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def sign_label(value: float) -> str:
    if math.isnan(value):
        return "nan"
    return "negative" if value < 0.0 else "positive"


def build_touchdown_rows():
    diag_path = ROUND3A.latest_round3_diag()
    return build_touchdown_rows_for_diag(diag_path)


def build_touchdown_rows_for_diag(diag_path):
    fk_rows = ROUND3A.load_csv(diag_path)
    ROUND3A.attach_fk_metrics(fk_rows)
    events = ROUND3A.detect_touchdowns(fk_rows)
    events = sorted(events, key=lambda event: event.timestamp_sec)
    early_events = events[:EARLY_TOUCHDOWN_LIMIT]
    touchdown_rows = [ROUND3A.summarize_event(fk_rows, event) for event in early_events]
    diag_rows = ROUND3B.load_diag_rows(diag_path)
    return diag_path, diag_rows, touchdown_rows


def enrich_rows(diag_rows, touchdown_rows):
    rows = []
    for touchdown_row in touchdown_rows:
        row = ROUND3B.classify_attitude_axis(dict(touchdown_row))
        row = ROUND3B.add_checkpoint_fields(row, diag_rows)
        row = ROUND3B.classify_three_layer_cause(row)

        touch_row = ROUND3B.row_at_or_before(diag_rows, row["touchdown_time_sec"])
        side = row["side"]
        ankle_pitch_joint = f"{side}_ankle_pitch_joint"
        ankle_roll_joint = f"{side}_ankle_roll_joint"

        row["ankle_pitch_q_touch_rad"] = touch_row.get(f"pos_{ankle_pitch_joint}", math.nan)
        row["ankle_roll_q_touch_rad"] = touch_row.get(f"pos_{ankle_roll_joint}", math.nan)
        row["ankle_pitch_vel_touch_radps"] = touch_row.get(f"vel_{ankle_pitch_joint}", math.nan)
        row["ankle_roll_vel_touch_radps"] = touch_row.get(f"vel_{ankle_roll_joint}", math.nan)
        row["ankle_pitch_raw_touch_rad"] = touch_row.get(f"pos_des_raw_{ankle_pitch_joint}", math.nan)
        row["ankle_roll_raw_touch_rad"] = touch_row.get(f"pos_des_raw_{ankle_roll_joint}", math.nan)
        row["ankle_pitch_tau_lpf_touch"] = touch_row.get(f"tau_des_lpf_{ankle_pitch_joint}", math.nan)
        row["ankle_roll_tau_lpf_touch"] = touch_row.get(f"tau_des_lpf_{ankle_roll_joint}", math.nan)

        row["abs_sole_pitch_touch_rad"] = abs(row["sole_pitch_touch_rad"])
        row["abs_sole_roll_touch_rad"] = abs(row["sole_roll_touch_rad"])
        row["abs_ankle_pitch_q_touch_rad"] = abs(row["ankle_pitch_q_touch_rad"])
        row["abs_ankle_roll_q_touch_rad"] = abs(row["ankle_roll_q_touch_rad"])
        row["roll_to_joint_gain_ratio"] = row["abs_sole_roll_touch_rad"] / max(
            row["abs_ankle_roll_q_touch_rad"], 1e-6
        )
        row["pitch_to_joint_gain_ratio"] = row["abs_sole_pitch_touch_rad"] / max(
            row["abs_ankle_pitch_q_touch_rad"], 1e-6
        )
        row["foot_axis_sign"] = sign_label(row["foot_axis_touch_rad"])
        rows.append(row)
    return rows


def annotate_side_majority(rows):
    side_sign_votes = defaultdict(list)
    for row in rows:
        side_sign_votes[row["side"]].append(sign_label(row["sole_roll_touch_rad"]))
    side_majority = {}
    for side, votes in side_sign_votes.items():
        side_majority[side] = Counter(votes).most_common(1)[0][0]

    for row in rows:
        row["side_roll_sign_majority"] = side_majority[row["side"]]
        row["matches_side_roll_majority"] = 1 if sign_label(row["sole_roll_touch_rad"]) == side_majority[row["side"]] else 0
    sides_present = sorted(side_majority.keys())
    if len(sides_present) == 2:
        left_sign = side_majority.get("left")
        right_sign = side_majority.get("right")
        if left_sign != "nan" and right_sign != "nan" and left_sign != right_sign:
            cross_side_pattern = "bilateral_mirror_stable"
        elif left_sign == right_sign:
            cross_side_pattern = "bilateral_same_sign"
        else:
            cross_side_pattern = "bilateral_mixed"
    else:
        cross_side_pattern = "single_side_only"

    for row in rows:
        row["cross_side_roll_pattern"] = cross_side_pattern
    return side_majority, cross_side_pattern


def classify_suspected_geometry_mode(row):
    small_roll_joint = row["abs_ankle_roll_q_touch_rad"] <= SMALL_JOINT_BIAS_RAD
    large_roll_attitude = row["abs_sole_roll_touch_rad"] >= LARGE_SOLE_ROLL_RAD
    strong_pitch_participation = row["abs_sole_pitch_touch_rad"] >= LARGE_SOLE_PITCH_RAD
    small_tracking = (
        abs(row["ankle_pitch_err_touch_rad"]) <= SMALL_TRACKING_ERR_RAD
        and abs(row["ankle_roll_err_touch_rad"]) <= SMALL_TRACKING_ERR_RAD
    )
    high_roll_gain = row["roll_to_joint_gain_ratio"] >= FOOT_TO_JOINT_GAIN_RATIO
    sign_stable = row["matches_side_roll_majority"] == 1
    mirrored_bilateral_pattern = row["cross_side_roll_pattern"] == "bilateral_mirror_stable"

    if row["abs_sole_roll_touch_rad"] >= LARGE_SOLE_PITCH_RAD and strong_pitch_participation:
        mode = "pitch_roll_coupling_mismatch"
    elif mirrored_bilateral_pattern and high_roll_gain:
        mode = "parallel_mapping_mismatch"
    elif sign_stable and small_roll_joint and large_roll_attitude and not high_roll_gain:
        mode = "roll_axis_sign_or_zero_bias"
    elif high_roll_gain and not small_tracking:
        mode = "parallel_mapping_mismatch"
    else:
        mode = "touchdown_contact_geometry_bias"

    rationale_parts = []
    if sign_stable:
        rationale_parts.append("roll_sign_stable")
    if mirrored_bilateral_pattern:
        rationale_parts.append("left_right_roll_mirror_stable")
    if small_roll_joint:
        rationale_parts.append("ankle_roll_q_small")
    if large_roll_attitude:
        rationale_parts.append("sole_roll_large")
    if strong_pitch_participation:
        rationale_parts.append("pitch_participates")
    if high_roll_gain:
        rationale_parts.append("foot_to_joint_gain_high")
    if small_tracking:
        rationale_parts.append("joint_tracking_not_extreme")
    row["suspected_geometry_mode"] = mode
    row["suspected_geometry_rationale"] = ",".join(rationale_parts) if rationale_parts else "none"
    return row


def write_csv(path: str, rows):
    if not rows:
        return
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: str, diag_path: str, rows, side_majority, cross_side_pattern):
    mode_counts = Counter(row["suspected_geometry_mode"] for row in rows)
    attitude_counts = Counter(row["touchdown_attitude_type"] for row in rows)
    cause_counts = Counter(row["three_layer_root_cause"] for row in rows)
    dominant_axis_counts = Counter(row["attitude_dominant_axis"] for row in rows)

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Coupled Geometry Probe Summary\n\n")
        handle.write(f"- Source diag csv: `{diag_path}`\n")
        handle.write(f"- Touchdowns analyzed: `{len(rows)}` (first `{EARLY_TOUCHDOWN_LIMIT}` only)\n")
        handle.write("- `sole_pitch_touch_rad / sole_roll_touch_rad` below are baseline-corrected foot-frame residuals, not raw ankle-roll-link orientation.\n")
        handle.write(f"- Dominant axis counts: `{dict(dominant_axis_counts)}`\n")
        handle.write(f"- Touchdown attitude counts: `{dict(attitude_counts)}`\n")
        handle.write(f"- Three-layer root counts: `{dict(cause_counts)}`\n")
        handle.write(f"- Suspected geometry mode counts: `{dict(mode_counts)}`\n")
        handle.write(f"- Side roll sign majority: `{side_majority}`\n")
        handle.write(f"- Cross-side roll pattern: `{cross_side_pattern}`\n\n")

        handle.write("## Interpretation\n\n")
        handle.write("- `roll_axis_sign_or_zero_bias`: touchdown roll sign on one side is stable, ankle roll joint angle itself is not large, but baseline-corrected foot-frame roll residual remains material.\n")
        handle.write("- `pitch_roll_coupling_mismatch`: pitch and roll both materially participate in the corrected touchdown residual.\n")
        handle.write("- `parallel_mapping_mismatch`: left/right roll sign shows mirror-stable behavior or corrected foot-frame tilt is strongly amplified relative to joint-space motion, and tracking cannot explain it away.\n")
        handle.write("- `touchdown_contact_geometry_bias`: joint-space values are not extreme, but corrected touchdown foot-frame residual remains biased and is more consistent with contact geometry or foot reference mismatch.\n\n")

        handle.write("## Per-Touchdown Table\n\n")
        handle.write("| side | touchdown_time_sec | attitude_type | sole_pitch_touch_rad | sole_roll_touch_rad | ankle_pitch_q_touch_rad | ankle_roll_q_touch_rad | ankle_pitch_err_touch_rad | ankle_roll_err_touch_rad | roll_to_joint_gain_ratio | suspected_geometry_mode | rationale |\n")
        handle.write("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|\n")
        for row in rows:
            handle.write(
                f"| {row['side']} | {format_float(row['touchdown_time_sec'], 3)} | {row['touchdown_attitude_type']} | "
                f"{format_float(row['sole_pitch_touch_rad'])} | {format_float(row['sole_roll_touch_rad'])} | "
                f"{format_float(row['ankle_pitch_q_touch_rad'])} | {format_float(row['ankle_roll_q_touch_rad'])} | "
                f"{format_float(row['ankle_pitch_err_touch_rad'])} | {format_float(row['ankle_roll_err_touch_rad'])} | "
                f"{format_float(row['roll_to_joint_gain_ratio'])} | {row['suspected_geometry_mode']} | {row['suspected_geometry_rationale']} |\n"
            )

        handle.write("\n## Side-Level Notes\n\n")
        for side in sorted(side_majority):
            side_rows = [row for row in rows if row["side"] == side]
            handle.write(f"### {side}\n\n")
            handle.write(f"- Roll sign majority: `{side_majority[side]}`\n")
            handle.write(f"- Mean sole_roll_touch_rad: `{format_float(mean([row['sole_roll_touch_rad'] for row in side_rows]))}`\n")
            handle.write(f"- Mean sole_pitch_touch_rad: `{format_float(mean([row['sole_pitch_touch_rad'] for row in side_rows]))}`\n")
            handle.write(f"- Mean ankle_roll_q_touch_rad: `{format_float(mean([row['ankle_roll_q_touch_rad'] for row in side_rows]))}`\n")
            handle.write(f"- Mean roll_to_joint_gain_ratio: `{format_float(mean([row['roll_to_joint_gain_ratio'] for row in side_rows]))}`\n\n")


def write_mapping_notes(path: str, diag_path: str):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Mapping Consistency Notes\n\n")
        handle.write(f"- Source diag csv: `{diag_path}`\n\n")
        handle.write("## Current Code-Path Facts\n\n")
        handle.write("1. `src/module/control_module/src/rl_controller.cc`\n")
        handle.write("   - Parallel ankle joints first compute joint-space torque intent with `tau = kp * (pos_des - q) + kd * (0 - dq)`.\n")
        handle.write("   - For parallel joints, `joint_cmd.effort = tau_des_lpf`, while `joint_cmd.stiffness = 0` and `joint_cmd.damping = 0`.\n")
        handle.write("   - This means walk-stage parallel ankles are effectively torque-dominant at joint command output.\n\n")
        handle.write("2. `src/module/dcu_driver_module/src/ankle_transmission.cc`\n")
        handle.write("   - The transmission maps joint-space `position / velocity / effort / kp / kd` into actuator-space MIT command fields.\n")
        handle.write("   - Actuator `kp / kd` are copied from joint command, so current walk path keeps actuator MIT package shape but with zero stiffness/damping for parallel joints.\n\n")
        handle.write("3. `src/module/dcu_driver_module/src/dcu_driver_module.cc`\n")
        handle.write("   - The mapped actuator command is sent through `SetMitCmd(position, velocity, effort, kp, kd)`.\n\n")
        handle.write("4. `src/module/dcu_driver_module/xyber_controller/xyber_api/src/power_flow.cpp`\n")
        handle.write("   - Motor-side command interface is standard MIT five-tuple packaging.\n\n")
        handle.write("## Current Risk Focus\n\n")
        handle.write("- If all 4 ankles are softened and extra roll-direction shaking drops, but touchdown still stays in `coupled_geometry`, force magnitude alone is not sufficient to explain the residual issue.\n")
        handle.write("- Priority checks should therefore move to:\n")
        handle.write("  - joint/actuator direction sign consistency\n")
        handle.write("  - zero bias between joint-space and foot-space\n")
        handle.write("  - pitch/roll coupling inside parallel mapping\n")
        handle.write("  - touchdown contact reference mismatch between FK body and real sole contact edge\n")


def main():
    diag_path, diag_rows, touchdown_rows = build_touchdown_rows()
    rows = enrich_rows(diag_rows, touchdown_rows)
    side_majority, cross_side_pattern = annotate_side_majority(rows)
    rows = [classify_suspected_geometry_mode(row) for row in rows]

    base_name = os.path.basename(diag_path).replace(".csv", "")
    out_csv = os.path.join(OUT_DIR, f"{base_name}_coupled_geometry_touchdown_table.csv")
    out_md = os.path.join(OUT_DIR, f"{base_name}_coupled_geometry_summary.md")
    out_notes = os.path.join(OUT_DIR, f"{base_name}_mapping_consistency_notes.md")

    write_csv(out_csv, rows)
    write_summary(out_md, diag_path, rows, side_majority, cross_side_pattern)
    write_mapping_notes(out_notes, diag_path)

    print(f"Coupled geometry touchdown table: {out_csv}")
    print(f"Coupled geometry summary: {out_md}")
    print(f"Mapping consistency notes: {out_notes}")


if __name__ == "__main__":
    main()
