#!/usr/bin/env python3

import argparse
import csv
import json
import math
import statistics
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
OMA_DIR = SCRIPT_DIR.parent
REPO_ROOT = OMA_DIR.parent


def resolve_existing_path(path, fallback_candidates=None):
    candidates = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.extend(
            [
                path,
                REPO_ROOT / path,
                SCRIPT_DIR / path,
                OMA_DIR / path,
            ]
        )
    if fallback_candidates:
        candidates.extend(fallback_candidates)

    seen = set()
    unique_candidates = []
    for candidate in candidates:
        resolved_key = str(candidate)
        if resolved_key in seen:
            continue
        seen.add(resolved_key)
        unique_candidates.append(candidate)
        if candidate.exists():
            return candidate

    checked = "\n  - ".join(str(candidate) for candidate in unique_candidates)
    raise FileNotFoundError(f"Could not find required file. Checked:\n  - {checked}")


def resolve_deploy_info_path(deploy_info_path):
    return resolve_existing_path(
        deploy_info_path,
        fallback_candidates=[
            OMA_DIR / "deploy_info.json",
            REPO_ROOT / ".oma" / "deploy_info.json",
        ],
    )


def load_rows(csv_path):
    csv_path = resolve_existing_path(csv_path)
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "time_sec": float(row["time_sec"]),
                    "phase": row["phase"],
                    "iteration": int(row["iteration"]),
                    "primary_joint": row["primary_joint"],
                    "coupled_joint": row["coupled_joint"],
                    "target_primary": float(row["target_primary"]),
                    "target_coupled": float(row["target_coupled"]),
                    "actual_primary": float(row["actual_primary"]),
                    "actual_coupled": float(row["actual_coupled"]),
                    "actual_primary_vel": float(row["actual_primary_vel"]),
                    "actual_coupled_vel": float(row["actual_coupled_vel"]),
                    "actual_primary_effort": float(row["actual_primary_effort"]),
                    "actual_coupled_effort": float(row["actual_coupled_effort"]),
                }
            )
    return rows


def split_by_phase(rows):
    phase_map = {"pre_hold": [], "active": [], "post_hold": []}
    for row in rows:
        phase_map.setdefault(row["phase"], []).append(row)
    return phase_map


def mean(values):
    return statistics.fmean(values) if values else 0.0


def max_abs(values):
    return max((abs(v) for v in values), default=0.0)


def stddev(values):
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def group_by_iteration(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["iteration"], []).append(row)
    return grouped


def interpolate_crossing(t0, y0, t1, y1, level):
    if abs(y1 - y0) < 1e-12:
        return t1
    ratio = (level - y0) / (y1 - y0)
    ratio = max(0.0, min(1.0, ratio))
    return t0 + ratio * (t1 - t0)


def first_crossing_time(times, values, level):
    if not times:
        return None
    if values[0] >= level:
        return times[0]
    for i in range(1, len(times)):
        if values[i] >= level and values[i - 1] < level:
            return interpolate_crossing(times[i - 1], values[i - 1], times[i], values[i], level)
    return None


def settling_time(times, values, target, band):
    if not times:
        return None
    deviations = [abs(v - target) for v in values]
    for i in range(len(times)):
        if all(dev <= band for dev in deviations[i:]):
            return times[i]
    return None


def zero_crossings(times, values):
    crossings = []
    if not times:
        return crossings
    prev_t = times[0]
    prev_v = values[0]
    for cur_t, cur_v in zip(times[1:], values[1:]):
        if prev_v == 0.0:
            crossings.append(prev_t)
        elif cur_v == 0.0:
            crossings.append(cur_t)
        elif (prev_v < 0.0 < cur_v) or (prev_v > 0.0 > cur_v):
            crossings.append(interpolate_crossing(prev_t, prev_v, cur_t, cur_v, 0.0))
        prev_t = cur_t
        prev_v = cur_v
    return crossings


def find_local_extrema(times, values):
    extrema = []
    if len(values) < 3:
        return extrema
    for i in range(1, len(values) - 1):
        prev_v = values[i - 1]
        cur_v = values[i]
        next_v = values[i + 1]
        if (cur_v >= prev_v and cur_v > next_v) or (cur_v > prev_v and cur_v >= next_v):
            extrema.append((times[i], cur_v))
        elif (cur_v <= prev_v and cur_v < next_v) or (cur_v < prev_v and cur_v <= next_v):
            extrema.append((times[i], cur_v))
    return extrema


