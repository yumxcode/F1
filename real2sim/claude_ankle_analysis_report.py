"""
claude_ankle_analysis_report.py
=================================
前6步触地期踝关节控制分析报告

数据来源（28号脚本生成的 CSV）：
  forward_x_failure_first6_delay_detail.csv
  forward_x_failure_first6_joint_change_frequency_detail.csv
  forward_x_failure_first6_touchdown_posture.csv

5 个分析模块：
  1. 延迟统计      — lag_ms，swing & touchdown 窗口，摆动腿（事件腿）
  2. 方向变化率    — dir-chg (Hz)，ankle pitch/roll，target & joint
  3. 振幅指标      — joint_amp, target_amp, amplitude_gain, joint_range_rad
  4. 触地瞬间姿态  — 前 N 步各关节角度（触地腿）
  5. 范围指标      — target_range, joint_range, target_range / joint_range

窗口定义：
  swing     = 触地前 350ms → 触地前 80ms（摆动末期，约 270ms）
  touchdown = 触地前 50ms  → 触地后 100ms（触地瞬间，约 150ms）

角色说明：
  delay_detail：side == touchdown_side → 摆动腿（事件腿）
  freq_detail ：swing 窗口的 event_leg / touchdown 窗口的 landing_leg = 摆动腿
"""

import os
import math
import numpy as np
import pandas as pd

# ─── 路径配置 ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABLE_DIR  = os.path.join(SCRIPT_DIR, "table", "forward_x_failure_first6")
PREFIX     = "forward_x_failure_first6_"

DELAY_CSV   = os.path.join(TABLE_DIR, PREFIX + "delay_detail.csv")
FREQ_CSV    = os.path.join(TABLE_DIR, PREFIX + "joint_change_frequency_detail.csv")
POSTURE_CSV = os.path.join(TABLE_DIR, PREFIX + "touchdown_posture.csv")

# ─── 参数 ──────────────────────────────────────────────────────────────────────
CORR_THRESH   = 0.20   # 仅统计相关系数达标的延迟样本
MAX_STEPS     = 10     # 触地姿态展示前 N 步（实际取 min(N, 可用步数)）

# case_label → (ankle_kp, ankle_kd)
CASE_KP_KD = {
    "25/0.4 all_ankles": (25.0, 0.4),
    "30/0.4 all_ankles": (30.0, 0.4),
    "35/0.5 all_ankles": (35.0, 0.5),
    "40/0.8 all_ankles": (40.0, 0.8),
    "2504": (25.0, 0.4),
    "3505": (35.0, 0.5),
    "4005": (40.0, 0.5),
    "5008": (50.0, 0.8),
}


# ─── 辅助函数 ──────────────────────────────────────────────────────────────────
def pct(arr, q):
    a = np.asarray(arr, dtype=float)
    a = a[~np.isnan(a)]
    return float(np.percentile(a, q)) if len(a) > 0 else np.nan


def fmt(v, decimals=1):
    """格式化数值，nan 显示为 '—'"""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{decimals}f}"


def sep(char="═", width=78):
    print(char * width)


def add_kp_kd(df: pd.DataFrame) -> pd.DataFrame:
    """给 delay_detail（无 ankle_kp 列）追加 ankle_kp / ankle_kd"""
    df = df.copy()
    df["ankle_kp"] = df["case_label"].map(lambda c: CASE_KP_KD.get(c, (np.nan,))[0])
    df["ankle_kd"] = df["case_label"].map(
        lambda c: CASE_KP_KD.get(c, (np.nan, np.nan))[1]
    )
    return df


def case_label_short(kp, kd):
    return f"Kp{int(kp)}/Kd{kd}"


def print_pivot(df, index, columns, values, aggfunc="mean", title="", decimals=2):
    """通用透视表打印（行=index，列=columns）"""
    if df.empty:
        print(f"  （无数据）")
        return
    piv = df.pivot_table(index=index, columns=columns, values=values,
                         aggfunc=aggfunc).round(decimals)
    if title:
        print(f"\n  {title}")
    # 列名扁平化
    if isinstance(piv.columns, pd.MultiIndex):
        piv.columns = [" | ".join(str(c) for c in col) for col in piv.columns]
    print("  " + piv.to_string().replace("\n", "\n  "))


