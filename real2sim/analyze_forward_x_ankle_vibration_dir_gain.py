#!/usr/bin/env python3
"""Analyze ankle vibration frequency and windowed direction/gain metrics."""

from __future__ import annotations

import csv
import html
import math
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TABLE_DIR = ROOT / "real2sim" / "table" / "forward_x_failure_first6"
PLOT_DIR = TABLE_DIR / "plots"
WINDOW_DETAIL_CSV = TABLE_DIR / "forward_x_failure_first6_joint_change_frequency_detail.csv"

VIBRATION_DETAIL_CSV = TABLE_DIR / "forward_x_failure_first6_ankle_vibration_frequency_detail.csv"
VIBRATION_SUMMARY_CSV = TABLE_DIR / "forward_x_failure_first6_ankle_vibration_frequency_summary.csv"
DIR_GAIN_SUMMARY_CSV = TABLE_DIR / "forward_x_failure_first6_ankle_window_dir_gain_summary.csv"

VIBRATION_SVG = PLOT_DIR / "forward_x_failure_first6_ankle_vibration_frequency.svg"
DIR_GAIN_SVG = PLOT_DIR / "forward_x_failure_first6_ankle_window_dir_gain.svg"

REAL_CASES = [
    ("real", "25/0.4 all_ankles", "kp25_kd0.4", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100024.csv"),
    ("real", "30/0.4 all_ankles", "kp30_kd0.4", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100314.csv"),
    ("real", "35/0.5 all_ankles", "kp35_kd0.5", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100705.csv"),
    ("real", "40/0.8 all_ankles", "kp40_kd0.8", "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv"),
]

SIM_CASES = [
    ("sim", "2504", "kp25_kd0.4", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133905_2504.csv"),
    ("sim", "3505", "kp35_kd0.5", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133024_3505.csv"),
    ("sim", "4005", "kp40_kd0.5", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134153_4005.csv"),
    ("sim", "5008", "kp50_kd0.8", "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134417_5008.csv"),
]

JOINTS = ("ankle_pitch", "ankle_roll")
SIDES = ("left", "right")
DATASETS = ("real", "sim")
WINDOWS = ("swing", "touchdown")
VIBRATION_BAND_HZ = (5.0, 30.0)
WELCH_SEGMENT_SEC = 2.0
WELCH_OVERLAP = 0.5
MAX_ALIGNMENT_LAG_SEC = 0.30
MIN_ALIGNMENT_CORR = 0.20
RESIDUAL_TARGET_POWER_RATIO_THRESHOLD = 3.0
MIN_LAG_SAMPLE_POINTS = 16
DIFF_EPS_RAD = 5e-4
MIN_GAIN_TARGET_AMP_RAD = 0.01


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_float(value: str | None) -> float:
    if value is None or value == "":
        return math.nan
    return float(value)


def mean(values: list[float]) -> float:
    valid = [value for value in values if not math.isnan(value)]
    return sum(valid) / len(valid) if valid else math.nan


def stdev(values: list[float]) -> float:
    valid = [value for value in values if not math.isnan(value)]
    if len(valid) < 2:
        return 0.0 if valid else math.nan
    return statistics.pstdev(valid)


def median(values: list[float]) -> float:
    valid = [value for value in values if not math.isnan(value)]
    return statistics.median(valid) if valid else math.nan


def fmt(value: float, digits: int = 2) -> str:
    if value is None or math.isnan(value):
        return ""
    return f"{value:.{digits}f}"


def load_log(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    rows = read_csv(path)
    times: list[float] = []
    series: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        t = int(row["timestamp_ns"]) / 1e9
        times.append(t)
        for side in SIDES:
            for joint in JOINTS:
                joint_key = f"pos_{side}_{joint}_joint"
                target_key = f"pos_des_raw_{side}_{joint}_joint"
                series[joint_key].append(parse_float(row[joint_key]))
                series[target_key].append(parse_float(row[target_key]))
    return times, series


def finite_pairs(left: list[float], right: list[float]) -> tuple[list[float], list[float]]:
    out_left: list[float] = []
    out_right: list[float] = []
    for left_value, right_value in zip(left, right):
        if math.isnan(left_value) or math.isnan(right_value):
            continue
        out_left.append(left_value)
        out_right.append(right_value)
    return out_left, out_right


def first_differences(values: list[float]) -> list[float]:
    return [curr - prev for prev, curr in zip(values[:-1], values[1:])]


def zscore(values: list[float]) -> list[float]:
    if not values:
        return []
    mu = sum(values) / len(values)
    var = sum((value - mu) ** 2 for value in values) / len(values)
    std = math.sqrt(var)
    if std <= 1e-12:
        return [0.0] * len(values)
    return [(value - mu) / std for value in values]


def pearson_corr(left: list[float], right: list[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        return math.nan
    n = min(len(left), len(right))
    left = left[:n]
    right = right[:n]
    ml = sum(left) / n
    mr = sum(right) / n
    num = sum((lv - ml) * (rv - mr) for lv, rv in zip(left, right))
    den_l = sum((lv - ml) ** 2 for lv in left)
    den_r = sum((rv - mr) ** 2 for rv in right)
    den = math.sqrt(den_l * den_r)
    return num / den if den > 1e-12 else 0.0


def best_lag_samples(target: list[float], joint: list[float], max_lag_samples: int) -> tuple[int, float]:
    """Return lag where joint[k + lag] best matches target[k]."""
    x = zscore(first_differences(target))
    y = zscore(first_differences(joint))
    n = min(len(x), len(y))
    if n < MIN_LAG_SAMPLE_POINTS:
        return 0, math.nan
    x = x[:n]
    y = y[:n]
    best_lag = 0
    best_corr = -1.0
    for lag in range(0, min(max_lag_samples + 1, n)):
        if lag == 0:
            corr = pearson_corr(x, y)
        else:
            corr = pearson_corr(x[:-lag], y[lag:])
        if math.isnan(corr):
            continue
        if corr > best_corr:
            best_corr = corr
            best_lag = lag
    return best_lag, best_corr


def delay_aligned_residual(
    target: list[float],
    joint: list[float],
    sample_rate_hz: float,
) -> tuple[list[float], list[float], int, float, bool]:
    max_lag_samples = max(1, int(round(MAX_ALIGNMENT_LAG_SEC * sample_rate_hz)))
    lag_samples, corr = best_lag_samples(target, joint, max_lag_samples)
    apply_alignment = (
        not math.isnan(corr)
        and corr >= MIN_ALIGNMENT_CORR
        and lag_samples > 0
        and lag_samples < min(len(target), len(joint))
    )
    if apply_alignment:
        n = min(len(target), len(joint) - lag_samples)
        residual = [
            joint[idx + lag_samples] - target[idx]
            for idx in range(n)
        ]
        aligned_target = target[:n]
    else:
        lag_samples = 0
        residual = [joint_pos - target_pos for joint_pos, target_pos in zip(joint, target)]
        aligned_target = target[: len(residual)]
    return residual, aligned_target, lag_samples, corr, apply_alignment


def hann(n: int) -> list[float]:
    if n <= 1:
        return [1.0] * n
    return [0.5 - 0.5 * math.cos(2.0 * math.pi * idx / (n - 1)) for idx in range(n)]


def dft_power(segment: list[float], sample_rate_hz: float, band_hz: tuple[float, float]) -> tuple[list[float], list[float]]:
    n = len(segment)
    if n < 8:
        return [], []
    mu = sum(segment) / n
    window = hann(n)
    x = [(value - mu) * window[idx] for idx, value in enumerate(segment)]
    lo, hi = band_hz
    freqs: list[float] = []
    powers: list[float] = []
    for k in range(1, n // 2 + 1):
        freq = k * sample_rate_hz / n
        if freq < lo or freq > hi:
            continue
        real = 0.0
        imag = 0.0
        for idx, value in enumerate(x):
            angle = -2.0 * math.pi * k * idx / n
            real += value * math.cos(angle)
            imag += value * math.sin(angle)
        freqs.append(freq)
        powers.append(real * real + imag * imag)
    return freqs, powers


def parabolic_peak(freqs: list[float], powers: list[float], idx: int) -> tuple[float, float]:
    if idx <= 0 or idx >= len(powers) - 1:
        return freqs[idx], powers[idx]
    y0 = math.log(max(powers[idx - 1], 1e-300))
    y1 = math.log(max(powers[idx], 1e-300))
    y2 = math.log(max(powers[idx + 1], 1e-300))
    denom = y0 - 2.0 * y1 + y2
    if abs(denom) < 1e-12:
        return freqs[idx], powers[idx]
    offset = 0.5 * (y0 - y2) / denom
    offset = max(-1.0, min(1.0, offset))
    df = freqs[1] - freqs[0] if len(freqs) > 1 else 0.0
    peak_freq = freqs[idx] + offset * df
    peak_log_power = y1 - 0.25 * (y0 - y2) * offset
    return peak_freq, math.exp(peak_log_power)


def welch_peak_frequency(
    signal: list[float],
    sample_rate_hz: float,
    band_hz: tuple[float, float] = VIBRATION_BAND_HZ,
) -> dict[str, float]:
    freqs, powers, segment_count = welch_spectrum(signal, sample_rate_hz, band_hz)
    if segment_count == 0:
        return {"peak_hz": math.nan, "peak_power": math.nan, "band_power": math.nan, "segment_count": 0}
    best_idx = max(range(len(powers)), key=lambda idx: powers[idx])
    peak_hz, peak_power = parabolic_peak(freqs, powers, best_idx)
    return {
        "peak_hz": peak_hz,
        "peak_power": peak_power,
        "band_power": sum(powers),
        "segment_count": segment_count,
    }


def welch_spectrum(
    signal: list[float],
    sample_rate_hz: float,
    band_hz: tuple[float, float] = VIBRATION_BAND_HZ,
) -> tuple[list[float], list[float], int]:
    n = len(signal)
    if n < 16:
        return [], [], 0
    seg_n = min(n, max(32, int(round(WELCH_SEGMENT_SEC * sample_rate_hz))))
    step = max(1, int(round(seg_n * (1.0 - WELCH_OVERLAP))))
    psd_sum: list[float] = []
    freqs: list[float] = []
    segment_count = 0
    for start in range(0, n - seg_n + 1, step):
        segment = signal[start : start + seg_n]
        local_freqs, local_powers = dft_power(segment, sample_rate_hz, band_hz)
        if not local_freqs:
            continue
        if not freqs:
            freqs = local_freqs
            psd_sum = [0.0] * len(local_powers)
        if len(local_powers) != len(psd_sum):
            continue
        for idx, power in enumerate(local_powers):
            psd_sum[idx] += power
        segment_count += 1
    if segment_count == 0:
        return [], [], 0
    powers = [power / segment_count for power in psd_sum]
    return freqs, powers, segment_count


def nearest_power(freqs: list[float], powers: list[float], freq_hz: float) -> float:
    if not freqs or not powers or math.isnan(freq_hz):
        return math.nan
    idx = min(range(len(freqs)), key=lambda item: abs(freqs[item] - freq_hz))
    return powers[idx]


def direction_change_rate_hz(values: list[float], duration_sec: float) -> float:
    if len(values) < 3 or duration_sec <= 0:
        return math.nan
    signs: list[int] = []
    for prev, curr in zip(values[:-1], values[1:]):
        diff = curr - prev
        if abs(diff) <= DIFF_EPS_RAD:
            continue
        signs.append(1 if diff > 0.0 else -1)
    if len(signs) < 2:
        return 0.0
    flips = sum(1 for left, right in zip(signs[:-1], signs[1:]) if left != right)
    return flips / duration_sec


def build_vibration_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    detail_rows: list[dict[str, object]] = []
    for dataset, case_label, kp_case, rel_path in REAL_CASES + SIM_CASES:
        times, series = load_log(ROOT / rel_path)
        duration_sec = times[-1] - times[0]
        sample_rate_hz = (len(times) - 1) / duration_sec
        for side in SIDES:
            for joint in JOINTS:
                joint_key = f"pos_{side}_{joint}_joint"
                target_key = f"pos_des_raw_{side}_{joint}_joint"
                joint_values, target_values = finite_pairs(series[joint_key], series[target_key])
                residual, aligned_target, lag_samples, lag_corr, alignment_applied = delay_aligned_residual(
                    target_values, joint_values, sample_rate_hz
                )
                peak = welch_peak_frequency(residual, sample_rate_hz)
                target_peak = welch_peak_frequency(aligned_target, sample_rate_hz)
                target_freqs, target_powers, _ = welch_spectrum(aligned_target, sample_rate_hz)
                target_power_at_residual_peak = nearest_power(
                    target_freqs, target_powers, peak["peak_hz"]
                )
                if target_power_at_residual_peak > 1e-300:
                    residual_target_power_ratio = peak["peak_power"] / target_power_at_residual_peak
                    residual_target_power_ratio_db = 10.0 * math.log10(residual_target_power_ratio)
                else:
                    residual_target_power_ratio = math.inf
                    residual_target_power_ratio_db = math.inf
                closed_loop_dominant = (
                    not math.isnan(residual_target_power_ratio)
                    and residual_target_power_ratio >= RESIDUAL_TARGET_POWER_RATIO_THRESHOLD
                )
                detail_rows.append(
                    {
                        "dataset": dataset,
                        "case_label": case_label,
                        "kp_case": kp_case,
                        "diag_csv": Path(rel_path).name,
                        "side": side,
                        "joint": joint,
                        "signal": "delay_aligned_joint_pos_minus_pos_des_raw",
                        "band_low_hz": VIBRATION_BAND_HZ[0],
                        "band_high_hz": VIBRATION_BAND_HZ[1],
                        "sample_count": len(residual),
                        "duration_sec": duration_sec,
                        "sample_rate_hz": sample_rate_hz,
                        "alignment_lag_samples": lag_samples,
                        "alignment_lag_ms": lag_samples / sample_rate_hz * 1000.0,
                        "alignment_corr": lag_corr,
                        "alignment_applied": alignment_applied,
                        "welch_segment_sec": WELCH_SEGMENT_SEC,
                        "welch_segment_count": peak["segment_count"],
                        "vibration_peak_hz": peak["peak_hz"],
                        "vibration_peak_power": peak["peak_power"],
                        "vibration_band_power": peak["band_power"],
                        "target_peak_hz": target_peak["peak_hz"],
                        "target_peak_power": target_peak["peak_power"],
                        "target_band_power": target_peak["band_power"],
                        "target_power_at_vibration_peak": target_power_at_residual_peak,
                        "residual_target_power_ratio": residual_target_power_ratio,
                        "residual_target_power_ratio_db": residual_target_power_ratio_db,
                        "closed_loop_dominant": closed_loop_dominant,
                    }
                )

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in detail_rows:
        grouped[(str(row["dataset"]), str(row["joint"]))].append(row)

    summary_rows: list[dict[str, object]] = []
    for (dataset, joint), items in sorted(grouped.items()):
        peaks = [float(item["vibration_peak_hz"]) for item in items]
        powers = [float(item["vibration_band_power"]) for item in items]
        lags = [float(item["alignment_lag_ms"]) for item in items]
        corrs = [float(item["alignment_corr"]) for item in items]
        ratios = [float(item["residual_target_power_ratio"]) for item in items]
        ratio_dbs = [float(item["residual_target_power_ratio_db"]) for item in items]
        applied_count = sum(1 for item in items if item["alignment_applied"])
        closed_loop_count = sum(1 for item in items if item["closed_loop_dominant"])
        summary_rows.append(
            {
                "dataset": dataset,
                "joint": joint,
                "curve_count": len(items),
                "mean_vibration_peak_hz": mean(peaks),
                "median_vibration_peak_hz": median(peaks),
                "std_vibration_peak_hz": stdev(peaks),
                "mean_alignment_lag_ms": mean(lags),
                "median_alignment_lag_ms": median(lags),
                "mean_alignment_corr": mean(corrs),
                "alignment_applied_count": applied_count,
                "mean_residual_target_power_ratio": mean(ratios),
                "median_residual_target_power_ratio": median(ratios),
                "mean_residual_target_power_ratio_db": mean(ratio_dbs),
                "closed_loop_dominant_count": closed_loop_count,
                "mean_vibration_band_power": mean(powers),
            }
        )
    return detail_rows, summary_rows


def build_dir_gain_summary() -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(WINDOW_DETAIL_CSV):
        if row["joint"] not in JOINTS or row["window"] not in WINDOWS:
            continue
        grouped[(row["kp_case"], row["dataset"], row["window"], row["joint"])].append(row)

    out: list[dict[str, object]] = []
    for (kp_case, dataset, window, joint), items in sorted(grouped.items()):
        target_dir = [parse_float(item["target_direction_change_rate_hz"]) for item in items]
        joint_dir = [parse_float(item["joint_direction_change_rate_hz"]) for item in items]
        target_amp = [parse_float(item["target_range_rad"]) for item in items]
        joint_amp = [parse_float(item["joint_range_rad"]) for item in items]
        gains = [
            j_amp / t_amp
            for t_amp, j_amp in zip(target_amp, joint_amp)
            if not math.isnan(t_amp) and not math.isnan(j_amp) and abs(t_amp) >= MIN_GAIN_TARGET_AMP_RAD
        ]
        out.append(
            {
                "kp_case": kp_case,
                "dataset": dataset,
                "window": window,
                "joint": joint,
                "curve_count": len(items),
                "gain_curve_count": len(gains),
                "mean_target_dir_chg_hz": mean(target_dir),
                "mean_joint_dir_chg_hz": mean(joint_dir),
                "mean_target_amp_rad": mean(target_amp),
                "mean_joint_amp_rad": mean(joint_amp),
                "mean_amplitude_gain": mean(gains),
                "median_amplitude_gain": median(gains),
            }
        )
    return out


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Arial,Helvetica,sans-serif;fill:#18212f}",
        ".title{font-size:25px;font-weight:700}",
        ".subtitle{font-size:13px;fill:#526174}",
        ".section{font-size:16px;font-weight:700}",
        ".label{font-size:11px;fill:#334155}",
        ".small{font-size:10px;fill:#526174}",
        ".grid{stroke:#d8dee8;stroke-width:1}",
        ".real{fill:#2563eb}",
        ".sim{fill:#dc2626}",
        ".bg{fill:#f8fafc}",
        ".panel{fill:#ffffff;stroke:#d8dee8;stroke-width:1}",
        "</style>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]


def draw_bar(svg: list[str], x: float, y: float, width: float, height: float, value: float, max_value: float, cls: str) -> None:
    if math.isnan(value) or max_value <= 0:
        return
    bar_h = max(1.0, value / max_value * height)
    svg.append(f'<rect x="{x:.1f}" y="{(y + height - bar_h):.1f}" width="{width:.1f}" height="{bar_h:.1f}" class="{cls}"/>')


def write_vibration_svg(summary_rows: list[dict[str, object]], detail_rows: list[dict[str, object]]) -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 940, 520
    svg = svg_header(width, height)
    svg.extend(
        [
            '<text x="34" y="42" class="title">Ankle true vibration frequency from full logs</text>',
            '<text x="34" y="66" class="subtitle">Signal: delay-aligned residual. Target PSD is checked at the residual peak; closed_loop_dominant means residual/target power >= 3x.</text>',
            '<rect x="34" y="86" width="14" height="8" class="real"/><text x="54" y="94" class="subtitle">real</text>',
            '<rect x="104" y="86" width="14" height="8" class="sim"/><text x="124" y="94" class="subtitle">sim</text>',
        ]
    )
    panel_x, panel_y, panel_w, panel_h = 70, 125, 340, 285
    max_value = max(float(row["mean_vibration_peak_hz"]) for row in summary_rows)
    for idx, joint in enumerate(JOINTS):
        x0 = panel_x + idx * 445
        svg.append(f'<rect x="{x0}" y="{panel_y}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        svg.append(f'<text x="{x0 + 12}" y="{panel_y + 25}" class="section">{esc(joint)}</text>')
        for tick in range(0, int(math.ceil(max_value / 5.0)) * 5 + 1, 5):
            y = panel_y + panel_h - 38 - (tick / max_value * (panel_h - 70) if max_value else 0)
            svg.append(f'<line x1="{x0 + 45}" y1="{y:.1f}" x2="{x0 + panel_w - 20}" y2="{y:.1f}" class="grid"/>')
            svg.append(f'<text x="{x0 + 14}" y="{y + 3:.1f}" class="small">{tick}</text>')
        bar_base_y = panel_y + 45
        bar_h = panel_h - 83
        for didx, dataset in enumerate(DATASETS):
            row = next(r for r in summary_rows if r["dataset"] == dataset and r["joint"] == joint)
            x = x0 + 90 + didx * 95
            cls = dataset
            value = float(row["mean_vibration_peak_hz"])
            draw_bar(svg, x, bar_base_y, 52, bar_h, value, max_value, cls)
            svg.append(f'<text x="{x + 2}" y="{panel_y + panel_h - 18}" class="label">{dataset}</text>')
            svg.append(f'<text x="{x - 2}" y="{bar_base_y + bar_h - max(1.0, value / max_value * bar_h) - 6:.1f}" class="label">{fmt(value)}</text>')
            svg.append(f'<text x="{x - 12}" y="{panel_y + panel_h - 5}" class="small">std {fmt(float(row["std_vibration_peak_hz"]))}</text>')

    y = 455
    svg.append(f'<text x="34" y="{y}" class="subtitle">Per-case peaks are in {esc(VIBRATION_DETAIL_CSV.relative_to(ROOT))}; summary CSV is {esc(VIBRATION_SUMMARY_CSV.relative_to(ROOT))}.</text>')
    svg.append("</svg>")
    VIBRATION_SVG.write_text("\n".join(svg) + "\n")


def write_dir_gain_svg(rows: list[dict[str, object]]) -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    kp_cases = sorted({str(row["kp_case"]) for row in rows})
    metrics = [
        ("target dir chg", "mean_target_dir_chg_hz", "Hz"),
        ("joint dir chg", "mean_joint_dir_chg_hz", "Hz"),
        ("amplitude gain", "mean_amplitude_gain", "x"),
    ]
    panel_w, panel_h = 360, 200
    width = 80 + len(metrics) * (panel_w + 26)
    height = 128 + len(JOINTS) * len(WINDOWS) * (panel_h + 58)
    svg = svg_header(width, height)
    svg.extend(
        [
            '<text x="34" y="42" class="title">Ankle swing/touchdown direction-change and amplitude gain</text>',
            '<text x="34" y="66" class="subtitle">amplitude_gain = joint_amp / target_amp, using per-window range. Target amplitudes below 0.01 rad are excluded from gain.</text>',
            '<rect x="34" y="88" width="14" height="8" class="real"/><text x="54" y="96" class="subtitle">real</text>',
            '<rect x="104" y="88" width="14" height="8" class="sim"/><text x="124" y="96" class="subtitle">sim</text>',
        ]
    )
    y = 128
    for joint in JOINTS:
        for window in WINDOWS:
            svg.append(f'<text x="34" y="{y - 12}" class="section">{esc(joint)} | {esc(window)}</text>')
            for midx, (title, key, unit) in enumerate(metrics):
                x0 = 60 + midx * (panel_w + 26)
                svg.append(f'<rect x="{x0}" y="{y}" width="{panel_w}" height="{panel_h}" class="panel"/>')
                svg.append(f'<text x="{x0 + 10}" y="{y + 22}" class="label">{esc(title)} ({esc(unit)})</text>')
                local_values = [
                    float(row[key])
                    for row in rows
                    if row["joint"] == joint and row["window"] == window and not math.isnan(float(row[key]))
                ]
                max_value = max(local_values) if local_values else 1.0
                max_value *= 1.15
                plot_x = x0 + 48
                plot_y = y + 36
                plot_w = panel_w - 68
                plot_h = panel_h - 74
                for frac in (0.0, 0.5, 1.0):
                    gy = plot_y + plot_h - frac * plot_h
                    svg.append(f'<line x1="{plot_x}" y1="{gy:.1f}" x2="{plot_x + plot_w}" y2="{gy:.1f}" class="grid"/>')
                    svg.append(f'<text x="{x0 + 8}" y="{gy + 3:.1f}" class="small">{fmt(max_value * frac)}</text>')
                group_w = plot_w / len(kp_cases)
                for kidx, kp_case in enumerate(kp_cases):
                    base_x = plot_x + kidx * group_w + 4
                    for didx, dataset in enumerate(DATASETS):
                        match = [
                            row
                            for row in rows
                            if row["kp_case"] == kp_case
                            and row["dataset"] == dataset
                            and row["window"] == window
                            and row["joint"] == joint
                        ]
                        if not match:
                            continue
                        value = float(match[0][key])
                        draw_bar(svg, base_x + didx * 10, plot_y, 8, plot_h, value, max_value, dataset)
                    svg.append(
                        f'<text x="{base_x - 3}" y="{y + panel_h - 12}" class="small" transform="rotate(-35 {base_x - 3},{y + panel_h - 12})">{esc(kp_case.replace("_", " "))}</text>'
                    )
            y += panel_h + 58
    svg.append("</svg>")
    DIR_GAIN_SVG.write_text("\n".join(svg) + "\n")


def main() -> None:
    vibration_detail, vibration_summary = build_vibration_rows()
    dir_gain_summary = build_dir_gain_summary()
    write_csv(VIBRATION_DETAIL_CSV, vibration_detail)
    write_csv(VIBRATION_SUMMARY_CSV, vibration_summary)
    write_csv(DIR_GAIN_SUMMARY_CSV, dir_gain_summary)
    write_vibration_svg(vibration_summary, vibration_detail)
    write_dir_gain_svg(dir_gain_summary)
    print(VIBRATION_DETAIL_CSV)
    print(VIBRATION_SUMMARY_CSV)
    print(DIR_GAIN_SUMMARY_CSV)
    print(VIBRATION_SVG)
    print(DIR_GAIN_SVG)


if __name__ == "__main__":
    main()