def estimate_decay_metrics(times, error_values, first_cross_time):
    if first_cross_time is None:
        return None, None

    filtered_times = []
    filtered_errors = []
    for t, e in zip(times, error_values):
        if t >= first_cross_time:
            filtered_times.append(t)
            filtered_errors.append(e)

    extrema = find_local_extrema(filtered_times, filtered_errors)
    envelope = [(t, abs(v)) for t, v in extrema if abs(v) > 1e-9]
    if len(envelope) < 2:
        return None, None

    amp1 = envelope[0][1]
    amp2 = envelope[1][1]
    if amp1 <= 1e-9 or amp2 <= 1e-9:
        return None, None

    decay_ratio = amp2 / amp1
    if decay_ratio <= 0.0 or decay_ratio >= 1.0:
        return decay_ratio, None

    log_dec = math.log(amp1 / amp2)
    damping_ratio = log_dec / math.sqrt((2.0 * math.pi) ** 2 + log_dec**2)
    return decay_ratio, damping_ratio


def ringdown_same_sign_peaks(times, error_values, min_peak_abs, min_peak_interval_sec):
    extrema = find_local_extrema(times, error_values)
    candidates = []
    for sign_name, sign in (("positive", 1.0), ("negative", -1.0)):
        raw_peaks = [
            (t, abs(v))
            for t, v in extrema
            if sign * v > 0.0 and abs(v) >= min_peak_abs
        ]
        peaks = []
        for t, amp in raw_peaks:
            if not peaks or t - peaks[-1][0] >= min_peak_interval_sec:
                peaks.append((t, amp))
            elif amp > peaks[-1][1]:
                peaks[-1] = (t, amp)
        if len(peaks) < 2:
            continue
        log_decrements = []
        periods = []
        for (t0, a0), (t1, a1) in zip(peaks, peaks[1:]):
            if t1 <= t0 or a0 <= 1e-9 or a1 <= 1e-9:
                continue
            periods.append(t1 - t0)
            if a1 < a0:
                log_decrements.append(math.log(a0 / a1))
        candidates.append(
            {
                "sign": sign_name,
                "peaks": peaks,
                "log_decrements": log_decrements,
                "periods": periods,
            }
        )

    if not candidates:
        return None

    # Prefer the polarity that yields the most valid decreasing peak pairs.
    # Tie-break by the first same-sign peak amplitude.
    candidates.sort(
        key=lambda item: (
            len(item["log_decrements"]),
            item["peaks"][0][1] if item["peaks"] else 0.0,
        ),
        reverse=True,
    )
    return candidates[0]


def first_settling_time_from_zero(times, values, band):
    if not times:
        return None
    deviations = [abs(v) for v in values]
    for i in range(len(times)):
        if all(dev <= band for dev in deviations[i:]):
            return times[i]
    return None


