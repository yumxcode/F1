#!/usr/bin/env python3

import csv
import glob
import math
import os
import re
import cmath
from collections import defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def find_repo_root(start):
    cur = start
    while True:
        if (cur / "real2sim").is_dir() and (cur / "test_logs").is_dir():
            return cur
        if cur.parent == cur:
            raise RuntimeError(f"failed to locate repo root from {start}")
        cur = cur.parent


REPO_ROOT = find_repo_root(SCRIPT_DIR)
OUT_DIR = REPO_ROOT / "real2sim/table/forward_x_failure_first6"
RESULT_MD = REPO_ROOT / ".oma/sim2real/results/forward_x_failure/35_ankle_zeta_natural_frequency_stats.md"
DETAIL_CSV = OUT_DIR / "forward_x_failure_first6_t27_ankle_zeta_fn_detail.csv"
SUMMARY_CSV = OUT_DIR / "forward_x_failure_first6_t27_ankle_zeta_fn_summary.csv"

ANKLE_JOINTS = (
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
)

REAL_CASE_HINTS = {
    "20260430_100024": ("25/0.4 all_ankles", 25.0, 0.4),
    "20260430_100314": ("30/0.4 all_ankles", 30.0, 0.4),
    "20260430_100705": ("35/0.5 all_ankles", 35.0, 0.5),
    "20260430_101404": ("40/0.8 all_ankles", 40.0, 0.8),
}

SIM_CASE_HINTS = {
    "2504": ("25/0.4 all_ankles", 25.0, 0.4),
    "3505": ("35/0.5 all_ankles", 35.0, 0.5),
    "4005": ("40/0.5 all_ankles", 40.0, 0.5),
    "5008": ("50/0.8 all_ankles", 50.0, 0.8),
}

FMIN_HZ = 2.0
FMAX_HZ = 30.0
MIN_POINTS = 64
EPS = 1e-12


def fmt(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def mean(values):
    vals = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not vals:
        return math.nan
    return float(sum(vals) / len(vals))


def stddev(values):
    vals = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if len(vals) < 2:
        return 0.0 if vals else math.nan
    mu = mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def median(values):
    vals = sorted(v for v in values if isinstance(v, (int, float)) and not math.isnan(v))
    if not vals:
        return math.nan
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return 0.5 * (vals[mid - 1] + vals[mid])


def rms_ac(values):
    vals = valid_array(values)
    if not vals:
        return math.nan
    mu = mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals))


def rel(path):
    return str(path.relative_to(REPO_ROOT))


def collect_files():
    real = sorted((REPO_ROOT / "test_logs/data_csv").glob("t27*.csv"))
    sim = sorted((REPO_ROOT / "test_logs/data_csv/sim").glob("t27*.csv"))
    return [("real", p) for p in real] + [("sim", p) for p in sim]


def infer_case(dataset, path):
    name = path.name
    if dataset == "sim":
        suffix = name.replace(".csv", "").split("_")[-1]
        label, kp, kd = SIM_CASE_HINTS.get(suffix, (suffix, math.nan, math.nan))
        return label, kp, kd
    for token, item in REAL_CASE_HINTS.items():
        if token in name:
            return item
    return name.replace("t27_tracking_lag_b1_diag_", "").replace(".csv", ""), math.nan, math.nan


def load_columns(path, columns):
    data = {col: [] for col in columns}
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [col for col in columns if col not in reader.fieldnames]
        if missing:
            return None, missing
        for row in reader:
            for col in columns:
                raw = row.get(col, "")
                try:
                    data[col].append(float(raw) if raw is not None and raw != "" else math.nan)
                except (TypeError, ValueError):
                    data[col].append(math.nan)
    return data, []


def valid_array(values):
    return [float(v) for v in values if math.isfinite(float(v))]


def sample_rate_hz(timestamp_ns):
    t = [v * 1e-9 for v in valid_array(timestamp_ns)]
    if len(t) < 3:
        return math.nan
    dt = [b - a for a, b in zip(t, t[1:]) if b > a]
    if len(dt) == 0:
        return math.nan
    return float(1.0 / median(dt))


def detrend(values):
    x = valid_array(values)
    if len(x) < MIN_POINTS:
        return None
    mu = mean(x)
    return [v - mu for v in x]


def next_power_of_two(n):
    out = 1
    while out < n:
        out <<= 1
    return out


