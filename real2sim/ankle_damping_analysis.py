#!/usr/bin/env python3
"""
踝关节欠阻尼/谐振分析脚本
===========================
基于 ankle_damping_analysis_methodology.md，从真机/仿真行走日志中
自动计算各级指标，输出 detail CSV / summary CSV / markdown 报告。

用法: python ankle_damping_analysis.py

数据源:
  - 仿真: test_logs/data_csv/sim/t27*.csv
  - 真机: test_logs/data_csv/t27*.csv

输出:
  - real2sim/table/ankle_damping_detail.csv
  - real2sim/table/ankle_damping_summary.csv
  - real2sim/ankle_damping_analysis_report.md
"""

from __future__ import annotations

import math
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.signal import (
    butter,
    coherence,
    csd,
    detrend,
    find_peaks,
    hilbert,
    sosfiltfilt,
    welch,
)

# ─── Paths ───────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DATA_DIR = REPO_ROOT / "test_logs" / "data_csv"
SIM_DIR = DATA_DIR / "sim"
TABLE_DIR = SCRIPT_DIR / "table"
REPORT_PATH = SCRIPT_DIR / "ankle_damping_analysis_report.md"
DETAIL_CSV = TABLE_DIR / "ankle_damping_detail.csv"
SUMMARY_CSV = TABLE_DIR / "ankle_damping_summary.csv"

# ─── Constants ───────────────────────────────────────────────────────
J_EFF_DEFAULT = 0.0965  # kg·m², swing-phase equivalent inertia
AXES = ("pitch", "roll")
SIDES = ("left", "right")
ANKLE_JOINTS = [f"{s}_ankle_{a}_joint" for s in SIDES for a in AXES]

# Welding & filtering
MIN_TD_GAP_S = 0.25
SWING_PRE_S = 0.35
SWING_POST_S = 0.02
TD_PRE_S = 0.02
TD_POST_S = 0.90
DELAY_MAX_LAG_SAMPLES = 30
DELAY_MIN_CORR = 0.20
MIN_FREQ_HZ = 2.0
MAX_FREQ_HZ = 20.0
SWING_FREQ_BAND = (2.0, 7.0)
STANCE_FREQ_BAND = (3.0, 20.0)
AMPLITUDE_GAIN_FLOOR_RAD = 0.010  # 10 mrad threshold for valid cycle

# ─── Real-case Kp/Kd mapping (by timestamp token in filename) ───────
REAL_KPKD_MAP = {
    "20260430_100024": (25.0, 0.4),
    "20260430_100314": (30.0, 0.4),
    "20260430_100705": (35.0, 0.5),
    "20260430_101404": (40.0, 0.8),
    # older runs — Kp/Kd unknown, will try actuator columns
}

# ─── Helpers ─────────────────────────────────────────────────────────


def finite(v):
    return v is not None and np.isfinite(v)


def rms(x: np.ndarray) -> float | None:
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    return float(np.sqrt(np.mean(x**2))) if len(x) > 0 else None


def nanmean(x):
    return float(np.nanmean(x)) if np.any(np.isfinite(x)) else None


def nanmedian(x):
    return float(np.nanmedian(x)) if np.any(np.isfinite(x)) else None


def valid_pair(x, y):
    mask = np.isfinite(x) & np.isfinite(y)
    return x[mask], y[mask]


def zscore(x):
    x = np.asarray(x, dtype=np.float64)
    if len(x) < 8:
        return None
    s = np.nanstd(x)
    if s < 1e-9:
        return None
    return (x - np.nanmean(x)) / s


def contiguous_regions(mask):
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return []
    breaks = np.where(np.diff(idx) > 1)[0] + 1
    groups = np.split(idx, breaks)
    return [slice(int(g[0]), int(g[-1]) + 1) for g in groups if len(g) >= 8]


def bandpass_sos(fs, lo, hi):
    nyq = 0.5 * fs
    lo = max(0.2, lo)
    hi = min(nyq * 0.95, hi)
    if lo >= hi:
        return None
    return butter(2, (lo / nyq, hi / nyq), btype="bandpass", output="sos")


# ─── File discovery & case mapping ──────────────────────────────────


def discover_files():
    sim_files = sorted(SIM_DIR.glob("t27*.csv"))
    real_files = sorted(DATA_DIR.glob("t27*.csv"))
    return sim_files, real_files


def infer_case(filepath: Path, dataset: str) -> tuple[str, float | None, float | None]:
    """Return (label, kp, kd) for a given file."""
    name = filepath.name
    if dataset == "sim":
        # Suffix like 2504 -> Kp=25, Kd=0.4; 4005 -> Kp=40, Kd=0.5
        suffix = name.replace(".csv", "").split("_")[-1]
        if len(suffix) == 4 and suffix.isdigit():
            kp = float(suffix[:2])
            kd = float(suffix[2:]) / 10.0
            return (f"{kp:.0f}/{kd:.1f}", kp, kd)
        return (suffix, None, None)
    # real
    for token, (kp, kd) in REAL_KPKD_MAP.items():
        if token in name:
            return (f"{kp:.0f}/{kd:.1f}", kp, kd)
    return (name.replace("t27_tracking_lag_b1_diag_", "").replace(".csv", ""), None, None)


# ─── Data loading ────────────────────────────────────────────────────


def load_file(filepath: Path):
    df = pd.read_csv(filepath)
    t_ns = df["timestamp_ns"].to_numpy(dtype=np.float64)
    t = (t_ns - t_ns[0]) / 1e9
    dt_vals = np.diff(t)
    dt_vals = dt_vals[dt_vals > 0]
    if len(dt_vals) == 0:
        raise ValueError(f"Invalid timestamps in {filepath}")
    dt = float(np.nanmedian(dt_vals))
    fs = 1.0 / dt if dt > 0 else 0.0
    if fs <= 0:
        raise ValueError(f"Zero sample rate in {filepath}")
    return df, t, dt, fs