def summarize_step_ringdown(rows):
    phases = split_by_phase(rows)
    pre_rows = phases.get("pre_hold", [])
    active_rows = phases.get("active", [])
    post_rows = phases.get("post_hold", [])
    if not pre_rows or not active_rows or not post_rows:
        return {
            "ringdown_valid": False,
            "ringdown_invalid_reason": "missing_pre_active_or_post_rows",
        }

    pre_target = mean([r["target_primary"] for r in pre_rows])
    active_target = mean([r["target_primary"] for r in active_rows])
    command_step = active_target - pre_target
    step_size = abs(command_step)
    if step_size <= 1e-9:
        return {
            "ringdown_valid": False,
            "ringdown_invalid_reason": "zero_command_step",
            "ringdown_command_step": command_step,
        }

    t0 = post_rows[0]["time_sec"]
    times = [r["time_sec"] - t0 for r in post_rows]
    errors = [r["actual_primary"] - r["target_primary"] for r in post_rows]
    max_abs_error = max_abs(errors)
    overshoot_ratio = max_abs_error / step_size
    settling_band = max(0.02 * step_size, 1e-6)
    settling = first_settling_time_from_zero(times, errors, settling_band)

    min_peak_interval_sec = 1.0 / 30.0
    peak_info = ringdown_same_sign_peaks(
        times,
        errors,
        min_peak_abs=settling_band,
        min_peak_interval_sec=min_peak_interval_sec,
    )
    peak_count = len(peak_info["peaks"]) if peak_info else 0
    valid_log_decrements = peak_info["log_decrements"] if peak_info else []
    periods = peak_info["periods"] if peak_info else []

    log_decrement_delta = mean(valid_log_decrements) if valid_log_decrements else None
    zeta_step = None
    if log_decrement_delta is not None:
        zeta_step = log_decrement_delta / math.sqrt((2.0 * math.pi) ** 2 + log_decrement_delta**2)

    ringdown_freq_hz = None
    if periods:
        ringdown_freq_hz = 1.0 / mean(periods)

    f_n_closed_loop_hz = None
    if ringdown_freq_hz is not None and zeta_step is not None and zeta_step < 1.0:
        f_n_closed_loop_hz = ringdown_freq_hz / math.sqrt(max(1e-12, 1.0 - zeta_step**2))

    invalid_reason = None
    if peak_count < 2:
        invalid_reason = "same_sign_peak_count_lt_2"
    elif not valid_log_decrements:
        invalid_reason = "no_decreasing_same_sign_peak_pairs"

    return {
        "ringdown_valid": invalid_reason is None,
        "ringdown_invalid_reason": invalid_reason,
        "ringdown_command_step": command_step,
        "ringdown_step_amplitude_rad": step_size,
        "ringdown_peak_polarity": peak_info["sign"] if peak_info else None,
        "ringdown_peak_count": peak_count,
        "ringdown_valid_log_decrement_pair_count": len(valid_log_decrements),
        "log_decrement_delta": log_decrement_delta,
        "zeta_step": zeta_step,
        "ringdown_freq_hz": ringdown_freq_hz,
        "f_n_closed_loop_hz": f_n_closed_loop_hz,
        "max_abs_overshoot": max_abs_error,
        "ringdown_overshoot_ratio": overshoot_ratio,
        "settling_threshold_rad": settling_band,
        "settling_time_ms": settling * 1000.0 if settling is not None else None,
        "post_hold_duration_sec": times[-1] if times else None,
        "ringdown_min_peak_interval_sec": min_peak_interval_sec,
        "ringdown_min_peak_abs": settling_band,
        "ringdown_first_peak_time_sec": peak_info["peaks"][0][0] if peak_info else None,
        "ringdown_first_peak_abs_error": peak_info["peaks"][0][1] if peak_info else None,
    }


def classify_response(overshoot, zero_crossing_count, settling_time_sec, tracking_ratio):
    if tracking_ratio is None:
        return "unknown"
    if tracking_ratio < 0.8:
        return "undershoot_soft"
    if overshoot <= 1e-6 and zero_crossing_count == 0 and tracking_ratio <= 1.05:
        return "well_damped_tracking"
    if overshoot <= 1e-6:
        return "no_overshoot"
    if zero_crossing_count <= 1:
        return "single_overshoot"
    if settling_time_sec is None:
        return "sustained_oscillation"
    return "oscillatory_but_settling"


def summarize_numeric_dicts(items, fields):
    summary = {}
    for field in fields:
        values = [item[field] for item in items if item.get(field) is not None]
        if not values:
            summary[field] = {"mean": None, "std": None}
            continue
        summary[field] = {"mean": mean(values), "std": stddev(values)}
    return summary


def load_timing_context(deploy_info_path):
    deploy_info_path = resolve_deploy_info_path(deploy_info_path)
    with open(deploy_info_path, "r", encoding="utf-8") as f:
        deploy_info = json.load(f)

    control_hz = deploy_info["deployment_target"]["control_frequency_hz"]
    cycle_time_sec = deploy_info["rl_walk_leg_params"]["walk_step_conf"]["cycle_time"]
    stance_ratio = 0.6
    rise_budget_ratio = 0.2
    peak_budget_ratio = 0.35

    stance_time_sec = cycle_time_sec * stance_ratio
    return {
        "deploy_info_path": str(deploy_info_path),
        "control_hz": control_hz,
        "control_period_sec": 1.0 / control_hz if control_hz > 0 else None,
        "cycle_time_sec": cycle_time_sec,
        "stance_ratio": stance_ratio,
        "stance_time_sec": stance_time_sec,
        "rise_budget_ratio": rise_budget_ratio,
        "peak_budget_ratio": peak_budget_ratio,
        "rise_time_upper_sec": stance_time_sec * rise_budget_ratio,
        "peak_time_upper_sec": stance_time_sec * peak_budget_ratio,
        "rise_time_lower_sec": (1.0 / control_hz) * 5.0 if control_hz > 0 else None,
        "peak_time_lower_sec": 0.015,
    }


