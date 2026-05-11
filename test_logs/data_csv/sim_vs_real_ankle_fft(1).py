"""
Sim vs Real: Ankle Roll FFT comparison.

Default mode compares the original t23 simulation CSV against the May7 real
baseline. CLI mode accepts single files or globs, e.g. t27 real vs t27 sim:

  conda run -n x1 python 'sim_vs_real_ankle_fft(1).py' \
    --tag t27 \
    --sim 'sim/t27_tracking_lag_b1_diag_*.csv' \
    --real 't27_tracking_lag_b1_diag_*.csv'
"""

import argparse
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import welch

FS = 100  # Hz
PEAK_BAND = (0.5, 20.0)
HF_BAND = (5.0, 15.0)
TOTAL_BAND = (0.5, 20.0)  # AC motion band; excludes DC offset.

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_SIM_FILE = (
    r"d:\工作资料\02机器人\01F1项目\locomotion-lab\experiments\X1-12DOF"
    r"\real_walking_0.6\部署代码仿真数据\t23_joint_sim.csv"
)
DEFAULT_REAL_FILE = (
    r"d:\工作资料\02机器人\01F1项目\sim-to-real\F1\test_logs"
    r"\前馈正确测试数据\round_kp40_kd3_ff0_20260507_134731.csv"
)

COLOR_SIM = "#1565C0"
COLOR_REAL = "#C62828"
SIDES = ["left", "right"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare sim vs real ankle-roll FFT/PSD metrics."
    )
    parser.add_argument("--sim", nargs="+", default=[DEFAULT_SIM_FILE],
                        help="Simulation CSV path(s) or glob(s).")
    parser.add_argument("--real", nargs="+", default=[DEFAULT_REAL_FILE],
                        help="Real CSV path(s) or glob(s).")
    parser.add_argument("--tag", default="default",
                        help="Output filename tag.")
    parser.add_argument("--out-dir", default=SCRIPT_DIR,
                        help="Directory for figures and metric files.")
    parser.add_argument("--fs", type=float, default=FS,
                        help="Sampling rate in Hz.")
    parser.add_argument("--real-skip", type=int, default=5,
                        help="Rows to skip at the start of real logs.")
    parser.add_argument("--sim-skip", type=int, default=0,
                        help="Rows to skip at the start of sim logs.")
    parser.add_argument("--no-trim-real", action="store_true",
                        help="Disable active-window trimming for real logs.")
    parser.add_argument("--trim-win", type=int, default=50)
    parser.add_argument("--trim-thresh", type=float, default=0.003)
    parser.add_argument("--max-plot-files", type=int, default=8,
                        help="Max files per source to overlay in figures.")
    return parser.parse_args()


def resolve_input_file(path):
    if os.path.exists(path):
        return path
    filename = path.replace("\\", "/").split("/")[-1]
    local_path = os.path.join(SCRIPT_DIR, filename)
    if os.path.exists(local_path):
        return local_path
    return path


def expand_inputs(patterns):
    paths = []
    for item in patterns:
        resolved = resolve_input_file(item)
        matches = sorted(glob.glob(resolved))
        if not matches and not os.path.isabs(item):
            matches = sorted(glob.glob(os.path.join(SCRIPT_DIR, item)))
        if matches:
            paths.extend(matches)
        else:
            paths.append(resolved)

    seen = set()
    out = []
    for path in paths:
        abspath = os.path.abspath(path)
        if abspath not in seen:
            seen.add(abspath)
            out.append(abspath)
    return out


def normalize_columns(df):
    rename = {}
    for col in df.columns:
        if col.startswith("target_lpf_"):
            rename[col] = col.replace("target_lpf_", "pos_des_lpf_")
        elif col.startswith("target_"):
            rename[col] = col.replace("target_", "pos_des_raw_")
    if rename:
        df = df.rename(columns=rename)
    return df


def add_time_seconds(df, fs):
    if "timestamp_ns" in df.columns:
        df["t_s"] = (df["timestamp_ns"] - df["timestamp_ns"].iloc[0]) * 1e-9
    elif "time_s" in df.columns:
        df["t_s"] = df["time_s"] - df["time_s"].iloc[0]
    elif "t_s" in df.columns:
        df["t_s"] = df["t_s"] - df["t_s"].iloc[0]
    else:
        df["t_s"] = np.arange(len(df), dtype=float) / fs
    return df


def trim_active_window(df, win, thresh):
    trim_col = next(
        (c for c in ["pos_left_knee_pitch_joint", "pos_left_hip_roll_joint"]
         if c in df.columns),
        None,
    )
    if not trim_col:
        return df

    roll_std = df[trim_col].rolling(win, min_periods=1).std().fillna(0)
    active = np.where(roll_std.values > thresh)[0]
    if len(active):
        df = df.iloc[:active[-1] + 1].reset_index(drop=True)
        df["t_s"] = df["t_s"] - df["t_s"].iloc[0]
    return df