def get_kpkd_from_actuator(df: pd.DataFrame, side: str, axis: str) -> tuple[float | None, float | None]:
    """Try to read Kp/Kd from actuator_cmd columns for a given ankle joint."""
    # Map to actuator naming: left_ankle_roll_joint -> left_ankle_left_actuator / right_actuator
    # For parallel ankle, there are two actuators per joint. Take the left actuator's Kp/Kd as reference.
    kp_col = f"actuator_cmd_kp_{side}_ankle_left_actuator"
    kd_col = f"actuator_cmd_kd_{side}_ankle_left_actuator"
    if kp_col in df.columns and kd_col in df.columns:
        kp_vals = df[kp_col].dropna().values
        kd_vals = df[kd_col].dropna().values
        if len(kp_vals) > 0 and len(kd_vals) > 0:
            return float(np.nanmedian(kp_vals)), float(np.nanmedian(kd_vals))
    return None, None


def get_touchdown_indices(df, t, side):
    contact_col = f"{side}_contact"
    if contact_col not in df.columns:
        return np.array([], dtype=int)
    contact = np.nan_to_num(df[contact_col].to_numpy(dtype=np.float64), nan=0.0).astype(int)
    edges = np.where(np.diff(contact) > 0)[0] + 1
    if len(edges) == 0:
        return edges
    kept = [int(edges[0])]
    for idx in edges[1:]:
        if t[idx] - t[kept[-1]] >= MIN_TD_GAP_S:
            kept.append(int(idx))
    return np.array(kept, dtype=int)


def segment_windows(t, td_idx, pre_s, post_s):
    windows = []
    for idx in td_idx:
        t0 = t[idx] - pre_s
        t1 = t[idx] + post_s
        win = np.flatnonzero((t >= t0) & (t <= t1))
        if len(win) >= 8:
            windows.append(win)
    return windows


def phase_windows(df, t, side, phase):
    contact = df[f"{side}_contact"].to_numpy(dtype=np.float64) > 0.5
    if phase == "swing":
        base = ~contact
    elif phase == "stance":
        base = contact
    else:
        raise ValueError(f"Unknown phase: {phase}")
    regions = contiguous_regions(base)
    return [np.arange(s.start, s.stop) for s in regions if (t[s.stop - 1] - t[s.start]) >= 0.20]


# ═════════════════════════════════════════════════════════════════════
# Metric 1: Natural frequency (fn)
# ═════════════════════════════════════════════════════════════════════


def average_window_spectrum(
    signal, fs, windows, band
) -> tuple[float | None, float | None, int, float | None]:
    """Phase-gated average FFT spectrum. Returns (fn_hz, prominence, n_windows, resolution)."""
    spectra = []
    freq_ref = None
    resolution = None
    for win in windows:
        x = signal[win]
        x = x[np.isfinite(x)]
        if len(x) < 16:
            continue
        x = detrend(x, type="linear")
        n = len(x)
        if resolution is None:
            resolution = fs / n
        else:
            resolution = min(resolution, fs / n)
        f = np.fft.rfftfreq(n, 1.0 / fs)
        mag = np.abs(np.fft.rfft(x * np.hanning(n)))
        mask = (f >= band[0]) & (f <= band[1])
        if not mask.any():
            continue
        if freq_ref is None:
            freq_ref = f[mask]
        mag_interp = np.interp(freq_ref, f[mask], mag[mask])
        spectra.append(mag_interp)
    if not spectra or freq_ref is None:
        return None, None, 0, None
    mean_mag = np.nanmean(np.vstack(spectra), axis=0)
    if np.nanmax(mean_mag) <= 0:
        return None, None, len(spectra), resolution
    peak_idx = int(np.nanargmax(mean_mag))
    peak = float(mean_mag[peak_idx])
    floor = float(np.nanmedian(mean_mag)) + 1e-12
    return float(freq_ref[peak_idx]), peak / floor, len(spectra), resolution