# ══════════════════════════════════════════════════════════════════════════════
#  1. 延迟统计
# ══════════════════════════════════════════════════════════════════════════════
def section1_delay(delay_df: pd.DataFrame):
    sep()
    print("  § 1  延迟统计 — lag_ms（摆动腿 / swing & touchdown 窗口）")
    print()
    print("  过滤条件：corr ≥ 0.20（相关性达标的样本）")
    print("  摆动腿 = 当步触地腿（side == touchdown_side）")
    sep("─")

    df = add_kp_kd(delay_df)

    # 只保留摆动腿（事件腿）
    event = df[df["side"] == df["touchdown_side"]].copy()
    good  = event[event["corr"] >= CORR_THRESH].copy()
    good["case"] = good.apply(lambda r: case_label_short(r.ankle_kp, r.ankle_kd), axis=1)

    rows = []
    for (kp, kd, ds, win, ax), g in good.groupby(
            ["ankle_kp", "ankle_kd", "dataset", "window", "axis"], sort=True):
        lag = g["lag_ms"].values
        rows.append({
            "case": case_label_short(kp, kd),
            "dataset": ds,
            "window": win,
            "axis": f"ankle_{ax}",
            "n": len(lag),
            "p50_ms": round(pct(lag, 50), 1),
            "p75_ms": round(pct(lag, 75), 1),
            "p90_ms": round(pct(lag, 90), 1),
        })
    stat = pd.DataFrame(rows)

    for win in ["swing", "touchdown"]:
        for ax in ["ankle_pitch", "ankle_roll"]:
            sub = stat[(stat["window"] == win) & (stat["axis"] == ax)]
            if sub.empty:
                continue
            print(f"\n  [{win}]  {ax}  延迟 (ms)")
            piv = sub.pivot_table(
                index="case", columns="dataset",
                values=["p50_ms", "p75_ms", "p90_ms"], aggfunc="first"
            ).round(1)
            piv.columns = [f"{m}({d})" for m, d in piv.columns]
            desired = [f"{m}({d})" for d in ["real", "sim"]
                       for m in ["p50_ms", "p75_ms", "p90_ms"]]
            piv = piv[[c for c in desired if c in piv.columns]]
            print("  " + piv.to_string().replace("\n", "\n  "))

    return stat


# ══════════════════════════════════════════════════════════════════════════════
#  2. 方向变化率 (dir-chg)
# ══════════════════════════════════════════════════════════════════════════════
def section2_dirchg(freq_df: pd.DataFrame):
    sep()
    print("  § 2  方向变化率 — dir-chg (Hz)（ankle pitch & roll，摆动腿）")
    print()
    print("  dir-chg = 每秒信号方向（升/降）切换次数（反映抖动频率）")
    print("  摆动腿：swing 窗口 → event_leg；touchdown 窗口 → landing_leg")
    sep("─")

    # 筛选 ankle 关节，摆动腿角色
    event_roles = {"swing": "event_leg", "touchdown": "landing_leg"}
    ankle = freq_df[freq_df["joint"].str.startswith("ankle")].copy()
    ankle["axis"] = ankle["joint"]  # ankle_pitch / ankle_roll
    ankle["case"] = ankle.apply(lambda r: case_label_short(r.ankle_kp, r.ankle_kd), axis=1)

    rows = []
    for win, role in event_roles.items():
        sub = ankle[(ankle["window"] == win) & (ankle["role"] == role)]
        for (kp, kd, ds, ax), g in sub.groupby(
                ["ankle_kp", "ankle_kd", "dataset", "axis"], sort=True):
            rows.append({
                "case": case_label_short(kp, kd),
                "dataset": ds,
                "window": win,
                "axis": ax,
                "target_dirchg_p50": round(pct(g["target_direction_change_rate_hz"].values, 50), 2),
                "joint_dirchg_p50":  round(pct(g["joint_direction_change_rate_hz"].values,  50), 2),
            })
    stat = pd.DataFrame(rows)

    for win in ["swing", "touchdown"]:
        for ax in ["ankle_pitch", "ankle_roll"]:
            sub = stat[(stat["window"] == win) & (stat["axis"] == ax)]
            if sub.empty:
                continue
            print(f"\n  [{win}]  {ax}  方向变化率 (Hz)")
            piv = sub.pivot_table(
                index="case", columns="dataset",
                values=["target_dirchg_p50", "joint_dirchg_p50"], aggfunc="first"
            ).round(2)
            piv.columns = [f"{m}({d})" for m, d in piv.columns]
            desired = [f"{m}({d})" for d in ["real", "sim"]
                       for m in ["target_dirchg_p50", "joint_dirchg_p50"]]
            piv = piv[[c for c in desired if c in piv.columns]]
            print("  " + piv.to_string().replace("\n", "\n  "))

    return stat


