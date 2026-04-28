#!/usr/bin/env python3

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


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


def load_timing_context(deploy_info_path):
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


AGGREGATE_FIELDS = [
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
    "primary_peak_velocity",
    "coupled_peak_velocity",
    "primary_peak_effort",
    "coupled_peak_effort",
]


def _fmt(v, digits=6):
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def write_json_report(output_dir, csv_name, mode, basic_info, signal_path_info,
                      timing_context, iteration_summaries=None, aggregate=None,
                      response_classes=None, rise_statuses=None, peak_statuses=None,
                      sine_summary=None):
    report = {
        "csv_file": csv_name,
        "mode": mode,
        "basic_info": basic_info,
        "signal_path": signal_path_info,
        "timing_context": timing_context,
    }
    if mode == "step" and iteration_summaries is not None:
        report["iterations"] = iteration_summaries
        report["aggregate"] = aggregate
        report["response_classes"] = response_classes
        report["rise_time_statuses"] = rise_statuses
        report["peak_time_statuses"] = peak_statuses
    elif mode == "sine" and sine_summary is not None:
        report["sine_summary"] = sine_summary

    stem = Path(csv_name).stem
    json_path = output_dir / f"{stem}_analysis.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"JSON report saved: {json_path}")
    return json_path


def write_markdown_report(output_dir, csv_name, mode, basic_info, signal_path_info,
                          timing_context, iteration_summaries=None, aggregate=None,
                          response_classes=None, rise_statuses=None, peak_statuses=None,
                          sine_summary=None):
    stem = Path(csv_name).stem
    md_path = output_dir / f"{stem}_report.md"
    lines = []
    lines.append(f"# Ankle Identifier Analysis: {csv_name}\n")

    # Basic info
    lines.append("## Basic Info\n")
    for k, v in basic_info.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    # Signal path
    lines.append("## Signal Path Check\n")
    lines.append(f"- **status**: {signal_path_info['status']}")
    lines.append(f"- **target_span**: {_fmt(signal_path_info['target_span'])}")
    lines.append(f"- **actual_span**: {_fmt(signal_path_info['actual_span'])}")
    lines.append("")

    # Timing context
    lines.append("## Timing Context\n")
    lines.append(f"- **control_hz**: {timing_context['control_hz']}")
    lines.append(f"- **cycle_time_sec**: {_fmt(timing_context['cycle_time_sec'])}")
    lines.append(f"- **stance_time_sec**: {_fmt(timing_context['stance_time_sec'])}")
    lines.append(f"- **rise_time_bounds**: [{_fmt(timing_context['rise_time_lower_sec'])}, {_fmt(timing_context['rise_time_upper_sec'])}]")
    lines.append(f"- **peak_time_bounds**: [{_fmt(timing_context['peak_time_lower_sec'])}, {_fmt(timing_context['peak_time_upper_sec'])}]")
    lines.append("")

    if mode == "step" and iteration_summaries:
        # Per-iteration table
        lines.append("## Per-Iteration Results\n")
        key_fields = [
            "command_step", "actual_step", "tracking_ratio", "peak_tracking_ratio",
            "tail_tracking_ratio", "final_tracking_ratio",
            "peak_overshoot", "overshoot_ratio", "steady_error",
            "rise_time_sec", "rise_time_status", "peak_time_sec", "peak_time_status",
            "settling_time_sec", "zero_crossing_count", "response_class",
        ]
        header = "| Field | " + " | ".join(f"Iter {i+1}" for i in range(len(iteration_summaries))) + " |"
        sep = "|---| " + " | ".join("---" for _ in iteration_summaries) + " |"
        lines.append(header)
        lines.append(sep)
        for field in key_fields:
            row = f"| {field} | "
            row += " | ".join(_fmt(s.get(field)) for s in iteration_summaries)
            row += " |"
            lines.append(row)
        lines.append("")

        # Aggregate
        lines.append("## Aggregate (mean ± std)\n")
        lines.append("| Field | Mean | Std |")
        lines.append("|---|---|---|")
        for field in AGGREGATE_FIELDS:
            stats = aggregate[field]
            if stats["mean"] is None:
                continue
            lines.append(f"| {field} | {_fmt(stats['mean'])} | {_fmt(stats['std'])} |")
        lines.append("")
        lines.append(f"- **response_classes**: {response_classes}")
        lines.append(f"- **rise_time_statuses**: {rise_statuses}")
        lines.append(f"- **peak_time_statuses**: {peak_statuses}")
        lines.append("")

    elif mode == "sine" and sine_summary:
        lines.append("## Sine Summary\n")
        for k, v in sine_summary.items():
            lines.append(f"- **{k}**: {_fmt(v)}")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Markdown report saved: {md_path}")
    return md_path