def full_welch_frequency(signal, fs, band) -> tuple[float | None, float | None]:
    x = signal[np.isfinite(signal)]
    if len(x) < 64:
        return None, None
    x = detrend(x, type="constant")
    nperseg = min(int(4.0 * fs), max(64, len(x) // 2))
    if nperseg >= len(x):
        nperseg = max(32, len(x) // 2)
    f, pxx = welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2, window="hann")
    mask = (f >= band[0]) & (f <= band[1])
    if not mask.any():
        return None, None
    p = pxx[mask]
    idx = int(np.nanargmax(p))
    peak = float(p[idx])
    floor = float(np.nanmedian(p)) + 1e-18
    return float(f[mask][idx]), peak / floor


# ═════════════════════════════════════════════════════════════════════
# Metric 2: Damping ratio from touchdown envelope (ζ_hat)
# ═════════════════════════════════════════════════════════════════════


# Free-decay prerequisite: for a touchdown event to qualify as "free decay"
# (rather than "forced tracking"), the target (des) must be approximately
# stationary within the [40ms, 800ms] post-touchdown window.
# If des change > this threshold, the event is forced — ζ estimate is invalid.
DES_STATIONARY_THRESHOLD_RAD = 0.2


def touchdown_damping_one_event(err, des, fs, fn_hz=None):
    """
    Estimate ζ from one touchdown event's error envelope decay.

    CRITICAL: Log-decrement requires FREE DECAY — the target must be
    approximately stationary during the decay window. If the target keeps
    moving, the error is a tracking residual, not a natural oscillation.
    We check this by measuring des (target position) change in the decay
    window and rejecting events where it exceeds DES_STATIONARY_THRESHOLD_RAD.

    Returns (zeta, tau_ms, alpha, r2, is_forced).
    is_forced=True means the event was rejected due to non-stationary target.
    """
    n = min(len(err), len(des))
    if n < int(0.35 * fs):
        return None, None, None, None, False

    # ── Prerequisite: is the target approximately stationary? ──
    decay_start = int(0.04 * fs)
    decay_stop = min(n, int(0.80 * fs))
    if decay_stop - decay_start < max(16, int(0.25 * fs)):
        return None, None, None, None, False
    des_decay = np.asarray(des[decay_start:decay_stop], dtype=np.float64)
    des_decay = des_decay[np.isfinite(des_decay)]
    if len(des_decay) < 8:
        return None, None, None, None, False
    des_range = float(np.nanmax(des_decay) - np.nanmin(des_decay))
    if des_range > DES_STATIONARY_THRESHOLD_RAD:
        return None, None, None, None, True  # forced — target still moving

    x = np.asarray(err[:n], dtype=np.float64)
    x = x[np.isfinite(x)]
    if len(x) < int(0.35 * fs):
        return None, None, None, None, False
    x = detrend(x, type="linear")

    if not finite(fn_hz):
        fn_hz, _ = full_welch_frequency(x, fs, STANCE_FREQ_BAND)
    if not finite(fn_hz) or fn_hz <= 0:
        return None, None, None, None, False

    sos = bandpass_sos(fs, max(1.0, fn_hz - 2.5), fn_hz + 2.5)
    if sos is None:
        return None, None, None, None, False
    try:
        y = sosfiltfilt(sos, x)
    except Exception:
        return None, None, None, None, False

    env = np.abs(hilbert(y))
    t_local = np.arange(len(env), dtype=np.float64) / fs
    if decay_stop - decay_start < max(16, int(0.25 * fs)):
        return None, None, None, None, False
    tt = t_local[decay_start:decay_stop]
    ee = env[decay_start:decay_stop]
    floor_val = np.nanpercentile(ee, 15)
    ee = np.maximum(ee - floor_val * 0.5, 1e-9)
    log_env = np.log(ee)
    if np.nanstd(log_env) < 1e-6:
        return None, None, None, None, False
    slope, intercept = np.polyfit(tt, log_env, 1)
    pred = slope * tt + intercept
    ss_res = float(np.nansum((log_env - pred) ** 2))
    ss_tot = float(np.nansum((log_env - np.nanmean(log_env)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    if slope >= 0:
        return None, None, None, r2, False
    omega_d = 2.0 * math.pi * float(fn_hz)
    alpha = -float(slope)
    omega_n = math.sqrt(omega_d**2 + alpha**2)
    zeta = alpha / omega_n
    tau_ms = 1000.0 / alpha if alpha > 0 else None
    return float(zeta), tau_ms, float(alpha), float(r2), False


def summarize_touchdown_damping(err, des, fs, windows, fn_hz=None):
    zetas, taus, r2s = [], [], []
    n_total = 0
    n_forced = 0
    for win in windows:
        n_total += 1
        z, tau, _, r2, is_forced = touchdown_damping_one_event(
            err[win], des[win], fs, fn_hz
        )
        if is_forced:
            n_forced += 1
            continue
        if finite(z) and finite(tau) and finite(r2) and 0.005 < z < 1.0 and r2 >= 0.25:
            zetas.append(z)
            taus.append(tau)
            r2s.append(r2)
    if not zetas:
        return None, None, None, 0, n_total, n_forced
    return nanmedian(zetas), nanmedian(taus), nanmedian(r2s), len(zetas), n_total, n_forced


# ═════════════════════════════════════════════════════════════════════
# Metric 3: Damping ratio from half-power bandwidth (ζ_BW)
# ═════════════════════════════════════════════════════════════════════


def zeta_from_half_power_bandwidth(signal, fs, band=(2.0, 30.0)):
    """Estimate ζ from the half-power bandwidth of the residual FFT peak."""
    x = signal[np.isfinite(signal)]
    if len(x) < 64:
        return None, None, None, None, None
    x = detrend(x, type="linear")
    n = len(x)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    mag = np.abs(np.fft.rfft(x * np.hanning(n)))
    mask = (f >= band[0]) & (f <= band[1])
    if not mask.any():
        return None, None, None, None, None
    f_b = f[mask]
    m_b = mag[mask]
    peak_idx = int(np.nanargmax(m_b))
    f_peak = float(f_b[peak_idx])
    p_peak = float(m_b[peak_idx] ** 2)
    floor = float(np.nanmedian(m_b**2)) + 1e-18
    prominence = p_peak / floor
    half = p_peak * 0.5
    left = peak_idx
    while left > 0 and m_b[left] ** 2 >= half:
        left -= 1
    right = peak_idx
    while right < len(m_b) - 1 and m_b[right] ** 2 >= half:
        right += 1
    if left == 0 or right == len(m_b) - 1:
        return f_peak, prominence, None, None, None
    f1, f2 = float(f_b[left]), float(f_b[right])
    bw = f2 - f1
    zeta = bw / (2.0 * f_peak) if f_peak > 0 else None
    fn_equiv = f_peak / math.sqrt(max(1e-9, 1.0 - zeta**2)) if finite(zeta) and zeta < 1.0 else None
    return f_peak, prominence, zeta, bw, fn_equiv


# ═════════════════════════════════════════════════════════════════════
# Metric 4: Amplitude gain & self-excitation
# ═════════════════════════════════════════════════════════════════════


def per_cycle_amplitude_gain(
    target, joint, fs, windows
) -> tuple[float | None, float | None, int, int, int]:
    """
    For each window, estimate amplitude_gain = joint_amp / target_amp.
    Only counts cycles where target_amp >= AMPLITUDE_GAIN_FLOOR_RAD.
    Returns (median_gain, std_gain, n_valid, n_total, n_self_excite).
    """
    gains = []
    total = 0
    n_self_excite = 0
    for win in windows:
        total += 1
        tg = target[win]
        jt = joint[win]
        tg = tg[np.isfinite(tg)]
        jt = jt[np.isfinite(jt)]
        n = min(len(tg), len(jt))
        if len(tg) < 8:
            continue
        tg = detrend(tg, type="linear")
        jt = detrend(jt[:n], type="linear")
        tg_amp = float(np.nanmax(np.abs(tg)))
        jt_amp = float(np.nanmax(np.abs(jt[:n])))
        if tg_amp < AMPLITUDE_GAIN_FLOOR_RAD:
            continue
        gain = jt_amp / tg_amp
        gains.append(gain)
        # Self-excitation: joint vel > target vel
        if len(tg) >= 4:
            tg_vrms = rms(np.diff(tg) * fs)
            jt_vrms = rms(np.diff(jt[:n]) * fs)
            if tg_vrms and jt_vrms and jt_vrms > tg_vrms:
                n_self_excite += 1
    if not gains:
        return None, None, 0, total, n_self_excite
    return nanmedian(gains), float(np.nanstd(gains)), len(gains), total, n_self_excite


# ═════════════════════════════════════════════════════════════════════
# Metric 5: Control delay (τ_d)
# ═════════════════════════════════════════════════════════════════════


def delay_one_window(ref, out, dt):
    x, y = valid_pair(ref, out)
    xz = zscore(detrend(x, type="linear")) if len(x) >= 8 else None
    yz = zscore(detrend(y, type="linear")) if len(y) >= 8 else None
    if xz is None or yz is None or len(xz) != len(yz):
        return None, None
    lags = np.arange(-DELAY_MAX_LAG_SAMPLES, DELAY_MAX_LAG_SAMPLES + 1)
    vals = []
    for lag in lags:
        if lag < 0:
            a, b = yz[:lag], xz[-lag:]
        elif lag > 0:
            a, b = yz[lag:], xz[:-lag]
        else:
            a, b = yz, xz
        vals.append(float(np.nanmean(a * b)) if len(a) >= 8 else np.nan)
    vals_a = np.asarray(vals)
    if not np.isfinite(vals_a).any():
        return None, None
    best_i = int(np.nanargmax(vals_a))
    return float(lags[best_i]) * dt * 1000.0, float(vals_a[best_i])


def summarize_delays(ref, out, dt, windows):
    lags, corrs = [], []
    n_total = 0
    for win in windows:
        lag, corr = delay_one_window(ref[win], out[win], dt)
        if finite(lag) and finite(corr):
            n_total += 1
            if corr >= DELAY_MIN_CORR:
                lags.append(lag)
                corrs.append(corr)
    if not lags:
        return None, None, None, 0, n_total
    lag_a = np.asarray(lags)
    return (
        nanmedian(lag_a),
        float(np.nanpercentile(lag_a, 75) - np.nanpercentile(lag_a, 25)),
        nanmedian(corrs),
        len(lags),
        n_total,
    )


# ═════════════════════════════════════════════════════════════════════
# Metric 6: Frequency-domain transfer gain
# ═════════════════════════════════════════════════════════════════════


def transfer_at_frequency(ref, out, fs, fn, bw_hz=0.75):
    if not finite(fn):
        return None, None, None
    x, y = valid_pair(ref, out)
    if len(x) < 128:
        return None, None, None
    x = detrend(x, type="constant")
    y = detrend(y, type="constant")
    nperseg = min(int(4.0 * fs), len(x) // 2)
    if nperseg < 64:
        return None, None, None
    f, pxx = welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2, window="hann")
    _, pyx = csd(y, x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2, window="hann")
    _, coh = coherence(x, y, fs=fs, nperseg=nperseg, noverlap=nperseg // 2, window="hann")
    mask = (f >= fn - bw_hz / 2.0) & (f <= fn + bw_hz / 2.0)
    if not mask.any() or np.nanmean(pxx[mask]) < 1e-14:
        return None, None, None
    h = pyx[mask] / np.maximum(pxx[mask], 1e-18)
    gain = float(np.nanmedian(np.abs(h)))
    phase_deg = float(np.rad2deg(np.angle(np.nanmean(h))))
    coh_med = float(np.nanmedian(coh[mask]))
    return gain, phase_deg, coh_med


# ═════════════════════════════════════════════════════════════════════
# Metric 7: Touchdown overshoot (A_peak)
# ═════════════════════════════════════════════════════════════════════


def touchdown_overshoot(err, fs, windows):
    vals = []
    for win in windows:
        x = np.asarray(err[win], dtype=np.float64)
        if len(x) < int(0.45 * fs):
            continue
        early = x[: max(2, int(0.15 * fs))]
        late = x[int(0.40 * fs) :]
        denom = float(np.nanstd(late))
        if denom > 1e-5:
            vals.append(float(np.nanmax(np.abs(early)) / denom))
    if not vals:
        return None, 0
    return nanmedian(vals), len(vals)


# ═════════════════════════════════════════════════════════════════════
# Metric 8: Target direction change frequency
# ═════════════════════════════════════════════════════════════════════


def direction_change_frequency(signal, fs, windows):
    """Estimate direction-change frequency (Hz) — about 2x oscillation frequency."""
    rates = []
    for win in windows:
        x = signal[win]
        x = x[np.isfinite(x)]
        if len(x) < 8:
            continue
        x = detrend(x, type="linear")
        dx = np.diff(x)
        crossings = np.sum((dx[:-1] * dx[1:]) < 0)
        duration = len(x) / fs
        if duration > 0:
            rates.append(crossings / duration)
    if not rates:
        return None, 0
    return nanmedian(rates), len(rates)


# ═════════════════════════════════════════════════════════════════════
# Theory calculations
# ═════════════════════════════════════════════════════════════════════


def theoretical_metrics(kp, kd, jeff=J_EFF_DEFAULT):
    if not finite(kp) or not finite(kd) or kp <= 0:
        return {}
    wn = math.sqrt(kp / jeff)
    fn = wn / (2.0 * math.pi)
    zeta = kd / (2.0 * math.sqrt(kp * jeff))
    tau_ms = 1000.0 / (zeta * wn) if zeta > 0 else None
    mr = None
    if zeta < 1.0 / math.sqrt(2.0):
        mr = 1.0 / (2.0 * zeta * math.sqrt(1.0 - zeta**2))
    pm_deg = None
    if zeta > 0:
        radicand = max(math.sqrt(1.0 + 4.0 * zeta**4) - 2.0 * zeta**2, 1e-12)
        pm_rad = math.atan2(2.0 * zeta, math.sqrt(radicand))
        pm_deg = math.degrees(pm_rad)
    return {
        "fn_theory_hz": fn,
        "zeta_theory": zeta,
        "tau_theory_ms": tau_ms,
        "Mr_theory": mr,
        "PM_theory_deg": pm_deg,
    }


# ═════════════════════════════════════════════════════════════════════
# Main per-joint computation
# ═════════════════════════════════════════════════════════════════════


def compute_joint_metrics(df, t, dt, fs, filepath, dataset, case_label, kp, kd, side, axis):
    joint = f"{side}_ankle_{axis}_joint"
    pos_col = f"pos_{joint}"
    ref_raw_col = f"pos_des_raw_{joint}"
    ref_lpf_col = f"pos_des_lpf_{joint}"
    contact_col = f"{side}_contact"

    # Determine which reference to use (prefer lpf if available and non-empty)
    ref_col = ref_raw_col
    if ref_lpf_col in df.columns:
        lpf_vals = df[ref_lpf_col].dropna()
        if len(lpf_vals) > 64:
            ref_col = ref_lpf_col

    if pos_col not in df.columns or ref_col not in df.columns or contact_col not in df.columns:
        return None

    out = df[pos_col].to_numpy(dtype=np.float64)
    ref = df[ref_col].to_numpy(dtype=np.float64)
    err = out - ref
    contact = df[contact_col].to_numpy(dtype=np.float64) > 0.5
    td_idx = get_touchdown_indices(df, t, side)

    # Try to get Kp/Kd from actuator if not known
    kp_used, kd_used = kp, kd
    if not finite(kp_used) or not finite(kd_used):
        act_kp, act_kd = get_kpkd_from_actuator(df, side, axis)
        if finite(act_kp):
            kp_used = act_kp
        if finite(act_kd):
            kd_used = act_kd

    ref_valid_ratio = float(np.isfinite(ref).mean())

    # Phase regions
    swing_regions = phase_windows(df, t, side, "swing")
    stance_regions = phase_windows(df, t, side, "stance")
    swing_delay_wins = segment_windows(t, td_idx, SWING_PRE_S, -SWING_POST_S)
    td_wins = segment_windows(t, td_idx, TD_PRE_S, TD_POST_S)

    # ── fn (natural frequency) ──
    fn_swing, fn_swing_prom, n_swing_freq, swing_res = average_window_spectrum(
        err, fs, swing_regions, SWING_FREQ_BAND
    )
    fn_stance, fn_stance_prom, n_stance_freq, stance_res = average_window_spectrum(
        err, fs, td_wins, STANCE_FREQ_BAND
    )
    fn_full, fn_full_prom = full_welch_frequency(err, fs, SWING_FREQ_BAND)

    # ── ζ_BW (half-power bandwidth damping) ──
    f_peak_bw, prom_bw, zeta_bw, bw_bw, fn_equiv_bw = zeta_from_half_power_bandwidth(
        err, fs, (2.0, 30.0)
    )

    # ── ζ_hat (touchdown envelope damping) ──
    zeta_hat, tau_hat, zeta_r2, n_zeta, n_zeta_total, n_zeta_forced = summarize_touchdown_damping(
        err, ref, fs, td_wins, fn_stance
    )

    # ── e_RMS ──
    e_rms_all = rms(err)
    e_rms_swing = rms(err[~contact]) if np.any(~contact) else None
    e_rms_stance = rms(err[contact]) if np.any(contact) else None

    # ── Amplitude gain & self-excitation ──
    amp_gain_swing, amp_gain_swing_std, n_gain_swing, _, n_self_swing = per_cycle_amplitude_gain(
        ref, out, fs, swing_regions
    )
    amp_gain_td, amp_gain_td_std, n_gain_td, _, n_self_td = per_cycle_amplitude_gain(
        ref, out, fs, td_wins
    )

    # ── Delay ──
    delay_med, delay_iqr, delay_corr, n_delay_valid, n_delay_total = summarize_delays(
        ref, out, dt, swing_delay_wins
    )

    # ── Transfer gain ──
    fn_for_h = fn_swing if finite(fn_swing) else fn_full
    h_gain, h_phase, h_coh = transfer_at_frequency(ref, out, fs, fn_for_h)

    # ── Touchdown overshoot ──
    a_peak, n_apeak = touchdown_overshoot(err, fs, td_wins)

    # ── Target direction change frequency ──
    tgt_dir_chg_swing, n_dir_swing = direction_change_frequency(ref, fs, swing_regions)
    tgt_dir_chg_td, n_dir_td = direction_change_frequency(ref, fs, td_wins)
    jnt_dir_chg_swing, _ = direction_change_frequency(out, fs, swing_regions)
    jnt_dir_chg_td, _ = direction_change_frequency(out, fs, td_wins)

    # ── Jeff estimate ──
    jeff_hat = None
    if finite(kp_used) and finite(fn_swing) and fn_swing > 0:
        jeff_hat = kp_used / (2.0 * math.pi * fn_swing) ** 2

    # ── Derived from ζ_hat ──
    mr_hat = None
    pm_hat = None
    if finite(zeta_hat) and zeta_hat < 1.0 / math.sqrt(2.0):
        mr_hat = 1.0 / (2.0 * zeta_hat * math.sqrt(max(1e-9, 1.0 - zeta_hat**2)))
    if finite(zeta_hat) and zeta_hat > 0:
        rad = max(math.sqrt(1.0 + 4.0 * zeta_hat**4) - 2.0 * zeta_hat**2, 1e-12)
        pm_hat = math.degrees(math.atan2(2.0 * zeta_hat, math.sqrt(rad)))

    # ── Theory ──
    theory = theoretical_metrics(kp_used or 0, kd_used or 0)

    # ── Delay phase loss at fn ──
    delay_phase_loss_deg = None
    if finite(delay_med) and finite(fn_swing) and fn_swing > 0:
        delay_phase_loss_deg = 360.0 * fn_swing * abs(delay_med) / 1000.0

    row = {
        "dataset": dataset,
        "case_label": case_label,
        "kp": kp_used,
        "kd": kd_used,
        "file": filepath.name,
        "side": side,
        "axis": axis,
        "reference_col": ref_col,
        "ref_valid_ratio": ref_valid_ratio,
        "duration_s": float(t[-1]),
        "fs_hz": fs,
        "n_td": len(td_idx),
        # fn
        "fn_swing_hz": fn_swing,
        "fn_swing_prominence": fn_swing_prom,
        "fn_swing_n_windows": n_swing_freq,
        "fn_swing_resolution_hz": swing_res,
        "fn_stance_hz": fn_stance,
        "fn_stance_prominence": fn_stance_prom,
        "fn_stance_n_windows": n_stance_freq,
        "fn_full_hz": fn_full,
        "fn_full_prominence": fn_full_prom,
        # zeta
        "zeta_theory": theory.get("zeta_theory"),
        "zeta_hat": zeta_hat,
        "zeta_hat_r2": zeta_r2,
        "zeta_hat_n_events": n_zeta,
        "zeta_hat_n_total": n_zeta_total,
        "zeta_hat_n_forced": n_zeta_forced,
        "zeta_BW": zeta_bw,
        "zeta_BW_peak_hz": f_peak_bw,
        "zeta_BW_prominence": prom_bw,
        "zeta_BW_bandwidth_hz": bw_bw,
        "fn_equiv_BW_hz": fn_equiv_bw,
        # Mr & PM
        "Mr_theory": theory.get("Mr_theory"),
        "Mr_hat": mr_hat,
        "PM_theory_deg": theory.get("PM_theory_deg"),
        "PM_hat_deg": pm_hat,
        # tau
        "tau_theory_ms": theory.get("tau_theory_ms"),
        "tau_hat_ms": tau_hat,
        # fn theory
        "fn_theory_hz": theory.get("fn_theory_hz"),
        # error
        "e_rms_rad": e_rms_all,
        "e_rms_swing_rad": e_rms_swing,
        "e_rms_stance_rad": e_rms_stance,
        # amplitude gain
        "amplitude_gain_swing_median": amp_gain_swing,
        "amplitude_gain_swing_std": amp_gain_swing_std,
        "amplitude_gain_swing_n_valid": n_gain_swing,
        "amplitude_gain_td_median": amp_gain_td,
        "amplitude_gain_td_std": amp_gain_td_std,
        "amplitude_gain_td_n_valid": n_gain_td,
        # self-excitation
        "n_self_excite_swing": n_self_swing,
        "n_self_excite_td": n_self_td,
        # delay
        "delay_ms_median": delay_med,
        "delay_ms_iqr": delay_iqr,
        "delay_corr_median": delay_corr,
        "delay_n_valid": n_delay_valid,
        "delay_n_total": n_delay_total,
        "delay_phase_loss_at_fn_deg": delay_phase_loss_deg,
        # transfer
        "transfer_gain": h_gain,
        "transfer_phase_deg": h_phase,
        "transfer_coherence": h_coh,
        # touchdown overshoot
        "A_peak": a_peak,
        "A_peak_n_events": n_apeak,
        # direction change frequency
        "target_dir_chg_swing_hz": tgt_dir_chg_swing,
        "target_dir_chg_td_hz": tgt_dir_chg_td,
        "joint_dir_chg_swing_hz": jnt_dir_chg_swing,
        "joint_dir_chg_td_hz": jnt_dir_chg_td,
        # Jeff
        "jeff_hat": jeff_hat,
    }
    return row


# ═════════════════════════════════════════════════════════════════════
# Quality assessment
# ═════════════════════════════════════════════════════════════════════


def assess_quality(row):
    flags = []
    if (row.get("ref_valid_ratio") or 0) < 0.5:
        flags.append("empty_ref")
    if (row.get("fn_swing_prominence") or 0) < 1.5:
        flags.append("weak_fn_swing")
    if (row.get("zeta_hat_r2") or 0) < 0.35:
        flags.append("low_zeta_r2")
    if (row.get("zeta_hat_n_events") or 0) < 3:
        flags.append("few_zeta_events")
    if (row.get("transfer_coherence") or 0) < 0.35:
        flags.append("low_coherence")
    if (row.get("delay_n_valid") or 0) < 3:
        flags.append("few_delay")
    if (row.get("zeta_BW_prominence") or 0) < 4.0:
        flags.append("weak_zeta_BW_peak")
    return "ok" if not flags else ";".join(flags)


# ═════════════════════════════════════════════════════════════════════
# Damping risk grade
# ═════════════════════════════════════════════════════════════════════


def damping_risk_grade(zeta):
    """Grade the underdamping risk based on ζ value."""
    if not finite(zeta):
        return "unknown"
    if zeta < 0.1:
        return "severe"
    if zeta < 0.2:
        return "high"
    if zeta < 0.4:
        return "moderate"
    if zeta < 0.7:
        return "low"
    return "safe"


# ═════════════════════════════════════════════════════════════════════
# Left-right asymmetry
# ═════════════════════════════════════════════════════════════════════


def add_delta_lr(rows):
    grouped = {}
    for r in rows:
        key = (r["dataset"], r["case_label"], r["axis"], r["file"])
        grouped.setdefault(key, {})[r["side"]] = r
    for lr in grouped.values():
        left = lr.get("left")
        right = lr.get("right")
        if not left or not right:
            continue
        for metric in [
            "e_rms_rad",
            "e_rms_swing_rad",
            "e_rms_stance_rad",
            "fn_swing_hz",
            "zeta_hat",
            "amplitude_gain_swing_median",
            "delay_ms_median",
        ]:
            lv = left.get(metric)
            rv = right.get(metric)
            if finite(lv) and finite(rv) and abs(rv) > 1e-12:
                left[f"DeltaLR_{metric}"] = lv / rv
                right[f"DeltaLR_{metric}"] = lv / rv
            else:
                left[f"DeltaLR_{metric}"] = None
                right[f"DeltaLR_{metric}"] = None


# ═════════════════════════════════════════════════════════════════════
# Reports
# ═════════════════════════════════════════════════════════════════════


def build_summary(detail_rows):
    numeric_cols = [
        "ref_valid_ratio", "e_rms_rad", "e_rms_swing_rad", "e_rms_stance_rad",
        "fn_swing_hz", "fn_stance_hz", "fn_full_hz",
        "zeta_theory", "zeta_hat", "zeta_hat_r2", "zeta_BW",
        "Mr_theory", "Mr_hat", "PM_theory_deg", "PM_hat_deg",
        "tau_theory_ms", "tau_hat_ms", "fn_theory_hz",
        "amplitude_gain_swing_median", "amplitude_gain_td_median",
        "delay_ms_median", "delay_phase_loss_at_fn_deg",
        "transfer_gain", "transfer_coherence",
        "A_peak", "jeff_hat",
    ]
    count_cols = [
        "n_td", "n_self_excite_swing", "n_self_excite_td",
        "delay_n_valid", "zeta_hat_n_events",
    ]
    df = pd.DataFrame(detail_rows)
    agg = {}
    for col in numeric_cols:
        if col in df.columns:
            agg[col] = "mean"
    for col in count_cols:
        if col in df.columns:
            agg[col] = "sum"
    grp = df.groupby(["dataset", "case_label", "kp", "kd", "axis"], as_index=False)
    summary = grp.agg(agg)
    # Add risk grade
    zeta_col = "zeta_hat" if "zeta_hat" in summary.columns else "zeta_theory"
    if zeta_col in summary.columns:
        summary["damping_risk"] = summary[zeta_col].apply(damping_risk_grade)
    for c in summary.columns:
        if pd.api.types.is_float_dtype(summary[c]):
            summary[c] = summary[c].round(5)
    return summary


def write_markdown_report(detail_rows, summary_df):
    """Generate a comprehensive markdown report."""
    df = pd.DataFrame(detail_rows)

    # ── Helper for tables ──
    def md_table(data, cols, max_rows=None):
        rows = data[:max_rows] if max_rows else data
        header = "| " + " | ".join(cols) + " |"
        sep = "|" + "|".join("---" for _ in cols) + "|"
        lines = [header, sep]
        for _, row in rows.iterrows():
            cells = []
            for c in cols:
                v = row.get(c) if c in row.index else ""
                if isinstance(v, float) and not math.isnan(v):
                    cells.append(f"{v:.4f}")
                elif isinstance(v, float):
                    cells.append("")
                else:
                    cells.append(str(v) if v is not None else "")
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    # ── Key metrics columns for display ──
    key_cols = [
        "dataset", "case_label", "side", "axis",
        "fn_swing_hz", "fn_stance_hz", "zeta_theory", "zeta_hat", "zeta_BW",
        "Mr_theory", "PM_theory_deg", "tau_theory_ms", "tau_hat_ms",
        "e_rms_rad", "amplitude_gain_swing_median", "delay_ms_median",
        "A_peak", "n_self_excite_swing", "n_self_excite_td",
        "transfer_coherence", "quality",
    ]

    # Build quality column
    df["quality"] = df.apply(assess_quality, axis=1)
    df["damping_risk"] = df["zeta_theory"].apply(damping_risk_grade)

    # Filter to present columns
    present_cols = [c for c in key_cols if c in df.columns]

    # ── 1. Executive summary ──
    real_df = df[df["dataset"] == "real"]
    sim_df = df[df["dataset"] == "sim"]
    n_real_files = real_df["file"].nunique()
    n_sim_files = sim_df["file"].nunique()

    report = f"""# 踝关节欠阻尼/谐振分析报告

> 自动生成 · {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}
> 真机数据: {n_real_files} 个文件  ·  仿真数据: {n_sim_files} 个文件
> 参考: `ankle_damping_analysis_methodology.md`

---

## 一、执行摘要

### 1.1 数据概览

| | 真机 | 仿真 |
|---|---|---|
| 文件数 | {n_real_files} | {n_sim_files} |
| 关节 | ankle_pitch / ankle_roll (左+右) | ankle_pitch / ankle_roll (左+右) |

### 1.2 阻尼风险评估

"""
    # Risk summary
    for dataset_name, sub_df in [("real", real_df), ("sim", sim_df)]:
        if sub_df.empty:
            continue
        report += f"\n**{dataset_name}** 阻尼风险分布 (基于 ζ_theory):\n\n"
        for risk in ["severe", "high", "moderate", "low", "safe", "unknown"]:
            count = (sub_df["damping_risk"] == risk).sum()
            if count > 0:
                emoji = {"severe": "🔴", "high": "🟠", "moderate": "🟡", "low": "🟢", "safe": "✅", "unknown": "⬜"}
                label = {"severe": "严重 ζ<0.1", "high": "高风险 ζ<0.2", "moderate": "中等 ζ<0.4",
                         "low": "低风险 ζ<0.7", "safe": "安全 ζ≥0.7", "unknown": "未知"}
                report += f"- {emoji.get(risk, '⬜')} {label.get(risk, risk)}: {count} 行\n"

    # ── 2. Per-case detail ──
    report += f"""
---

## 二、详细指标 (按 Case × 关节)

"""
    for case_label in df["case_label"].unique():
        case_data = df[df["case_label"] == case_label]
        report += f"\n### {case_label}\n\n"
        report += md_table(case_data, present_cols) + "\n"

    # ── 3. Summary ──
    report += f"""
---

## 三、汇总 (left/right 平均)

"""
    sum_cols = [
        "dataset", "case_label", "axis",
        "fn_swing_hz", "fn_stance_hz", "zeta_theory", "zeta_hat", "zeta_BW",
        "Mr_theory", "PM_theory_deg", "tau_theory_ms",
        "e_rms_rad", "amplitude_gain_swing_median", "delay_ms_median",
        "A_peak", "n_self_excite_swing", "damping_risk",
    ]
    sum_present = [c for c in sum_cols if c in summary_df.columns]
    report += md_table(summary_df, sum_present) + "\n"

    # ── 4. Self-excitation analysis ──
    report += f"""
---

## 四、自激检测

`n_self_excite > 0` 表示该文件中检测到 `joint_vel > target_vel` 的摆动周期，关口有额外能量注入。

"""
    se_data = df[(df["n_self_excite_swing"] > 0) | (df["n_self_excite_td"] > 0)]
    if not se_data.empty:
        se_cols = ["dataset", "case_label", "side", "axis",
                    "n_self_excite_swing", "n_self_excite_td",
                    "amplitude_gain_swing_median", "delay_ms_median", "damping_risk"]
        se_present = [c for c in se_cols if c in se_data.columns]
        report += md_table(se_data, se_present) + "\n"
    else:
        report += "_未检测到自激。_\n\n"

    # ── 5. Delay analysis ──
    report += f"""
---

## 五、延迟分析

"""
    delay_cols = ["dataset", "case_label", "side", "axis",
                   "delay_ms_median", "delay_ms_iqr", "delay_corr_median",
                   "delay_n_valid", "delay_n_total",
                   "delay_phase_loss_at_fn_deg", "fn_swing_hz"]
    delay_present = [c for c in delay_cols if c in df.columns]
    report += md_table(df, delay_present) + "\n"

    # ── 6. Left-right asymmetry ──
    report += f"""
---

## 六、左右不对称

"""
    lr_rows = [r for r in detail_rows if r.get("DeltaLR_e_rms_rad") is not None]
    if lr_rows:
        lr_cols = ["dataset", "case_label", "side", "axis",
                    "e_rms_rad", "DeltaLR_e_rms_rad",
                    "DeltaLR_fn_swing_hz", "DeltaLR_zeta_hat"]
        lr_present = [c for c in lr_cols if c in lr_rows[0]]
        lr_df = pd.DataFrame(lr_rows)[lr_present].drop_duplicates(
            subset=["dataset", "case_label", "axis"]
        )
        report += md_table(lr_df, lr_present) + "\n"
    else:
        report += "_无左右配对数据。_\n\n"

    # ── 7. Interpretation guide ──
    report += f"""
---

## 七、指标解读速查

| 指标 | 含义 | 良好 | 警告 | 危险 |
|------|------|------|------|------|
| `zeta_theory` / `zeta_hat` | 阻尼比 | > 0.4 | 0.2–0.4 | < 0.2 |
| `Mr_theory` | 谐振峰增益 | < 1.3 | 1.3–3.0 | > 3.0 |
| `PM_theory_deg` | 相位裕度 | > 40° | 20°–40° | < 20° |
| `tau_theory_ms` | 衰减时间常数 | < 150 | 150–300 | > 300 |
| `amplitude_gain` | 关节/目标幅值比 | 0.8–1.2 | 1.2–1.5 | > 1.5 |
| `n_self_excite` | 自激周期数 | 0 | 1–2 | ≥ 3 |
| `delay_ms` | 控制延迟 | < 30 | 30–60 | > 60 |
| `A_peak` | 接地过冲倍数 | < 1.5 | 1.5–2.5 | > 2.5 |
| `transfer_coherence` | 频域可信度 | > 0.5 | 0.35–0.5 | < 0.35 |

### 诊断矩阵

| 现象 | 指标组合 | 诊断 |
|------|----------|------|
| 持续高频振荡 | ζ < 0.2 + Mr > 2.5 + τ > 300ms | 严重欠阻尼 |
| 振荡频率 ~3 Hz | fn ≈ 3 Hz, 与步态 1.8 Hz 无关 | 系统固有谐振 |
| 接地后振铃 | fn_stance ≫ fn_swing + A_peak > 2 | 支撑相频率突变+谐振放大 |
| 关节超调 | amplitude_gain > 1 + 自激点 > 0 | 负阻尼/自激 |
| 延迟问题 | τ_d > 50ms + phase_loss > PM | 延迟透支相位裕度 |
| sim 不抖 real 抖 | real 有自激 + sim gain < 0.7 | sim 缺乏真实弹性/冲击 |

---

## 八、输出文件

| 文件 | 路径 |
|------|------|
| Detail CSV | `{DETAIL_CSV.relative_to(REPO_ROOT)}` |
| Summary CSV | `{SUMMARY_CSV.relative_to(REPO_ROOT)}` |
| Report MD | `{REPORT_PATH.relative_to(REPO_ROOT)}` |

> 方法论参考: `real2sim/ankle_damping_analysis_methodology.md`
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


# ═════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════


def main():
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    sim_files, real_files = discover_files()
    all_files = [(f, "sim") for f in sim_files] + [(f, "real") for f in real_files]

    print(f"Found {len(sim_files)} sim files, {len(real_files)} real files")
    print(f"Analyzing {len(all_files)} files × {len(ANKLE_JOINTS)} joints...")

    detail_rows = []
    for filepath, dataset in all_files:
        case_label, kp, kd = infer_case(filepath, dataset)
        print(f"  [{dataset}] {case_label}  {filepath.name}")
        try:
            df, t, dt, fs = load_file(filepath)
        except Exception as e:
            print(f"    SKIP: load error {e}")
            continue

        for joint in ANKLE_JOINTS:
            parts = joint.split("_")
            side = parts[0]  # left or right
            axis = "pitch" if "pitch" in joint else "roll"
            try:
                row = compute_joint_metrics(
                    df, t, dt, fs, filepath, dataset, case_label, kp, kd, side, axis
                )
                if row:
                    detail_rows.append(row)
            except Exception as e:
                print(f"    ERROR {joint}: {e}")

    add_delta_lr(detail_rows)

    # Write detail CSV
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    detail_df = pd.DataFrame(detail_rows)
    for c in detail_df.columns:
        if pd.api.types.is_float_dtype(detail_df[c]):
            detail_df[c] = detail_df[c].round(5)
    detail_df.to_csv(DETAIL_CSV, index=False)
    print(f"\nDetail CSV: {DETAIL_CSV}  ({len(detail_df)} rows)")

    # Write summary CSV
    summary_df = build_summary(detail_rows)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    print(f"Summary CSV: {SUMMARY_CSV}  ({len(summary_df)} rows)")

    # Write markdown report
    write_markdown_report(detail_rows, summary_df)
    print(f"Report: {REPORT_PATH}")

    # Quick console summary
    print("\n" + "=" * 70)
    print("QUICK SUMMARY — damping risk by case:")
    print("=" * 70)
    key_cols = ["dataset", "case_label", "axis", "zeta_theory", "Mr_theory",
                "PM_theory_deg", "tau_theory_ms", "damping_risk"]
    for c in key_cols:
        if c not in summary_df.columns:
            continue
    print(summary_df[[c for c in key_cols if c in summary_df.columns]].to_string(index=False))


if __name__ == "__main__":
    main()
