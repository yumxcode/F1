#!/usr/bin/env python3
"""Analyze t23 joint target tracking for high-speed walk instability.

The t23 log contains joint position, velocity, raw target, and LPF target
columns. For parallel ankle joints, the LPF column can represent a torque-side
signal, so this script uses raw target-vs-position tracking for all joints.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path


def finite_float(value: str) -> float | None:
    try:
        out = float(value)
    except ValueError:
        return None
    if not math.isfinite(out):
        return None
    return out


def rms(values: list[float]) -> float:
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else math.nan


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return ordered[idx]


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
        mx = statistics.fmean(xs)
        my = statistics.fmean(ys)
        vx = [x - mx for x in xs]
        vy = [y - my for y in ys]
        den = math.sqrt(sum(x * x for x in vx) * sum(y * y for y in vy))
        corr = sum(x * y for x, y in zip(vx, vy)) / den if den > 1e-12 else 0.0
        if corr > best_corr:
            best_corr = corr
            best_lag = lag
    return best_lag / sample_hz * 1000.0, best_corr


def analyze(csv_path: Path) -> tuple[dict[str, float], list[dict[str, float | str]]]:
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 3:
        raise ValueError(f"not enough rows in {csv_path}")

    timestamps = [int(row["timestamp_ns"]) for row in rows]
    dts = [(b - a) / 1e9 for a, b in zip(timestamps, timestamps[1:]) if b > a]
    sample_hz = 1.0 / statistics.fmean(dts)
    duration_s = (timestamps[-1] - timestamps[0]) / 1e9

    joints = [name[4:] for name in rows[0] if name.startswith("pos_")]
    details: list[dict[str, float | str]] = []
    for joint in joints:
        pos: list[float] = []
        target: list[float] = []
        vel_abs: list[float] = []
        for row in rows[2:]:
            p = finite_float(row.get(f"pos_{joint}", ""))
            t = finite_float(row.get(f"target_{joint}", ""))
            v = finite_float(row.get(f"vel_{joint}", ""))
            if p is None or t is None or v is None:
                continue
            pos.append(p)
            target.append(t)
            vel_abs.append(abs(v))
        errors = [t - p for t, p in zip(target, pos)]
        delay_ms, delay_corr = best_delay_ms(target, pos, sample_hz)
        target_range = max(target) - min(target)
        pos_range = max(pos) - min(pos)
        details.append(
            {
                "joint": joint,
                "rms_error_rad": rms(errors),
                "max_abs_error_rad": max(abs(v) for v in errors),
                "target_range_rad": target_range,
                "pos_range_rad": pos_range,
                "range_ratio_pos_over_target": pos_range / target_range if target_range > 1e-9 else math.nan,
                "vel_abs_p95_rad_s": percentile(vel_abs, 0.95),
                "best_delay_ms": delay_ms,
                "best_delay_corr": delay_corr,
            }
        )

    meta = {
        "rows": len(rows),
        "duration_s": duration_s,
        "sample_hz": sample_hz,
        "dt_min_s": min(dts),
        "dt_max_s": max(dts),
    }
    return meta, details


def write_outputs(meta: dict[str, float], details: list[dict[str, float | str]], out_dir: Path, source: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_out = out_dir / "t23_joint_tracking_summary.csv"
    md_out = out_dir / "t23_joint_tracking_summary.md"

    fields = list(details[0].keys()) if details else []
    with csv_out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(details)

    sorted_by_error = sorted(details, key=lambda item: float(item["rms_error_rad"]), reverse=True)
    lines = [
        "# t23 Joint Tracking Initial Screen",
        "",
        f"Source: `{source}`",
        f"Rows: {int(meta['rows'])}",
        f"Duration: {meta['duration_s']:.3f} s",
        f"Sample rate: {meta['sample_hz']:.3f} Hz",
        f"dt range: {meta['dt_min_s'] * 1000.0:.3f} .. {meta['dt_max_s'] * 1000.0:.3f} ms",
        "",
        "## Top Tracking Errors",
        "",
        "| Joint | RMS err rad | Max err rad | Target range | Pos range | Pos/target | Delay ms | Corr | Vel p95 rad/s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted_by_error:
        lines.append(
            "| {joint} | {rms_error_rad:.4f} | {max_abs_error_rad:.4f} | "
            "{target_range_rad:.4f} | {pos_range_rad:.4f} | "
            "{range_ratio_pos_over_target:.3f} | {best_delay_ms:.1f} | "
            "{best_delay_corr:.3f} | {vel_abs_p95_rad_s:.3f} |".format(**row)
        )

    lines += [
        "",
        "## Interpretation Boundary",
        "",
        "- This log can reveal execution-chain tracking stress at high speed.",
        "- It cannot by itself prove body instability because it lacks velocity command, IMU, odometry, contact, and fall-event annotations.",
        "- For parallel ankle joints, raw target tracking is used; LPF columns are not compared to position in this report.",
    ]
    md_out.write_text("\n".join(lines) + "\n")
    print(md_out)
    print(csv_out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    meta, details = analyze(args.csv)
    write_outputs(meta, details, args.out_dir, args.csv)


if __name__ == "__main__":
    main()
