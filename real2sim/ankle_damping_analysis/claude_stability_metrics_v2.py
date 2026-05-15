"""
Improved ankle stability metrics analysis.

This script intentionally keeps the original claude_stability_metrics.py intact.
It fixes the main statistical issues in that script:

1. Report raw and LPF command references separately.
2. Estimate frequencies from phase-gated data instead of full-signal only.
3. Estimate touchdown damping from log-envelope regression with confidence.
4. Estimate gain with cross spectral transfer H=P_yx/P_xx and coherence.
5. Estimate delay per window, then summarize median/IQR instead of concatenating
   unrelated windows.
6. Mark low-confidence physical metrics instead of silently treating them as
   reliable parameters.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.signal import butter, coherence, csd, detrend, find_peaks, hilbert, sosfiltfilt, welch


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DATA_DIR = REPO_ROOT / "test_logs" / "data_csv"
SIM_DIR = DATA_DIR / "sim"

OUT_DETAIL = SCRIPT_DIR / "claude_stability_metrics_v2_detail.csv"
OUT_SUMMARY = SCRIPT_DIR / "claude_stability_metrics_v2_summary.csv"
OUT_COMPARE = SCRIPT_DIR / "claude_stability_metrics_v2_real_sim_compare.csv"

J_EFF_DEFAULT = 0.0965
AXES = ("ankle_pitch", "ankle_roll")
SIDES = ("left", "right")
REFS = ("raw", "lpf")

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


@dataclass(frozen=True)
class Case:
    source: str
    label: str
    kp: float
    kd: float
    path: Path


CASES = (
    Case("real", "25/0.4", 25.0, 0.4, DATA_DIR / "t27_tracking_lag_b1_diag_20260430_100024.csv"),
    Case("real", "30/0.4", 30.0, 0.4, DATA_DIR / "t27_tracking_lag_b1_diag_20260430_100314.csv"),
    Case("real", "35/0.5", 35.0, 0.5, DATA_DIR / "t27_tracking_lag_b1_diag_20260430_100705.csv"),
    Case("real", "40/0.8", 40.0, 0.8, DATA_DIR / "t27_tracking_lag_b1_diag_20260430_101404.csv"),
    Case("sim", "25/0.4", 25.0, 0.4, SIM_DIR / "t27_tracking_lag_b1_diag_20260506_133905_2504.csv"),
    Case("sim", "35/0.5", 35.0, 0.5, SIM_DIR / "t27_tracking_lag_b1_diag_20260506_133024_3505.csv"),
    Case("sim", "40/0.5", 40.0, 0.5, SIM_DIR / "t27_tracking_lag_b1_diag_20260506_134153_4005.csv"),
    Case("sim", "50/0.8", 50.0, 0.8, SIM_DIR / "t27_tracking_lag_b1_diag_20260506_134417_5008.csv"),
)


def finite(v: float | None) -> bool:
    return v is not None and np.isfinite(v)


def round_or_none(v: float | None, ndigits: int = 4) -> float | None:
    return round(float(v), ndigits) if finite(v) else None


def rms_or_none(x: np.ndarray) -> float | None:
    x = np.asarray(x, dtype=np.float64)
    if not np.isfinite(x).any():
        return None
    return float(np.sqrt(np.nanmean(x**2)))


def load_case(path: Path) -> tuple[pd.DataFrame, np.ndarray, float, float]:
    df = pd.read_csv(path)
    t_ns = df["timestamp_ns"].to_numpy(dtype=np.float64)
    t = (t_ns - t_ns[0]) / 1e9
    dt = float(np.nanmedian(np.diff(t)))
    fs = 1.0 / dt
    return df, t, dt, fs


def touchdown_indices(df: pd.DataFrame, t: np.ndarray, side: str) -> np.ndarray:
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


def valid_pair(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(x) & np.isfinite(y)
    return x[mask], y[mask]


def zscore(x: np.ndarray) -> np.ndarray | None:
    x = np.asarray(x, dtype=np.float64)
    if len(x) < 8:
        return None
    s = float(np.nanstd(x))
    if s < 1e-9:
        return None
    return (x - np.nanmean(x)) / s


def contiguous_true_regions(mask: np.ndarray) -> list[slice]:
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return []
    breaks = np.where(np.diff(idx) > 1)[0] + 1
    groups = np.split(idx, breaks)
    return [slice(int(g[0]), int(g[-1]) + 1) for g in groups if len(g) >= 8]


def segment_windows_by_td(
    t: np.ndarray,
    td_idx: np.ndarray,
    pre_s: float,
    post_s: float,
) -> list[np.ndarray]:
    windows = []
    for idx in td_idx:
        t0 = t[idx] - pre_s
        t1 = t[idx] + post_s
        win = np.flatnonzero((t >= t0) & (t <= t1))
        if len(win) >= 8:
            windows.append(win)
    return windows


def phase_windows(df: pd.DataFrame, t: np.ndarray, side: str, phase: str) -> list[np.ndarray]:
    contact = df[f"{side}_contact"].to_numpy(dtype=np.float64) > 0.5
    if phase == "swing":
        base_mask = ~contact
        regions = contiguous_true_regions(base_mask)
        return [np.arange(s.start, s.stop) for s in regions if (t[s.stop - 1] - t[s.start]) >= 0.20]
    if phase == "stance":
        base_mask = contact
        regions = contiguous_true_regions(base_mask)
        return [np.arange(s.start, s.stop) for s in regions if (t[s.stop - 1] - t[s.start]) >= 0.20]
    raise ValueError(f"unknown phase: {phase}")


def average_window_spectrum(
    signal: np.ndarray,
    fs: float,
    windows: Iterable[np.ndarray],
    band: tuple[float, float],
) -> tuple[float | None, float | None, int, float | None]:
    """Return dominant frequency, peak prominence ratio, window count, resolution."""
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
        resolution = fs / n if resolution is None else min(resolution, fs / n)
        f = np.fft.rfftfreq(n, 1.0 / fs)
        mag = np.abs(np.fft.rfft(x * np.hanning(n)))
        mask = (f >= band[0]) & (f <= band[1])
        if not mask.any():
            continue
        f_band = f[mask]
        mag_band = mag[mask]
        if freq_ref is None:
            freq_ref = f_band
        mag_interp = np.interp(freq_ref, f_band, mag_band)
        spectra.append(mag_interp)
    if not spectra or freq_ref is None:
        return None, None, 0, None
    mean_mag = np.nanmean(np.vstack(spectra), axis=0)
    if len(mean_mag) == 0 or np.nanmax(mean_mag) <= 0:
        return None, None, len(spectra), resolution
    peak_idx = int(np.nanargmax(mean_mag))
    peak = float(mean_mag[peak_idx])
    floor = float(np.nanmedian(mean_mag)) + 1e-12
    prominence = peak / floor
    return float(freq_ref[peak_idx]), prominence, len(spectra), resolution


def full_signal_welch_frequency(
    signal: np.ndarray,
    fs: float,
    band: tuple[float, float],
) -> tuple[float | None, float | None]:
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


def transfer_at_frequency(
    ref: np.ndarray,
    out: np.ndarray,
    fs: float,
    fn: float | None,
    bw_hz: float = 0.75,
) -> tuple[float | None, float | None, float | None]:
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


def delay_one_window(ref: np.ndarray, out: np.ndarray, dt: float) -> tuple[float | None, float | None]:
    x, y = valid_pair(ref, out)
    xz = zscore(detrend(x, type="linear")) if len(x) >= 8 else None
    yz = zscore(detrend(y, type="linear")) if len(y) >= 8 else None
    if xz is None or yz is None or len(xz) != len(yz):
        return None, None
    lags = np.arange(-DELAY_MAX_LAG_SAMPLES, DELAY_MAX_LAG_SAMPLES + 1)
    vals = []
    for lag in lags:
        if lag < 0:
            a = yz[:lag]
            b = xz[-lag:]
        elif lag > 0:
            a = yz[lag:]
            b = xz[:-lag]
        else:
            a = yz
            b = xz
        if len(a) < 8:
            vals.append(np.nan)
        else:
            vals.append(float(np.nanmean(a * b)))
    vals_a = np.asarray(vals)
    if not np.isfinite(vals_a).any():
        return None, None
    best_i = int(np.nanargmax(vals_a))
    best_lag = int(lags[best_i])
    return best_lag * dt * 1000.0, float(vals_a[best_i])


def delay_align_pair(
    ref: np.ndarray,
    out: np.ndarray,
    lag_ms: float | None,
    dt: float,
) -> tuple[np.ndarray, np.ndarray, int | None]:
    """Align output to reference using the measured lag.

    Positive lag means the output follows the reference. The returned arrays are
    cropped so that ref[k] is compared with out[k + lag_samples].
    """
    if not finite(lag_ms):
        return ref, out, None
    lag_samples = int(round((lag_ms / 1000.0) / dt))
    if lag_samples > 0:
        if lag_samples >= len(ref):
            return np.array([]), np.array([]), lag_samples
        return ref[:-lag_samples], out[lag_samples:], lag_samples
    if lag_samples < 0:
        lead = -lag_samples
        if lead >= len(ref):
            return np.array([]), np.array([]), lag_samples
        return ref[lead:], out[:-lead], lag_samples
    return ref, out, 0


def summarize_delays(
    ref: np.ndarray,
    out: np.ndarray,
    dt: float,
    windows: Iterable[np.ndarray],
) -> tuple[float | None, float | None, float | None, int, int]:
    lags = []
    corrs = []
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
        float(np.nanmedian(lag_a)),
        float(np.nanpercentile(lag_a, 75) - np.nanpercentile(lag_a, 25)),
        float(np.nanmedian(corrs)),
        len(lags),
        n_total,
    )


def bandpass_sos(fs: float, lo: float, hi: float):
    nyq = 0.5 * fs
    lo = max(0.2, lo)
    hi = min(nyq * 0.95, hi)
    if lo >= hi:
        return None
    return butter(2, (lo / nyq, hi / nyq), btype="bandpass", output="sos")


def touchdown_damping_one_event(
    err: np.ndarray,
    fs: float,
    fn_hz: float | None,
) -> tuple[float | None, float | None, float | None, float | None]:
    if len(err) < int(0.35 * fs):
        return None, None, None, None
    x = np.asarray(err, dtype=np.float64)
    x = x[np.isfinite(x)]
    if len(x) < int(0.35 * fs):
        return None, None, None, None
    x = detrend(x, type="linear")

    if not finite(fn_hz):
        fn_hz, _ = full_signal_welch_frequency(x, fs, STANCE_FREQ_BAND)
    if not finite(fn_hz):
        return None, None, None, None

    sos = bandpass_sos(fs, max(1.0, fn_hz - 2.5), fn_hz + 2.5)
    if sos is None:
        return None, None, None, None
    try:
        y = sosfiltfilt(sos, x)
    except Exception:
        return None, None, None, None

    env = np.abs(hilbert(y))
    t_local = np.arange(len(env), dtype=np.float64) / fs
    start = int(0.04 * fs)
    stop = min(len(env), int(0.80 * fs))
    if stop - start < max(16, int(0.25 * fs)):
        return None, None, None, None
    tt = t_local[start:stop]
    ee = env[start:stop]
    floor = np.nanpercentile(ee, 15)
    ee = np.maximum(ee - floor * 0.5, 1e-9)

    log_env = np.log(ee)
    if np.nanstd(log_env) < 1e-6:
        return None, None, None, None
    slope, intercept = np.polyfit(tt, log_env, 1)
    pred = slope * tt + intercept
    ss_res = float(np.nansum((log_env - pred) ** 2))
    ss_tot = float(np.nansum((log_env - np.nanmean(log_env)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    if slope >= 0:
        return None, None, None, r2

    omega_d = 2.0 * math.pi * float(fn_hz)
    alpha = -float(slope)
    omega_n = math.sqrt(omega_d * omega_d + alpha * alpha)
    zeta = alpha / omega_n
    tau_ms = 1000.0 / alpha if alpha > 0 else None
    return float(zeta), tau_ms, float(alpha), float(r2)


def summarize_touchdown_damping(
    err: np.ndarray,
    fs: float,
    windows: Iterable[np.ndarray],
    fn_hz: float | None,
) -> tuple[float | None, float | None, float | None, int, int]:
    zetas = []
    taus = []
    r2s = []
    total = 0
    for win in windows:
        total += 1
        zeta, tau_ms, _alpha, r2 = touchdown_damping_one_event(err[win], fs, fn_hz)
        if finite(zeta) and finite(tau_ms) and finite(r2) and 0.005 < zeta < 1.0 and r2 >= 0.25:
            zetas.append(zeta)
            taus.append(tau_ms)
            r2s.append(r2)
    if not zetas:
        return None, None, None, 0, total
    return float(np.nanmedian(zetas)), float(np.nanmedian(taus)), float(np.nanmedian(r2s)), len(zetas), total


def touchdown_overshoot(err: np.ndarray, fs: float, windows: Iterable[np.ndarray]) -> tuple[float | None, int]:
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
    return float(np.nanmedian(vals)), len(vals)


def theoretical_metrics(kp: float, kd: float) -> dict[str, float | None]:
    wn = math.sqrt(kp / J_EFF_DEFAULT)
    fn = wn / (2.0 * math.pi)
    zeta = kd / (2.0 * math.sqrt(kp * J_EFF_DEFAULT))
    tau_ms = 1000.0 / (zeta * wn) if zeta > 0 else None
    if zeta < 1.0 / math.sqrt(2.0):
        mr = 1.0 / (2.0 * zeta * math.sqrt(1.0 - zeta * zeta))
    else:
        mr = None
    if zeta > 0:
        # Exact second-order phase-margin approximation from damping ratio.
        pm_rad = math.atan2(2.0 * zeta, math.sqrt(max(math.sqrt(1.0 + 4.0 * zeta**4) - 2.0 * zeta**2, 1e-12)))
        pm_deg = math.degrees(pm_rad)
    else:
        pm_deg = None
    return {
        "fn_theory_hz": fn,
        "zeta_theory": zeta,
        "tau_theory_ms": tau_ms,
        "Mr_theory": mr,
        "PM_theory_deg": pm_deg,
    }


def metric_quality(row: dict) -> str:
    flags = []
    if (row.get("reference_valid_ratio") or 0.0) < 0.5:
        flags.append("empty_reference")
    if (row.get("transfer_coherence") or 0.0) < 0.35:
        flags.append("low_coherence")
    if (row.get("zeta_r2") or 0.0) < 0.35:
        flags.append("low_zeta_r2")
    if (row.get("n_zeta_events") or 0) < 3:
        flags.append("few_zeta_events")
    if (row.get("n_delay_valid") or 0) < 3:
        flags.append("few_delay_windows")
    if (row.get("fn_stance_prominence") or 0.0) < 2.0:
        flags.append("weak_stance_peak")
    return "ok" if not flags else ";".join(flags)


def compute_metrics_for_axis(
    df: pd.DataFrame,
    t: np.ndarray,
    dt: float,
    fs: float,
    case: Case,
    side: str,
    axis: str,
    ref_kind: str,
) -> dict | None:
    pos_col = f"pos_{side}_{axis}_joint"
    ref_col = f"pos_des_{ref_kind}_{side}_{axis}_joint"
    if pos_col not in df.columns or ref_col not in df.columns or f"{side}_contact" not in df.columns:
        return None

    out = df[pos_col].to_numpy(dtype=np.float64)
    ref = df[ref_col].to_numpy(dtype=np.float64)
    reference_valid_ratio = float(np.isfinite(ref).mean())
    err = out - ref
    contact = df[f"{side}_contact"].to_numpy(dtype=np.float64) > 0.5
    td_idx = touchdown_indices(df, t, side)

    if reference_valid_ratio < 0.5 or not np.isfinite(out).any():
        row = {
            "source": case.source,
            "kpkd": case.label,
            "kp": case.kp,
            "kd": case.kd,
            "file": case.path.name,
            "side": side,
            "axis": axis,
            "reference": ref_kind,
            "reference_valid_ratio": reference_valid_ratio,
            "duration_s": float(t[-1]),
            "fs_hz": fs,
            "n_td": len(td_idx),
            **theoretical_metrics(case.kp, case.kd),
        }
        row["quality_flags"] = metric_quality(row)
        return row

    swing_regions = phase_windows(df, t, side, "swing")
    stance_regions = phase_windows(df, t, side, "stance")
    swing_delay_windows = segment_windows_by_td(t, td_idx, SWING_PRE_S, -SWING_POST_S)
    td_windows = segment_windows_by_td(t, td_idx, TD_PRE_S, TD_POST_S)

    e_rms = rms_or_none(err)
    e_rms_swing = rms_or_none(err[~contact]) if np.any(~contact) else None
    e_rms_stance = rms_or_none(err[contact]) if np.any(contact) else None

    fn_full, fn_full_prom = full_signal_welch_frequency(err, fs, SWING_FREQ_BAND)
    fn_swing, fn_swing_prom, n_swing_freq, swing_res = average_window_spectrum(err, fs, swing_regions, SWING_FREQ_BAND)
    fn_stance, fn_stance_prom, n_stance_freq, stance_res = average_window_spectrum(err, fs, td_windows, STANCE_FREQ_BAND)

    fn_for_transfer = fn_swing if finite(fn_swing) else fn_full
    gain, phase_deg, coh = transfer_at_frequency(ref, out, fs, fn_for_transfer)

    delay_med, delay_iqr, delay_corr, n_delay_valid, n_delay_total = summarize_delays(ref, out, dt, swing_delay_windows)
    ref_aligned, out_aligned, delay_lag_samples = delay_align_pair(ref, out, delay_med, dt)
    err_aligned = out_aligned - ref_aligned if len(ref_aligned) == len(out_aligned) else np.array([])
    e_rms_delay_aligned = rms_or_none(err_aligned)
    gain_aligned, phase_aligned_deg, coh_aligned = transfer_at_frequency(
        ref_aligned,
        out_aligned,
        fs,
        fn_for_transfer,
    )
    zeta, tau_hat, zeta_r2, n_zeta, n_zeta_total = summarize_touchdown_damping(err, fs, td_windows, fn_stance)
    a_peak, n_apeak = touchdown_overshoot(err, fs, td_windows)

    jeff_hat = case.kp / (2.0 * math.pi * fn_swing) ** 2 if finite(fn_swing) and fn_swing > 0 else None
    mr_hat_zeta = None
    pm_hat = None
    if finite(zeta):
        if zeta < 1.0 / math.sqrt(2.0):
            mr_hat_zeta = 1.0 / (2.0 * zeta * math.sqrt(max(1.0 - zeta * zeta, 1e-9)))
        pm_hat = math.degrees(math.atan2(2.0 * zeta, math.sqrt(max(math.sqrt(1.0 + 4.0 * zeta**4) - 2.0 * zeta**2, 1e-12))))

    theory = theoretical_metrics(case.kp, case.kd)
    row = {
        "source": case.source,
        "kpkd": case.label,
        "kp": case.kp,
        "kd": case.kd,
        "file": case.path.name,
        "side": side,
        "axis": axis,
        "reference": ref_kind,
        "reference_valid_ratio": reference_valid_ratio,
        "duration_s": float(t[-1]),
        "fs_hz": fs,
        "n_td": len(td_idx),
        "e_rms_rad": e_rms,
        "e_rms_swing_rad": e_rms_swing,
        "e_rms_stance_rad": e_rms_stance,
        "fn_full_err_hz": fn_full,
        "fn_full_prominence": fn_full_prom,
        "fn_swing_hz": fn_swing,
        "fn_swing_prominence": fn_swing_prom,
        "fn_swing_resolution_hz": swing_res,
        "n_swing_freq_windows": n_swing_freq,
        "fn_stance_hz": fn_stance,
        "fn_stance_prominence": fn_stance_prom,
        "fn_stance_resolution_hz": stance_res,
        "n_stance_freq_windows": n_stance_freq,
        "jeff_hat": jeff_hat,
        "transfer_gain": gain,
        "transfer_phase_deg": phase_deg,
        "transfer_coherence": coh,
        "transfer_gain_delay_aligned": gain_aligned,
        "transfer_phase_delay_aligned_deg": phase_aligned_deg,
        "transfer_coherence_delay_aligned": coh_aligned,
        "delay_ms_median": delay_med,
        "delay_ms_iqr": delay_iqr,
        "delay_lag_samples": delay_lag_samples,
        "e_rms_delay_aligned_rad": e_rms_delay_aligned,
        "delay_corr_median": delay_corr,
        "n_delay_valid": n_delay_valid,
        "n_delay_total": n_delay_total,
        "zeta_hat": zeta,
        "zeta_r2": zeta_r2,
        "tau_hat_ms": tau_hat,
        "Mr_hat_zeta": mr_hat_zeta,
        "PM_hat_deg": pm_hat,
        "n_zeta_events": n_zeta,
        "n_zeta_total": n_zeta_total,
        "A_peak": a_peak,
        "n_A_peak": n_apeak,
        **theory,
    }
    row["quality_flags"] = metric_quality(row)
    return row


def add_delta_lr(rows: list[dict]) -> None:
    grouped = {}
    for r in rows:
        key = (r["source"], r["kpkd"], r["axis"], r["reference"])
        grouped.setdefault(key, {})[r["side"]] = r
    for lr in grouped.values():
        left = lr.get("left")
        right = lr.get("right")
        if not left or not right:
            continue
        el = left.get("e_rms_rad")
        er = right.get("e_rms_rad")
        if finite(el) and finite(er) and er > 0:
            val = float(el / er)
            left["DeltaLR_eRMS"] = val
            right["DeltaLR_eRMS"] = val


def rounded_dataframe(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].round(5)
    return df


def build_summary(detail: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        "reference_valid_ratio",
        "e_rms_rad",
        "e_rms_delay_aligned_rad",
        "e_rms_swing_rad",
        "e_rms_stance_rad",
        "fn_swing_hz",
        "fn_stance_hz",
        "jeff_hat",
        "transfer_gain",
        "transfer_coherence",
        "transfer_gain_delay_aligned",
        "transfer_coherence_delay_aligned",
        "delay_ms_median",
        "delay_ms_iqr",
        "delay_lag_samples",
        "zeta_hat",
        "zeta_r2",
        "tau_hat_ms",
        "A_peak",
        "DeltaLR_eRMS",
        "fn_theory_hz",
        "zeta_theory",
        "tau_theory_ms",
        "PM_theory_deg",
    ]
    agg = {}
    for col in numeric_cols:
        if col in detail.columns:
            agg[col] = "mean"
    count_cols = ["n_td", "n_delay_valid", "n_delay_total", "n_zeta_events", "n_zeta_total"]
    for col in count_cols:
        if col in detail.columns:
            agg[col] = "sum"
    summary = detail.groupby(["source", "kpkd", "kp", "kd", "axis", "reference"], as_index=False).agg(agg)
    if "DeltaLR_eRMS" in summary.columns:
        summary["DeltaLR_eRMS"] = detail.groupby(["source", "kpkd", "axis", "reference"])["DeltaLR_eRMS"].first().values
    for c in summary.columns:
        if pd.api.types.is_float_dtype(summary[c]):
            summary[c] = summary[c].round(5)
    return summary


def build_compare(summary: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "e_rms_rad",
        "e_rms_delay_aligned_rad",
        "e_rms_swing_rad",
        "e_rms_stance_rad",
        "fn_swing_hz",
        "fn_stance_hz",
        "transfer_gain",
        "transfer_coherence",
        "transfer_gain_delay_aligned",
        "transfer_coherence_delay_aligned",
        "delay_ms_median",
        "zeta_hat",
        "tau_hat_ms",
        "A_peak",
    ]
    rows = []
    for label in ("25/0.4", "35/0.5"):
        for axis in AXES:
            for ref in REFS:
                real = summary[(summary.source == "real") & (summary.kpkd == label) & (summary.axis == axis) & (summary.reference == ref)]
                sim = summary[(summary.source == "sim") & (summary.kpkd == label) & (summary.axis == axis) & (summary.reference == ref)]
                if real.empty or sim.empty:
                    continue
                rr = real.iloc[0]
                ss = sim.iloc[0]
                if (rr.get("reference_valid_ratio", 0.0) < 0.5) or (ss.get("reference_valid_ratio", 0.0) < 0.5):
                    continue
                row = {"kpkd": label, "axis": axis, "reference": ref}
                for m in metrics:
                    if m not in summary.columns:
                        continue
                    rv = rr[m]
                    sv = ss[m]
                    row[f"real_{m}"] = rv
                    row[f"sim_{m}"] = sv
                    row[f"real_minus_sim_{m}"] = rv - sv if finite(rv) and finite(sv) else np.nan
                    row[f"real_over_sim_{m}"] = rv / sv if finite(rv) and finite(sv) and abs(sv) > 1e-12 else np.nan
                rows.append(row)
    df = pd.DataFrame(rows)
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].round(5)
    return df


def print_key_tables(summary: pd.DataFrame, compare: pd.DataFrame) -> None:
    cols = [
        "source",
        "kpkd",
        "axis",
        "reference",
        "reference_valid_ratio",
        "e_rms_rad",
        "e_rms_delay_aligned_rad",
        "fn_swing_hz",
        "fn_stance_hz",
        "transfer_gain",
        "transfer_coherence",
        "transfer_gain_delay_aligned",
        "transfer_coherence_delay_aligned",
        "delay_ms_median",
        "zeta_hat",
        "zeta_r2",
        "n_zeta_events",
        "quality_score",
    ]
    printable = summary[summary.get("reference_valid_ratio", 0.0) >= 0.5].copy()
    printable["quality_score"] = (
        printable.get("transfer_coherence", 0).fillna(0).clip(0, 1)
        + printable.get("zeta_r2", 0).fillna(0).clip(0, 1)
    ) / 2.0
    print("\nSUMMARY (left/right averaged)")
    print(printable[[c for c in cols if c in printable.columns]].to_string(index=False))

    if not compare.empty:
        ccols = [
            "kpkd",
            "axis",
            "reference",
            "real_minus_sim_e_rms_rad",
            "real_minus_sim_delay_ms_median",
            "real_minus_sim_fn_swing_hz",
            "real_minus_sim_zeta_hat",
            "real_over_sim_transfer_gain",
        ]
        print("\nREAL - SIM matched cases")
        print(compare[[c for c in ccols if c in compare.columns]].to_string(index=False))


def main() -> None:
    missing = [str(c.path) for c in CASES if not c.path.exists()]
    if missing:
        raise FileNotFoundError("Missing input CSV files:\n" + "\n".join(missing))

    rows = []
    for case in CASES:
        print(f"[{case.source}] {case.label} {case.path.name}")
        df, t, dt, fs = load_case(case.path)
        for side in SIDES:
            for axis in AXES:
                for ref_kind in REFS:
                    row = compute_metrics_for_axis(df, t, dt, fs, case, side, axis, ref_kind)
                    if row is not None:
                        rows.append(row)
    add_delta_lr(rows)

    detail = rounded_dataframe(rows)
    summary = build_summary(detail)
    compare = build_compare(summary)

    detail.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    compare.to_csv(OUT_COMPARE, index=False)

    print_key_tables(summary, compare)
    print(f"\nSaved detail:  {OUT_DETAIL}")
    print(f"Saved summary: {OUT_SUMMARY}")
    print(f"Saved compare: {OUT_COMPARE}")


if __name__ == "__main__":
    # Keep BLAS from oversubscribing small CSV analysis jobs.
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    main()