# ══════════════════════════════════════════════════════════════════════════════
#  3. 振幅指标
# ══════════════════════════════════════════════════════════════════════════════
def section3_amplitude(freq_df: pd.DataFrame):
    sep()
    print("  § 3  振幅指标 — joint_amp / target_amp / amplitude_gain / joint_range_rad")
    print()
    print("  定义：")
    print("    target_amp      = target_range_rad / 2  （期望幅值半峰）")
    print("    joint_amp       = joint_range_rad  / 2  （实际幅值半峰）")
    print("    amplitude_gain  = joint_range_rad / target_range_rad（增益比，>1 表示放大）")
    print("    joint_range_rad = 关节角度峰峰值")
    print("  摆动腿：swing → event_leg；touchdown → landing_leg")
    sep("─")

    event_roles = {"swing": "event_leg", "touchdown": "landing_leg"}
    ankle = freq_df[freq_df["joint"].str.startswith("ankle")].copy()
    ankle["case"] = ankle.apply(lambda r: case_label_short(r.ankle_kp, r.ankle_kd), axis=1)

    rows = []
    for win, role in event_roles.items():
        sub = ankle[(ankle["window"] == win) & (ankle["role"] == role)]
        for (kp, kd, ds, joint), g in sub.groupby(
                ["ankle_kp", "ankle_kd", "dataset", "joint"], sort=True):
            tr = g["target_range_rad"].values
            jr = g["joint_range_rad"].values
            gain = jr / np.where(tr > 1e-6, tr, np.nan)
            rows.append({
                "case":           case_label_short(kp, kd),
                "dataset":        ds,
                "window":         win,
                "axis":           joint,
                "target_amp_p50": round(pct(tr, 50) / 2, 4),
                "joint_amp_p50":  round(pct(jr, 50) / 2, 4),
                "amp_gain_p50":   round(pct(gain, 50), 3),
                "joint_range_p50":round(pct(jr, 50), 4),
            })
    stat = pd.DataFrame(rows)

    for win in ["swing", "touchdown"]:
        for ax in ["ankle_pitch", "ankle_roll"]:
            sub = stat[(stat["window"] == win) & (stat["axis"] == ax)]
            if sub.empty:
                continue
            print(f"\n  [{win}]  {ax}  振幅指标")
            piv = sub.pivot_table(
                index="case", columns="dataset",
                values=["target_amp_p50", "joint_amp_p50", "amp_gain_p50",
                        "joint_range_p50"],
                aggfunc="first"
            ).round(4)
            piv.columns = [f"{m}({d})" for m, d in piv.columns]
            desired = [f"{m}({d})" for d in ["real", "sim"]
                       for m in ["target_amp_p50", "joint_amp_p50",
                                 "amp_gain_p50", "joint_range_p50"]]
            piv = piv[[c for c in desired if c in piv.columns]]
            print("  " + piv.to_string().replace("\n", "\n  "))

    return stat


# ══════════════════════════════════════════════════════════════════════════════
#  4. 触地瞬间姿态（前 N 步）
# ══════════════════════════════════════════════════════════════════════════════
def section4_posture(posture_df: pd.DataFrame):
    sep()
    print(f"  § 4  触地瞬间姿态（触地腿关节角度，前 {MAX_STEPS} 步）单位: rad")
    print()
    print("  触地腿 = touchdown_leg_*（即该步正在落地的腿）")
    print("  关节：hip_pitch / hip_roll / knee_pitch / ankle_pitch / ankle_roll / sole_roll")
    sep("─")

    JOINTS_MAP = {
        "hip_pitch":   "touchdown_leg_hip_pitch_rad",
        "hip_roll":    "touchdown_leg_hip_roll_rad",
        "knee_pitch":  "touchdown_leg_knee_pitch_rad",
        "ankle_pitch": "touchdown_leg_ankle_pitch_rad",
        "ankle_roll":  "touchdown_leg_ankle_roll_rad",
        "sole_roll":   "touchdown_leg_sole_roll_rad",
    }
    joint_names = list(JOINTS_MAP.keys())
    joint_cols  = list(JOINTS_MAP.values())

    df = posture_df[posture_df["step_index"] <= MAX_STEPS].copy()

    for ds in ["real", "sim"]:
        sub = df[df["dataset"] == ds].copy()
        if sub.empty:
            continue

        cases = sorted(sub["case_label"].unique())
        for case in cases:
            c = sub[sub["case_label"] == case].copy()
            c = c.sort_values("step_index")

            # 构建展示 DataFrame
            disp = c[["step_index", "touchdown_side"] + joint_cols].copy()
            disp = disp.rename(columns={"step_index": "step",
                                         "touchdown_side": "side"})
            rename = {v: k for k, v in JOINTS_MAP.items()}
            disp = disp.rename(columns=rename)

            print(f"\n  [{ds}]  {case}")
            print("  " + disp.to_string(index=False, float_format=lambda x: f"{x:+.4f}")
                  .replace("\n", "\n  "))

    return df


