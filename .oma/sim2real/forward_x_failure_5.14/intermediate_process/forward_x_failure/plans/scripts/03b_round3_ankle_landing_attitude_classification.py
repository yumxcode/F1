import csv
import glob
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
ROUND3_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
LOG_DIR = os.path.join(BASE_DIR, "test_logs", "data_csv")
DOMINANCE_RATIO = 1.15
EFFECTIVE_DELAY_SEC = 0.020
DELAY_SWEEP_SEC = (0.010, 0.020, 0.030)
EXECUTION_COMPLETION_SEC = 0.010
DELAY_WINDOW_HALF_WIDTH_SEC = 0.010
RAW_FLATTEN_MARGIN_RAD = 0.02
RAW_NOT_FLAT_TOUCH_RAD = 0.12
TRACKING_LAG_ERR_RAD = 0.20
MIN_EFFECTIVE_TAU = 0.50
FILTER_RATIO_DELAY = 0.55
AXIS_COUPLING_MIN_RAD = 0.20
MIN_FOOT_FRAME_RESIDUAL_FOR_CAUSE_RAD = 0.15
CHECKPOINTS = (
    ("minus_100ms", -0.10),
    ("minus_50ms", -0.05),
    ("minus_20ms", -0.02),
    ("touch", 0.0),
)


def latest_touchdown_summary() -> str:
    matches = sorted(glob.glob(os.path.join(ROUND3_DIR, "*_touchdown_summary.csv")))
    if not matches:
        raise FileNotFoundError("No *_touchdown_summary.csv files found under real2sim/table/round3")
    return matches[-1]


def parse_float(value):
    if value is None or value == "":
        return math.nan
    return float(value)