PHASE_COLORS = {"pre_hold": "#bdbdbd", "active": "#fee08b", "post_hold": "#d9ef8b"}
ITER_COLORS = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"]


def plot_step_response(rows, iteration_groups, iteration_summaries, timing_context,
                       output_dir, csv_stem):
    """Generate 4-panel step response figure with Chinese labels."""
    import os
    from matplotlib import font_manager as fm
    _cjk_font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ]
    for _path in _cjk_font_paths:
        if os.path.isfile(_path):
            fm.fontManager.addfont(_path)
            _prop = fm.FontProperties(fname=_path)
            plt.rcParams["font.sans-serif"] = [_prop.get_name()] + plt.rcParams.get("font.sans-serif", [])
            break
    plt.rcParams["axes.unicode_minus"] = False

    PHASE_LABELS = {"pre_hold": "预保持", "active": "激励", "post_hold": "后保持"}
    sorted_iters = sorted(iteration_groups.keys())
    fig, axes = plt.subplots(3, 1, figsize=(14, 13), sharex=False)
    fig.suptitle(f"阶跃响应分析: {csv_stem}", fontsize=14, fontweight="bold")

    # ── Panel 1: 位置跟踪 ──
    ax = axes[0]
    for idx, iteration in enumerate(sorted_iters):
        iter_rows = iteration_groups[iteration]
        color = ITER_COLORS[idx % len(ITER_COLORS)]
        phases = split_by_phase(iter_rows)

        for phase_name in ("pre_hold", "active", "post_hold"):
            phase_rows = phases.get(phase_name, [])
            if not phase_rows:
                continue
            t = [r["time_sec"] for r in phase_rows]
            target = [r["target_primary"] for r in phase_rows]
            actual = [r["actual_primary"] for r in phase_rows]
            if idx == 0:
                ax.fill_betweenx(
                    [min(target + actual) * 0.999, max(target + actual) * 1.001],
                    t[0], t[-1], alpha=0.08,
                    color=PHASE_COLORS.get(phase_name, "#eeeeee"),
                    label=PHASE_LABELS.get(phase_name) if phase_name == "active" else None,
                )
            ax.plot(t, target, color=color, ls="--", lw=0.8, alpha=0.6)
            ax.plot(t, actual, color=color, lw=1.2,
                    label=f"第{iteration}次" if phase_name == "pre_hold" else None)

    ax.set_ylabel("位置 (rad)")
    ax.set_title("位置跟踪: 目标(虚线) vs 实际(实线)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── Panel 2: 归一化阶跃响应 ──
    ax = axes[1]
    for idx, iteration in enumerate(sorted_iters):
        iter_rows = iteration_groups[iteration]
        summary = iteration_summaries[idx]
        phases = split_by_phase(iter_rows)
        active_rows = phases.get("active", [])
        if not active_rows:
            continue
        color = ITER_COLORS[idx % len(ITER_COLORS)]
        t0 = active_rows[0]["time_sec"]
        t = [r["time_sec"] - t0 for r in active_rows]
        pre_actual = summary["pre_actual"]
        step_size = abs(summary["command_step"])
        direction = 1.0 if summary["command_step"] >= 0 else -1.0
        norm_resp = [direction * (r["actual_primary"] - pre_actual) / step_size
                     if step_size > 1e-9 else 0.0 for r in active_rows]
        ax.plot(t, norm_resp, color=color, lw=1.2, label=f"第{iteration}次")

    ax.axhline(1.0, color="black", ls="--", lw=0.8, label="目标 (1.0)")
    ax.axhline(0.9, color="gray", ls=":", lw=0.6, alpha=0.6, label="90%")
    ax.axhline(0.1, color="gray", ls=":", lw=0.6, alpha=0.6, label="10%")
    if iteration_summaries and iteration_summaries[0].get("rise_time_sec") is not None:
        rt = iteration_summaries[0]["rise_time_sec"]
        ax.axvline(rt, color="#e41a1c", ls="-.", lw=0.8, alpha=0.7, label=f"上升时间 {rt*1000:.1f}ms")
    if iteration_summaries and iteration_summaries[0].get("settling_time_sec") is not None:
        st = iteration_summaries[0]["settling_time_sec"]
        ax.axvline(st, color="#377eb8", ls="-.", lw=0.8, alpha=0.7, label=f"稳定时间 {st*1000:.1f}ms")
    ax.set_xlabel("阶跃后时间 (s)")
    ax.set_ylabel("归一化响应")
    ax.set_title("归一化阶跃响应 (激励阶段)")
    ax.legend(loc="lower right", fontsize=7, ncol=2)
    ax.grid(True, alpha=0.3)

    # ── Panel 3: 跟踪误差 ──
    ax = axes[2]
    for idx, iteration in enumerate(sorted_iters):
        iter_rows = iteration_groups[iteration]
        phases = split_by_phase(iter_rows)
        active_rows = phases.get("active", [])
        if not active_rows:
            continue
        color = ITER_COLORS[idx % len(ITER_COLORS)]
        t0 = active_rows[0]["time_sec"]
        t = [r["time_sec"] - t0 for r in active_rows]
        error = [r["actual_primary"] - r["target_primary"] for r in active_rows]
        ax.plot(t, error, color=color, lw=1.0, label=f"第{iteration}次")

    step_size = abs(iteration_summaries[0]["command_step"]) if iteration_summaries else 0.015
    band = max(0.02 * step_size, 1e-6)
    ax.axhline(band, color="orange", ls=":", lw=0.8, alpha=0.7, label=f"±2% 稳态带 ({band:.6f})")
    ax.axhline(-band, color="orange", ls=":", lw=0.8, alpha=0.7)
    ax.axhline(0, color="black", ls="-", lw=0.5, alpha=0.5)
    ax.set_xlabel("阶跃后时间 (s)")
    ax.set_ylabel("误差 (rad)")
    ax.set_title("跟踪误差 (实际 − 目标)")
    ax.legend(loc="upper right", fontsize=7)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = output_dir / f"{csv_stem}_step_response.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Step response plot saved: {fig_path}")


