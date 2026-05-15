#!/usr/bin/env python3
"""
踝关节欠阻尼/谐振分析脚本
===========================
基于 `plans/踝关节阻尼谐振分析方法论.md`，从真机/仿真行走日志中
自动计算各级指标，输出 detail CSV / summary CSV / markdown 报告。

用法: python ankle_damping_analysis.py

数据源:
  - 仿真: test_logs/data_csv/sim/t27*.csv
  - 真机: test_logs/data_csv/t27*.csv

输出:
  - sim2real/walk_data_analysis/table/ankle_damping/ankle_damping_detail.csv
  - sim2real/walk_data_analysis/table/ankle_damping/ankle_damping_summary.csv
  - sim2real/walk_data_analysis/reports/踝关节阻尼分析报告.md
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
ANALYSIS_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
DATA_DIR = REPO_ROOT / "test_logs" / "data_csv"
SIM_DIR = DATA_DIR / "sim"
TABLE_DIR = ANALYSIS_DIR / "table" / "ankle_damping"
REPORT_PATH = ANALYSIS_DIR / "reports" / "踝关节阻尼分析报告.md"
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

# ─── Swing-phase FRF constants (v5) ──────────────────────────────────
SWING_BUF_S = 0.05       # trim buffer at each end of a swing segment
SWING_MIN_S = 0.15       # minimum valid swing segment length after trimming
SWING_NPERSEG_S = 2.0    # Welch nperseg (seconds) for swing-FRF segments
SWING_COH_MIN = 0.30     # coherence threshold for reliable G_fn_sw conclusion (v5.2: 0.40→0.30)
N_SW_MIN      = 5         # minimum swing segments for reliable swing-phase FRF

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
#
# CRITICAL: The log-decrement method requires FREE DECAY — the system
# must be oscillating under its own dynamics after a single impulse,
# WITHOUT the target continuing to move. In walking data, the target
# (pos_des) keeps changing through the touchdown window, so the error
# is a TRACKING RESIDUAL, not a free oscillation. Applying log-decrement
# to tracking residuals produces spurious ζ values (often accidentally
# matching ζ_theory because the gait period ≈ 1/fn).
#
# Fix: Check if target is approximately stationary during the decay
# window. If target change > DES_STATIONARY_THRESHOLD_RAD, mark the
# event as "forced" and reject it.
# ═════════════════════════════════════════════════════════════════════

# Maximum target (des) change within the decay window [40ms, 800ms]
# for an event to qualify as "free decay" rather than "forced tracking".
DES_STATIONARY_THRESHOLD_RAD = 0.2


def touchdown_damping_one_event(err, des, fs, fn_hz=None):
    """
    Estimate ζ from a single touchdown event's error envelope decay.

    Parameters
    ----------
    err : np.ndarray — pos - des, within the touchdown window
    des : np.ndarray — target position, same length as err
    fs : float — sample rate
    fn_hz : float | None — natural frequency estimate

    Returns
    -------
    zeta : float | None
    tau_ms : float | None
    alpha : float | None
    r2 : float | None
    is_forced : bool — True if rejected because target was non-stationary
    """
    if len(err) < int(0.35 * fs):
        return None, None, None, None, False

    # ── Prerequisite check: is the target stationary? ──
    # The log-decrement method requires FREE DECAY. If the target is
    # still moving during the decay window, the error is a tracking
    # residual, not a damped oscillation.
    decay_start = int(0.04 * fs)
    decay_stop = min(len(des), int(0.80 * fs))
    if decay_stop - decay_start < max(16, int(0.25 * fs)):
        return None, None, None, None, False
    des_decay = np.asarray(des[decay_start:decay_stop], dtype=np.float64)
    des_decay = des_decay[np.isfinite(des_decay)]
    if len(des_decay) < 8:
        return None, None, None, None, False
    des_range = float(np.nanmax(des_decay) - np.nanmin(des_decay))
    if des_range > DES_STATIONARY_THRESHOLD_RAD:
        # Target keeps moving → error is forced tracking, not free decay
        return None, None, None, None, True

    x = np.asarray(err, dtype=np.float64)
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
    n_free = 0
    for win in windows:
        n_total += 1
        z, tau, _, r2, is_forced = touchdown_damping_one_event(
            err[win], des[win], fs, fn_hz
        )
        if is_forced:
            n_forced += 1
            continue
        n_free += 1
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
    _, pyx = csd(x, y, fs=fs, nperseg=nperseg, noverlap=nperseg // 2, window="hann")
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
# Metric 1b: FRF-based fn and ζ estimation (v4 methodology)
#
# Fixes three defects in walking-data damping estimation:
#   Defect 1: fn from error PSD → fix: fn from FRF phase ∠H(fn)=-90°
#   Defect 2: ζ from half-power BW (underdamped only) → fix: ζ=1/(2·|H(fn)|)
#   Defect 3: csd(jnt, des) wrong direction → fix: csd(des, jnt) = G_CL·Sxx
#
# Key property: |H(jωn)| = 1/(2ζ) holds for ANY ζ (under/critical/over).
#   |H(fn)| > 0.5 → ζ < 1.0 → underdamped
#   |H(fn)| = 0.5 → ζ = 1.0 → critically damped
#   |H(fn)| < 0.5 → ζ > 1.0 → overdamped
# ═════════════════════════════════════════════════════════════════════

MAX_DELAY_MS = 150  # max credible delay for FRF phase compensation


def compute_frf(jnt, des, fs, nperseg_s=4.0):
    """
    Forward FRF: H(f) = G_CL(f), input=des, output=jnt.

    Uses csd(des, jnt) = E[des*·jnt] = G_CL·Sxx_des  (correct direction)
    Returns (freq, H_complex, coherence).
    """
    jnt_c = np.where(np.isnan(jnt), 0.0, jnt)
    des_c = np.where(np.isnan(des), 0.0, des)
    nperseg = min(int(nperseg_s * fs), len(jnt_c) // 2)
    if nperseg < 32:
        return None, None, None
    f, Sxy = csd(des_c, jnt_c, fs=fs, nperseg=nperseg,
                 noverlap=nperseg // 2, window="hann")
    _, Sxx = welch(des_c, fs=fs, nperseg=nperseg,
                   noverlap=nperseg // 2, window="hann")
    _, Syy = welch(jnt_c, fs=fs, nperseg=nperseg,
                   noverlap=nperseg // 2, window="hann")
    H = np.zeros(len(f), dtype=complex)
    valid = Sxx > 1e-14
    H[valid] = Sxy[valid] / Sxx[valid]
    denom = np.maximum(Sxx * Syy, 1e-20)
    coh = np.abs(Sxy) ** 2 / denom
    return f, H, coh


def detect_liftoff(df, t, side, min_gap=MIN_TD_GAP_S):
    """
    Detect liftoff events: contact signal falling edges (1→0), debounced.

    Returns (lo_times, lo_idx) — parallel arrays of liftoff timestamps and indices.
    """
    contact_col = f"{side}_contact"
    if contact_col not in df.columns:
        return np.array([], dtype=np.float64), np.array([], dtype=int)
    contact = np.nan_to_num(df[contact_col].to_numpy(dtype=np.float64), nan=0.0).astype(int)
    edges = np.where(np.diff(contact) < 0)[0] + 1  # falling edge indices
    if len(edges) == 0:
        return np.array([], dtype=np.float64), np.array([], dtype=int)
    # Debounce: require at least min_gap between consecutive liftoffs
    kept = [int(edges[0])]
    for idx in edges[1:]:
        if t[idx] - t[kept[-1]] >= min_gap:
            kept.append(int(idx))
    lo_idx = np.array(kept, dtype=int)
    lo_times = t[lo_idx]
    return lo_times, lo_idx


def compute_swing_frf(jnt, des, t, fs, td_times, lo_times, buf_s=SWING_BUF_S,
                      min_len_s=SWING_MIN_S, nperseg_s=SWING_NPERSEG_S,
                      freq_res_hz=0.25):
    """
    Swing-phase separated FRF (v5 primary damping indicator).

    For each liftoff→touchdown pair, accumulate segmental cross/auto spectra
    onto a fixed fine-resolution frequency grid (zero-padded FFT), then compute:
      H_sw  = ΣSxy / ΣSxx       (H1 averaged transfer function estimator)
      coh_sw = |ΣSxy|² / (ΣSxx·ΣSyy)

    Parameters
    ----------
    jnt          : joint position array (output)
    des          : desired position array (input/reference)
    t            : time array
    fs           : sample rate
    td_times     : touchdown timestamps
    lo_times     : liftoff timestamps
    buf_s        : trim buffer at each end of swing segment (default 0.05 s)
    min_len_s    : minimum valid swing segment after trimming (default 0.15 s)
    nperseg_s    : max Welch nperseg in seconds (default 2.0 s)
    freq_res_hz  : target frequency resolution via zero-padding (default 0.25 Hz)

    Returns
    -------
    f_out  : frequency array (fine grid, 0 to fs/2, step ≈ freq_res_hz)
    H_sw   : complex H at each frequency
    coh_sw : coherence array
    n_segs : number of swing segments accumulated
    """
    if len(lo_times) == 0 or len(td_times) == 0:
        return None, None, None, 0

    # Fixed fine-resolution frequency grid via zero-padding
    nfft = max(64, int(round(fs / freq_res_hz)))
    f_ref = np.fft.rfftfreq(nfft, 1.0 / fs)
    Sxy_sum = np.zeros(len(f_ref), dtype=complex)
    Sxx_sum = np.zeros(len(f_ref), dtype=np.float64)
    Syy_sum = np.zeros(len(f_ref), dtype=np.float64)
    n_segs = 0

    # nperseg for Welch sub-windowing (limits per-segment Welch window size)
    nperseg_max = max(8, min(int(nperseg_s * fs), nfft))

    # Pair each liftoff with the next touchdown
    for lo_t in lo_times:
        future_td = td_times[td_times > lo_t]
        if len(future_td) == 0:
            continue
        td_t = float(future_td[0])

        # Apply buffer
        seg_start = lo_t + buf_s
        seg_end = td_t - buf_s
        if seg_end - seg_start < min_len_s:
            continue

        mask = (t >= seg_start) & (t <= seg_end)
        n_samp = int(mask.sum())
        if n_samp < 8:
            continue

        seg_jnt = np.where(np.isnan(jnt[mask]), 0.0, jnt[mask])
        seg_des = np.where(np.isnan(des[mask]), 0.0, des[mask])
        seg_jnt = detrend(seg_jnt, type="constant")
        seg_des = detrend(seg_des, type="constant")

        # Use whole segment as one window (no sub-windowing for short segs),
        # zero-pad to nfft for fine frequency resolution
        nperseg_use = min(nperseg_max, n_samp)

        try:
            f_seg, Sxy = csd(seg_des, seg_jnt, fs=fs,
                             nperseg=nperseg_use, nfft=nfft,
                             noverlap=nperseg_use // 2, window="hann")
            _, Sxx = welch(seg_des, fs=fs,
                           nperseg=nperseg_use, nfft=nfft,
                           noverlap=nperseg_use // 2, window="hann")
            _, Syy = welch(seg_jnt, fs=fs,
                           nperseg=nperseg_use, nfft=nfft,
                           noverlap=nperseg_use // 2, window="hann")
        except Exception:
            continue

        # Because nfft is fixed, f_seg should equal f_ref (same rfftfreq)
        if len(f_seg) == len(f_ref):
            Sxy_sum += Sxy
            Sxx_sum += Sxx
            Syy_sum += Syy
        else:
            # Interpolate as fallback
            Sxy_sum += np.interp(f_ref, f_seg, np.real(Sxy)) + 1j * np.interp(f_ref, f_seg, np.imag(Sxy))
            Sxx_sum += np.interp(f_ref, f_seg, Sxx)
            Syy_sum += np.interp(f_ref, f_seg, Syy)
        n_segs += 1

    if n_segs == 0:
        return None, None, None, 0

    # H_sw = ΣSxy / ΣSxx
    H_sw = np.zeros(len(f_ref), dtype=complex)
    valid = Sxx_sum > 1e-20
    H_sw[valid] = Sxy_sum[valid] / Sxx_sum[valid]

    # coh_sw = |ΣSxy|² / (ΣSxx · ΣSyy)
    denom = np.maximum(Sxx_sum * Syy_sum, 1e-30)
    coh_sw = np.abs(Sxy_sum) ** 2 / denom
    coh_sw = np.clip(coh_sw, 0.0, 1.0)

    return f_ref, H_sw, coh_sw, n_segs


def estimate_fn_frf(f, H, coh, fn_th, delay_ms, search_bw=2.0, coh_min=0.10):
    """
    Estimate natural frequency from FRF phase = -90° (delay compensated).

    Theory: ∠G_CL(jωn) = -90° for any ζ (since H(jωn) = 1/(2jζ)).
    Steps:
      1. Compensate delay: H_comp = H · exp(+jωτ)
      2. Find frequency where phase is closest to -90° in [fn_th ± search_bw]
      3. Check coherence at that point.
    """
    if f is None or H is None or not finite(fn_th):
        return None, None
    tau = np.clip(delay_ms if finite(delay_ms) else 0.0,
                  0, MAX_DELAY_MS) / 1000.0
    H_comp = H * np.exp(1j * 2 * np.pi * f * tau)
    flo = max(0.5, fn_th - search_bw)
    fhi = min(f[-1] - 0.1, fn_th + search_bw)
    mask = (f >= flo) & (f <= fhi)
    if not mask.any():
        return None, None
    phase_deg = np.angle(H_comp[mask], deg=True)
    f_sub = f[mask]
    coh_sub = coh[mask] if coh is not None else np.ones(mask.sum())
    idx = np.argmin(np.abs(phase_deg + 90.0))
    fn_frf = float(f_sub[idx])
    coh_fn = float(coh_sub[idx])
    if coh_fn < coh_min:
        fn_frf = None
    return fn_frf, coh_fn


def estimate_zeta_frf(f, H, coh, fn, bw_hz=0.75, coh_min=0.10):
    """
    Estimate ζ from |H(fn)| = 1/(2ζ). Works for ANY ζ.

    Returns (G_fn, zeta_frf, coherence_at_fn).
      G_fn > 1.0 → ζ < 0.5 → underdamped (resonance amplification)
      G_fn = 0.5 → ζ = 1.0 → critically damped
      G_fn < 0.5 → ζ > 1.0 → overdamped (signal attenuated)
    """
    if f is None or H is None or not finite(fn):
        return None, None, None
    mask = (f >= fn - bw_hz / 2) & (f <= fn + bw_hz / 2)
    if not mask.any():
        return None, None, None
    H_mag = np.abs(H[mask])
    coh_vals = coh[mask] if coh is not None else np.ones(mask.sum())
    weights = np.maximum(coh_vals, 1e-3)
    G_fn = float(np.average(H_mag, weights=weights))
    coh_mean = float(np.mean(coh_vals))
    if G_fn < 1e-6:
        return G_fn, None, coh_mean
    zeta_frf = float(np.clip(1.0 / (2.0 * G_fn), 0.01, 10.0))
    return G_fn, zeta_frf, coh_mean


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
# Damping status classification (v5 decision tree)
# ═════════════════════════════════════════════════════════════════════


def classify_damping_status(G_fn_sw, coh_sw, n_swing_segs=None, amp_gain_swing=None):
    """
    Classify damping status per v5.2 methodology decision tree.

    Priority:
      1. If coh_sw >= SWING_COH_MIN AND n_sw >= N_SW_MIN → use G_fn_sw thresholds
      2. Else → use amp_gain_swing as primary time-domain judgment
      3. Else → unknown

    Returns one of: "underdamped" / "weak_underdamped" / "critical" /
                    "overdamped" / "underdamped_timedomain" / "overdamped_timedomain" / "unknown"
    """
    # FRF reliable: coh达标 AND 片段足够
    n_sw_ok = (n_swing_segs is not None and n_swing_segs >= N_SW_MIN)
    if finite(G_fn_sw) and finite(coh_sw) and coh_sw >= SWING_COH_MIN and n_sw_ok:
        if G_fn_sw > 1.5:
            return "underdamped"
        if G_fn_sw >= 1.0:
            return "weak_underdamped"
        if G_fn_sw >= 0.5:
            return "critical"
        return "overdamped"
    # FRF not reliable — time-domain primary judgment (v5.2: upgraded from fallback)
    if finite(amp_gain_swing):
        if amp_gain_swing > 1.5:
            return "underdamped_timedomain"    # strong evidence
        if amp_gain_swing > 1.0:
            return "weak_underdamped_timedomain"
        return "overdamped_timedomain"
    return "unknown"


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

    # ── Theory computation (needed for fn_th in FRF evaluation) ──
    theory = theoretical_metrics(kp_used or 0, kd_used or 0)
    fn_theory = theory.get("fn_theory_hz")

    # ── Delay ── (must be computed BEFORE FRF so safe_delay is available)
    delay_med, delay_iqr, delay_corr, n_delay_valid, n_delay_total = summarize_delays(
        ref, out, dt, swing_delay_wins
    )

    # ── Full-gait FRF (v4 reference: csd(des, jnt), ∠H=-90°, ζ=1/(2G_fn)) ──
    f_frf, H_frf, coh_frf = compute_frf(out, ref, fs)
    # fn from FRF phase = -90° (delay compensated)
    safe_delay = delay_med if (finite(delay_med) and abs(delay_med) <= MAX_DELAY_MS) else 0.0
    fn_frf, coh_at_fn = estimate_fn_frf(f_frf, H_frf, coh_frf, fn_theory, safe_delay)
    # ζ = 1/(2·|H(fn_th)|) — works for any ζ (full-gait, reference)
    G_fn, zeta_frf, coh_at_fn2 = estimate_zeta_frf(f_frf, H_frf, coh_frf, fn_theory)
    if coh_at_fn2 is not None and coh_at_fn2 > (coh_at_fn or 0):
        coh_at_fn = coh_at_fn2

    # ── Swing-phase separated FRF (v5 PRIMARY metric) ──
    lo_times, lo_idx = detect_liftoff(df, t, side)
    td_times = t[td_idx] if len(td_idx) > 0 else np.array([], dtype=np.float64)
    f_sw, H_sw, coh_sw, n_swing_segs = compute_swing_frf(
        out, ref, t, fs, td_times, lo_times
    )
    # G_fn_sw = |H_sw(fn_th)| using coherence-weighted average
    frf_gain_at_fn_swing, zeta_frf_swing, frf_coherence_swing = estimate_zeta_frf(
        f_sw, H_sw, coh_sw, fn_theory
    )
    # fn from swing FRF phase = -90° (delay compensated)
    fn_frf_swing, _ = estimate_fn_frf(f_sw, H_sw, coh_sw, fn_theory, safe_delay)

    # ── Damping status placeholder (re-classified after amp_gain computed) ──
    damping_status = "unknown"

    # ── Derived from ζ_frf ──
    tau_frf = 1000.0 / (zeta_frf * math.sqrt(kp_used / J_EFF_DEFAULT)) if finite(zeta_frf) and finite(kp_used) and zeta_frf > 0 else None
    pm_frf = 100.0 * zeta_frf if finite(zeta_frf) else None

    # ── ζ_hat (touchdown envelope damping, reference only — usually None for walking data) ──
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

    # Re-classify damping_status now that amp_gain_swing is available (v5.2: +n_swing_segs)
    damping_status = classify_damping_status(
        frf_gain_at_fn_swing, frf_coherence_swing, n_swing_segs, amp_gain_swing
    )

    # ── Transfer gain (old method, kept for backward reference) ──
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

    # ── Theory (already computed above) ──

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
        # ── fn (PSD + FRF) ──
        # ── v5 primary damping indicators (swing-phase separated FRF) ──
        "frf_gain_at_fn_swing": frf_gain_at_fn_swing,   # G_fn_sw: |H_sw(fn_th)|
        "frf_coherence_swing": frf_coherence_swing,      # coh_sw at fn_th
        "zeta_frf_swing": zeta_frf_swing,                # ζ_sw = 1/(2·G_fn_sw)
        "fn_frf_swing_hz": fn_frf_swing,                 # fn from swing FRF phase=-90°
        "n_swing_segs": n_swing_segs,                    # number of swing segments used
        "damping_status": damping_status,                 # v5 classification
        # ── unified field name aliases (per plan naming convention) ──
        "tracking_lag_ms": delay_med,                    # alias for delay_ms_median
        "xcorr_coeff": delay_corr,                       # alias for delay_corr_median
        "range_gain_phase": amp_gain_swing,              # alias for amplitude_gain_swing_median
        # ── fn (PSD + FRF) ──
        "fn_swing_hz": fn_swing,
        "fn_swing_prominence": fn_swing_prom,
        "fn_swing_n_windows": n_swing_freq,
        "fn_swing_resolution_hz": swing_res,
        "fn_stance_hz": fn_stance,
        "fn_stance_prominence": fn_stance_prom,
        "fn_frf_hz": fn_frf,          # v4: FRF phase = -90° (delay compensated)
        # ── ζ (theory + FRF + log-decrement reference) ──
        "zeta_theory": theory.get("zeta_theory"),
        "G_fn": G_fn,                  # v4: |H(fn_th)| — direct observable
        "zeta_frf": zeta_frf,          # v4: ζ = 1/(2·G_fn) — primary ζ metric
        "coh_at_fn": coh_at_fn,        # v4: coherence at fn (FRF quality)
        "zeta_hat": zeta_hat,          # log-decrement (reference; usually None)
        "zeta_hat_r2": zeta_r2,
        "zeta_hat_n_events": n_zeta,
        "zeta_hat_n_total": n_zeta_total,
        "zeta_hat_n_forced": n_zeta_forced,
        "zeta_BW": zeta_bw,            # half-power BW (reference; only valid for underdamped)
        "zeta_BW_peak_hz": f_peak_bw,
        "fn_stance_n_windows": n_stance_freq,
        "fn_full_hz": fn_full,
        "fn_full_prominence": fn_full_prom,
        "fn_equiv_BW_hz": fn_equiv_bw,
        # Mr & PM (theory + FRF-derived)
        "Mr_theory": theory.get("Mr_theory"),
        "PM_theory_deg": theory.get("PM_theory_deg"),
        "PM_frf_deg": pm_frf,            # v4: from zeta_frf
        # tau
        "tau_theory_ms": theory.get("tau_theory_ms"),
        "tau_frf_ms": tau_frf,           # v4: from zeta_frf
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
        # Jeff (from fn_frf, more accurate than from fn_swing)
        "jeff_hat": kp_used / (2.0 * math.pi * fn_frf) ** 2 if finite(kp_used) and finite(fn_frf) and fn_frf > 0 else None,
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
        if (row.get("zeta_hat_n_total") or 0) > 0 and (row.get("zeta_hat_n_forced") or 0) == (row.get("zeta_hat_n_total") or 0):
            flags.append("all_zeta_forced")  # v3: all events rejected — target not stationary
        else:
            flags.append("few_zeta_events")
    if (row.get("transfer_coherence") or 0) < 0.35:
        flags.append("low_coherence")
    if (row.get("delay_n_valid") or 0) < 3:
        flags.append("few_delay")
    if (row.get("zeta_BW_prominence") or 0) < 4.0:
        flags.append("weak_zeta_BW_peak")
    if (row.get("coh_at_fn") or 0) < 0.10:
        flags.append("low_frf_coherence")  # v4: FRF-based ζ may be unreliable
    return "ok" if not flags else ";".join(flags)


# ═════════════════════════════════════════════════════════════════════
# Damping risk grade (based on zeta_frf, fallback to zeta_theory)
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
        # v5 primary
        "frf_gain_at_fn_swing", "frf_coherence_swing", "zeta_frf_swing",
        "fn_frf_swing_hz",
        # full-gait FRF (reference)
        "fn_swing_hz", "fn_stance_hz", "fn_full_hz", "fn_frf_hz",
        "zeta_theory", "zeta_hat", "zeta_hat_r2", "zeta_BW",
        "zeta_frf", "G_fn", "coh_at_fn",
        "Mr_theory", "PM_theory_deg", "PM_frf_deg",
        "tau_theory_ms", "tau_frf_ms", "fn_theory_hz",
        "amplitude_gain_swing_median", "amplitude_gain_td_median",
        "range_gain_phase",
        "delay_ms_median", "tracking_lag_ms", "delay_phase_loss_at_fn_deg",
        "transfer_gain", "transfer_coherence",
        "A_peak", "jeff_hat",
    ]
    count_cols = [
        "n_td", "n_swing_segs",
        "n_self_excite_swing", "n_self_excite_td",
        "delay_n_valid", "zeta_hat_n_events", "zeta_hat_n_forced",
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
    # Add risk grade — prefer swing-phase ζ (v5 primary); fallback to full-gait FRF → theory
    for zeta_col in ("zeta_frf_swing", "zeta_frf", "zeta_theory"):
        if zeta_col in summary.columns:
            summary["damping_risk"] = summary[zeta_col].apply(damping_risk_grade)
            break
    for c in summary.columns:
        if pd.api.types.is_float_dtype(summary[c]):
            summary[c] = summary[c].round(5)
    return summary


def write_markdown_report(detail_rows, summary_df):
    """Generate a comprehensive markdown report."""
    df = pd.DataFrame(detail_rows)

    # ── Helper for tables ──
    # FRF columns that should be masked "无法判断" when coherence is too low
    FRF_MASK_COLS = {"frf_gain_at_fn_swing", "zeta_frf_swing"}

    def md_table(data, cols, max_rows=None):
        rows = data[:max_rows] if max_rows else data
        header = "| " + " | ".join(cols) + " |"
        sep = "|" + "|".join("---" for _ in cols) + "|"
        lines = [header, sep]
        for _, row in rows.iterrows():
            # Determine if this row has unreliable swing FRF
            coh_val = row.get("frf_coherence_swing") if "frf_coherence_swing" in row.index else None
            low_coh = (
                coh_val is None
                or (isinstance(coh_val, float) and (math.isnan(coh_val) or coh_val < SWING_COH_MIN))
            )
            cells = []
            for c in cols:
                v = row.get(c) if c in row.index else ""
                # Mask FRF-derived numbers when coherence is insufficient
                if c in FRF_MASK_COLS and low_coh:
                    cells.append("无法判断")
                elif isinstance(v, float) and not math.isnan(v):
                    cells.append(f"{v:.4f}")
                elif isinstance(v, float):
                    cells.append("")
                else:
                    cells.append(str(v) if v is not None else "")
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    # ── Key metrics columns for display ──
    # Only include columns directly useful for damping diagnosis;
    # full-gait FRF (G_fn/zeta_frf/coh_at_fn) and quality flags are omitted.
    key_cols = [
        "dataset", "case_label", "side", "axis",
        # v5 primary — FRF values masked when coh_sw < 0.40
        "frf_coherence_swing", "frf_gain_at_fn_swing", "zeta_frf_swing",
        "damping_status",
        # time-domain evidence
        "range_gain_phase", "A_peak",
        "e_rms_swing_rad",
        "tracking_lag_ms", "n_self_excite_swing",
    ]

    # Build quality column
    df["quality"] = df.apply(assess_quality, axis=1)
    # Risk based on swing-phase ζ (v5 primary)
    for zeta_col in ("zeta_frf_swing", "zeta_frf", "zeta_theory"):
        if zeta_col in df.columns:
            df["damping_risk"] = df[zeta_col].apply(damping_risk_grade)
            break

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
> 参考: `plans/踝关节阻尼谐振分析方法论.md`

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
        # v5 primary — FRF values masked when coh_sw < 0.40
        "frf_coherence_swing", "frf_gain_at_fn_swing", "zeta_frf_swing",
        # time-domain evidence
        "range_gain_phase", "A_peak",
        "e_rms_swing_rad",
        "tracking_lag_ms", "n_self_excite_swing",
        "damping_risk",
    ]
    sum_present = [c for c in sum_cols if c in summary_df.columns]
    report += md_table(summary_df, sum_present) + "\n"

    # ── 4. Self-excitation analysis ──
    se_data = df[df.get("n_self_excite_swing", pd.Series(0, index=df.index)) > 0] if "n_self_excite_swing" in df.columns else pd.DataFrame()
    if not se_data.empty:
        report += f"""
