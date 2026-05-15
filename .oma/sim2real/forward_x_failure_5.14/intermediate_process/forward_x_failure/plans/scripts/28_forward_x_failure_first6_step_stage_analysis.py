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
            raise RuntimeError("Failed to locate repository root from analysis script path")
        cursor = parent


BASE_DIR = find_repo_root(SCRIPT_DIR)
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "forward_x_failure_first6")
RESULT_DIR = os.path.join(BASE_DIR, ".oma", "sim2real", "results", "forward_x_failure")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

STEP_LIMIT = 6
SWING_PRE_SEC = 0.35
SWING_POST_SEC = 0.02
TOUCHDOWN_PRE_SEC = 0.05
TOUCHDOWN_POST_SEC = 0.10
SWING_MAX_LAG_SEC = 0.20        # swing window ~330 ms — wide search OK
TOUCHDOWN_MAX_LAG_SEC = 0.05    # touchdown window 150 ms — cap at 1/3 of window
MIN_SAMPLE_POINTS = 10
DIFF_EPS_RAD = 5e-4
MIN_GAIN_TARGET_AMP_RAD = 0.01  # 10 mrad: below this target amplitude, gain is noise
PROFILE_BINS = 21

ANKLE_AXES = ("roll", "pitch")
LEG_JOINTS = ("hip_pitch", "hip_roll", "hip_yaw", "knee_pitch", "ankle_pitch", "ankle_roll")
PROFILE_JOINTS = ("hip_pitch", "knee_pitch", "ankle_pitch", "ankle_roll")
AMPLITUDE_BINS = (0.0, 0.005, 0.01, 0.02, 0.04, 0.08, 1.0)
FREQ_BINS = (0.0, 1.0, 2.5, 5.0, 8.0, 12.0, 20.0, 1000.0)


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