def classify_time_status(value_sec, lower_sec, upper_sec, too_slow_label):
    if value_sec is None:
        return "not_available"
    if lower_sec is not None and value_sec < lower_sec:
        return "too_fast"
    if upper_sec is not None and value_sec > upper_sec:
        return too_slow_label
    return "good"


def detect_signal_path(rows):
    target_values = [r["target_primary"] for r in rows]
    actual_values = [r["actual_primary"] for r in rows]
    target_span = max(target_values, default=0.0) - min(target_values, default=0.0)
    actual_span = max(actual_values, default=0.0) - min(actual_values, default=0.0)

    if target_span < 1e-6:
        return "no_target_change", target_span, actual_span
    if actual_span < max(1e-4, target_span * 0.05):
        return "target_changed_but_actual_static", target_span, actual_span
    return "ok", target_span, actual_span


def summarize_step(rows, timing_context):
    phases = split_by_phase(rows)
    pre_rows = phases.get("pre_hold", [])
    active_rows = phases.get("active", [])
    post_rows = phases.get("post_hold", [])

    pre_target = mean([r["target_primary"] for r in pre_rows])
    active_target = mean([r["target_primary"] for r in active_rows])
    post_target = mean([r["target_primary"] for r in post_rows])

    pre_actual = mean([r["actual_primary"] for r in pre_rows])
    active_actual = mean([r["actual_primary"] for r in active_rows])
    post_actual = mean([r["actual_primary"] for r in post_rows])

    command_step = active_target - pre_target
    actual_step = active_actual - pre_actual
    tracking_ratio = actual_step / command_step if abs(command_step) > 1e-9 else None
    coupled_motion = mean([r["actual_coupled"] for r in active_rows]) - mean(
        [r["actual_coupled"] for r in pre_rows]
    )

    steady_error = post_actual - post_target
    direction = 1.0 if command_step >= 0 else -1.0
    step_size = abs(command_step)

    active_times = [r["time_sec"] - active_rows[0]["time_sec"] for r in active_rows] if active_rows else []
    active_positions = [r["actual_primary"] for r in active_rows]
    normalized_response = [direction * (pos - pre_actual) for pos in active_positions]

    peak_normalized = max(normalized_response, default=0.0)
    peak_idx = normalized_response.index(peak_normalized) if normalized_response else 0
    peak_overshoot = max(0.0, peak_normalized - step_size)
    overshoot_ratio = peak_overshoot / step_size if step_size > 1e-9 else None
    peak_tracking_ratio = peak_normalized / step_size if step_size > 1e-9 else None
    peak_time_sec = active_times[peak_idx] if active_times else None
    rise_time_10 = first_crossing_time(active_times, normalized_response, 0.1 * step_size)
    rise_time_90 = first_crossing_time(active_times, normalized_response, 0.9 * step_size)
    rise_time_sec = (
        rise_time_90 - rise_time_10
        if rise_time_10 is not None and rise_time_90 is not None and rise_time_90 >= rise_time_10
        else None
    )
    first_target_cross_time = first_crossing_time(active_times, normalized_response, step_size)
    settling_band = max(0.02 * step_size, 1e-6)
    settling_time_sec = settling_time(active_times, active_positions, active_target, settling_band)

    active_duration_sec = active_times[-1] if active_times else 0.0
    tail_duration_sec = min(0.1, active_duration_sec)
    tail_rows = []
    if active_rows:
        tail_start_time = active_rows[-1]["time_sec"] - tail_duration_sec
        tail_rows = [row for row in active_rows if row["time_sec"] >= tail_start_time]
    tail_actual = mean([r["actual_primary"] for r in tail_rows]) if tail_rows else None
    tail_actual_step = (tail_actual - pre_actual) if tail_actual is not None else None
    tail_tracking_ratio = tail_actual_step / command_step if tail_actual_step is not None and abs(command_step) > 1e-9 else None

    post_actual_step = post_actual - pre_actual
    final_tracking_ratio = post_actual_step / command_step if abs(command_step) > 1e-9 else None

    error_values = [direction * (pos - active_target) for pos in active_positions]
    crossings = zero_crossings(active_times, error_values)
    oscillation_frequency_hz = None
    if len(crossings) >= 3:
        half_periods = [crossings[i] - crossings[i - 1] for i in range(1, len(crossings))]
        valid_half_periods = [dt for dt in half_periods if dt > 1e-6]
        if valid_half_periods:
            oscillation_frequency_hz = 1.0 / (2.0 * mean(valid_half_periods))
    decay_ratio, estimated_damping_ratio = estimate_decay_metrics(
        active_times, error_values, first_target_cross_time
    )
    rise_time_status = classify_time_status(
        rise_time_sec,
        timing_context["rise_time_lower_sec"],
        timing_context["rise_time_upper_sec"],
        "too_slow_for_walking",
    )
    peak_time_status = classify_time_status(
        peak_time_sec,
        timing_context["peak_time_lower_sec"],
        timing_context["peak_time_upper_sec"],
        "unusable_for_walking",
    )

    return {
        "pre_target": pre_target,
        "active_target": active_target,
        "post_target": post_target,
        "pre_actual": pre_actual,
        "active_actual": active_actual,
        "post_actual": post_actual,
        "command_step": command_step,
        "actual_step": actual_step,
        "tracking_ratio": tracking_ratio,
        "peak_tracking_ratio": peak_tracking_ratio,
        "tail_actual_step": tail_actual_step,
        "tail_tracking_ratio": tail_tracking_ratio,
        "post_actual_step": post_actual_step,
        "final_tracking_ratio": final_tracking_ratio,
        "coupled_motion": coupled_motion,
        "peak_overshoot": peak_overshoot,
        "overshoot_ratio": overshoot_ratio,
        "steady_error": steady_error,
        "rise_time_sec": rise_time_sec,
        "rise_time_status": rise_time_status,
        "peak_time_sec": peak_time_sec,
        "peak_time_status": peak_time_status,
        "first_target_cross_time_sec": first_target_cross_time,
        "settling_time_sec": settling_time_sec,
        "zero_crossing_count": len(crossings),
        "oscillation_frequency_hz": oscillation_frequency_hz,
        "decay_ratio": decay_ratio,
        "estimated_damping_ratio": estimated_damping_ratio,
        "response_class": classify_response(
            peak_overshoot, len(crossings), settling_time_sec, tracking_ratio
        ),
        "primary_peak_velocity": max_abs([r["actual_primary_vel"] for r in active_rows]),
        "coupled_peak_velocity": max_abs([r["actual_coupled_vel"] for r in active_rows]),
        "primary_peak_effort": max_abs([r["actual_primary_effort"] for r in active_rows]),
        "coupled_peak_effort": max_abs([r["actual_coupled_effort"] for r in active_rows]),
    }


