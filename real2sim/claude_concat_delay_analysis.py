"""
Concatenated Cross-Correlation Delay Analysis
=============================================
Instead of per-window estimates (noisy due to short windows ~33 samples),
concatenate all swing or touchdown windows into one long signal and compute
a single cross-correlation — more data, more reliable lag peak.

Also runs full-signal cross-correlation for comparison.

Method:
  1. Detect touchdown events via contact-signal rising edges
  2. For each event, slice swing window [touch-350ms, touch-20ms]
     and touchdown window [touch-50ms, touch+100ms]
  3. Concatenate all windows (both legs) into one target array and one joint array
  4. numpy cross-correlation → peak lag → delay in ms
  5. Also compute full-signal xcorr for comparison
  6. Report correlation peak height as confidence proxy
"""

import numpy as np
import pandas as pd
from scipy.signal import correlate, correlation_lags
import warnings
warnings.filterwarnings('ignore')

# ─── Cases ────────────────────────────────────────────────────────────────────
BASE = '/sessions/wonderful-vibrant-turing/mnt/agibot_x1_infer/test_logs/data_csv/'
CASES = [
    ('25/0.4', BASE + 't27_tracking_lag_b1_diag_20260430_100024.csv'),
    ('30/0.4', BASE + 't27_tracking_lag_b1_diag_20260430_100314.csv'),
    ('35/0.5', BASE + 't27_tracking_lag_b1_diag_20260430_100705.csv'),
    ('40/0.8', BASE + 't27_tracking_lag_b1_diag_20260430_101404.csv'),
]

AXES = ['ankle_pitch', 'ankle_roll']

# Window definitions (seconds)
SWING_PRE   = 0.350  # before touchdown
SWING_POST  = 0.020  # before touchdown (exclude last 20ms)
TD_PRE      = 0.050  # before touchdown
TD_POST     = 0.100  # after touchdown

# Max search lag (samples, at 100 Hz → 1 sample = 10ms)
MAX_LAG_SAMPLES = 30  # 300ms max


def load_case(csv_path):
    df = pd.read_csv(csv_path)
    t_ns = df['timestamp_ns'].values
    t_s  = (t_ns - t_ns[0]) / 1e9
    dt   = np.median(np.diff(t_s))
    fs   = 1.0 / dt
    return df, t_s, dt, fs


MIN_TD_GAP = 0.25  # minimum seconds between touchdowns (debounce)

def detect_touchdowns(df, t_s, side):
    """Return debounced touchdown timestamps (rising edge of contact signal)."""
    contact = df[f'{side}_contact'].values.astype(int)
    edges   = np.where(np.diff(contact) > 0)[0] + 1  # rising edge indices
    times_all = t_s[edges]
    if len(times_all) == 0:
        return np.array([]), np.array([], dtype=int)
    # Debounce: keep only touchdowns separated by at least MIN_TD_GAP
    kept_times = [times_all[0]]
    kept_edges = [edges[0]]
    for i, tt in enumerate(times_all[1:], 1):
        if tt - kept_times[-1] >= MIN_TD_GAP:
            kept_times.append(tt)
            kept_edges.append(edges[i])
    return np.array(kept_times), np.array(kept_edges)


def slice_window(t_s, signal_target, signal_joint, t_touch, pre, post, dt):
    """
    Slice [t_touch - pre, t_touch - post] (for swing)
    or   [t_touch - pre, t_touch + post] (for touchdown).
    Returns (tgt_segment, jnt_segment) or (None, None) if too short.
    """
    t0 = t_touch - pre
    t1 = t_touch + post   # post is negative for swing trailing edge
    mask = (t_s >= t0) & (t_s <= t1)
    if mask.sum() < 8:
        return None, None
    return signal_target[mask], signal_joint[mask]


