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
    coupled_motion = mean([r["actual_coupled"] for r in active_rows]) - mean(
        [r["actual_coupled"] for r in pre_rows]
    )

    peak_active = max([r["actual_primary"] for r in active_rows], default=active_actual)
    peak_overshoot = peak_active - active_target if command_step >= 0 else active_target - min(
        [r["actual_primary"] for r in active_rows], default=active_actual
    )

    steady_error = post_actual - post_target

    return {
        "pre_target": pre_target,
        "active_target": active_target,
        "post_target": post_target,
        "pre_actual": pre_actual,
        "active_actual": active_actual,
        "post_actual": post_actual,
        "command_step": command_step,
        "actual_step": actual_step,
        "coupled_motion": coupled_motion,
        "peak_overshoot": peak_overshoot,
        "steady_error": steady_error,
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
    print(f"  coupled_motion: {summary['coupled_motion']:.6f}")
    print(f"  peak_overshoot: {summary['peak_overshoot']:.6f}")
    print(f"  steady_error: {summary['steady_error']:.6f}")
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
        print_step_summary(summarize_step(rows))
    elif mode == "sine":
        print_sine_summary(summarize_sine(rows))
    else:
        print("Mode: unknown")


if __name__ == "__main__":
    main()
