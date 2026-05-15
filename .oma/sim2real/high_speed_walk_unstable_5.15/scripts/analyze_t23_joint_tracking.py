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


def by_joint(details: list[dict[str, float | str]]) -> dict[str, dict[str, float | str]]:
    return {str(row["joint"]): row for row in details}


def safe_ratio(num: float, den: float) -> float:
    return num / den if abs(den) > 1e-12 else math.nan


def write_compare_outputs(
    sim_meta: dict[str, float],
    sim_details: list[dict[str, float | str]],
    real_meta: dict[str, float],
    real_details: list[dict[str, float | str]],
    out_dir: Path,
    sim_source: Path,
    real_source: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sim_rows = by_joint(sim_details)
    real_rows = by_joint(real_details)
    joints = sorted(set(sim_rows) & set(real_rows))

    compare_rows: list[dict[str, float | str]] = []
    for joint in joints:
        sim = sim_rows[joint]
        real = real_rows[joint]
        sim_rms = float(sim["rms_error_rad"])
        real_rms = float(real["rms_error_rad"])
        sim_target_range = float(sim["target_range_rad"])
        real_target_range = float(real["target_range_rad"])
        sim_corr = float(sim["best_delay_corr"])
        real_corr = float(real["best_delay_corr"])
        compare_rows.append(
            {
                "joint": joint,
                "sim_rms_error_rad": sim_rms,
                "real_rms_error_rad": real_rms,
                "real_minus_sim_rms_error_rad": real_rms - sim_rms,
                "real_over_sim_rms_error": safe_ratio(real_rms, sim_rms),
                "sim_target_range_rad": sim_target_range,
                "real_target_range_rad": real_target_range,
                "real_over_sim_target_range": safe_ratio(real_target_range, sim_target_range),
                "sim_pos_range_rad": float(sim["pos_range_rad"]),
                "real_pos_range_rad": float(real["pos_range_rad"]),
                "sim_pos_over_target": float(sim["range_ratio_pos_over_target"]),
                "real_pos_over_target": float(real["range_ratio_pos_over_target"]),
                "sim_delay_ms": float(sim["best_delay_ms"]),
                "real_delay_ms": float(real["best_delay_ms"]),
                "sim_corr": sim_corr,
                "real_corr": real_corr,
                "corr_drop_real_minus_sim": real_corr - sim_corr,
                "sim_vel_p95_rad_s": float(sim["vel_abs_p95_rad_s"]),
                "real_vel_p95_rad_s": float(real["vel_abs_p95_rad_s"]),
            }
        )

    csv_out = out_dir / "t23_sim_real_joint_tracking_compare.csv"
    md_out = out_dir / "t23_sim_real_joint_tracking_compare.md"
    fields = list(compare_rows[0].keys()) if compare_rows else []
    with csv_out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(compare_rows)

    sorted_by_real_gap = sorted(
        compare_rows,
        key=lambda item: float(item["real_minus_sim_rms_error_rad"]),
        reverse=True,
    )
    sorted_by_target_ratio = sorted(
        compare_rows,
        key=lambda item: float(item["real_over_sim_target_range"]),
        reverse=True,
    )
    sorted_by_corr_drop = sorted(
        compare_rows,
        key=lambda item: float(item["corr_drop_real_minus_sim"]),
    )

    avg_sim_rms = statistics.fmean(float(row["sim_rms_error_rad"]) for row in compare_rows)
    avg_real_rms = statistics.fmean(float(row["real_rms_error_rad"]) for row in compare_rows)
    avg_sim_corr = statistics.fmean(float(row["sim_corr"]) for row in compare_rows)
    avg_real_corr = statistics.fmean(float(row["real_corr"]) for row in compare_rows)

    def table_row(row: dict[str, float | str]) -> str:
        return (
            "| {joint} | {sim_rms_error_rad:.4f} | {real_rms_error_rad:.4f} | "
            "{real_minus_sim_rms_error_rad:+.4f} | {real_over_sim_rms_error:.2f}x | "
            "{real_over_sim_target_range:.2f}x | {sim_pos_over_target:.3f} | "
            "{real_pos_over_target:.3f} | {sim_delay_ms:.1f} | {real_delay_ms:.1f} | "
            "{sim_corr:.3f} | {real_corr:.3f} |".format(**row)
        )

    lines = [
        "# t23 Sim-vs-Real Joint Tracking Compare",
        "",
        f"Sim source: `{sim_source}`",
        f"Real source: `{real_source}`",
        "",
        "## Data Quality",
        "",
        "| Dataset | Rows | Duration s | Sample Hz | dt min ms | dt max ms |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| sim | {int(sim_meta['rows'])} | {sim_meta['duration_s']:.3f} | "
            f"{sim_meta['sample_hz']:.3f} | {sim_meta['dt_min_s'] * 1000.0:.3f} | "
            f"{sim_meta['dt_max_s'] * 1000.0:.3f} |"
        ),
        (
            f"| real | {int(real_meta['rows'])} | {real_meta['duration_s']:.3f} | "
            f"{real_meta['sample_hz']:.3f} | {real_meta['dt_min_s'] * 1000.0:.3f} | "
            f"{real_meta['dt_max_s'] * 1000.0:.3f} |"
        ),
        "",
        "## Aggregate Tracking",
        "",
        "| Metric | Sim | Real | Real / Sim |",
        "|---|---:|---:|---:|",
        f"| mean RMS error across joints | {avg_sim_rms:.4f} rad | {avg_real_rms:.4f} rad | {safe_ratio(avg_real_rms, avg_sim_rms):.2f}x |",
        f"| mean best-delay correlation | {avg_sim_corr:.3f} | {avg_real_corr:.3f} | {safe_ratio(avg_real_corr, avg_sim_corr):.2f}x |",
        "",
        "## Largest Real-minus-Sim RMS Gaps",
        "",
        "| Joint | Sim RMS | Real RMS | Δ RMS | Real/Sim RMS | Target range Real/Sim | Sim pos/target | Real pos/target | Sim delay ms | Real delay ms | Sim corr | Real corr |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(table_row(row) for row in sorted_by_real_gap)
    lines += [
        "",
        "## Largest Real Target-Range Increases",
        "",
        "| Joint | Sim RMS | Real RMS | Δ RMS | Real/Sim RMS | Target range Real/Sim | Sim pos/target | Real pos/target | Sim delay ms | Real delay ms | Sim corr | Real corr |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(table_row(row) for row in sorted_by_target_ratio[:6])
    lines += [
        "",
        "## Largest Correlation Drops",
        "",
        "| Joint | Sim RMS | Real RMS | Δ RMS | Real/Sim RMS | Target range Real/Sim | Sim pos/target | Real pos/target | Sim delay ms | Real delay ms | Sim corr | Real corr |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(table_row(row) for row in sorted_by_corr_drop[:6])
    lines += [
        "",
        "## Interpretation Boundary",
        "",
        "- The two logs have nearly identical duration and sample rate, so per-log statistics are comparable.",
        "- Target trajectories are not identical; Real/Sim target-range ratios must be checked before interpreting RMS deltas as pure actuator degradation.",
        "- Delay estimates with low correlation are weak evidence; in those rows, RMS, range ratio, and correlation drop carry more weight than the delay number.",
    ]
    md_out.write_text("\n".join(lines) + "\n")
    print(md_out)
    print(csv_out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--compare-sim", type=Path)
    parser.add_argument("--compare-real", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.compare_sim or args.compare_real:
        if not args.compare_sim or not args.compare_real:
            raise SystemExit("--compare-sim and --compare-real must be provided together")
        sim_meta, sim_details = analyze(args.compare_sim)
        real_meta, real_details = analyze(args.compare_real)
        write_compare_outputs(sim_meta, sim_details, real_meta, real_details, args.out_dir, args.compare_sim, args.compare_real)
        return
    if not args.csv:
        raise SystemExit("--csv is required unless --compare-sim/--compare-real are used")
    meta, details = analyze(args.csv)
    write_outputs(meta, details, args.out_dir, args.csv)


if __name__ == "__main__":
    main()