def fft(values):
    n = len(values)
    if n == 1:
        return values
    even = fft(values[0::2])
    odd = fft(values[1::2])
    out = [0j] * n
    for k in range(n // 2):
        twiddle = cmath.exp(-2j * math.pi * k / n) * odd[k]
        out[k] = even[k] + twiddle
        out[k + n // 2] = even[k] - twiddle
    return out


def fft_power(values, fs):
    x = detrend(values)
    if x is None or not math.isfinite(fs) or fs <= 0.0:
        return None, None
    raw_n = len(x)
    n = next_power_of_two(raw_n)
    if raw_n > 1:
        windowed = [
            value * (0.5 - 0.5 * math.cos(2.0 * math.pi * idx / (raw_n - 1)))
            for idx, value in enumerate(x)
        ]
    else:
        windowed = x
    window_power = sum(
        (0.5 - 0.5 * math.cos(2.0 * math.pi * idx / (raw_n - 1))) ** 2
        for idx in range(raw_n)
    ) if raw_n > 1 else 1.0
    padded = [complex(v, 0.0) for v in windowed] + [0j] * (n - raw_n)
    spec = fft(padded)
    half_n = n // 2 + 1
    freq = [k * fs / n for k in range(half_n)]
    power = [(abs(spec[k]) ** 2) / max(EPS, window_power) for k in range(half_n)]
    return freq, power


def peak_and_bandwidth(freq, power):
    if freq is None or power is None:
        return {}
    idxs = [idx for idx, f in enumerate(freq) if FMIN_HZ <= f <= FMAX_HZ and math.isfinite(power[idx])]
    if len(idxs) == 0:
        return {}
    local = [power[idx] for idx in idxs]
    if len(local) == 0 or max(local) <= EPS:
        return {}
    peak_i = idxs[local.index(max(local))]
    f_peak = float(freq[peak_i])
    p_peak = float(power[peak_i])
    floor = float(median(local))
    prominence = p_peak / max(EPS, floor)
    half = p_peak * 0.5

    left = peak_i
    while left > idxs[0] and power[left] >= half:
        left -= 1
    right = peak_i
    while right < idxs[-1] and power[right] >= half:
        right += 1

    if left == idxs[0] or right == idxs[-1]:
        f1 = math.nan
        f2 = math.nan
        bandwidth = math.nan
        zeta = math.nan
    else:
        f1 = float(freq[left])
        f2 = float(freq[right])
        bandwidth = f2 - f1
        zeta = bandwidth / (2.0 * f_peak) if f_peak > EPS else math.nan

    return {
        "peak_hz": f_peak,
        "peak_power": p_peak,
        "median_power": floor,
        "peak_prominence": prominence,
        "half_power_f1_hz": f1,
        "half_power_f2_hz": f2,
        "half_power_bandwidth_hz": bandwidth,
        "zeta_bandwidth": zeta,
    }


def power_at(freq, power, target_hz):
    if freq is None or power is None or not math.isfinite(target_hz):
        return math.nan
    idx = min(range(len(freq)), key=lambda i: abs(freq[i] - target_hz))
    return float(power[idx])


def analyze_joint(dataset, path, joint):
    target_col = f"pos_des_lpf_{joint}"
    raw_col = f"pos_des_raw_{joint}"
    pos_col = f"pos_{joint}"
    cols = ["timestamp_ns", pos_col, target_col, raw_col]
    data, missing = load_columns(path, cols)
    if data is None and target_col in missing:
        data, missing = load_columns(path, ["timestamp_ns", pos_col, raw_col])
        target_col = raw_col
    if data is None:
        return None
    if target_col in data and len(valid_array(data[target_col])) < MIN_POINTS:
        target_col = raw_col
    if target_col not in data or len(valid_array(data[target_col])) < MIN_POINTS:
        return None

    fs = sample_rate_hz(data["timestamp_ns"])
    pos = [float(v) for v in data[pos_col]]
    target = [float(v) for v in data[target_col]]
    n = min(len(pos), len(target))
    pos = pos[:n]
    target = target[:n]
    residual = [
        (p - t) if math.isfinite(p) and math.isfinite(t) else math.nan
        for p, t in zip(pos, target)
    ]

    freq_res, power_res = fft_power(residual, fs)
    freq_pos, power_pos = fft_power(pos, fs)
    freq_tgt, power_tgt = fft_power(target, fs)
    res_peak = peak_and_bandwidth(freq_res, power_res)
    pos_peak = peak_and_bandwidth(freq_pos, power_pos)
    tgt_peak = peak_and_bandwidth(freq_tgt, power_tgt)
    if not res_peak:
        return None

    peak_hz = res_peak["peak_hz"]
    residual_power = power_at(freq_res, power_res, peak_hz)
    target_power = power_at(freq_tgt, power_tgt, peak_hz)
    pos_power = power_at(freq_pos, power_pos, peak_hz)
    residual_target_ratio = residual_power / max(EPS, target_power)
    output_target_gain = math.sqrt(pos_power / max(EPS, target_power))

    side = "left" if joint.startswith("left_") else "right"
    axis = "pitch" if "pitch" in joint else "roll"
    case_label, kp, kd = infer_case(dataset, path)
    zeta = res_peak["zeta_bandwidth"]
    f_n_equiv = (
        peak_hz / math.sqrt(max(EPS, 1.0 - zeta * zeta))
        if math.isfinite(zeta) and zeta < 1.0
        else math.nan
    )
    reliable = (
        math.isfinite(zeta)
        and 0.0 < zeta < 1.0
        and res_peak["peak_prominence"] >= 4.0
        and residual_target_ratio >= 1.0
    )
    return {
        "dataset": dataset,
        "case_label": case_label,
        "ankle_kp": kp,
        "ankle_kd": kd,
        "diag_csv": path.name,
        "source_path": rel(path),
        "joint": joint,
        "side": side,
        "axis": axis,
        "sample_count": n,
        "duration_sec": n / fs if math.isfinite(fs) and fs > 0.0 else math.nan,
        "sample_rate_hz": fs,
        "target_column": target_col,
        "residual_peak_hz": peak_hz,
        "f_modal_candidate_hz": peak_hz,
        "zeta_bandwidth": zeta,
        "f_n_equiv_hz": f_n_equiv,
        "half_power_bandwidth_hz": res_peak["half_power_bandwidth_hz"],
        "half_power_f1_hz": res_peak["half_power_f1_hz"],
        "half_power_f2_hz": res_peak["half_power_f2_hz"],
        "residual_peak_prominence": res_peak["peak_prominence"],
        "residual_target_power_ratio": residual_target_ratio,
        "output_target_gain_at_residual_peak": output_target_gain,
        "target_peak_hz": tgt_peak.get("peak_hz", math.nan),
        "pos_peak_hz": pos_peak.get("peak_hz", math.nan),
        "target_rms_rad": rms_ac(target),
        "pos_rms_rad": rms_ac(pos),
        "residual_rms_rad": rms_ac(residual),
        "frequency_source": "t27_walking_residual_fft_half_power",
        "reliable_zeta_bandwidth": reliable,
    }


def write_csv(path, rows):
    if not rows:
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["dataset"], row["axis"], row["case_label"])].append(row)
    out = []
    for (dataset, axis, case_label), items in sorted(groups.items()):
        reliable_items = [r for r in items if r["reliable_zeta_bandwidth"]]
        source = reliable_items if reliable_items else items
        out.append(
            {
                "dataset": dataset,
                "axis": axis,
                "case_label": case_label,
                "joint_count": len(items),
                "reliable_joint_count": len(reliable_items),
                "median_f_modal_candidate_hz": median([r["f_modal_candidate_hz"] for r in source]),
                "mean_f_modal_candidate_hz": mean([r["f_modal_candidate_hz"] for r in source]),
                "median_zeta_bandwidth": median([r["zeta_bandwidth"] for r in source]),
                "mean_zeta_bandwidth": mean([r["zeta_bandwidth"] for r in source]),
                "std_zeta_bandwidth": stddev([r["zeta_bandwidth"] for r in source]),
                "median_f_n_equiv_hz": median([r["f_n_equiv_hz"] for r in source]),
                "median_residual_target_power_ratio": median(
                    [r["residual_target_power_ratio"] for r in source]
                ),
                "median_output_target_gain_at_peak": median(
                    [r["output_target_gain_at_residual_peak"] for r in source]
                ),
                "source_rule": "reliable_only" if reliable_items else "all_unreliable",
            }
        )
    return out


