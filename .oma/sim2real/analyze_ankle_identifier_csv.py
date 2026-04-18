#!/usr/bin/env python3

import argparse
import csv
import math
import statistics
from pathlib import Path


def load_rows(csv_path):
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


def summarize_step(rows):
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
        "coupled_motion": coupled_motion,
        "peak_overshoot": peak_overshoot,
        "overshoot_ratio": overshoot_ratio,
        "steady_error": steady_error,
        "rise_time_sec": rise_time_sec,
        "peak_time_sec": peak_time_sec,
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


def print_step_summary(summary):
    print("Mode: step")
    print(f"  command_step: {summary['command_step']:.6f}")
    print(f"  actual_step: {summary['actual_step']:.6f}")
    if summary["tracking_ratio"] is not None:
        print(f"  tracking_ratio: {summary['tracking_ratio']:.6f}")
    print(f"  coupled_motion: {summary['coupled_motion']:.6f}")
    print(f"  peak_overshoot: {summary['peak_overshoot']:.6f}")
    if summary["overshoot_ratio"] is not None:
        print(f"  overshoot_ratio: {summary['overshoot_ratio']:.6f}")
    print(f"  steady_error: {summary['steady_error']:.6f}")
    if summary["rise_time_sec"] is not None:
        print(f"  rise_time_sec: {summary['rise_time_sec']:.6f}")
    if summary["peak_time_sec"] is not None:
        print(f"  peak_time_sec: {summary['peak_time_sec']:.6f}")
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
    args = parser.parse_args()

    rows = load_rows(args.csv_path)
    if not rows:
        raise SystemExit("CSV has no data rows.")

    print_basic(rows)
    status, target_span, actual_span = detect_signal_path(rows)
    print_signal_path_result(status, target_span, actual_span)

    mode = infer_mode(rows)
    if mode == "step":
        iteration_groups = group_by_iteration(rows)
        iteration_summaries = []
        for iteration in sorted(iteration_groups):
            summary = summarize_step(iteration_groups[iteration])
            iteration_summaries.append(summary)
            print(f"Iteration {iteration}:")
            print_step_summary(summary)

        aggregate_fields = [
            "command_step",
            "actual_step",
            "tracking_ratio",
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
            "primary_peak_velocity",
            "coupled_peak_velocity",
            "primary_peak_effort",
            "coupled_peak_effort",
        ]
        aggregate = summarize_numeric_dicts(iteration_summaries, aggregate_fields)
        response_classes = [summary["response_class"] for summary in iteration_summaries]

        print("Aggregate across iterations:")
        for field in aggregate_fields:
            stats = aggregate[field]
            if stats["mean"] is None:
                continue
            print(f"  {field}: {stats['mean']:.6f} ± {stats['std']:.6f}")
        print(f"  response_classes: {response_classes}")
    elif mode == "sine":
        print_sine_summary(summarize_sine(rows))
    else:
        print("Mode: unknown")


if __name__ == "__main__":
    main()