def load_touchdown_rows(path: str):
    rows = []
    with open(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {}
            for key, value in raw.items():
                if key in ("side", "touchdown_source", "primary_flag", "all_flags"):
                    row[key] = value
                else:
                    row[key] = parse_float(value)
            rows.append(row)
    return rows


def load_diag_rows(path: str):
    rows = []
    with open(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {}
            for key, value in raw.items():
                row[key] = parse_float(value) if key != "timestamp_ns" else int(value)
            row["time_sec"] = row["timestamp_ns"] / 1e9
            rows.append(row)
    if not rows:
        raise RuntimeError(f"No rows loaded from {path}")
    return rows


def diag_path_for_touchdown_summary(summary_path: str) -> str:
    base_name = os.path.basename(summary_path).replace("_touchdown_summary.csv", ".csv")
    diag_path = os.path.join(LOG_DIR, base_name)
    if not os.path.exists(diag_path):
        raise FileNotFoundError(f"Missing source diag csv for {summary_path}: {diag_path}")
    return diag_path


def row_at_or_before(rows, target_time: float):
    for idx in range(len(rows) - 1, -1, -1):
        if rows[idx]["time_sec"] <= target_time:
            return rows[idx]
    return rows[0]


def rows_in_window(rows, start_time: float, end_time: float):
    window_rows = [row for row in rows if start_time <= row["time_sec"] <= end_time]
    if window_rows:
        return window_rows
    center_time = 0.5 * (start_time + end_time)
    return [row_at_or_before(rows, center_time)]


def mean(values):
    valid = [value for value in values if not math.isnan(value)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def abs_max(values):
    valid = [abs(value) for value in values if not math.isnan(value)]
    if not valid:
        return math.nan
    return max(valid)


def sign_label(value: float) -> str:
    if math.isnan(value):
        return "nan"
    return "negative" if value < 0.0 else "positive"


def classify_attitude_axis(row):
    pitch = row["sole_pitch_touch_rad"]
    roll = row["sole_roll_touch_rad"]
    abs_pitch = abs(pitch)
    abs_roll = abs(roll)

    if abs_pitch >= abs_roll * DOMINANCE_RATIO:
        dominant_axis = "pitch"
        touchdown_type = "toe_first_like" if pitch < 0.0 else "heel_first_like"
    elif abs_roll >= abs_pitch * DOMINANCE_RATIO:
        dominant_axis = "roll"
        touchdown_type = "roll_negative_dominant" if roll < 0.0 else "roll_positive_dominant"
    else:
        dominant_axis = "coupled"
        touchdown_type = "pitch_roll_coupled"

    ankle_pitch_err = abs(row["ankle_pitch_err_touch_rad"])
    ankle_roll_err = abs(row["ankle_roll_err_touch_rad"])
    if ankle_pitch_err >= ankle_roll_err * DOMINANCE_RATIO:
        tracking_axis = "ankle_pitch"
    elif ankle_roll_err >= ankle_pitch_err * DOMINANCE_RATIO:
        tracking_axis = "ankle_roll"
    else:
        tracking_axis = "coupled"

    row["attitude_dominant_axis"] = dominant_axis
    row["touchdown_attitude_type"] = touchdown_type
    row["touchdown_pitch_sign"] = sign_label(pitch)
    row["touchdown_roll_sign"] = sign_label(roll)
    row["touchdown_dominant_abs_rad"] = max(abs_pitch, abs_roll)
    row["ankle_tracking_dominant_axis"] = tracking_axis
    row["ankle_tracking_dominant_abs_rad"] = max(ankle_pitch_err, ankle_roll_err)
    return row


def flattening_intent(raw_value: float, q_value: float) -> bool:
    if math.isnan(raw_value) or math.isnan(q_value):
        return False
    if raw_value * q_value <= 0.0:
        return True
    return abs(raw_value) + RAW_FLATTEN_MARGIN_RAD < abs(q_value)


def add_checkpoint_fields(row, diag_rows):
    side = row["side"]
    touchdown_time = row["touchdown_time_sec"]
    dominant_axis = row["attitude_dominant_axis"]
    if dominant_axis == "roll":
        dominant_joint = f"{side}_ankle_roll_joint"
        orthogonal_joint = f"{side}_ankle_pitch_joint"
        foot_axis_touch = row["sole_roll_touch_rad"]
    elif dominant_axis == "pitch":
        dominant_joint = f"{side}_ankle_pitch_joint"
        orthogonal_joint = f"{side}_ankle_roll_joint"
        foot_axis_touch = row["sole_pitch_touch_rad"]
    else:
        dominant_joint = f"{side}_ankle_roll_joint"
        orthogonal_joint = f"{side}_ankle_pitch_joint"
        foot_axis_touch = row["sole_roll_touch_rad"]

    row["dominant_joint"] = dominant_joint
    row["orthogonal_joint"] = orthogonal_joint
    row["foot_axis_touch_rad"] = foot_axis_touch

    flattening_flags = []
    tau_ratios = []
    dominant_joint_errs = []
    for checkpoint_name, delta_sec in CHECKPOINTS:
        sample_row = row_at_or_before(diag_rows, touchdown_time + delta_sec)
        raw_value = sample_row.get(f"pos_des_raw_{dominant_joint}", math.nan)
        q_value = sample_row.get(f"pos_{dominant_joint}", math.nan)
        tau_raw = sample_row.get(f"tau_des_raw_{dominant_joint}", math.nan)
        tau_lpf = sample_row.get(f"tau_des_lpf_{dominant_joint}", math.nan)
        ortho_raw = sample_row.get(f"pos_des_raw_{orthogonal_joint}", math.nan)
        ortho_q = sample_row.get(f"pos_{orthogonal_joint}", math.nan)

        row[f"{checkpoint_name}_raw_rad"] = raw_value
        row[f"{checkpoint_name}_q_rad"] = q_value
        row[f"{checkpoint_name}_tau_raw"] = tau_raw
        row[f"{checkpoint_name}_tau_lpf"] = tau_lpf
        row[f"{checkpoint_name}_q_err_rad"] = raw_value - q_value
        row[f"{checkpoint_name}_orthogonal_raw_rad"] = ortho_raw
        row[f"{checkpoint_name}_orthogonal_q_rad"] = ortho_q

        flatten_flag = 1 if flattening_intent(raw_value, q_value) else 0
        row[f"{checkpoint_name}_raw_flattening_intent"] = flatten_flag
        flattening_flags.append(flatten_flag)

        if not math.isnan(tau_raw) and not math.isnan(tau_lpf) and abs(tau_raw) >= MIN_EFFECTIVE_TAU:
            tau_ratio = abs(tau_lpf) / max(abs(tau_raw), 1e-6)
            tau_ratios.append(tau_ratio)
            row[f"{checkpoint_name}_tau_lpf_ratio"] = tau_ratio
        else:
            row[f"{checkpoint_name}_tau_lpf_ratio"] = math.nan

        if not math.isnan(raw_value) and not math.isnan(q_value):
            dominant_joint_errs.append(abs(raw_value - q_value))

    row["raw_flattening_intent_count"] = float(sum(flattening_flags))
    row["raw_flattening_intent_ratio"] = float(sum(flattening_flags)) / len(CHECKPOINTS)
    row["tau_lpf_ratio_mean"] = mean(tau_ratios)
    row["dominant_joint_tracking_err_max_rad"] = abs_max(dominant_joint_errs)
    row["dominant_joint_tracking_err_touch_rad"] = abs(row["touch_raw_rad"] - row["touch_q_rad"])
    row["axis_coupling_score_rad"] = min(abs(row["sole_pitch_touch_rad"]), abs(row["sole_roll_touch_rad"]))

    delayed_row = row_at_or_before(diag_rows, touchdown_time - EFFECTIVE_DELAY_SEC)
    touch_row = row_at_or_before(diag_rows, touchdown_time)
    delayed_raw = delayed_row.get(f"pos_des_raw_{dominant_joint}", math.nan)
    delayed_q = delayed_row.get(f"pos_{dominant_joint}", math.nan)
    delayed_tau_raw = delayed_row.get(f"tau_des_raw_{dominant_joint}", math.nan)
    delayed_tau_lpf = delayed_row.get(f"tau_des_lpf_{dominant_joint}", math.nan)
    delayed_ortho_raw = delayed_row.get(f"pos_des_raw_{orthogonal_joint}", math.nan)
    delayed_ortho_q = delayed_row.get(f"pos_{orthogonal_joint}", math.nan)
    delayed_flatten_flag = 1 if flattening_intent(delayed_raw, delayed_q) else 0

    row["effective_delay_sec"] = EFFECTIVE_DELAY_SEC
    row["effective_delay_raw_rad"] = delayed_raw
    row["effective_delay_q_rad"] = delayed_q
    row["effective_delay_tau_raw"] = delayed_tau_raw
    row["effective_delay_tau_lpf"] = delayed_tau_lpf
    row["effective_delay_q_err_rad"] = delayed_raw - delayed_q
    row["effective_delay_orthogonal_raw_rad"] = delayed_ortho_raw
    row["effective_delay_orthogonal_q_rad"] = delayed_ortho_q
    row["effective_delay_raw_flattening_intent"] = delayed_flatten_flag
    row["effective_delay_to_touch_tracking_err_rad"] = abs(delayed_raw - touch_row.get(f"pos_{dominant_joint}", math.nan))
    if not math.isnan(delayed_tau_raw) and not math.isnan(delayed_tau_lpf) and abs(delayed_tau_raw) >= MIN_EFFECTIVE_TAU:
      row["effective_delay_tau_lpf_ratio"] = abs(delayed_tau_lpf) / max(abs(delayed_tau_raw), 1e-6)
    else:
      row["effective_delay_tau_lpf_ratio"] = math.nan

    sweep_labels = []
    for delay_sec in DELAY_SWEEP_SEC:
        delay_ms = int(round(delay_sec * 1000.0))
        prefix = f"delay_{delay_ms}ms"
        center_time = touchdown_time - delay_sec
        start_time = center_time - DELAY_WINDOW_HALF_WIDTH_SEC
        end_time = center_time + DELAY_WINDOW_HALF_WIDTH_SEC
        window_rows = rows_in_window(diag_rows, start_time, end_time)

        flatten_flags = []
        tau_ratios = []
        raw_to_touch_errs = []
        raw_values = []
        for sample_row in window_rows:
            raw_value = sample_row.get(f"pos_des_raw_{dominant_joint}", math.nan)
            q_value = sample_row.get(f"pos_{dominant_joint}", math.nan)
            tau_raw = sample_row.get(f"tau_des_raw_{dominant_joint}", math.nan)
            tau_lpf = sample_row.get(f"tau_des_lpf_{dominant_joint}", math.nan)
            raw_values.append(abs(raw_value) if not math.isnan(raw_value) else math.nan)
            flatten_flags.append(1 if flattening_intent(raw_value, q_value) else 0)
            raw_to_touch_errs.append(abs(raw_value - touch_row.get(f"pos_{dominant_joint}", math.nan)))
            if not math.isnan(tau_raw) and not math.isnan(tau_lpf) and abs(tau_raw) >= MIN_EFFECTIVE_TAU:
                tau_ratios.append(abs(tau_lpf) / max(abs(tau_raw), 1e-6))

        flatten_ratio = mean(flatten_flags)
        tau_ratio_mean = mean(tau_ratios)
        tracking_err_mean = mean(raw_to_touch_errs)
        raw_abs_mean = mean(raw_values)
        row[f"{prefix}_window_start_sec"] = start_time
        row[f"{prefix}_window_end_sec"] = end_time
        row[f"{prefix}_sample_count"] = float(len(window_rows))
        row[f"{prefix}_raw_flattening_intent_ratio"] = flatten_ratio
        row[f"{prefix}_tau_lpf_ratio_mean"] = tau_ratio_mean
        row[f"{prefix}_raw_to_touch_tracking_err_mean_rad"] = tracking_err_mean
        row[f"{prefix}_raw_abs_mean_rad"] = raw_abs_mean

        if flatten_ratio < 0.5:
            root_cause = "command_not_flat"
        elif not math.isnan(tau_ratio_mean) and tau_ratio_mean < FILTER_RATIO_DELAY:
            root_cause = "filter_delay"
        elif not math.isnan(tracking_err_mean) and tracking_err_mean >= TRACKING_LAG_ERR_RAD:
            root_cause = "tracking_lag"
        elif row["axis_coupling_score_rad"] >= AXIS_COUPLING_MIN_RAD:
            root_cause = "coupled_geometry"
        else:
            root_cause = "coupled_geometry"
        row[f"{prefix}_root_cause"] = root_cause
        sweep_labels.append(root_cause)

    row["delay_sweep_root_cause_sequence"] = " -> ".join(sweep_labels)
    row["delay_sweep_is_stable"] = 1 if len(set(sweep_labels)) == 1 else 0
    return row


def classify_three_layer_cause(row):
    foot_frame_residual = row["foot_flat_error_touch_rad"]
    intent_ratio = row["raw_flattening_intent_ratio"]
    delayed_flatten = row["effective_delay_raw_flattening_intent"]
    delayed_raw = abs(row["effective_delay_raw_rad"])
    delayed_tau_ratio = row["effective_delay_tau_lpf_ratio"]
    delayed_tracking_err = row["effective_delay_to_touch_tracking_err_rad"]
    coupling_score = row["axis_coupling_score_rad"]

    if foot_frame_residual < MIN_FOOT_FRAME_RESIDUAL_FOR_CAUSE_RAD:
        root_cause = "residual_not_large_enough"
        rationale = "baseline-corrected foot-frame residual is small, so touchdown-side three-layer cause is not treated as a blocker"
    elif delayed_flatten == 0 or (intent_ratio <= 0.25 and delayed_raw >= RAW_NOT_FLAT_TOUCH_RAD):
        root_cause = "command_not_flat"
        rationale = "with 20 ms actuation delay compensation, raw intent still does not move the dominant ankle joint toward reducing the baseline-corrected foot-frame residual"
    elif not math.isnan(delayed_tau_ratio) and delayed_tau_ratio < FILTER_RATIO_DELAY:
        root_cause = "filter_delay"
        rationale = "with 20 ms delay compensation, lpf torque path is still attenuated before touchdown response should arrive"
    elif not math.isnan(delayed_tracking_err) and delayed_tracking_err >= TRACKING_LAG_ERR_RAD:
        root_cause = "tracking_lag"
        rationale = "with 20 ms delay compensation, raw intent and lpf response exist, but touchdown q still lags dominant joint target"
    elif coupling_score >= AXIS_COUPLING_MIN_RAD:
        root_cause = "coupled_geometry"
        rationale = "after 20 ms delay compensation, single-axis command chain is still insufficient to explain touchdown attitude"
    else:
        root_cause = "coupled_geometry"
        rationale = "after 20 ms delay compensation, residual touchdown attitude is more consistent with geometry/coupling than single-axis delay"

    row["three_layer_root_cause"] = root_cause
    row["three_layer_rationale"] = rationale
    return row


def build_rows():
    source_path = latest_touchdown_summary()
    diag_path = diag_path_for_touchdown_summary(source_path)
    touchdown_rows = load_touchdown_rows(source_path)
    diag_rows = load_diag_rows(diag_path)

    rows = []
    for touchdown_row in touchdown_rows:
        row = classify_attitude_axis(dict(touchdown_row))
        row = add_checkpoint_fields(row, diag_rows)
        row = classify_three_layer_cause(row)
        rows.append(row)
    return source_path, diag_path, rows


def format_float(value, digits=4):
    if isinstance(value, str):
        return value
    if value is None or math.isnan(value):
        return "nan"
    return f"{value:.{digits}f}"


def write_csv(path: str, rows):
    if not rows:
        return
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_ranked_csvs(base_name: str, rows):
    ranked_flat = sorted(rows, key=lambda row: row["foot_flat_error_touch_rad"], reverse=True)
    ranked_tracking = sorted(rows, key=lambda row: row["effective_delay_to_touch_tracking_err_rad"], reverse=True)
    ranked_flat_path = os.path.join(ROUND3_DIR, f"{base_name}_ankle_attitude_ranked_by_flat_error.csv")
    ranked_tracking_path = os.path.join(ROUND3_DIR, f"{base_name}_ankle_attitude_ranked_by_tracking_error.csv")
    write_csv(ranked_flat_path, ranked_flat)
    write_csv(ranked_tracking_path, ranked_tracking)
    return ranked_flat_path, ranked_tracking_path, ranked_flat, ranked_tracking


def write_summary(path: str, source_path: str, diag_path: str, rows, ranked_flat, ranked_tracking):
    type_counts = Counter(row["touchdown_attitude_type"] for row in rows)
    axis_counts = Counter(row["attitude_dominant_axis"] for row in rows)
    tracking_counts = Counter(row["ankle_tracking_dominant_axis"] for row in rows)
    cause_counts = Counter(row["three_layer_root_cause"] for row in rows)
    sweep_counts = {}
    for delay_sec in DELAY_SWEEP_SEC:
        delay_ms = int(round(delay_sec * 1000.0))
        prefix = f"delay_{delay_ms}ms_root_cause"
        sweep_counts[f"{delay_ms}ms"] = dict(Counter(row[prefix] for row in rows))
    stable_count = sum(int(row["delay_sweep_is_stable"]) for row in rows)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Round 3 Ankle Landing Attitude Classification\n\n")
        handle.write(f"- Source touchdown summary: `{source_path}`\n")
        handle.write(f"- Source diag csv: `{diag_path}`\n")
        handle.write(f"- Touchdowns classified: `{len(rows)}`\n")
        handle.write(f"- Minimum residual for blocker-style root cause: `{MIN_FOOT_FRAME_RESIDUAL_FOR_CAUSE_RAD:.2f} rad`\n")
        handle.write(f"- Attitude dominant axis counts: `{dict(axis_counts)}`\n")
        handle.write(f"- Touchdown type counts: `{dict(type_counts)}`\n")
        handle.write(f"- Ankle tracking dominant axis counts: `{dict(tracking_counts)}`\n")
        handle.write(f"- Three-layer root cause counts: `{dict(cause_counts)}`\n\n")
        handle.write(f"- Delay sweep counts: `{sweep_counts}`\n")
        handle.write(f"- Delay-sweep stable touch-downs: `{stable_count}/{len(rows)}`\n\n")

        handle.write("## Interpretation Rules\n\n")
        handle.write("- `foot_flat_error_touch_rad` / `sole_pitch_touch_rad` / `sole_roll_touch_rad` are baseline-corrected foot-frame residuals, not raw link orientation.\n")
        handle.write("- `raw` = `pos_des_raw_*`, interpreted as ankle touchdown correction intent.\n")
        handle.write("- `lpf` = `tau_des_lpf_*`, because current ankle joints are parallel joints and the filtered execution path is torque-domain.\n")
        handle.write("- `q` = actual joint position `pos_*`.\n")
        handle.write(f"- Default delay compensation: uses measured actuator response delay `Δt = {EFFECTIVE_DELAY_SEC * 1000:.0f} ms`.\n")
        handle.write(f"- Delay sweep: evaluates `Δt = 10 / 20 / 30 ms`, each with a `+/- {DELAY_WINDOW_HALF_WIDTH_SEC * 1000:.0f} ms` window.\n")
        handle.write(f"- Window choice: actuator response onset is about `20 ms`, and small-step completion is about `10 ms`; the sweep therefore uses windowed evidence rather than a single sample.\n")
        handle.write("- `command_not_flat`: raw intent at `touchdown - Δt` still does not keep moving the dominant ankle axis toward flatter touchdown.\n")
        handle.write("- `filter_delay`: raw intent exists at `touchdown - Δt`, but lpf torque response is still notably attenuated.\n")
        handle.write("- `tracking_lag`: raw intent and lpf response both exist at `touchdown - Δt`, but touchdown q still lags target.\n")
        handle.write("- `coupled_geometry`: single-axis chain cannot fully explain foot attitude; pitch/roll coupling or geometry mismatch remains.\n\n")

        handle.write("## Ranked by Foot-Flat Error\n\n")
        handle.write("| rank | side | touchdown_time_sec | touchdown_attitude_type | foot_flat_error_touch_rad | sole_pitch_touch_rad | sole_roll_touch_rad | dominant_joint | three_layer_root_cause |\n")
        handle.write("|---:|---|---:|---|---:|---:|---:|---|---|\n")
        for rank, row in enumerate(ranked_flat, start=1):
            handle.write(
                f"| {rank} | {row['side']} | {format_float(row['touchdown_time_sec'], 3)} | "
                f"{row['touchdown_attitude_type']} | {format_float(row['foot_flat_error_touch_rad'])} | "
                f"{format_float(row['sole_pitch_touch_rad'])} | {format_float(row['sole_roll_touch_rad'])} | "
                f"{row['dominant_joint']} | {row['three_layer_root_cause']} |\n"
            )

        handle.write("\n## Ranked by Dominant-Joint Tracking Error\n\n")
        handle.write("| rank | side | touchdown_time_sec | dominant_joint | effective_delay_to_touch_tracking_err_rad | effective_delay_raw_rad | touch_q_rad | effective_delay_tau_lpf_ratio | three_layer_root_cause |\n")
        handle.write("|---:|---|---:|---|---:|---:|---:|---:|---|\n")
        for rank, row in enumerate(ranked_tracking, start=1):
            handle.write(
                f"| {rank} | {row['side']} | {format_float(row['touchdown_time_sec'], 3)} | {row['dominant_joint']} | "
                f"{format_float(row['effective_delay_to_touch_tracking_err_rad'])} | {format_float(row['effective_delay_raw_rad'])} | "
                f"{format_float(row['touch_q_rad'])} | {format_float(row['effective_delay_tau_lpf_ratio'])} | "
                f"{row['three_layer_root_cause']} |\n"
            )

        handle.write("\n## Per-Touchdown Three-Layer Diagnosis\n\n")
        handle.write("| side | touchdown_time_sec | dominant_axis | dominant_joint | effective_delay_raw_flattening_intent | effective_delay_tau_lpf_ratio | effective_delay_to_touch_tracking_err_rad | three_layer_root_cause | rationale |\n")
        handle.write("|---|---:|---|---|---:|---:|---:|---|---|\n")
        for row in rows:
            handle.write(
                f"| {row['side']} | {format_float(row['touchdown_time_sec'], 3)} | {row['attitude_dominant_axis']} | "
                f"{row['dominant_joint']} | {format_float(row['effective_delay_raw_flattening_intent'], 0)} | "
                f"{format_float(row['effective_delay_tau_lpf_ratio'])} | {format_float(row['effective_delay_to_touch_tracking_err_rad'])} | "
                f"{row['three_layer_root_cause']} | {row['three_layer_rationale']} |\n"
            )

        handle.write("\n## Delay Sweep\n\n")
        handle.write("| side | touchdown_time_sec | delay_10ms_root_cause | delay_20ms_root_cause | delay_30ms_root_cause | delay_sweep_is_stable | delay_sweep_root_cause_sequence |\n")
        handle.write("|---|---:|---|---|---|---:|---|\n")
        for row in rows:
            handle.write(
                f"| {row['side']} | {format_float(row['touchdown_time_sec'], 3)} | "
                f"{row['delay_10ms_root_cause']} | {row['delay_20ms_root_cause']} | {row['delay_30ms_root_cause']} | "
                f"{int(row['delay_sweep_is_stable'])} | {row['delay_sweep_root_cause_sequence']} |\n"
            )

        handle.write("\n## Notes\n\n")
        handle.write("- `toe_first_like` / `heel_first_like` come directly from `sole_pitch_touch_rad` sign.\n")
        handle.write("- Roll currently keeps sign-preserving labels (`roll_negative_dominant` / `roll_positive_dominant`).\n")
        handle.write("- Inside/outside edge mapping is intentionally not hard-coded here, because that depends on confirmed foot frame sign convention.\n")


def main():
    source_path, diag_path, rows = build_rows()
    base_name = os.path.basename(source_path).replace("_touchdown_summary.csv", "")
    out_csv = os.path.join(ROUND3_DIR, f"{base_name}_ankle_attitude_classification.csv")
    out_md = os.path.join(ROUND3_DIR, f"{base_name}_ankle_attitude_classification.md")
    write_csv(out_csv, rows)
    ranked_flat_path, ranked_tracking_path, ranked_flat, ranked_tracking = write_ranked_csvs(base_name, rows)
    write_summary(out_md, source_path, diag_path, rows, ranked_flat, ranked_tracking)
    print(f"Round 3 ankle attitude classification csv: {out_csv}")
    print(f"Round 3 ankle attitude classification md: {out_md}")
    print(f"Round 3 ankle attitude ranking csv (flat error): {ranked_flat_path}")
    print(f"Round 3 ankle attitude ranking csv (tracking error): {ranked_tracking_path}")


if __name__ == "__main__":
    main()