def summarize_sine(rows):
    phases = split_by_phase(rows)
    active_rows = phases.get("active", [])

    target_values = [r["target_primary"] for r in active_rows]
    actual_values = [r["actual_primary"] for r in active_rows]
    coupled_values = [r["actual_coupled"] for r in active_rows]

    target_amp = (max(target_values, default=0.0) - min(target_values, default=0.0)) / 2.0
    actual_amp = (max(actual_values, default=0.0) - min(actual_values, default=0.0)) / 2.0
    coupled_amp = (max(coupled_values, default=0.0) - min(coupled_values, default=0.0)) / 2.0

    gain = actual_amp / target_amp if target_amp > 1e-8 else 0.0
    coupling_ratio = coupled_amp / actual_amp if actual_amp > 1e-8 else 0.0

    return {
        "target_amplitude": target_amp,
        "actual_amplitude": actual_amp,
        "coupled_amplitude": coupled_amp,
        "gain": gain,
        "coupling_ratio": coupling_ratio,
        "primary_peak_velocity": max_abs([r["actual_primary_vel"] for r in active_rows]),
        "coupled_peak_velocity": max_abs([r["actual_coupled_vel"] for r in active_rows]),
        "primary_peak_effort": max_abs([r["actual_primary_effort"] for r in active_rows]),
        "coupled_peak_effort": max_abs([r["actual_coupled_effort"] for r in active_rows]),
    }


def infer_mode(rows):
    phases = split_by_phase(rows)
    active_rows = phases.get("active", [])
    target_values = [r["target_primary"] for r in active_rows]
    if not target_values:
        return "unknown"
    unique_count = len({round(v, 6) for v in target_values})
    return "step" if unique_count <= 3 else "sine"