def xcorr_lag_ms(target_segs, joint_segs, dt, max_lag_samp):
    """
    Concatenate segments, compute normalized cross-correlation,
    find peak within ±max_lag_samp.
    Returns (lag_ms, peak_corr, n_samples_total).
    """
    if not target_segs:
        return np.nan, np.nan, 0

    # z-score each segment independently before concatenating
    # (removes DC offset differences between steps)
    tgt_all, jnt_all = [], []
    for t, j in zip(target_segs, joint_segs):
        t_std = t.std()
        j_std = j.std()
        if t_std < 1e-6 or j_std < 1e-6:
            continue  # flat segment, skip
        tgt_all.append((t - t.mean()) / t_std)
        jnt_all.append((j - j.mean()) / j_std)

    if not tgt_all:
        return np.nan, np.nan, 0

    tgt_cat = np.concatenate(tgt_all)
    jnt_cat = np.concatenate(jnt_all)
    n = len(tgt_cat)

    # Full cross-correlation
    cc   = correlate(jnt_cat, tgt_cat, mode='full')
    lags = correlation_lags(len(jnt_cat), len(tgt_cat), mode='full')

    # Normalize to [-1, 1]
    cc_norm = cc / n  # ≈ normalized (both z-scored, n samples)

    # Restrict to [0, max_lag_samp]  (joint lags behind target → positive lag)
    # Also allow small negative lags to avoid one-sided bias
    mask = (lags >= -5) & (lags <= max_lag_samp)
    cc_sub   = cc_norm[mask]
    lags_sub = lags[mask]

    peak_idx  = np.argmax(cc_sub)
    best_lag  = lags_sub[peak_idx]
    peak_corr = cc_sub[peak_idx]

    return best_lag * dt * 1000, float(peak_corr), n


def full_signal_xcorr(df, t_s, dt, axis, max_lag_samp):
    """
    Cross-correlate full signal (both legs averaged) for one axis.
    """
    results = {}
    for side in ['left', 'right']:
        tgt_col = f'pos_des_raw_{side}_{axis}_joint'
        jnt_col = f'pos_{side}_{axis}_joint'
        if tgt_col not in df.columns:
            continue
        tgt = df[tgt_col].values
        jnt = df[jnt_col].values
        tgt_z = (tgt - tgt.mean()) / (tgt.std() + 1e-9)
        jnt_z = (jnt - jnt.mean()) / (jnt.std() + 1e-9)

        cc   = correlate(jnt_z, tgt_z, mode='full')
        lags = correlation_lags(len(jnt_z), len(tgt_z), mode='full')
        n    = len(tgt)
        cc_norm = cc / n

        mask = (lags >= -5) & (lags <= max_lag_samp)
        cc_sub   = cc_norm[mask]
        lags_sub = lags[mask]
        peak_idx  = np.argmax(cc_sub)
        best_lag  = lags_sub[peak_idx]
        peak_corr = cc_sub[peak_idx]
        results[side] = (best_lag * dt * 1000, float(peak_corr))

    if not results:
        return np.nan, np.nan
    lags_ms   = [v[0] for v in results.values()]
    corrs     = [v[1] for v in results.values()]
    return float(np.mean(lags_ms)), float(np.mean(corrs))


# ─── Main ─────────────────────────────────────────────────────────────────────
rows = []

