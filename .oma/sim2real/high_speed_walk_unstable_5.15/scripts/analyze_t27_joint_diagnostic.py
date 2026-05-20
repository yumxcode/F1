#!/usr/bin/env python3
"""Analyze t27 full diagnostic logs for high-speed walk instability."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path


JOINTS = [
    "left_hip_pitch_joint",
    "left_hip_roll_joint",
    "left_hip_yaw_joint",
    "left_knee_pitch_joint",
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
    "right_hip_pitch_joint",
    "right_hip_roll_joint",
    "right_hip_yaw_joint",
    "right_knee_pitch_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
]

JOINT_LIMITS = {
    "left_hip_pitch_joint": (-1.0, 2.0),
    "left_hip_roll_joint": (-1.5, 0.2),
    "left_hip_yaw_joint": (-1.5, 1.5),
    "left_knee_pitch_joint": (0.0, 2.0),
    "left_ankle_pitch_joint": (-0.41, 0.35),
    "left_ankle_roll_joint": (-0.64, 0.64),
    "right_hip_pitch_joint": (-2.0, 1.0),
    "right_hip_roll_joint": (-0.2, 1.5),
    "right_hip_yaw_joint": (-1.5, 1.5),
    "right_knee_pitch_joint": (0.0, 2.0),
    "right_ankle_pitch_joint": (-0.41, 0.35),
    "right_ankle_roll_joint": (-0.64, 0.64),
}


def finite_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except ValueError:
        return None
    if not math.isfinite(out):
        return None
    return out


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else math.nan


def std(values: list[float]) -> float:
    return statistics.pstdev(values) if values else math.nan


def rms(values: list[float]) -> float:
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else math.nan


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return ordered[idx]


def corr(xs: list[float], ys: list[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return math.nan
    x = xs[:n]
    y = ys[:n]
    mx = mean(x)
    my = mean(y)
    vx = [v - mx for v in x]
    vy = [v - my for v in y]
    den = math.sqrt(sum(v * v for v in vx) * sum(v * v for v in vy))
    return sum(a * b for a, b in zip(vx, vy)) / den if den > 1e-12 else math.nan


def best_delay_ms(target: list[float], position: list[float], sample_hz: float, max_lag_samples: int = 25) -> tuple[float, float]:
    """Return positive delay when position lags target."""
    best_lag = 0
    best_corr = -2.0
    n = min(len(target), len(position))
    for lag in range(-max_lag_samples, max_lag_samples + 1):
        xs: list[float] = []
        ys: list[float] = []
        for i in range(n):
            j = i + lag
            if 0 <= j < n:
                xs.append(target[i])
                ys.append(position[j])
        if len(xs) < 10:
            continue
        c = corr(xs, ys)
        if not math.isnan(c) and c > best_corr:
            best_corr = c
            best_lag = lag
    return best_lag / sample_hz * 1000.0, best_corr


def transitions(values: list[int]) -> int:
    return sum(1 for a, b in zip(values, values[1:]) if a != b)


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 3:
        raise ValueError(f"not enough rows in {csv_path}")
    return rows


def scalar_series(rows: list[dict[str, str]], key: str) -> list[float]:
    out: list[float] = []
    for row in rows:
        value = finite_float(row.get(key))
        if value is not None:
            out.append(value)
    return out


def analyze(csv_path: Path) -> tuple[dict[str, float], list[dict[str, float | str]], list[dict[str, float | str]]]:
    rows = load_rows(csv_path)
    timestamps = [int(row["timestamp_ns"]) for row in rows]
    dts = [(b - a) / 1e9 for a, b in zip(timestamps, timestamps[1:]) if b > a]
    sample_hz = 1.0 / mean(dts)
    duration_s = (timestamps[-1] - timestamps[0]) / 1e9

    cmd_x = scalar_series(rows, "cmd_linear_x")
    cmd_y = scalar_series(rows, "cmd_linear_y")
    cmd_yaw = scalar_series(rows, "cmd_angular_z")
    left_contact = [int(finite_float(row.get("left_contact")) or 0) for row in rows]
    right_contact = [int(finite_float(row.get("right_contact")) or 0) for row in rows]

    meta = {
        "rows": float(len(rows)),
        "duration_s": duration_s,
        "sample_hz": sample_hz,
        "dt_min_ms": min(dts) * 1000.0,
        "dt_max_ms": max(dts) * 1000.0,
        "cmd_linear_x_mean": mean(cmd_x),
        "cmd_linear_x_max": max(cmd_x) if cmd_x else math.nan,
        "cmd_linear_y_abs_max": max(abs(v) for v in cmd_y) if cmd_y else math.nan,
        "cmd_angular_z_abs_max": max(abs(v) for v in cmd_yaw) if cmd_yaw else math.nan,
        "left_contact_fraction": mean([float(v) for v in left_contact]),
        "right_contact_fraction": mean([float(v) for v in right_contact]),
        "left_contact_transitions": float(transitions(left_contact)),
        "right_contact_transitions": float(transitions(right_contact)),
    }
    for key in ["base_euler_x", "base_euler_y", "base_euler_z", "base_ang_vel_x", "base_ang_vel_y", "base_ang_vel_z"]:
        values = scalar_series(rows, key)
        meta[f"{key}_mean"] = mean(values)
        meta[f"{key}_std"] = std(values)
        meta[f"{key}_range"] = (max(values) - min(values)) if values else math.nan
        meta[f"{key}_abs_p95"] = percentile([abs(v) for v in values], 0.95)
        meta[f"{key}_abs_max"] = max(abs(v) for v in values) if values else math.nan

    joint_rows: list[dict[str, float | str]] = []
    for joint in JOINTS:
        pos = scalar_series(rows, f"pos_{joint}")
        vel = scalar_series(rows, f"vel_{joint}")
        effort = scalar_series(rows, f"effort_{joint}")
        raw = scalar_series(rows, f"pos_des_raw_{joint}")
        lpf = scalar_series(rows, f"pos_des_lpf_{joint}")
        tau_raw = scalar_series(rows, f"tau_des_raw_{joint}")
        tau_lpf = scalar_series(rows, f"tau_des_lpf_{joint}")
        is_parallel_values = scalar_series(rows, f"is_parallel_{joint}")
        is_parallel = int(round(mean(is_parallel_values))) if is_parallel_values else 0
        target = raw if is_parallel else lpf
        target_name = "pos_des_raw" if is_parallel else "pos_des_lpf"
        n = min(len(target), len(pos))
        target = target[:n]
        pos = pos[:n]
        errors = [t - p for t, p in zip(target, pos)]
        delay_ms, best_corr = best_delay_ms(target, pos, sample_hz)
        lower, upper = JOINT_LIMITS[joint]
        near_eps = 1e-3
        raw_n = raw[:n]
        target_range = max(target) - min(target) if target else math.nan
        pos_range = max(pos) - min(pos) if pos else math.nan
        joint_rows.append(
            {
                "joint": joint,
                "is_parallel": float(is_parallel),
                "target_used": target_name,
                "rms_error_rad": rms(errors),
                "error_mean_rad": mean(errors),
                "error_std_rad": std(errors),
                "max_abs_error_rad": max(abs(v) for v in errors) if errors else math.nan,
                "target_mean_rad": mean(target),
                "target_std_rad": std(target),
                "target_range_rad": target_range,
                "pos_mean_rad": mean(pos),
                "pos_std_rad": std(pos),
                "pos_range_rad": pos_range,
                "pos_over_target_range": pos_range / target_range if target_range and target_range > 1e-9 else math.nan,
                "zero_lag_corr": corr(target, pos),
                "best_delay_ms": delay_ms,
                "best_delay_corr": best_corr,
                "vel_abs_p95_rad_s": percentile([abs(v) for v in vel], 0.95),
                "effort_abs_p95": percentile([abs(v) for v in effort], 0.95),
                "pos_des_raw_lower_hit_frac": mean([1.0 if v <= lower + near_eps else 0.0 for v in raw_n]),
                "pos_des_raw_upper_hit_frac": mean([1.0 if v >= upper - near_eps else 0.0 for v in raw_n]),
                "tau_des_lpf_abs_p95": percentile([abs(v) for v in tau_lpf], 0.95),
                "tau_des_lpf_abs_max": max([abs(v) for v in tau_lpf], default=math.nan),
                "tau_effort_corr": corr(tau_lpf, effort) if tau_lpf and effort else math.nan,
                "tau_raw_abs_p95": percentile([abs(v) for v in tau_raw], 0.95),
            }
        )

    focus_rows = [row for row in joint_rows if str(row["joint"]) in {
        "left_hip_roll_joint",
        "right_hip_roll_joint",
        "left_ankle_pitch_joint",
        "left_ankle_roll_joint",
        "right_ankle_pitch_joint",
        "right_ankle_roll_joint",
    }]
    return meta, joint_rows, focus_rows


def write_outputs(meta: dict[str, float], joint_rows: list[dict[str, float | str]], focus_rows: list[dict[str, float | str]], out_dir: Path, source: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_out = out_dir / "t27_joint_diagnostic_summary.csv"
    md_out = out_dir / "t27_joint_diagnostic_summary.md"
    with csv_out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(joint_rows[0].keys()))
        writer.writeheader()
        writer.writerows(joint_rows)

    top_error = sorted(joint_rows, key=lambda row: float(row["rms_error_rad"]), reverse=True)
    top_bad_corr = sorted(joint_rows, key=lambda row: float(row["best_delay_corr"]))

    def joint_line(row: dict[str, float | str]) -> str:
        return (
            "| {joint} | {target_used} | {rms_error_rad:.4f} | {error_mean_rad:+.4f} | "
            "{error_std_rad:.4f} | {target_range_rad:.4f} | {pos_range_rad:.4f} | "
            "{pos_over_target_range:.3f} | {best_delay_ms:.1f} | {best_delay_corr:.3f} | "
            "{pos_des_raw_lower_hit_frac:.1%} | {pos_des_raw_upper_hit_frac:.1%} | "
            "{effort_abs_p95:.3f} | {tau_des_lpf_abs_p95:.3f} |".format(**row)
        )

    lines = [
        "# t27 Joint Diagnostic Summary",
        "",
        f"Source: `{source}`",
        f"Rows: {int(meta['rows'])}",
        f"Duration: {meta['duration_s']:.3f} s",
        f"Sample rate: {meta['sample_hz']:.3f} Hz",
        f"dt range: {meta['dt_min_ms']:.3f} .. {meta['dt_max_ms']:.3f} ms",
        "",
        "## Command / Contact / Base Motion",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| cmd_linear_x mean / max | {meta['cmd_linear_x_mean']:.3f} / {meta['cmd_linear_x_max']:.3f} |",
        f"| cmd_linear_y abs max | {meta['cmd_linear_y_abs_max']:.3f} |",
        f"| cmd_angular_z abs max | {meta['cmd_angular_z_abs_max']:.3f} |",
        f"| left_contact fraction / transitions | {meta['left_contact_fraction']:.3f} / {int(meta['left_contact_transitions'])} |",
        f"| right_contact fraction / transitions | {meta['right_contact_fraction']:.3f} / {int(meta['right_contact_transitions'])} |",
        f"| base roll x std / abs p95 / max | {meta['base_euler_x_std']:.4f} / {meta['base_euler_x_abs_p95']:.4f} / {meta['base_euler_x_abs_max']:.4f} |",
        f"| base pitch y std / abs p95 / max | {meta['base_euler_y_std']:.4f} / {meta['base_euler_y_abs_p95']:.4f} / {meta['base_euler_y_abs_max']:.4f} |",
        f"| base yaw z range | {meta['base_euler_z_range']:.4f} |",
        f"| gyro x/y/z abs p95 | {meta['base_ang_vel_x_abs_p95']:.4f} / {meta['base_ang_vel_y_abs_p95']:.4f} / {meta['base_ang_vel_z_abs_p95']:.4f} |",
        "",
        "## Top Tracking Errors",
        "",
        "| Joint | Target used | RMS | Err mean | Err std | Target range | Pos range | Pos/target | Delay ms | Corr | Lower hit | Upper hit | Effort p95 | Tau cmd p95 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(joint_line(row) for row in top_error)
    lines += [
        "",
        "## Focus: Roll And Ankle Channels",
        "",
        "| Joint | Target used | RMS | Err mean | Err std | Target range | Pos range | Pos/target | Delay ms | Corr | Lower hit | Upper hit | Effort p95 | Tau cmd p95 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(joint_line(row) for row in focus_rows)
    lines += [
        "",
        "## Lowest Correlations",
        "",
        "| Joint | Target used | RMS | Err mean | Err std | Target range | Pos range | Pos/target | Delay ms | Corr | Lower hit | Upper hit | Effort p95 | Tau cmd p95 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(joint_line(row) for row in top_bad_corr[:6])
    lines += [
        "",
        "## Interpretation Boundary",
        "",
        "- Serial joints are evaluated against `pos_des_lpf`, the position command actually sent by the controller.",
        "- Parallel ankle joints are evaluated against `pos_des_raw` as a virtual position target; their actual command path is `tau_des_lpf`.",
        "- Contact fields are controller-detected contact flags; they are useful for phase segmentation but are not force-plate ground truth.",
    ]
    md_out.write_text("\n".join(lines) + "\n")
    print(md_out)
    print(csv_out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    meta, joint_rows, focus_rows = analyze(args.csv)
    write_outputs(meta, joint_rows, focus_rows, args.out_dir, args.csv)


if __name__ == "__main__":
    main()