def load_log(path, source, fs, skip_rows=0, trim=False, trim_win=50, trim_thresh=0.003):
    df = pd.read_csv(path)
    if skip_rows:
        df = df.iloc[skip_rows:].reset_index(drop=True)
    df = normalize_columns(df)
    df = add_time_seconds(df, fs)
    if trim:
        df = trim_active_window(df, trim_win, trim_thresh)
    return {
        "source": source,
        "path": path,
        "run_id": os.path.splitext(os.path.basename(path))[0],
        "df": df,
    }


def find_actual_col(df, side):
    candidates = [
        f"pos_{side}_ankle_roll_joint",
        f"{side}_ankle_roll_joint",
        f"joint_pos_{side}_ankle_roll_joint",
    ]
    return next((col for col in candidates if col in df.columns), None)


def find_target_col(df, side):
    candidates = [
        f"pos_des_raw_{side}_ankle_roll_joint",
        f"pos_des_lpf_{side}_ankle_roll_joint",
        f"target_{side}_ankle_roll_joint",
        f"target_lpf_{side}_ankle_roll_joint",
        f"action_{side}_ankle_roll_joint",
    ]
    return next((col for col in candidates if col in df.columns), None)


def finite_ac_signal(sig):
    sig = np.asarray(sig, dtype=float)
    sig = sig[np.isfinite(sig)]
    if len(sig) == 0:
        return sig
    return sig - np.mean(sig)


def fft_spectrum(sig, fs):
    sig = finite_ac_signal(sig)
    n = len(sig)
    if n < 2:
        return np.array([]), np.array([])
    win = np.hanning(n)
    amp = 2.0 * np.abs(np.fft.rfft(sig * win)) / np.sum(win)
    freq = np.fft.rfftfreq(n, d=1.0 / fs)
    return freq, amp