for kpkd, csv_path in CASES:
    print(f"\n{'='*60}")
    print(f"Case Kp/Kd = {kpkd}  |  {csv_path.split('/')[-1]}")
    print(f"{'='*60}")

    df, t_s, dt, fs = load_case(csv_path)
    print(f"  Loaded: {len(df)} rows, {t_s[-1]:.2f}s, fs≈{fs:.1f} Hz")

    for axis in AXES:
        # ── collect window segments for both legs ────────────────────────────
        swing_tgt_segs, swing_jnt_segs   = [], []
        td_tgt_segs,    td_jnt_segs      = [], []

        for side in ['left', 'right']:
            tgt_col = f'pos_des_raw_{side}_{axis}_joint'
            jnt_col = f'pos_{side}_{axis}_joint'
            if tgt_col not in df.columns:
                continue

            tgt_sig = df[tgt_col].values
            jnt_sig = df[jnt_col].values

            touch_times, _ = detect_touchdowns(df, t_s, side)

            for t_touch in touch_times:
                # Swing window: [t_touch - SWING_PRE, t_touch - SWING_POST]
                t0s, t1s = t_touch - SWING_PRE, t_touch - SWING_POST
                mask_s = (t_s >= t0s) & (t_s <= t1s)
                if mask_s.sum() >= 8:
                    swing_tgt_segs.append(tgt_sig[mask_s])
                    swing_jnt_segs.append(jnt_sig[mask_s])

                # Touchdown window: [t_touch - TD_PRE, t_touch + TD_POST]
                t0d, t1d = t_touch - TD_PRE, t_touch + TD_POST
                mask_d = (t_s >= t0d) & (t_s <= t1d)
                if mask_d.sum() >= 8:
                    td_tgt_segs.append(tgt_sig[mask_d])
                    td_jnt_segs.append(jnt_sig[mask_d])

        # ── compute concatenated xcorr ───────────────────────────────────────
        sw_lag, sw_corr, sw_n = xcorr_lag_ms(swing_tgt_segs, swing_jnt_segs, dt, MAX_LAG_SAMPLES)
        td_lag, td_corr, td_n = xcorr_lag_ms(td_tgt_segs,    td_jnt_segs,    dt, MAX_LAG_SAMPLES)

        # ── full signal xcorr ────────────────────────────────────────────────
        fs_lag, fs_corr = full_signal_xcorr(df, t_s, dt, axis, MAX_LAG_SAMPLES)

        n_sw_segs = len(swing_tgt_segs)
        n_td_segs = len(td_tgt_segs)

        print(f"\n  [{axis}]")
        print(f"    Swing  ({n_sw_segs} segs, {sw_n} samples total): "
              f"lag={sw_lag:+.1f}ms  peak_corr={sw_corr:.3f}")
        print(f"    TD     ({n_td_segs} segs, {td_n} samples total): "
              f"lag={td_lag:+.1f}ms  peak_corr={td_corr:.3f}")
        print(f"    Full-sig (both legs avg):                  "
              f"lag={fs_lag:+.1f}ms  peak_corr={fs_corr:.3f}")

        rows.append({
            'kpkd':        kpkd,
            'axis':        axis,
            'swing_lag_ms':   round(sw_lag, 1) if not np.isnan(sw_lag) else None,
            'swing_corr':     round(sw_corr, 3) if not np.isnan(sw_corr) else None,
            'swing_n_segs':   n_sw_segs,
            'swing_n_samp':   sw_n,
            'td_lag_ms':      round(td_lag, 1) if not np.isnan(td_lag) else None,
            'td_corr':        round(td_corr, 3) if not np.isnan(td_corr) else None,
            'td_n_segs':      n_td_segs,
            'td_n_samp':      td_n,
            'fullsig_lag_ms': round(fs_lag, 1) if not np.isnan(fs_lag) else None,
            'fullsig_corr':   round(fs_corr, 3) if not np.isnan(fs_corr) else None,
        })

# ─── Summary table ────────────────────────────────────────────────────────────
results = pd.DataFrame(rows)
print("\n\n" + "="*70)
print("SUMMARY TABLE")
print("="*70)
print(results.to_string(index=False))

# Save
out_path = '/sessions/wonderful-vibrant-turing/mnt/agibot_x1_infer/real2sim/claude_concat_delay_results.csv'
results.to_csv(out_path, index=False)
print(f"\nSaved to {out_path}")

# ─── Pretty print comparison ──────────────────────────────────────────────────
print("\n\n" + "="*70)
print("DELAY COMPARISON: Swing-concat vs TD-concat vs Full-signal (ms)")
print("  positive = joint lags behind target (expected for real hardware)")
print("  peak_corr: >0.5 reliable, 0.3-0.5 moderate, <0.3 weak")
print("="*70)
header = f"{'Kp/Kd':>8}  {'Axis':>12}  {'Swing':>10}  {'Swing-corr':>11}  {'TD':>8}  {'TD-corr':>9}  {'FullSig':>9}  {'FS-corr':>9}"
print(header)
print("-"*85)
for _, r in results.iterrows():
    sw  = f"{r['swing_lag_ms']:+.1f}ms" if r['swing_lag_ms'] is not None else "  N/A"
    sco = f"{r['swing_corr']:.3f}"      if r['swing_corr']   is not None else "  N/A"
    td  = f"{r['td_lag_ms']:+.1f}ms"   if r['td_lag_ms']    is not None else "  N/A"
    tco = f"{r['td_corr']:.3f}"         if r['td_corr']      is not None else "  N/A"
    fs  = f"{r['fullsig_lag_ms']:+.1f}ms" if r['fullsig_lag_ms'] is not None else "  N/A"
    fco = f"{r['fullsig_corr']:.3f}"    if r['fullsig_corr'] is not None else "  N/A"
    print(f"{r['kpkd']:>8}  {r['axis']:>12}  {sw:>10}  {sco:>11}  {td:>8}  {tco:>9}  {fs:>9}  {fco:>9}")