def plot_sine_response(rows, sine_summary, output_dir, csv_stem):
    """Generate sine response figure."""
    phases = split_by_phase(rows)
    active_rows = phases.get("active", [])
    if not active_rows:
        return

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f"Sine Response Analysis: {csv_stem}", fontsize=14, fontweight="bold")

    t0 = active_rows[0]["time_sec"]
    t = [r["time_sec"] - t0 for r in active_rows]
    target = [r["target_primary"] for r in active_rows]
    actual = [r["actual_primary"] for r in active_rows]
    coupled = [r["actual_coupled"] for r in active_rows]

    ax = axes[0]
    ax.plot(t, target, color="gray", ls="--", lw=1.0, label="Target")
    ax.plot(t, actual, color="#e41a1c", lw=1.2, label="Actual primary")
    ax.plot(t, coupled, color="#377eb8", lw=0.8, alpha=0.7, label="Actual coupled")
    ax.set_ylabel("Position (rad)")
    ax.set_title(f"Sine Tracking (gain={sine_summary['gain']:.3f}, coupling={sine_summary['coupling_ratio']:.4f})")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    ax.plot(t, [r["actual_primary_vel"] for r in active_rows], color="#e41a1c", lw=1.0, label="Primary vel")
    ax.plot(t, [r["actual_coupled_vel"] for r in active_rows], color="#377eb8", lw=0.8, alpha=0.7, label="Coupled vel")
    ax.set_ylabel("Velocity (rad/s)")
    ax.set_title("Velocity")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    ax.plot(t, [r["actual_primary_effort"] for r in active_rows], color="#e41a1c", lw=1.0, label="Primary effort")
    ax.plot(t, [r["actual_coupled_effort"] for r in active_rows], color="#377eb8", lw=0.8, alpha=0.7, label="Coupled effort")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Effort (Nm)")
    ax.set_title("Effort")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = output_dir / f"{csv_stem}_sine_response.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Sine response plot saved: {fig_path}")


