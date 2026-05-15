#!/usr/bin/env python3
"""
Ankle modal identification from dedicated step/sine logs.

This script is intentionally separate from ankle_damping_analysis.py:
walking logs are closed-loop, contact-rich, and often low-coherence for
single-input FRF damping estimation. Dedicated ankle_identifier logs provide
the excitation needed to estimate damping ratio and natural frequency.

Input format:
  - ankle_identifier_module CSV:
      time_sec, phase, target_primary, actual_primary, ...
  - The target trajectory can be a step, a pulse, or sine. The script fits the
    measured target-to-joint response directly, so it does not require a perfect
    infinite step hold.

Model:
  q(t) - q0 = H(s) * (target(t-delay) - target0) + bias
  H(s) = gain * wn^2 / (s^2 + 2*zeta*wn*s + wn^2)

Outputs:
  sim2real/walk_data_analysis/table/ankle_modal_id/ankle_modal_id_results.csv
  sim2real/walk_data_analysis/reports/踝关节模态辨识报告.md

Run:
  conda run -n x1 python sim2real/walk_data_analysis/scripts/ankle_modal_identification.py
  conda run -n x1 python sim2real/walk_data_analysis/scripts/ankle_modal_identification.py --glob 'test_logs/data_csv/ankle_step/*.csv'
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal
from scipy.optimize import least_squares


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
OUT_DIR = ANALYSIS_DIR / "table" / "ankle_modal_id"
OUT_CSV = OUT_DIR / "ankle_modal_id_results.csv"
REPORT_PATH = ANALYSIS_DIR / "reports" / "踝关节模态辨识报告.md"


def finite(v) -> bool:
    return v is not None and np.isfinite(v)


def infer_kpkd(path: Path) -> tuple[float | None, float | None]:
    text = path.name
    m = re.search(r"kp([0-9]+(?:\.[0-9]+)?)_kd([0-9]+(?:\.[0-9]+)?)", text)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def infer_dataset(path: Path) -> str:
    p = str(path).lower()
    if "sim" in p:
        return "sim"
    if "real" in p:
        return "real"
    return "unknown"


def load_identifier_csv(path: Path) -> dict | None:
    df = pd.read_csv(path)
    required = {"time_sec", "target_primary", "actual_primary"}
    if not required.issubset(df.columns):
        return None
    t = df["time_sec"].to_numpy(dtype=float)
    target = df["target_primary"].to_numpy(dtype=float)
    actual = df["actual_primary"].to_numpy(dtype=float)
    mask = np.isfinite(t) & np.isfinite(target) & np.isfinite(actual)
    t, target, actual = t[mask], target[mask], actual[mask]
    if len(t) < 200:
        return None
    t = t - t[0]
    joint = str(df["primary_joint"].dropna().iloc[0]) if "primary_joint" in df.columns and df["primary_joint"].notna().any() else ""
    phase = df["phase"].astype(str).to_numpy()[mask] if "phase" in df.columns else np.array([""] * len(t))
    return {"t": t, "target": target, "actual": actual, "phase": phase, "joint": joint}


def find_fit_window(t: np.ndarray, target: np.ndarray, phase: np.ndarray) -> tuple[int, int, int]:
    active = np.flatnonzero(phase == "active")
    if len(active) > 10:
        start = int(active[0])
        stop = min(len(t), int(active[-1]) + int(round(1.2 / np.median(np.diff(t)))))
        pre_start = max(0, start - int(round(0.5 / np.median(np.diff(t)))))
        return pre_start, start, stop

    # Fallback: largest target jump.
    d = np.abs(np.diff(target))
    start = int(np.argmax(d) + 1)
    dt = float(np.median(np.diff(t)))
    pre_start = max(0, start - int(round(0.5 / dt)))
    stop = min(len(t), start + int(round(1.5 / dt)))
    return pre_start, start, stop


def simulate_second_order(t: np.ndarray, u: np.ndarray, gain: float, fn_hz: float, zeta: float) -> np.ndarray:
    wn = 2.0 * math.pi * fn_hz
    sys = signal.TransferFunction([gain * wn * wn], [1.0, 2.0 * zeta * wn, wn * wn])
    _, y, _ = signal.lsim(sys, U=u, T=t)
    return y


def fit_modal(path: Path) -> dict | None:
    loaded = load_identifier_csv(path)
    if loaded is None:
        return None

    t_all = loaded["t"]
    target_all = loaded["target"]
    actual_all = loaded["actual"]
    phase_all = loaded["phase"]
    pre_start, step_idx, stop = find_fit_window(t_all, target_all, phase_all)
    if stop - step_idx < 120:
        return None

    t_raw = t_all[pre_start:stop].copy()
    target_raw = target_all[pre_start:stop].copy()
    actual_raw = actual_all[pre_start:stop].copy()
    t_raw = t_raw - t_raw[0]
    dt_raw = float(np.median(np.diff(t_raw)))
    fit_dt = max(dt_raw, 0.005)  # 200 Hz is enough for <30 Hz modal fitting.
    # signal.lsim requires an equally spaced time vector. Controller logs are
    # close to periodic but not exact, so resample before fitting.
    t = np.arange(0.0, t_raw[-1], fit_dt)
    target = np.interp(t, t_raw, target_raw)
    actual = np.interp(t, t_raw, actual_raw)
    local_step_idx = step_idx - pre_start
    local_step_idx = int(round((t_all[step_idx] - t_all[pre_start]) / fit_dt))

    baseline_slice = slice(0, max(5, local_step_idx))
    target0 = float(np.nanmedian(target[baseline_slice]))
    actual0 = float(np.nanmedian(actual[baseline_slice]))
    u = target - target0
    y = actual - actual0
    amp = float(np.nanmax(u) - np.nanmin(u))
    y_amp = float(np.nanmax(y) - np.nanmin(y))
    if amp < 1e-4 or y_amp < 1e-5:
        return None

    dt = float(np.median(np.diff(t)))
    y_mean = float(np.nanmean(y))
    ss_tot = float(np.nansum((y - y_mean) ** 2))
    if ss_tot <= 1e-14:
        return None

    final_gain_guess = np.clip((np.nanmedian(y[-max(20, len(y) // 10):]) / (np.nanmedian(u[-max(20, len(u) // 10):]) + 1e-12)), 0.05, 2.0)
    best = None

    # Discrete delay grid keeps the nonlinear fit well-conditioned.
    for delay_ms in np.arange(0.0, 81.0, 10.0):
        delay_s = delay_ms / 1000.0
        u_delayed = np.interp(t - delay_s, t, u, left=u[0], right=u[-1])

        def residual(params: np.ndarray) -> np.ndarray:
            gain, fn_hz, zeta, bias = params
            pred = simulate_second_order(t, u_delayed, gain, fn_hz, zeta) + bias
            return pred - y

        for init in (
            [final_gain_guess, 2.5, 0.25, 0.0],
            [final_gain_guess, 4.0, 0.5, 0.0],
            [1.0, 6.0, 1.0, 0.0],
        ):
            res = least_squares(
                residual,
                x0=np.asarray(init, dtype=float),
                bounds=([0.01, 0.2, 0.01, -0.2], [3.0, 30.0, 5.0, 0.2]),
                max_nfev=250,
                ftol=1e-9,
                xtol=1e-9,
                gtol=1e-9,
            )
            ss_res = float(np.nansum(res.fun ** 2))
            r2 = 1.0 - ss_res / ss_tot
            score = r2 - 0.0005 * delay_ms
            if best is None or score > best["score"]:
                gain, fn_hz, zeta, bias = [float(x) for x in res.x]
                best = {
                    "dataset": infer_dataset(path),
                    "file": str(path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path),
                    "joint": loaded["joint"],
                    "kp": infer_kpkd(path)[0],
                    "kd": infer_kpkd(path)[1],
                    "n_samples": int(len(t)),
                    "fit_duration_s": float(t[-1] - t[0]),
                    "target_amp_rad": amp,
                    "response_amp_rad": y_amp,
                    "delay_ms": float(delay_ms),
                    "gain": gain,
                    "fn_hz": fn_hz,
                    "zeta": zeta,
                    "bias_rad": bias,
                    "r2": r2,
                    "rmse_rad": math.sqrt(ss_res / len(y)),
                    "score": score,
                }

    if best is None:
        return None
    best["quality"] = classify_quality(best)
    return best


def classify_quality(row: dict) -> str:
    flags = []
    if row["r2"] < 0.80:
        flags.append("low_r2")
    if row["target_amp_rad"] < 0.001:
        flags.append("tiny_excitation")
    if row["zeta"] <= 0.011 or row["zeta"] >= 4.95:
        flags.append("zeta_bound")
    if row["fn_hz"] <= 0.25 or row["fn_hz"] >= 29.5:
        flags.append("fn_bound")
    if row["gain"] <= 0.02 or row["gain"] >= 2.95:
        flags.append("gain_bound")
    return "ok" if not flags else ";".join(flags)


def write_report(rows: list[dict]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 踝关节模态辨识报告",
        "",
        "> 方法：专用 step/sine 输入 → 带延迟二阶闭环模型拟合，直接估计 `zeta` 与 `fn_hz`。",
        "> 该报告用于替代行走 FRF 在 real 低相干场景下的阻尼判定。",
        "",
    ]
    if not rows:
        lines += [
            "未找到可分析的 ankle_identifier CSV。",
            "",
            "建议采集：`src/module/ankle_identifier_module/cfg/ankle_identifier.yaml`，step 或多频 sine，四个踝关节轴分别测试。",
        ]
    else:
        lines += [
            "| dataset | file | joint | kp | kd | zeta | fn_hz | delay_ms | gain | r2 | quality |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['dataset']} | `{Path(r['file']).name}` | {r['joint']} | "
                f"{fmt(r['kp'])} | {fmt(r['kd'])} | {r['zeta']:.4f} | {r['fn_hz']:.3f} | "
                f"{r['delay_ms']:.1f} | {r['gain']:.3f} | {r['r2']:.4f} | {r['quality']} |"
            )
        lines += [
            "",
            "判定建议：`quality=ok` 且 `r2>=0.80` 时可用于阻尼比/固有频率判断；"
            "`low_r2` 或参数贴边时仅作参考，需要增大激励幅值、延长 active/post_hold 或改用多频 sine。",
        ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt(v) -> str:
    return "" if not finite(v) else f"{float(v):.3g}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--glob",
        action="append",
        default=[
            "test_logs/data_csv/ankle_step/*.csv",
            "test_logs/data_csv/ankle_sim/*step*.csv",
        ],
        help="Input glob relative to repo root. Can be passed multiple times.",
    )
    args = parser.parse_args()

    paths = []
    for pattern in args.glob:
        paths.extend(REPO_ROOT.glob(pattern))
    paths = sorted(set(paths))

    rows = []
    for path in paths:
        row = fit_modal(path)
        if row is not None:
            rows.append(row)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    write_report(rows)
    print(f"Wrote {OUT_CSV} ({len(rows)} rows)")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
