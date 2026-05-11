"""
Sim vs Real: Ankle Roll FFT comparison
Compares simulation (t23_joint_sim.csv) with best real-robot baseline (ff0 kd=1.5 May8).
Generates 3 figures:
  1. FFT amplitude spectrum (left & right ankle)
  2. Welch PSD (left & right ankle)
  3. Time series (actual + target, sim vs real side-by-side)
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import welch

FS = 100  # Hz

SIM_FILE  = r"d:\工作资料\02机器人\01F1项目\locomotion-lab\experiments\X1-12DOF\real_walking_0.6\部署代码仿真数据\t23_joint_sim.csv"
REAL_FILE = r"d:\工作资料\02机器人\01F1项目\sim-to-real\F1\test_logs\前馈正确测试数据\round_kp40_kd3_ff0_20260507_134731.csv"
OUT_DIR   = os.path.dirname(os.path.abspath(__file__))

COLOR_SIM  = "#1565C0"   # blue
COLOR_REAL = "#C62828"   # red


# ── helpers ──────────────────────────────────────────────────────────────────

def load_sim(path):
    df = pd.read_csv(path)
    df["t_s"] = (df["timestamp_ns"] - df["timestamp_ns"].iloc[0]) * 1e-9
    return df


def load_real(path, win=50, thresh=0.003):
    df = pd.read_csv(path)
    df = df.iloc[5:].reset_index(drop=True)
    df["t_s"] = (df["timestamp_ns"] - df["timestamp_ns"].iloc[0]) * 1e-9
    rename = {}
    for col in df.columns:
        if col.startswith("target_lpf_"):
            rename[col] = col.replace("target_lpf_", "pos_des_lpf_")
        elif col.startswith("target_"):
            rename[col] = col.replace("target_", "pos_des_raw_")
    if rename:
        df = df.rename(columns=rename)
    trim_col = next(
        (c for c in ["pos_left_knee_pitch_joint", "pos_left_hip_roll_joint"]
         if c in df.columns), None
    )
    if trim_col:
        roll_std = df[trim_col].rolling(win, min_periods=1).std().fillna(0)
        active = np.where(roll_std.values > thresh)[0]
        if len(active):
            df = df.iloc[:active[-1] + 1].reset_index(drop=True)
    return df


def fft_spectrum(sig, fs=FS):
    n = len(sig)
    amp  = 2.0 * np.abs(np.fft.rfft(sig * np.hanning(n))) / n
    freq = np.fft.rfftfreq(n, d=1.0 / fs)
    return freq, amp


def psd_welch(sig, fs=FS):
    nperseg = min(256, len(sig) // 4)
    return welch(sig, fs=fs, nperseg=nperseg, window="hann", scaling="density")


def top_peak(freq, amp, fmin=0.5, fmax=20.0):
    mask = (freq >= fmin) & (freq <= fmax)
    idx  = np.argmax(amp[mask])
    return freq[mask][idx], amp[mask][idx]


# ── load ─────────────────────────────────────────────────────────────────────

print("Loading sim ...")
df_sim  = load_sim(SIM_FILE)
print(f"  sim : {len(df_sim)} frames  {df_sim['t_s'].iloc[-1]:.1f}s")

print("Loading real ...")
df_real = load_real(REAL_FILE)
print(f"  real: {len(df_real)} frames  {df_real['t_s'].iloc[-1]:.1f}s")


# ── Fig 1+2: FFT & Welch PSD ──────────────────────────────────────────────────

fig, axes = plt.subplots(2, 2, figsize=(14, 9))
fig.suptitle("Ankle Roll: Sim vs Real\n"
             "Sim: t23_joint_sim  |  Real: ff=0 kd=0.5 (May7, oscillation present)\n"
             "Top: FFT amplitude  |  Bottom: Welch PSD", fontsize=11)

for ci, side in enumerate(["left", "right"]):
    col_sim  = f"pos_{side}_ankle_roll_joint"
    col_real = f"pos_{side}_ankle_roll_joint"
    ax_f, ax_p = axes[0][ci], axes[1][ci]
    ax_f.set_title(f"{side.capitalize()} Ankle Roll — FFT")
    ax_p.set_title(f"{side.capitalize()} Ankle Roll — Welch PSD")

    for label, df, col, color in [
        ("Sim (t23)",          df_sim,  col_sim,  COLOR_SIM),
        ("Real ff=0 kd=0.5",  df_real, col_real, COLOR_REAL),
    ]:
        if col not in df.columns:
            print(f"  [SKIP] {label} missing column {col}")
            continue
        sig = df[col].values

        freq, amp = fft_spectrum(sig)
        pk_f, pk_a = top_peak(freq, amp)
        ax_f.plot(freq, amp, color=color, lw=1.4, alpha=0.85,
                  label=f"{label} ({len(sig)/FS:.1f}s)  peak={pk_f:.2f}Hz")

        fp, psd = psd_welch(sig)
        ax_p.semilogy(fp, psd, color=color, lw=1.5, alpha=0.85,
                      label=f"{label}  peak={pk_f:.2f}Hz")

    for ax in (ax_f, ax_p):
        ax.set_xlim(0, 15)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
        for xv in [1.0, 2.0, 5.0]:
            ax.axvline(xv, color="gray", ls=":", lw=0.8, alpha=0.5)
    ax_f.set_ylabel("Amplitude [rad]")
    ax_p.set_ylabel("PSD [rad²/Hz]")
    ax_p.set_xlabel("Frequency [Hz]")

plt.tight_layout()
out1 = os.path.join(OUT_DIR, "sim_vs_real_ankle_fft.png")
fig.savefig(out1, dpi=150)
plt.close()
print(f"Saved: {out1}")


# ── Fig 3: Time series side-by-side ──────────────────────────────────────────

fig, axes = plt.subplots(2, 2, figsize=(16, 8), sharey="row")
fig.suptitle("Ankle Roll Time Series: Sim vs Real\n"
             "Sim: t23_joint_sim  |  Real: ff=0 kd=0.5 (May7, oscillation present)\n"
             "solid=actual  dashed=target", fontsize=11)

sides = ["left", "right"]
col_pairs = {
    "sim":  {s: (f"pos_{s}_ankle_roll_joint", f"target_{s}_ankle_roll_joint")         for s in sides},
    "real": {s: (f"pos_{s}_ankle_roll_joint", f"pos_des_raw_{s}_ankle_roll_joint")    for s in sides},
}

for ri, side in enumerate(sides):
    for ci, (src, src_key, df, color) in enumerate([
        ("Sim (t23)",         "sim",  df_sim,  COLOR_SIM),
        ("Real ff=0 kd=0.5",  "real", df_real, COLOR_REAL),
    ]):
        ax = axes[ri][ci]
        t  = df["t_s"].values
        col_act, col_tgt = col_pairs[src_key][side]

        if col_act in df.columns:
            ax.plot(t, df[col_act].values, color=color, lw=1.0, label="actual")
        if col_tgt in df.columns:
            ax.plot(t, df[col_tgt].values, color="green", lw=0.8, ls="--", alpha=0.6, label="target")

        ax.set_title(f"{src} — {side.capitalize()} Ankle Roll")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Position [rad]")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(left=0)

plt.tight_layout()
out2 = os.path.join(OUT_DIR, "sim_vs_real_ankle_timeseries.png")
fig.savefig(out2, dpi=150)
plt.close()
print(f"Saved: {out2}")


# ── Summary stats ─────────────────────────────────────────────────────────────

print("\n── Ankle Roll OSC (std of AC component) ──")
for side in sides:
    col = f"pos_{side}_ankle_roll_joint"
    for label, df in [("Sim", df_sim), ("Real", df_real)]:
        sig  = df[col].values
        mean = np.mean(sig)
        osc  = np.sqrt(np.mean((sig - mean)**2))
        print(f"  {label:4s} {side:5s}: mean={mean:+.4f} rad  osc={osc:.4f} rad")