def print_basic(rows):
    phases = split_by_phase(rows)
    print("Samples:", len(rows))
    print("Phase counts:")
    for phase in ("pre_hold", "active", "post_hold"):
        print(f"  {phase}: {len(phases.get(phase, []))}")
    if rows:
        print("Primary joint:", rows[0]["primary_joint"])
        print("Coupled joint:", rows[0]["coupled_joint"])
        iterations = sorted({r["iteration"] for r in rows})
        print("Iterations:", iterations)


def print_signal_path_result(status, target_span, actual_span):
    print("Signal path check:")
    print(f"  target_span: {target_span:.6f}")
    print(f"  actual_span: {actual_span:.6f}")
    if status == "ok":
        print("  result: OK, target and actual both changed.")
    elif status == "no_target_change":
        print("  result: target did not change. Check test mode or phase extraction.")
    else:
        print("  result: target changed but actual stayed nearly static. Check /joint_cmd delivery and driver side reception.")


def print_timing_context(timing_context):
    print("Timing context:")
    print(f"  deploy_info_path: {timing_context['deploy_info_path']}")
    print(f"  control_hz: {timing_context['control_hz']}")
    print(f"  cycle_time_sec: {timing_context['cycle_time_sec']:.6f}")
    print(f"  stance_time_sec: {timing_context['stance_time_sec']:.6f}")
    print(f"  rise_time_lower_sec: {timing_context['rise_time_lower_sec']:.6f}")
    print(f"  rise_time_upper_sec: {timing_context['rise_time_upper_sec']:.6f}")
    print(f"  peak_time_lower_sec: {timing_context['peak_time_lower_sec']:.6f}")
    print(f"  peak_time_upper_sec: {timing_context['peak_time_upper_sec']:.6f}")


def print_step_summary(summary):
    print("Mode: step")
    print(f"  command_step: {summary['command_step']:.6f}")
    print(f"  actual_step: {summary['actual_step']:.6f}")
    if summary["tracking_ratio"] is not None:
        print(f"  tracking_ratio(window_mean): {summary['tracking_ratio']:.6f}")
    if summary["peak_tracking_ratio"] is not None:
        print(f"  peak_tracking_ratio: {summary['peak_tracking_ratio']:.6f}")
    if summary["tail_actual_step"] is not None:
        print(f"  tail_actual_step: {summary['tail_actual_step']:.6f}")
    if summary["tail_tracking_ratio"] is not None:
        print(f"  tail_tracking_ratio: {summary['tail_tracking_ratio']:.6f}")
    if summary["post_actual_step"] is not None:
        print(f"  post_actual_step: {summary['post_actual_step']:.6f}")
    if summary["final_tracking_ratio"] is not None:
        print(f"  final_tracking_ratio: {summary['final_tracking_ratio']:.6f}")
    print(f"  coupled_motion: {summary['coupled_motion']:.6f}")
    print(f"  peak_overshoot: {summary['peak_overshoot']:.6f}")
    if summary["overshoot_ratio"] is not None:
        print(f"  overshoot_ratio: {summary['overshoot_ratio']:.6f}")
    print(f"  steady_error: {summary['steady_error']:.6f}")
    if summary["rise_time_sec"] is not None:
        print(f"  rise_time_sec: {summary['rise_time_sec']:.6f}")
        print(f"  rise_time_status: {summary['rise_time_status']}")
    if summary["peak_time_sec"] is not None:
        print(f"  peak_time_sec: {summary['peak_time_sec']:.6f}")
        print(f"  peak_time_status: {summary['peak_time_status']}")
    if summary["first_target_cross_time_sec"] is not None:
        print(f"  first_target_cross_time_sec: {summary['first_target_cross_time_sec']:.6f}")
    if summary["settling_time_sec"] is not None:
        print(f"  settling_time_sec: {summary['settling_time_sec']:.6f}")
    else:
        print("  settling_time_sec: not_settled_within_active_window")
    print(f"  zero_crossing_count: {summary['zero_crossing_count']}")
    if summary["oscillation_frequency_hz"] is not None:
        print(f"  oscillation_frequency_hz: {summary['oscillation_frequency_hz']:.6f}")
    if summary["decay_ratio"] is not None:
        print(f"  decay_ratio: {summary['decay_ratio']:.6f}")
    if summary["estimated_damping_ratio"] is not None:
        print(f"  estimated_damping_ratio: {summary['estimated_damping_ratio']:.6f}")
    print(f"  response_class: {summary['response_class']}")
    print(f"  primary_peak_velocity: {summary['primary_peak_velocity']:.6f}")
    print(f"  coupled_peak_velocity: {summary['coupled_peak_velocity']:.6f}")
    print(f"  primary_peak_effort: {summary['primary_peak_effort']:.6f}")
    print(f"  coupled_peak_effort: {summary['coupled_peak_effort']:.6f}")