---

## 四、自激检测

`n_self_excite > 0` 表示检测到摆动相内 joint_vel > target_vel，存在额外能量注入。

"""
        se_cols = ["dataset", "case_label", "side", "axis",
                   "n_self_excite_swing", "range_gain_phase", "tracking_lag_ms"]
        se_present = [c for c in se_cols if c in se_data.columns]
        report += md_table(se_data, se_present) + "\n"

    # ── 5. Interpretation guide ──
    report += f"""
---

## 五、指标解读速查 (v5)

| 指标 | 含义 | 欠阻尼/危险 | 正常 | 过阻尼/低 |
|------|------|-------------|------|-----------|
| `frf_coherence_swing` (coh_sw) | FRF可信度 | — | ≥ 0.40 可信 | < 0.40 → G/ζ标"无法判断" |
| `frf_gain_at_fn_swing` (G_fn_sw) | 摆动相FRF幅值@fn | > 1.5 | 0.5–1.5 | < 0.5 |
| `zeta_frf_swing` (ζ_sw) | 摆动相阻尼比=1/(2G) | < 0.33 | 0.33–1.0 | > 1.0 |
| `range_gain_phase` | 关节/目标幅值比（时域兜底） | > 1.5 | 0.8–1.5 | < 0.8 |
| `A_peak` | 接地过冲倍数 | > 2.5 | 1.0–2.5 | — |
| `e_rms_swing_rad` | 摆动相跟踪误差RMS | > 0.15 rad | 0.05–0.15 | < 0.05 |
| `tracking_lag_ms` | 控制延迟 | > 60 ms | 30–60 ms | < 30 ms |