def psd_welch(sig, fs):
    sig = finite_ac_signal(sig)
    if len(sig) < 8:
        return np.array([]), np.array([])
    nperseg = max(8, min(256, len(sig) // 4))
    return welch(sig, fs=fs, nperseg=nperseg, window="hann", scaling="density")


def top_peak(freq, amp, band=PEAK_BAND):
    if len(freq) == 0:
        return np.nan, np.nan
    fmin, fmax = band
    mask = (freq >= fmin) & (freq <= fmax)
    if not np.any(mask):
        return np.nan, np.nan
    idx = np.argmax(amp[mask])
    return freq[mask][idx], amp[mask][idx]


def band_energy(freq, psd, band):
    if len(freq) == 0:
        return np.nan
    fmin, fmax = band
    mask = (freq >= fmin) & (freq <= fmax)
    if np.count_nonzero(mask) < 2:
        return np.nan
    return np.trapezoid(psd[mask], freq[mask])


def spectral_metrics(sig, fs):
    freq, amp = fft_spectrum(sig, fs)
    peak_hz, peak_amp = top_peak(freq, amp)
    fp, psd = psd_welch(sig, fs)
    hf_energy = band_energy(fp, psd, HF_BAND)
    total_energy = band_energy(fp, psd, TOTAL_BAND)
    hf_ratio = hf_energy / total_energy if total_energy and total_energy > 0 else np.nan
    sig_arr = np.asarray(sig, dtype=float)
    sig_arr = sig_arr[np.isfinite(sig_arr)]
    mean = np.mean(sig_arr) if len(sig_arr) else np.nan
    osc = np.sqrt(np.mean((sig_arr - mean) ** 2)) if len(sig_arr) else np.nan
    return {
        "mean_rad": mean,
        "osc_rms_rad": osc,
        "peak_hz": peak_hz,
        "peak_amp_rad": peak_amp,
        "hf_energy_5_15_rad2": hf_energy,
        "total_energy_0p5_20_rad2": total_energy,
        "hf_over_total": hf_ratio,
    }


def ratio_or_nan(num, den):
    return num / den if den and den > 0 else np.nan


def metric_rows_for_logs(logs, fs):
    rows = []
    for log in logs:
        df = log["df"]
        for side in SIDES:
            col = find_actual_col(df, side)
            target_col = find_target_col(df, side)
            if not col:
                print(f"  [SKIP] {log['source']} {log['run_id']} missing {side} ankle roll actual column")
                continue
            m = spectral_metrics(df[col].values, fs)
            rows.append({
                "source": log["source"],
                "run_id": log["run_id"],
                "side": side,
                "column": col,
                "target_column": target_col or "",
                "csv_path": log["path"],
                "frames": len(df),
                "duration_s": df["t_s"].iloc[-1] if len(df) else np.nan,
                "peak_band_hz": f"{PEAK_BAND[0]}-{PEAK_BAND[1]}",
                "hf_band_hz": f"{HF_BAND[0]}-{HF_BAND[1]}",
                "total_band_hz": f"{TOTAL_BAND[0]}-{TOTAL_BAND[1]}",
                **m,
            })
    return rows


def add_ratio_rows(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        return rows

    ratio_rows = []
    for side in SIDES:
        sim = df[(df["source"] == "sim") & (df["side"] == side)]
        real = df[(df["source"] == "real") & (df["side"] == side)]
        if sim.empty or real.empty:
            continue

        sim_ref = sim[[
            "peak_amp_rad",
            "hf_energy_5_15_rad2",
            "total_energy_0p5_20_rad2",
        ]].median(numeric_only=True)

        for _, r in real.iterrows():
            ratio_rows.append({
                "source": "real_over_sim_median",
                "run_id": r["run_id"],
                "side": side,
                "column": r["column"],
                "target_column": r.get("target_column", ""),
                "csv_path": "",
                "frames": "",
                "duration_s": "",
                "peak_band_hz": f"{PEAK_BAND[0]}-{PEAK_BAND[1]}",
                "hf_band_hz": f"{HF_BAND[0]}-{HF_BAND[1]}",
                "total_band_hz": f"{TOTAL_BAND[0]}-{TOTAL_BAND[1]}",
                "mean_rad": "",
                "osc_rms_rad": "",
                "peak_hz": "",
                "peak_amp_rad": "",
                "hf_energy_5_15_rad2": "",
                "total_energy_0p5_20_rad2": "",
                "hf_over_total": "",
                "hf_energy_5_15_x": ratio_or_nan(
                    r["hf_energy_5_15_rad2"], sim_ref["hf_energy_5_15_rad2"]
                ),
                "total_energy_0p5_20_x": ratio_or_nan(
                    r["total_energy_0p5_20_rad2"], sim_ref["total_energy_0p5_20_rad2"]
                ),
                "peak_amp_x": ratio_or_nan(r["peak_amp_rad"], sim_ref["peak_amp_rad"]),
                "sim_reference": "median_of_sim_files",
            })
    return rows + ratio_rows


def print_summary(rows):
    df = pd.DataFrame(rows)
    print("\n-- Ankle Roll spectral metrics --")
    print(f"  peak search band: {PEAK_BAND[0]:.1f}-{PEAK_BAND[1]:.1f} Hz")
    print(f"  high-frequency band: {HF_BAND[0]:.1f}-{HF_BAND[1]:.1f} Hz")
    print(f"  total energy band: {TOTAL_BAND[0]:.1f}-{TOTAL_BAND[1]:.1f} Hz")

    base = df[df["source"].isin(["sim", "real"])].copy()
    for _, r in base.iterrows():
        print(
            f"  {r['source']:4s} {r['side']:5s} {r['run_id']}: "
            f"peak_hz={r['peak_hz']:.3f} Hz  "
            f"peak_amp={r['peak_amp_rad']:.6f} rad  "
            f"hf_energy_5_15={r['hf_energy_5_15_rad2']:.8e} rad^2  "
            f"total_energy_0p5_20={r['total_energy_0p5_20_rad2']:.8e} rad^2  "
            f"hf_over_total={r['hf_over_total']:.3%}"
        )

    ratios = df[df["source"] == "real_over_sim_median"]
    for _, r in ratios.iterrows():
        print(
            f"  Real/SimMedian {r['side']:5s} {r['run_id']}: "
            f"hf_energy_5_15_x={r['hf_energy_5_15_x']:.3f}  "
            f"total_energy_0p5_20_x={r['total_energy_0p5_20_x']:.3f}  "
            f"peak_amp_x={r['peak_amp_x']:.3f}"
        )


def save_metrics(rows, out_dir, tag):
    csv_path = os.path.join(out_dir, f"sim_vs_real_ankle_{tag}_spectral_metrics.csv")
    json_path = os.path.join(out_dir, f"sim_vs_real_ankle_{tag}_spectral_metrics.json")
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"Saved metrics: {csv_path}")
    print(f"Saved metrics: {json_path}")
    return csv_path, json_path


def plot_fft_psd(logs, out_dir, tag, fs, max_plot_files):
    plot_logs = logs[:max_plot_files]
    fig, axes = plt.subplots(2, 2, figsize=(15, 9))
    fig.suptitle(
        f"Ankle Roll: Sim vs Real ({tag})\n"
        "Top: FFT amplitude  |  Bottom: Welch PSD",
        fontsize=11,
    )

    for ci, side in enumerate(SIDES):
        ax_f, ax_p = axes[0][ci], axes[1][ci]
        ax_f.set_title(f"{side.capitalize()} Ankle Roll - FFT")
        ax_p.set_title(f"{side.capitalize()} Ankle Roll - Welch PSD")

        for log in plot_logs:
            df = log["df"]
            col = find_actual_col(df, side)
            if not col:
                continue
            color = COLOR_SIM if log["source"] == "sim" else COLOR_REAL
            alpha = 0.65 if len(plot_logs) > 2 else 0.85
            sig = df[col].values
            freq, amp = fft_spectrum(sig, fs)
            pk_f, _ = top_peak(freq, amp)
            label = f"{log['source']} {log['run_id']} peak={pk_f:.2f}Hz"
            ax_f.plot(freq, amp, color=color, lw=1.0, alpha=alpha, label=label)

            fp, psd = psd_welch(sig, fs)
            ax_p.semilogy(fp, psd, color=color, lw=1.0, alpha=alpha, label=label)

        for ax in (ax_f, ax_p):
            ax.set_xlim(0, 15)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=7)
            for xv in [1.0, 2.0, 5.0]:
                ax.axvline(xv, color="gray", ls=":", lw=0.8, alpha=0.5)
        ax_f.set_ylabel("Amplitude [rad]")
        ax_p.set_ylabel("PSD [rad^2/Hz]")
        ax_p.set_xlabel("Frequency [Hz]")

    plt.tight_layout()
    out = os.path.join(out_dir, f"sim_vs_real_ankle_{tag}_fft.png")
    fig.savefig(out, dpi=150)
    plt.close()
    print(f"Saved: {out}")
    return out


def plot_timeseries(logs, out_dir, tag, max_plot_files):
    plot_logs = logs[:max_plot_files]
    ncols = max(1, len(plot_logs))
    fig, axes = plt.subplots(len(SIDES), ncols, figsize=(5 * ncols, 8), sharey="row")
    axes = np.asarray(axes).reshape(len(SIDES), ncols)
    fig.suptitle(
        f"Ankle Roll Time Series: Sim vs Real ({tag})\n"
        "solid=actual  dashed=target",
        fontsize=11,
    )

    for ri, side in enumerate(SIDES):
        for ci, log in enumerate(plot_logs):
            df = log["df"]
            ax = axes[ri][ci]
            actual_col = find_actual_col(df, side)
            target_col = find_target_col(df, side)
            color = COLOR_SIM if log["source"] == "sim" else COLOR_REAL
            if actual_col:
                ax.plot(df["t_s"].values, df[actual_col].values, color=color, lw=0.9, label="actual")
            if target_col:
                ax.plot(
                    df["t_s"].values,
                    df[target_col].values,
                    color="green",
                    lw=0.7,
                    ls="--",
                    alpha=0.6,
                    label="target",
                )
            ax.set_title(f"{log['source']} - {log['run_id']} - {side}")
            ax.set_xlabel("Time [s]")
            ax.set_ylabel("Position [rad]")
            ax.legend(fontsize=7)
            ax.grid(True, alpha=0.3)
            ax.set_xlim(left=0)

    plt.tight_layout()
    out = os.path.join(out_dir, f"sim_vs_real_ankle_{tag}_timeseries.png")
    fig.savefig(out, dpi=150)
    plt.close()
    print(f"Saved: {out}")
    return out


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    sim_paths = expand_inputs(args.sim)
    real_paths = expand_inputs(args.real)
    print("Loading sim ...")
    sim_logs = []
    for path in sim_paths:
        log = load_log(path, "sim", args.fs, skip_rows=args.sim_skip)
        sim_logs.append(log)
        print(f"  sim : {len(log['df'])} frames  {log['df']['t_s'].iloc[-1]:.1f}s  source={path}")

    print("Loading real ...")
    real_logs = []
    for path in real_paths:
        log = load_log(
            path,
            "real",
            args.fs,
            skip_rows=args.real_skip,
            trim=not args.no_trim_real,
            trim_win=args.trim_win,
            trim_thresh=args.trim_thresh,
        )
        real_logs.append(log)
        print(f"  real: {len(log['df'])} frames  {log['df']['t_s'].iloc[-1]:.1f}s  source={path}")

    logs = sim_logs + real_logs
    rows = metric_rows_for_logs(logs, args.fs)
    rows = add_ratio_rows(rows)
    print_summary(rows)
    save_metrics(rows, args.out_dir, args.tag)
    plot_fft_psd(logs, args.out_dir, args.tag, args.fs, args.max_plot_files)
    plot_timeseries(logs, args.out_dir, args.tag, args.max_plot_files)


if __name__ == "__main__":
    main()