REAL_CASES = [
    ("real", "25/0.4 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100024.csv"),
    ("real", "30/0.4 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100314.csv"),
    ("real", "35/0.5 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100705.csv"),
    ("real", "40/0.8 all_ankles", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv"),
]

SIM_CASES = [
    ("sim", "2504", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133905_2504.csv"),
    ("sim", "3505", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133024_3505.csv"),
    ("sim", "4005", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134153_4005.csv"),
    ("sim", "5008", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134417_5008.csv"),
]


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def median(values):
    valid = sorted(v for v in values if isinstance(v, (int, float)) and not math.isnan(v))
    if not valid:
        return math.nan
    mid = len(valid) // 2
    if len(valid) % 2 == 1:
        return valid[mid]
    return 0.5 * (valid[mid - 1] + valid[mid])


def stddev(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if len(valid) < 2:
        return 0.0 if valid else math.nan
    mu = mean(valid)
    return math.sqrt(sum((v - mu) ** 2 for v in valid) / len(valid))


def rms(values):
    valid = [float(v) for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return math.sqrt(sum(v * v for v in valid) / len(valid))


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


def moving_average(signal, kernel_size: int):
    if not signal:
        return []
    kernel_size = max(1, min(kernel_size, len(signal)))
    half = kernel_size // 2
    out = []
    for idx in range(len(signal)):
        start = max(0, idx - half)
        end = min(len(signal), idx + half + 1)
        out.append(mean(signal[start:end]))
    return out


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
    return [(v - mu) / sigma if not math.isnan(v) else 0.0 for v in values]


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


def sign_flip_count(signal, eps: float):
    if len(signal) < 3:
        return 0
    diffs = [signal[i + 1] - signal[i] for i in range(len(signal) - 1)]
    signs = []
    for value in diffs:
        if abs(value) <= eps:
            continue
        signs.append(1 if value > 0.0 else -1)
    if len(signs) < 2:
        return 0
    return sum(1 for i in range(len(signs) - 1) if signs[i] != signs[i + 1])


def local_extrema_count(signal, eps: float):
    if len(signal) < 3:
        return 0
    count = 0
    for idx in range(1, len(signal) - 1):
        prev_delta = signal[idx] - signal[idx - 1]
        next_delta = signal[idx + 1] - signal[idx]
        if abs(prev_delta) <= eps or abs(next_delta) <= eps:
            continue
        if prev_delta * next_delta < 0:
            count += 1
    return count


def dominant_frequency_hz(signal, dt_sec):
    if len(signal) < 6 or dt_sec <= 0:
        return math.nan
    avg = mean(signal)
    centered = [float(value) - avg for value in signal]
    n = len(centered)
    best_freq = math.nan
    best_power = 0.0
    for k in range(1, n // 2 + 1):
        real = 0.0
        imag = 0.0
        for idx, value in enumerate(centered):
            angle = 2.0 * math.pi * k * idx / n
            real += value * math.cos(angle)
            imag -= value * math.sin(angle)
        power = real * real + imag * imag
        if power > best_power:
            best_power = power
            best_freq = k / (n * dt_sec)
    return best_freq


def jitter_metrics(values, dt_sec):
    signal = [float(value) for value in values]
    if len(signal) < 5:
        return {
            "range": math.nan,
            "path_length": math.nan,
            "hp_rms": math.nan,
            "vel_rms": math.nan,
            "direction_change_rate_hz": math.nan,
            "extrema_rate_hz": math.nan,
            "dominant_freq_hz": math.nan,
        }
    baseline = moving_average(signal, 5)
    residual = [value - base for value, base in zip(signal, baseline)]
    diffs = [signal[i + 1] - signal[i] for i in range(len(signal) - 1)]
    vel = [diff / max(dt_sec, 1e-6) for diff in diffs]
    duration_sec = max((len(signal) - 1) * dt_sec, 1e-6)
    return {
        "range": max(signal) - min(signal),
        "path_length": sum(abs(value) for value in diffs),
        "hp_rms": rms(residual),
        "vel_rms": rms(vel),
        "direction_change_rate_hz": sign_flip_count(signal, DIFF_EPS_RAD) / duration_sec,
        "extrema_rate_hz": local_extrema_count(signal, DIFF_EPS_RAD) / duration_sec,
        "dominant_freq_hz": dominant_frequency_hz(signal, dt_sec),
    }


def select_window_rows(rows, event_time, window_name):
    if window_name == "swing":
        start_t = event_time - SWING_PRE_SEC
        end_t = event_time - SWING_POST_SEC
    elif window_name == "touchdown":
        start_t = event_time - TOUCHDOWN_PRE_SEC
        end_t = event_time + TOUCHDOWN_POST_SEC
    else:
        raise ValueError(window_name)
    return [row for row in rows if start_t <= row["time_sec"] <= end_t]


def other_side(side: str) -> str:
    return "right" if side == "left" else "left"


def align_signals(target, joint, times, lag_samples):
    lag_samples = 0 if math.isnan(lag_samples) else int(max(0, lag_samples))
    if lag_samples >= len(target) or lag_samples >= len(joint):
        return [], [], []
    if lag_samples == 0:
        return list(target), list(joint), list(times)
    return list(target[:-lag_samples]), list(joint[lag_samples:]), list(times[:-lag_samples])


def extract_cycles(target, joint, times):
    if len(target) < 6 or len(joint) < 6 or len(times) < 6:
        return []
    diffs = [target[i + 1] - target[i] for i in range(len(target) - 1)]
    signs = []
    for diff in diffs:
        if diff > DIFF_EPS_RAD:
            signs.append(1)
        elif diff < -DIFF_EPS_RAD:
            signs.append(-1)
        else:
            signs.append(0)

    turning_points = [0]
    last_sign = 0
    for idx, sign in enumerate(signs, start=1):
        if sign == 0:
            continue
        if last_sign == 0:
            last_sign = sign
            continue
        if sign != last_sign:
            turning_points.append(idx)
            last_sign = sign
    turning_points.append(len(target) - 1)
    turning_points = sorted(set(turning_points))

    cycles = []
    for start_idx, end_idx in zip(turning_points[:-1], turning_points[1:]):
        if end_idx - start_idx < 2:
            continue
        dt = times[end_idx] - times[start_idx]
        if dt <= 0:
            continue
        target_amp = abs(target[end_idx] - target[start_idx])
        joint_amp = abs(joint[end_idx] - joint[start_idx])
        if target_amp <= DIFF_EPS_RAD and joint_amp <= DIFF_EPS_RAD:
            continue
        segment_target = target[start_idx : end_idx + 1]
        segment_joint = joint[start_idx : end_idx + 1]
        segment_err = [a - b for a, b in zip(segment_target, segment_joint)]
        cycles.append(
            {
                "target_amplitude_rad": target_amp,
                "joint_amplitude_rad": joint_amp,
                "amplitude_gain": joint_amp / target_amp if target_amp >= MIN_GAIN_TARGET_AMP_RAD else math.nan,
                "segment_duration_sec": dt,
                "equivalent_frequency_hz": 1.0 / max(2.0 * dt, 1e-6),
                "segment_tracking_err_rms_rad": rms(segment_err),
                "segment_target_path_rad": sum(abs(v) for v in first_differences(segment_target)),
                "segment_joint_path_rad": sum(abs(v) for v in first_differences(segment_joint)),
            }
        )
    return cycles


def bin_label(value, bins, digits=4):
    if value is None or math.isnan(value):
        return "nan"
    for low, high in zip(bins[:-1], bins[1:]):
        if low <= value < high:
            return f"[{low:.{digits}f},{high:.{digits}f})"
    return f"[{bins[-2]:.{digits}f},{bins[-1]:.{digits}f})"


def profile_sample(rows, field_name, phase):
    phase = min(max(phase, 0.0), 1.0)
    if not rows:
        return math.nan
    if len(rows) == 1:
        return rows[0][field_name]
    idx = phase * (len(rows) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return rows[lo][field_name]
    alpha = idx - lo
    return rows[lo][field_name] * (1.0 - alpha) + rows[hi][field_name] * alpha


def ascii_bar(value, max_value, width=24):
    if value is None or math.isnan(value) or max_value <= 0:
        return ""
    filled = int(round(width * max(0.0, value) / max_value))
    return "#" * max(0, filled)


def summarize_histogram(rows, value_key, bins, digits=4):
    counts = defaultdict(int)
    grouped = defaultdict(list)
    for row in rows:
        label = bin_label(row[value_key], bins, digits=digits)
        counts[label] += 1
        grouped[label].append(row)
    out = []
    max_count = max(counts.values()) if counts else 0
    for low, high in zip(bins[:-1], bins[1:]):
        label = f"[{low:.{digits}f},{high:.{digits}f})"
        items = grouped.get(label, [])
        out.append(
            {
                "bin_label": label,
                "count": len(items),
                "bar": ascii_bar(len(items), max_count),
                "mean_joint_amplitude_rad": mean([item.get("joint_amplitude_rad", math.nan) for item in items]),
                "mean_amplitude_gain": mean([item.get("amplitude_gain", math.nan) for item in items]),
                "mean_tracking_err_rms_rad": mean([item.get("segment_tracking_err_rms_rad", math.nan) for item in items]),
            }
        )
    return out


def add_delay_and_jitter_rows(dataset, case_label, rel_path, rows, events, delay_rows, cycle_rows, profile_rows, touchdown_rows):
    dt_sec = median([rows[i + 1]["time_sec"] - rows[i]["time_sec"] for i in range(len(rows) - 1)])
    swing_max_lag_samples = max(1, int(round(SWING_MAX_LAG_SEC / max(dt_sec, 1e-6))))
    touchdown_max_lag_samples = max(1, int(round(TOUCHDOWN_MAX_LAG_SEC / max(dt_sec, 1e-6))))
    diag_csv = os.path.basename(rel_path)

    for step_idx, event in enumerate(events, start=1):
        touchdown_row = rows[event.index]
        first_contact_row = rows[event.first_contact_index]
        fc_dt_ms = (event.timestamp_sec - event.first_contact_time_sec) * 1000.0
        td_side = event.side
        sp_side = other_side(td_side)
        touchdown_rows.append(
            {
                "dataset": dataset,
                "case_label": case_label,
                "diag_csv": diag_csv,
                "step_index": step_idx,
                "touchdown_side": td_side,
                "touchdown_time_sec": event.timestamp_sec,
                "first_contact_time_sec": event.first_contact_time_sec,
                "fc_to_stable_ms": round(fc_dt_ms, 1),
                "touchdown_source": event.source,
                "base_euler_x_rad": touchdown_row["base_euler_x"],
                "base_euler_y_rad": touchdown_row["base_euler_y"],
                "base_euler_z_rad": touchdown_row["base_euler_z"],
                # ---- 关节角（stable 时刻）----
                **{
                    f"touchdown_leg_{joint}_rad": touchdown_row[f"pos_{td_side}_{joint}_joint"]
                    for joint in LEG_JOINTS
                },
                **{
                    f"support_leg_{joint}_rad": touchdown_row[f"pos_{sp_side}_{joint}_joint"]
                    for joint in LEG_JOINTS
                },
                # ---- 脚掌世界系roll/pitch（stable 时刻，MuJoCo FK bias校正）----
                "touchdown_leg_sole_roll_rad":  touchdown_row.get(f"{td_side}_sole_roll", float("nan")),
                "touchdown_leg_sole_pitch_rad": touchdown_row.get(f"{td_side}_sole_pitch", float("nan")),
                "support_leg_sole_roll_rad":    touchdown_row.get(f"{sp_side}_sole_roll", float("nan")),
                "support_leg_sole_pitch_rad":   touchdown_row.get(f"{sp_side}_sole_pitch", float("nan")),
                # ---- 脚掌世界系roll/pitch（first_contact 时刻）----
                "fc_touchdown_leg_sole_roll_rad":  first_contact_row.get(f"{td_side}_sole_roll", float("nan")),
                "fc_touchdown_leg_sole_pitch_rad": first_contact_row.get(f"{td_side}_sole_pitch", float("nan")),
                "fc_touchdown_leg_ankle_roll_rad": first_contact_row.get(f"pos_{td_side}_ankle_roll_joint", float("nan")),
            }
        )

        for window_name in ("swing", "touchdown"):
            window_rows = select_window_rows(rows, event.timestamp_sec, window_name)
            if len(window_rows) < 8:
                continue

            role_map = {
                "swing": {"event_leg": event.side, "opposite_leg": other_side(event.side)},
                "touchdown": {"landing_leg": event.side, "stance_leg": other_side(event.side)},
            }[window_name]

            for role_name, side in role_map.items():
                for joint in PROFILE_JOINTS:
                    for bin_idx in range(PROFILE_BINS):
                        phase = bin_idx / (PROFILE_BINS - 1)
                        profile_rows.append(
                            {
                                "dataset": dataset,
                                "case_label": case_label,
                                "diag_csv": diag_csv,
                                "step_index": step_idx,
                                "touchdown_side": event.side,
                                "window": window_name,
                                "role": role_name,
                                "joint": joint,
                                "phase_bin": bin_idx,
                                "norm_phase": phase,
                                "pos_target_rad": profile_sample(window_rows, f"pos_des_raw_{side}_{joint}_joint", phase),
                                "joint_pos_rad": profile_sample(window_rows, f"pos_{side}_{joint}_joint", phase),
                            }
                        )

            for side in ("left", "right"):
                for axis in ANKLE_AXES:
                    target = [row[f"pos_des_raw_{side}_ankle_{axis}_joint"] for row in window_rows]
                    joint = [row[f"pos_{side}_ankle_{axis}_joint"] for row in window_rows]
                    times = [row["time_sec"] for row in window_rows]
                    window_max_lag = swing_max_lag_samples if window_name == "swing" else touchdown_max_lag_samples
                    lag_samples, corr = best_lag_samples(target, joint, window_max_lag)
                    aligned_target, aligned_joint, aligned_times = align_signals(target, joint, times, lag_samples)
                    aligned_err = [a - b for a, b in zip(aligned_target, aligned_joint)]
                    joint_metrics = jitter_metrics(aligned_joint, dt_sec)
                    target_metrics = jitter_metrics(aligned_target, dt_sec)
                    err_metrics = jitter_metrics(aligned_err, dt_sec)
                    delay_rows.append(
                        {
                            "dataset": dataset,
                            "case_label": case_label,
                            "diag_csv": diag_csv,
                            "step_index": step_idx,
                            "touchdown_side": event.side,
                            "window": window_name,
                            "side": side,
                            "axis": axis,
                            "touchdown_time_sec": event.timestamp_sec,
                            "lag_samples": lag_samples,
                            "lag_ms": lag_samples * dt_sec * 1000.0 if not math.isnan(lag_samples) else math.nan,
                            "corr": corr,
                            "raw_sample_count": len(window_rows),
                            "aligned_sample_count": len(aligned_joint),
                            "target_range_rad": target_metrics["range"],
                            "joint_range_rad": joint_metrics["range"],
                            "target_path_rad": target_metrics["path_length"],
                            "joint_path_rad": joint_metrics["path_length"],
                            "joint_hp_rms_rad": joint_metrics["hp_rms"],
                            "joint_vel_rms_radps": joint_metrics["vel_rms"],
                            "joint_direction_change_rate_hz": joint_metrics["direction_change_rate_hz"],
                            "joint_extrema_rate_hz": joint_metrics["extrema_rate_hz"],
                            "joint_dominant_freq_hz": joint_metrics["dominant_freq_hz"],
                            "aligned_tracking_err_rms_rad": rms(aligned_err),
                            "aligned_tracking_err_hp_rms_rad": err_metrics["hp_rms"],
                            "aligned_tracking_err_path_rad": err_metrics["path_length"],
                        }
                    )

                    for cycle_idx, cycle in enumerate(extract_cycles(aligned_target, aligned_joint, aligned_times), start=1):
                        cycle_rows.append(
                            {
                                "dataset": dataset,
                                "case_label": case_label,
                                "diag_csv": diag_csv,
                                "step_index": step_idx,
                                "touchdown_side": event.side,
                                "window": window_name,
                                "side": side,
                                "axis": axis,
                                "cycle_index": cycle_idx,
                                "lag_ms": lag_samples * dt_sec * 1000.0 if not math.isnan(lag_samples) else math.nan,
                                **cycle,
                            }
                        )


def build_markdown(path, delay_rows, cycle_rows, touchdown_rows, profile_rows):
    delay_by_group = defaultdict(list)
    for row in delay_rows:
        delay_by_group[(row["dataset"], row["case_label"], row["step_index"], row["window"])].append(row)

    cycles_by_group = defaultdict(list)
    for row in cycle_rows:
        cycles_by_group[(row["dataset"], row["case_label"], row["step_index"], row["window"], row["side"], row["axis"])].append(row)

    touchdown_by_case = defaultdict(list)
    for row in touchdown_rows:
        touchdown_by_case[(row["dataset"], row["case_label"])].append(row)

    profile_by_key = defaultdict(list)
    for row in profile_rows:
        profile_by_key[(row["dataset"], row["case_label"], row["step_index"], row["window"], row["role"], row["joint"])].append(row)

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# 28 Forward X Failure First-6-Step Stage Detail Analysis\n\n")
        handle.write("⚠️ STANDALONE MODE — `.oma/best.json` 缺失，本次按已有 deploy/forward_x_failure 上下文直接进入细粒度分析。\n\n")
        handle.write("## Scope\n\n")
        handle.write("- Data rerun scope: real 4 cases + sim 4 cases.\n")
        handle.write("- Event scope: each case first 6 touchdown events, no all-step averaging used as the primary readout.\n")
        handle.write("- Stage split: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.\n")
        handle.write("- Delay analysis: only `pos_target(pos_des_raw) -> joint_pos(pos)` network lag.\n")
        handle.write("- Jitter analysis: first align by the estimated delay, then read joint adjustment frequency, amplitude, and target-to-joint response.\n")
        handle.write("- Touchdown posture: use `joint_pos` only; no `sole_pos`-based touchdown attitude metric is used in this report.\n\n")

        handle.write("## Output Files\n\n")
        handle.write("- `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_delay_detail.csv`\n")
        handle.write("- `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_cycle_detail.csv`\n")
        handle.write("- `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_touchdown_posture.csv`\n")
        handle.write("- `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_phase_profiles.csv`\n")
        handle.write("- `real2sim/table/forward_x_failure_first6/forward_x_failure_first6_cycle_histograms.csv`\n\n")

        handle.write("## 1. Delay Per Step / Per Stage\n\n")
        for key in sorted(delay_by_group.keys()):
            dataset, case_label, step_index, window_name = key
            rows = sorted(delay_by_group[key], key=lambda item: (item["side"], item["axis"]))
            handle.write(f"### {dataset} | {case_label} | step {step_index} | {window_name}\n\n")
            handle.write("| side | axis | lag_ms | corr | joint_dom_hz | joint_dir_hz | joint_range | joint_path | aligned_track_err |\n")
            handle.write("|---|---|---:|---:|---:|---:|---:|---:|---:|\n")
            for row in rows:
                handle.write(
                    f"| {row['side']} | {row['axis']} | {fmt(row['lag_ms'], 2)} | {fmt(row['corr'], 3)} | "
                    f"{fmt(row['joint_dominant_freq_hz'], 2)} | {fmt(row['joint_direction_change_rate_hz'], 2)} | "
                    f"{fmt(row['joint_range_rad'])} | {fmt(row['joint_path_rad'])} | {fmt(row['aligned_tracking_err_rms_rad'])} |\n"
                )
            handle.write("\n")

        handle.write("## 2. Delay-Aligned Jitter Histograms\n\n")
        handle.write("每个小节都对应单个 `dataset/case/step/window/side/axis`，不再把前6步混成一个整体均值。\n\n")
        for key in sorted(cycles_by_group.keys()):
            dataset, case_label, step_index, window_name, side, axis = key
            rows = cycles_by_group[key]
            if not rows:
                continue
            freq_hist = summarize_histogram(rows, "equivalent_frequency_hz", FREQ_BINS, digits=2)
            amp_hist = summarize_histogram(rows, "target_amplitude_rad", AMPLITUDE_BINS, digits=3)
            handle.write(f"### {dataset} | {case_label} | step {step_index} | {window_name} | {side} {axis}\n\n")
            handle.write(f"- cycles: `{len(rows)}`\n")
            handle.write(f"- median lag_ms: `{fmt(median([row['lag_ms'] for row in rows]), 2)}`\n")
            handle.write(f"- mean target amp: `{fmt(mean([row['target_amplitude_rad'] for row in rows]))}` rad\n")
            handle.write(f"- mean joint amp: `{fmt(mean([row['joint_amplitude_rad'] for row in rows]))}` rad\n")
            handle.write(f"- mean gain: `{fmt(mean([row['amplitude_gain'] for row in rows]))}`\n")
            handle.write(f"- mean tracking err rms: `{fmt(mean([row['segment_tracking_err_rms_rad'] for row in rows]))}` rad\n\n")

            handle.write("频率柱状图（由延迟对齐后的 `pos_target` 变化周期提取，频率按半周期换算）：\n\n")
            handle.write("| freq bin (Hz) | count | bar |\n")
            handle.write("|---|---:|---|\n")
            for row in freq_hist:
                handle.write(f"| {row['bin_label']} | {row['count']} | {row['bar']} |\n")
            handle.write("\n")

            handle.write("幅值柱状图（同一组 cycle，以 `pos_target` 幅值分桶）：\n\n")
            handle.write("| amp bin (rad) | count | bar | mean joint amp | mean gain | mean track err |\n")
            handle.write("|---|---:|---|---:|---:|---:|\n")
            for row in amp_hist:
                handle.write(
                    f"| {row['bin_label']} | {row['count']} | {row['bar']} | {fmt(row['mean_joint_amplitude_rad'])} | "
                    f"{fmt(row['mean_amplitude_gain'])} | {fmt(row['mean_tracking_err_rms_rad'])} |\n"
                )
            handle.write("\n")

        handle.write("## 3. Touchdown Joint Posture\n\n")
        for key in sorted(touchdown_by_case.keys()):
            dataset, case_label = key
            rows = sorted(touchdown_by_case[key], key=lambda item: item["step_index"])
            handle.write(f"### {dataset} | {case_label}\n\n")
            handle.write("| step | side | hip_pitch | hip_roll | hip_yaw | knee_pitch | ankle_pitch | ankle_roll |\n")
            handle.write("|---|---|---:|---:|---:|---:|---:|---:|\n")
            for row in rows:
                handle.write(
                    f"| {row['step_index']} | {row['touchdown_side']} | "
                    f"{fmt(row['touchdown_leg_hip_pitch_rad'])} | {fmt(row['touchdown_leg_hip_roll_rad'])} | "
                    f"{fmt(row['touchdown_leg_hip_yaw_rad'])} | {fmt(row['touchdown_leg_knee_pitch_rad'])} | "
                    f"{fmt(row['touchdown_leg_ankle_pitch_rad'])} | {fmt(row['touchdown_leg_ankle_roll_rad'])} |\n"
                )
            handle.write("\n")
            for joint in LEG_JOINTS:
                values = [row[f"touchdown_leg_{joint}_rad"] for row in rows]
                handle.write(
                    f"- {joint}: mean `{fmt(mean(values))}` rad, std `{fmt(stddev(values))}` rad, "
                    f"min `{fmt(min(values))}`, max `{fmt(max(values))}`\n"
                )
            handle.write("\n")

        handle.write("## 4. Swing/Support Posture Curves\n\n")
        handle.write("下面给出每个 case、每一步、每个阶段下的关键关节相位曲线摘要；完整离散曲线已经写入 `forward_x_failure_first6_phase_profiles.csv`。\n\n")
        for key in sorted(profile_by_key.keys()):
            dataset, case_label, step_index, window_name, role, joint = key
            rows = sorted(profile_by_key[key], key=lambda item: item["phase_bin"])
            target_values = [row["pos_target_rad"] for row in rows]
            joint_values = [row["joint_pos_rad"] for row in rows]
            if not rows:
                continue
            handle.write(
                f"- {dataset} | {case_label} | step {step_index} | {window_name} | {role} | {joint}: "
                f"target range `{fmt(max(target_values) - min(target_values))}` rad, "
                f"joint range `{fmt(max(joint_values) - min(joint_values))}` rad, "
                f"end target/joint `{fmt(target_values[-1])}` / `{fmt(joint_values[-1])}` rad\n"
            )


def build_cycle_hist_rows(cycle_rows):
    grouped = defaultdict(list)
    for row in cycle_rows:
        grouped[(row["dataset"], row["case_label"], row["step_index"], row["window"], row["side"], row["axis"])].append(row)

    out = []
    for key, rows in sorted(grouped.items()):
        dataset, case_label, step_index, window_name, side, axis = key
        for row in summarize_histogram(rows, "equivalent_frequency_hz", FREQ_BINS, digits=2):
            out.append(
                {
                    "dataset": dataset,
                    "case_label": case_label,
                    "step_index": step_index,
                    "window": window_name,
                    "side": side,
                    "axis": axis,
                    "hist_type": "frequency",
                    **row,
                }
            )
        for row in summarize_histogram(rows, "target_amplitude_rad", AMPLITUDE_BINS, digits=3):
            out.append(
                {
                    "dataset": dataset,
                    "case_label": case_label,
                    "step_index": step_index,
                    "window": window_name,
                    "side": side,
                    "axis": axis,
                    "hist_type": "amplitude",
                    **row,
                }
            )
    return out


def main():
    delay_rows = []
    cycle_rows = []
    touchdown_rows = []
    profile_rows = []

    for dataset, case_label, rel_path in REAL_CASES + SIM_CASES:
        csv_path = os.path.join(BASE_DIR, rel_path)
        rows = ROUND3A.load_csv(csv_path)
        ROUND3A.attach_fk_metrics(rows)
        events = sorted(ROUND3A.detect_touchdowns(rows), key=lambda event: event.timestamp_sec)[:STEP_LIMIT]
        add_delay_and_jitter_rows(
            dataset,
            case_label,
            rel_path,
            rows,
            events,
            delay_rows,
            cycle_rows,
            profile_rows,
            touchdown_rows,
        )

    hist_rows = build_cycle_hist_rows(cycle_rows)

    delay_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_delay_detail.csv")
    cycle_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_cycle_detail.csv")
    touchdown_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_touchdown_posture.csv")
    profile_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_phase_profiles.csv")
    hist_csv = os.path.join(OUT_DIR, "forward_x_failure_first6_cycle_histograms.csv")
    result_md = os.path.join(RESULT_DIR, "28_forward_x_failure_first6_step_stage_analysis.md")

    write_csv(delay_csv, delay_rows)
    write_csv(cycle_csv, cycle_rows)
    write_csv(touchdown_csv, touchdown_rows)
    write_csv(profile_csv, profile_rows)
    write_csv(hist_csv, hist_rows)
    build_markdown(result_md, delay_rows, cycle_rows, touchdown_rows, profile_rows)

    print(delay_csv)
    print(cycle_csv)
    print(touchdown_csv)
    print(profile_csv)
    print(hist_csv)
    print(result_md)


if __name__ == "__main__":
    main()