> ⚠️ coh_sw < 0.40 时 FRF 不可信（H1 在低SNR下严重偏低），G_fn_sw/ζ_sw 列标注"无法判断"，以 range_gain_phase 作时域兜底。
> 全步态 G_fn 不列入报告——支撑相 J_eff 增大 4–8× 会虚压 fn_eff，对阻尼判断无意义。

---

## 六、输出文件


| 文件 | 路径 |
|------|------|
| Detail CSV | `{DETAIL_CSV.relative_to(REPO_ROOT)}` |
| Summary CSV | `{SUMMARY_CSV.relative_to(REPO_ROOT)}` |
| Report MD | `{REPORT_PATH.relative_to(REPO_ROOT)}` |

> 方法论参考: `plans/踝关节阻尼谐振分析方法论.md`
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
    print("QUICK SUMMARY (v5) — swing-phase FRF damping by case:")
    print("=" * 70)
    key_cols = [
        "dataset", "case_label", "axis",
        "frf_gain_at_fn_swing", "frf_coherence_swing", "zeta_frf_swing",
        "G_fn", "zeta_frf", "zeta_theory", "damping_risk",
    ]
    print(summary_df[[c for c in key_cols if c in summary_df.columns]].to_string(index=False))


if __name__ == "__main__":
    main()