def print_step_ringdown_summary(summary):
    print("  Ringdown after active->post release:")
    print(f"    valid: {summary['ringdown_valid']}")
    if summary.get("ringdown_invalid_reason"):
        print(f"    invalid_reason: {summary['ringdown_invalid_reason']}")
    if summary.get("ringdown_command_step") is not None:
        print(f"    command_step: {summary['ringdown_command_step']:.6f}")
    if summary.get("ringdown_step_amplitude_rad") is not None:
        print(f"    step_amplitude_rad: {summary['ringdown_step_amplitude_rad']:.6f}")
    if summary.get("ringdown_peak_polarity") is not None:
        print(f"    peak_polarity: {summary['ringdown_peak_polarity']}")
    print(f"    peak_count_after_step: {summary.get('ringdown_peak_count', 0)}")
    print(
        "    valid_log_decrement_pair_count: "
        f"{summary.get('ringdown_valid_log_decrement_pair_count', 0)}"
    )
    if summary.get("log_decrement_delta") is not None:
        print(f"    log_decrement_delta: {summary['log_decrement_delta']:.6f}")
    if summary.get("zeta_step") is not None:
        print(f"    zeta_step: {summary['zeta_step']:.6f}")
    if summary.get("ringdown_freq_hz") is not None:
        print(f"    ringdown_freq_hz: {summary['ringdown_freq_hz']:.6f}")
    if summary.get("f_n_closed_loop_hz") is not None:
        print(f"    f_n_closed_loop_hz: {summary['f_n_closed_loop_hz']:.6f}")
    if summary.get("max_abs_overshoot") is not None:
        print(f"    max_abs_overshoot: {summary['max_abs_overshoot']:.6f}")
    if summary.get("ringdown_overshoot_ratio") is not None:
        print(f"    overshoot_ratio: {summary['ringdown_overshoot_ratio']:.6f}")
    if summary.get("settling_threshold_rad") is not None:
        print(f"    settling_threshold_rad: {summary['settling_threshold_rad']:.6f}")
    if summary.get("settling_time_ms") is not None:
        print(f"    settling_time_ms: {summary['settling_time_ms']:.3f}")
    else:
        print("    settling_time_ms: not_settled_within_post_hold")


def print_sine_summary(summary):
    print("Mode: sine")
    print(f"  target_amplitude: {summary['target_amplitude']:.6f}")
    print(f"  actual_amplitude: {summary['actual_amplitude']:.6f}")
    print(f"  coupled_amplitude: {summary['coupled_amplitude']:.6f}")
    print(f"  gain: {summary['gain']:.6f}")
    print(f"  coupling_ratio: {summary['coupling_ratio']:.6f}")
    print(f"  primary_peak_velocity: {summary['primary_peak_velocity']:.6f}")
    print(f"  coupled_peak_velocity: {summary['coupled_peak_velocity']:.6f}")
    print(f"  primary_peak_effort: {summary['primary_peak_effort']:.6f}")
    print(f"  coupled_peak_effort: {summary['coupled_peak_effort']:.6f}")