def main():
    parser = argparse.ArgumentParser(description="Analyze native_ros2_ankle_identifier CSV output.")
    parser.add_argument("csv_path", type=Path, help="Path to CSV file generated by native_ros2_ankle_identifier")
    parser.add_argument(
        "--deploy-info",
        type=Path,
        default=Path(".oma/deploy_info.json"),
        help="Path to deploy_info.json used to derive control_hz and cycle_time",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to save analysis results (JSON + Markdown). If not set, only prints to stdout.",
    )
    args = parser.parse_args()

    rows = load_rows(args.csv_path)
    if not rows:
        raise SystemExit("CSV has no data rows.")
    timing_context = load_timing_context(args.deploy_info)

    print_basic(rows)
    status, target_span, actual_span = detect_signal_path(rows)
    print_signal_path_result(status, target_span, actual_span)
    print_timing_context(timing_context)

    basic_info = {
        "samples": len(rows),
        "primary_joint": rows[0]["primary_joint"],
        "coupled_joint": rows[0]["coupled_joint"],
        "iterations": sorted({r["iteration"] for r in rows}),
        "phases": {phase: len(rlist) for phase, rlist in split_by_phase(rows).items()},
    }
    signal_path_info = {"status": status, "target_span": target_span, "actual_span": actual_span}

    mode = infer_mode(rows)
    iteration_summaries = None
    aggregate = None
    response_classes = None
    rise_statuses = None
    peak_statuses = None
    sine_summary = None

    if mode == "step":
        iteration_groups = group_by_iteration(rows)
        iteration_summaries = []
        for iteration in sorted(iteration_groups):
            summary = summarize_step(iteration_groups[iteration], timing_context)
            iteration_summaries.append(summary)
            print(f"Iteration {iteration}:")
            print_step_summary(summary)

        aggregate = summarize_numeric_dicts(iteration_summaries, AGGREGATE_FIELDS)
        response_classes = [summary["response_class"] for summary in iteration_summaries]
        rise_statuses = [summary["rise_time_status"] for summary in iteration_summaries]
        peak_statuses = [summary["peak_time_status"] for summary in iteration_summaries]

        print("Aggregate across iterations:")
        for field in AGGREGATE_FIELDS:
            stats = aggregate[field]
            if stats["mean"] is None:
                continue
            print(f"  {field}: {stats['mean']:.6f} ± {stats['std']:.6f}")
        print(f"  response_classes: {response_classes}")
        print(f"  rise_time_statuses: {rise_statuses}")
        print(f"  peak_time_statuses: {peak_statuses}")
    elif mode == "sine":
        sine_summary = summarize_sine(rows)
        print_sine_summary(sine_summary)
    else:
        print("Mode: unknown")

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        csv_name = args.csv_path.name
        csv_stem = args.csv_path.stem
        write_json_report(
            args.output_dir, csv_name, mode, basic_info, signal_path_info,
            timing_context, iteration_summaries, aggregate,
            response_classes, rise_statuses, peak_statuses, sine_summary,
        )
        write_markdown_report(
            args.output_dir, csv_name, mode, basic_info, signal_path_info,
            timing_context, iteration_summaries, aggregate,
            response_classes, rise_statuses, peak_statuses, sine_summary,
        )
        if mode == "step" and iteration_summaries:
            iteration_groups = group_by_iteration(rows)
            plot_step_response(rows, iteration_groups, iteration_summaries,
                               timing_context, args.output_dir, csv_stem)
        elif mode == "sine" and sine_summary:
            plot_sine_response(rows, sine_summary, args.output_dir, csv_stem)


if __name__ == "__main__":
    main()