# ══════════════════════════════════════════════════════════════════════════════
#  5. 范围指标
# ══════════════════════════════════════════════════════════════════════════════
def section5_range(freq_df: pd.DataFrame):
    sep()
    print("  § 5  范围指标 — target_range / joint_range / target_range÷joint_range")
    print()
    print("  range = 窗口内信号峰峰值（rad）")
    print("  ratio = target_range / joint_range（>1 表示目标范围比关节大，跟踪不足）")
    print("  摆动腿：swing → event_leg；touchdown → landing_leg")
    sep("─")

    event_roles = {"swing": "event_leg", "touchdown": "landing_leg"}
    ankle = freq_df[freq_df["joint"].str.startswith("ankle")].copy()
    ankle["case"] = ankle.apply(lambda r: case_label_short(r.ankle_kp, r.ankle_kd), axis=1)

    rows = []
    for win, role in event_roles.items():
        sub = ankle[(ankle["window"] == win) & (ankle["role"] == role)]
        for (kp, kd, ds, joint), g in sub.groupby(
                ["ankle_kp", "ankle_kd", "dataset", "joint"], sort=True):
            tr = g["target_range_rad"].values
            jr = g["joint_range_rad"].values
            ratio = tr / np.where(jr > 1e-6, jr, np.nan)  # target/joint
            rows.append({
                "case":            case_label_short(kp, kd),
                "dataset":         ds,
                "window":          win,
                "axis":            joint,
                "target_range_p50": round(pct(tr, 50), 4),
                "joint_range_p50":  round(pct(jr, 50), 4),
                "tgt_jnt_ratio_p50":round(pct(ratio, 50), 3),
            })
    stat = pd.DataFrame(rows)

    for win in ["swing", "touchdown"]:
        for ax in ["ankle_pitch", "ankle_roll"]:
            sub = stat[(stat["window"] == win) & (stat["axis"] == ax)]
            if sub.empty:
                continue
            print(f"\n  [{win}]  {ax}  范围指标 (rad & ratio)")
            piv = sub.pivot_table(
                index="case", columns="dataset",
                values=["target_range_p50", "joint_range_p50", "tgt_jnt_ratio_p50"],
                aggfunc="first"
            ).round(4)
            piv.columns = [f"{m}({d})" for m, d in piv.columns]
            desired = [f"{m}({d})" for d in ["real", "sim"]
                       for m in ["target_range_p50", "joint_range_p50",
                                 "tgt_jnt_ratio_p50"]]
            piv = piv[[c for c in desired if c in piv.columns]]
            print("  " + piv.to_string().replace("\n", "\n  "))

    return stat


# ══════════════════════════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # 加载数据
    print(f"\n  加载数据...")
    delay_df   = pd.read_csv(DELAY_CSV)
    freq_df    = pd.read_csv(FREQ_CSV)
    posture_df = pd.read_csv(POSTURE_CSV)

    print(f"  delay_detail:   {len(delay_df)} 行，{delay_df['case_label'].nunique()} 个 case")
    print(f"  freq_detail:    {len(freq_df)} 行，{freq_df['case_label'].nunique()} 个 case")
    print(f"  posture_detail: {len(posture_df)} 行，步数 1~{posture_df['step_index'].max()}")

    sep("═")
    print("  踝关节控制分析报告  —  前6步触地期")
    sep("═")

    section1_delay(delay_df)
    section2_dirchg(freq_df)
    section3_amplitude(freq_df)
    section4_posture(posture_df)
    section5_range(freq_df)

    sep()
    print("  分析完成。")
    sep()


if __name__ == "__main__":
    main()