def main():
    parser = argparse.ArgumentParser(description="Analyze native_ros2_ankle_identifier CSV output.")
    parser.add_argument("csv_path", type=Path, help="Path to CSV file generated by native_ros2_ankle_identifier")
    parser.add_argument(
        "--deploy-info",
        type=Path,
        default=Path(".oma/deploy_info.json"),
        help="Path to deploy_info.json used to derive control_hz and cycle_time",
    )
    parser.add_argument("--out-json", type=Path, default=None, help="Optional path to write JSON metrics.")
    parser.add_argument("--out-csv", type=Path, default=None, help="Optional path to write per-iteration CSV metrics.")
    args = parser.parse_args()

    rows = load_rows(args.csv_path)
    if not rows:
        raise SystemExit("CSV has no data rows.")
    timing_context = load_timing_context(args.deploy_info)

    print_basic(rows)
    status, target_span, actual_span = detect_signal_path(rows)
    print_signal_path_result(status, target_span, actual_span)
    print_timing_context(timing_context)

    mode = infer_mode(rows)
    output = {
        "csv_path": str(args.csv_path),
        "mode": mode,
        "sample_count": len(rows),
        "primary_joint": rows[0]["primary_joint"],
        "coupled_joint": rows[0]["coupled_joint"],
        "iterations": sorted({r["iteration"] for r in rows}),
        "iterations_summary": [],
    }
    if mode == "step":
        iteration_groups = group_by_iteration(rows)
        iteration_summaries = []
        ringdown_summaries = []
        for iteration in sorted(iteration_groups):
            summary = summarize_step(iteration_groups[iteration], timing_context)
            ringdown_summary = summarize_step_ringdown(iteration_groups[iteration])
            summary.update(ringdown_summary)
            iteration_summaries.append(summary)
            ringdown_summaries.append(ringdown_summary)
            output["iterations_summary"].append({"iteration": iteration, **summary})
            print(f"Iteration {iteration}:")
            print_step_summary(summary)
            print_step_ringdown_summary(ringdown_summary)

        aggregate_fields = [
            "command_step",
            "actual_step",
            "tracking_ratio",
            "peak_tracking_ratio",
            "tail_actual_step",
            "tail_tracking_ratio",
            "post_actual_step",
            "final_tracking_ratio",
            "coupled_motion",
            "peak_overshoot",
            "overshoot_ratio",
            "steady_error",
            "rise_time_sec",
            "peak_time_sec",
            "first_target_cross_time_sec",
            "settling_time_sec",
            "zero_crossing_count",
            "oscillation_frequency_hz",
            "decay_ratio",
            "estimated_damping_ratio",
            "ringdown_command_step",
            "ringdown_step_amplitude_rad",
            "ringdown_peak_count",
            "ringdown_valid_log_decrement_pair_count",
            "log_decrement_delta",
            "zeta_step",
            "ringdown_freq_hz",
            "f_n_closed_loop_hz",
            "max_abs_overshoot",
            "ringdown_overshoot_ratio",
            "settling_threshold_rad",
            "settling_time_ms",
            "post_hold_duration_sec",
            "ringdown_min_peak_interval_sec",
            "ringdown_min_peak_abs",
            "primary_peak_velocity",
            "coupled_peak_velocity",
            "primary_peak_effort",
            "coupled_peak_effort",
        ]
        aggregate = summarize_numeric_dicts(iteration_summaries, aggregate_fields)
        output["aggregate"] = aggregate
        response_classes = [summary["response_class"] for summary in iteration_summaries]
        rise_statuses = [summary["rise_time_status"] for summary in iteration_summaries]
        peak_statuses = [summary["peak_time_status"] for summary in iteration_summaries]
        ringdown_valid_flags = [summary["ringdown_valid"] for summary in iteration_summaries]
        ringdown_invalid_reasons = [summary["ringdown_invalid_reason"] for summary in iteration_summaries]

        print("Aggregate across iterations:")
        for field in aggregate_fields:
            stats = aggregate[field]
            if stats["mean"] is None:
                continue
            print(f"  {field}: {stats['mean']:.6f} ± {stats['std']:.6f}")
        print(f"  response_classes: {response_classes}")
        print(f"  rise_time_statuses: {rise_statuses}")
        print(f"  peak_time_statuses: {peak_statuses}")
        print(f"  ringdown_valid_flags: {ringdown_valid_flags}")
        print(f"  ringdown_invalid_reasons: {ringdown_invalid_reasons}")
    elif mode == "sine":
        sine_summary = summarize_sine(rows)
        output["summary"] = sine_summary
        print_sine_summary(sine_summary)
    else:
        print("Mode: unknown")

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"Wrote JSON metrics: {args.out_json}")

    if args.out_csv and output["iterations_summary"]:
        args.out_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = sorted({key for item in output["iterations_summary"] for key in item})
        with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output["iterations_summary"])
        print(f"Wrote CSV metrics: {args.out_csv}")


if __name__ == "__main__":
    main()