def md_table(rows, fields, max_rows=None):
    selected = rows[:max_rows] if max_rows else rows
    lines = ["| " + " | ".join(fields) + " |", "|" + "|".join("---" for _ in fields) + "|"]
    for row in selected:
        cells = []
        for field in fields:
            value = row.get(field, "")
            if isinstance(value, float):
                digits = 4 if "zeta" in field else 2
                cells.append(fmt(value, digits))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(detail_rows, summary_rows):
    sim_files = sorted({r["source_path"] for r in detail_rows if r["dataset"] == "sim"})
    real_files = sorted({r["source_path"] for r in detail_rows if r["dataset"] == "real"})
    focus = [
        r
        for r in summary_rows
        if r["axis"] == "roll" and (r["dataset"] == "sim" or "40/0.8" in r["case_label"])
    ]
    fields = [
        "dataset",
        "axis",
        "case_label",
        "joint_count",
        "reliable_joint_count",
        "median_f_modal_candidate_hz",
        "median_zeta_bandwidth",
        "median_f_n_equiv_hz",
        "median_residual_target_power_ratio",
        "source_rule",
    ]
    report = f"""# 35 T27 Ankle Zeta and Natural Frequency Statistics

## 数据源

本轮已按指定口径重做统计：

- sim: `test_logs/data_csv/sim/t27*.csv`，共 `{len(sim_files)}` 个文件。
- real: `test_logs/data_csv/t27*.csv`，共 `{len(real_files)}` 个文件。

## 方法说明

这些 `t27` 是走路诊断日志，不是单关节 step ringdown。因此本报告不再输出严格的 `zeta_step`。

统计口径：

- 输入：优先用 `pos_des_lpf_<joint>`；该列缺失或有效样本不足时回退到 `pos_des_raw_<joint>`。并联踝关节在部分日志里 `pos_des_lpf_*` 为 `NaN`，因此会自动使用 raw target。
- 输出：`pos_<joint>`。
- 残差：`pos - target`。
- 频率：残差在 `{FMIN_HZ:.1f}~{FMAX_HZ:.1f} Hz` 的 FFT 峰值，记为 `f_modal_candidate_hz`。
- 阻尼近似：残差峰半功率带宽，`zeta_bandwidth = (f2 - f1) / (2 * f_peak)`。
- 等效自然频率：`f_n_equiv = f_peak / sqrt(1 - zeta_bandwidth^2)`。

可靠性筛选：

- 半功率左右边界都能找到。
- `0 < zeta_bandwidth < 1`。
- 残差峰相对频带中位功率 `>= 4x`。
- 残差峰处 `residual/target power >= 1x`。

注意：这是 walking-data 的等效闭环模态统计，用于 sim/real 对照和风险定位；最终阻尼比仍需 step/sine 专项实验确认。

## 重点汇总

{md_table(focus, fields)}

## 全量分组汇总

{md_table(summary_rows, fields)}

## 初步结论

1. sim 与 real 现在都来自 `t27*` 走路诊断日志，统计口径一致。
2. `zeta_bandwidth` 是频域半功率近似，不等价于 step 实验的 `zeta_step`；它适合比较 sim/real 的相对阻尼和峰宽。
3. 如果某组 `source_rule=all_unreliable`，说明该组残差谱不满足半功率/峰显著性条件，不能把其 `zeta` 当成稳定结论。
4. 下一步应优先看 detail 表中 `right_ankle_roll_joint` 的 real/sim 差异，尤其 `residual_target_power_ratio` 和 `output_target_gain_at_residual_peak`，再决定是否进入真实 step/sine 的 `kd` 扫描。

## 输出文件

- `{rel(DETAIL_CSV)}`
- `{rel(SUMMARY_CSV)}`
"""
    RESULT_MD.write_text(report, encoding="utf-8")


def main():
    detail_rows = []
    for dataset, path in collect_files():
        for joint in ANKLE_JOINTS:
            row = analyze_joint(dataset, path, joint)
            if row:
                detail_rows.append(row)
    summary_rows = summarize(detail_rows)
    write_csv(DETAIL_CSV, detail_rows)
    write_csv(SUMMARY_CSV, summary_rows)
    write_report(detail_rows, summary_rows)
    print(f"Wrote {rel(DETAIL_CSV)}")
    print(f"Wrote {rel(SUMMARY_CSV)}")
    print(f"Wrote {rel(RESULT_MD)}")


if __name__ == "__main__":
    main()
