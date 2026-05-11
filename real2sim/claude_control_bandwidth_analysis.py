"""
claude_control_bandwidth_analysis.py
========================================
分三步分析踝关节控制带宽：

  步骤1  分 Kp/Kd、分 sim/real、分摆动期/支撑期 统计延迟（lag_ms）
  步骤2  分 Kp/Kd、分 sim/real、分摆动期/支撑期 统计关节与目标频率
  步骤3  基于实测延迟 τ 与关节频率 f_joint 反推 J_eff，计算合理 Kp / Kd 范围

控制理论（PD + 纯延迟）：
  ωmax = π/(2τ)          纯延迟稳定带宽上限
  ωn   = √(Kp/J_eff)     开环自然频率
  ζ    = Kd/(2√(Kp·J_eff)) 阻尼比
  ωd   = ωn√(1-ζ²)       阻尼振荡频率

J_eff 由实测关节频率反推：J_eff = Kp / ωn_obs² = Kp / (2π·f_joint)²

输入（CSV）：
  forward_x_failure_first6_delay_detail.csv        （摆动末期/触地瞬间）
  claude_stance_delay_detail.csv                   （完整支撑期，由 claude_stance_delay_extract.py 生成）
  forward_x_failure_first6_joint_change_frequency_detail.csv

输出：
  claude_bandwidth_delay_table.csv           延迟统计汇总（含支撑期）
  claude_bandwidth_freq_table.csv            频率统计汇总
  claude_bandwidth_kpkd_recommendation.csv   Kp/Kd 推荐
  claude_bandwidth_visualization.html        可视化页面（在浏览器中打开）
"""

import os, json, math
import numpy as np
import pandas as pd

# ─── 路径 ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABLE_DIR  = os.path.join(SCRIPT_DIR, "table", "forward_x_failure_first6")
PREFIX     = "forward_x_failure_first6_"

DELAY_CSV  = os.path.join(TABLE_DIR, PREFIX + "delay_detail.csv")
STANCE_CSV = os.path.join(SCRIPT_DIR, "claude_stance_delay_detail.csv")
FREQ_CSV   = os.path.join(TABLE_DIR, PREFIX + "joint_change_frequency_detail.csv")

OUT_DELAY = os.path.join(SCRIPT_DIR, "claude_bandwidth_delay_table.csv")
OUT_FREQ  = os.path.join(SCRIPT_DIR, "claude_bandwidth_freq_table.csv")
OUT_REC   = os.path.join(SCRIPT_DIR, "claude_bandwidth_kpkd_recommendation.csv")
OUT_HTML  = os.path.join(SCRIPT_DIR, "claude_bandwidth_visualization.html")

# ─── 映射：case_label → (ankle_kp, ankle_kd) ───────────────────────────────
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

CORR_THRESH  = 0.20   # 仅统计有效相关样本
ZETA_TARGET  = 0.70   # 目标阻尼比
SAFETY       = 0.80   # 80% 带宽安全裕度

# ─── 辅助 ──────────────────────────────────────────────────────────────────
def pct(arr, q): return float(np.percentile(arr, q)) if len(arr) > 0 else np.nan
def hz2rads(f): return 2 * math.pi * f
def rads2hz(w): return w / (2 * math.pi)


# ══════════════════════════════════════════════════════════════════════════════
#  步骤 1：延迟统计（摆动末期 + 触地瞬间 + 完整支撑期）
# ══════════════════════════════════════════════════════════════════════════════
def step1_delay(delay_df, stance_df):
    print("\n" + "═"*72)
    print("  步骤1  延迟统计（lag_ms）— 分 Kp/Kd × dataset × side × window × axis")
    print("  窗口定义：")
    print("    swing     = 触地前350ms→触地前20ms （摆动末期330ms）")
    print("    touchdown = 触地前50ms→触地后100ms  （触地瞬间150ms）")
    print("    stance    = 触地[i]→触地[i+1]       （完整单腿支撑期）")
    print("  频率说明：joint_dominant_freq = 关节角度信号的主频（DFT），")
    print("           正常跟踪≈3Hz（步态频率），自激振荡时升至6Hz+")
    print("═"*72)

    # ── 处理 swing/touchdown 窗口（含 side 维度）─────────────────────────
    delay_df = delay_df.copy()
    delay_df["ankle_kp"] = delay_df["case_label"].map(lambda c: CASE_KP_KD.get(c, (np.nan,))[0])
    delay_df["ankle_kd"] = delay_df["case_label"].map(lambda c: CASE_KP_KD.get(c, (np.nan, np.nan))[1])
    good_old = delay_df[delay_df["corr"] >= CORR_THRESH].copy()

    rows = []
    for (kp, kd, ds, win, side, ax), g in good_old.groupby(
            ["ankle_kp", "ankle_kd", "dataset", "window", "side", "axis"], sort=True):
        lag = g["lag_ms"].values
        rows.append({
            "ankle_kp": kp, "ankle_kd": kd, "dataset": ds,
            "window": win, "side": side, "axis": ax, "role": "—",
            "n": len(lag),
            "p25_ms": round(pct(lag, 25), 1),
            "p50_ms": round(pct(lag, 50), 1),
            "p75_ms": round(pct(lag, 75), 1),
            "p90_ms": round(pct(lag, 90), 1),
        })

    # ── 处理支撑期（stance），分 role × side ──────────────────────────────
    if stance_df is not None and not stance_df.empty:
        good_st = stance_df[stance_df["corr"] >= CORR_THRESH].copy()
        for (kp, kd, ds, role, side, ax), g in good_st.groupby(
                ["ankle_kp", "ankle_kd", "dataset", "role", "side", "axis"], sort=True):
            lag = g["lag_ms"].values
            rows.append({
                "ankle_kp": kp, "ankle_kd": kd, "dataset": ds,
                "window": "stance", "side": side, "axis": ax, "role": role,
                "n": len(lag),
                "p25_ms": round(pct(lag, 25), 1),
                "p50_ms": round(pct(lag, 50), 1),
                "p75_ms": round(pct(lag, 75), 1),
                "p90_ms": round(pct(lag, 90), 1),
            })

    df = pd.DataFrame(rows)

    def _print_delay_table(sub, label):
        """sub 已经过滤好 window/role/ax，打印 case × dataset 透视表，列出 left/right"""
        if sub.empty: return
        sub = sub.copy()
        sub["case"] = sub["ankle_kp"].astype(int).astype(str) + "/" + sub["ankle_kd"].astype(str)
        # 行索引：case，列：(side, dataset) 组合
        sub["col"] = sub["side"] + "·" + sub["dataset"]
        pivot = sub.pivot_table(
            index="case", columns="col",
            values=["p50_ms", "p75_ms"], aggfunc="first"
        ).round(1)
        pivot.columns = [f"{v}({c})" for v, c in pivot.columns]
        # 排序列：left real, left sim, right real, right sim
        desired = []
        for s in ["left", "right"]:
            for d in ["real", "sim"]:
                for m in ["p50_ms", "p75_ms"]:
                    k = f"{m}({s}·{d})"
                    if k in pivot.columns:
                        desired.append(k)
        pivot = pivot[[c for c in desired if c in pivot.columns]]
        print(f"\n  {label}")
        print("  " + pivot.to_string().replace("\n", "\n  "))

    # ── 打印各窗口 ────────────────────────────────────────────────────────
    for win in ["swing", "touchdown"]:
        for ax in ["pitch", "roll"]:
            sub = df[(df["window"] == win) & (df["axis"] == ax)]
            _print_delay_table(sub, f"[{win} / ankle_{ax}]  延迟 p50/p75 (ms)  —  左右腿对比")

    if stance_df is not None:
        for role in ["stance_leg", "swing_leg"]:
            for ax in ["pitch", "roll"]:
                sub = df[(df["window"] == "stance") & (df["role"] == role) & (df["axis"] == ax)]
                _print_delay_table(sub, f"[stance / {role} / ankle_{ax}]  延迟 p50/p75 (ms)")

    # ── 三窗口 × 左右腿 对比摘要（real 端 p75）──────────────────────────
    print("\n" + "─"*72)
    print("  real 端 p75 延迟对比（三窗口 × 左/右腿）：")
    print(f"  {'场景':<30} {'left p75':>10} {'right p75':>10} {'差值':>8}")
    print("  " + "-"*62)
    real = df[df["dataset"] == "real"]
    for ax in ["pitch", "roll"]:
        for win, role, label in [
            ("swing",     "—",          f"摆动末期  ankle_{ax}"),
            ("touchdown", "—",          f"触地瞬间  ankle_{ax}"),
            ("stance",    "stance_leg", f"支撑-站立腿 ankle_{ax}"),
            ("stance",    "swing_leg",  f"支撑-摆动腿 ankle_{ax}"),
        ]:
            sub = real[(real["window"]==win) & (real["axis"]==ax)]
            if win == "stance":
                sub = sub[sub["role"] == role]
            lv = sub[sub["side"]=="left"]["p75_ms"].mean()
            rv = sub[sub["side"]=="right"]["p75_ms"].mean()
            diff = lv - rv if not (np.isnan(lv) or np.isnan(rv)) else float("nan")
            lstr = f"{lv:.1f}" if not np.isnan(lv) else " N/A"
            rstr = f"{rv:.1f}" if not np.isnan(rv) else " N/A"
            dstr = f"{diff:+.1f}" if not np.isnan(diff) else " N/A"
            print(f"  {label:<30} {lstr:>10} {rstr:>10} {dstr:>8}  ms")
        print()

    return df


# ══════════════════════════════════════════════════════════════════════════════
#  步骤 2：频率统计（ankle_pitch & ankle_roll）
# ══════════════════════════════════════════════════════════════════════════════
def step2_freq(freq_df):
    print("\n" + "═"*72)
    print("  步骤2  关节振荡频率统计（Hz）— 分 Kp/Kd × dataset × side × window × axis")
    print("  ★ joint_dominant_freq = ankle pitch/roll 关节角度信号的 DFT 主频")
    print("    · 正常跟踪时 ≈ 步态频率（~3Hz）")
    print("    · 发生自激振荡时升高（~6Hz+），是踝关节真实抖动频率的体现")
    print("    · target_dominant_freq = 期望轨迹的主频（由步态控制器决定，通常稳定）")
    print("    · joint/target 比值 > 1.5 说明关节在跟踪目标之上叠加了额外振荡")
    print("═"*72)

    ankle = freq_df[
        freq_df["joint"].str.contains("ankle") &
        freq_df["role"].isin(["event_leg", "stance_leg"])
    ].copy()
    ankle["axis"] = ankle["joint"].apply(lambda j: "pitch" if "pitch" in j else "roll")

    rows = []
    for (kp, kd, ds, win, side, ax), g in ankle.groupby(
            ["ankle_kp", "ankle_kd", "dataset", "window", "side", "axis"], sort=True):
        tf = g["target_dominant_freq_hz"].values
        jf = g["joint_dominant_freq_hz"].values
        rows.append({
            "ankle_kp": kp, "ankle_kd": kd, "dataset": ds,
            "window": win, "side": side, "axis": ax,
            "n": len(g),
            "target_freq_p50_hz": round(pct(tf, 50), 3),
            "joint_freq_p50_hz":  round(pct(jf, 50), 3),
            "joint_freq_p75_hz":  round(pct(jf, 75), 3),
            "ratio_p50":          round(pct(jf, 50) / max(pct(tf, 50), 0.01), 2),
        })

    df = pd.DataFrame(rows)

    def _print_freq_table(sub, label):
        if sub.empty: return
        sub = sub.copy()
        sub["case"] = sub["ankle_kp"].astype(int).astype(str) + "/" + sub["ankle_kd"].astype(str)
        sub["col"] = sub["side"] + "·" + sub["dataset"]
        # 打印 joint_freq_p50 和 ratio
        for metric, mname in [("joint_freq_p50_hz", "joint主频p50(Hz)"), ("ratio_p50", "joint/target比值")]:
            pivot = sub.pivot_table(
                index="case", columns="col", values=metric, aggfunc="first"
            ).round(3)
            # 排序列
            desired = [f"{s}·{d}" for s in ["left","right"] for d in ["real","sim"]]
            pivot = pivot[[c for c in desired if c in pivot.columns]]
            print(f"\n  {label}  —  {mname}")
            print("  " + pivot.to_string().replace("\n", "\n  "))

    for win in ["swing", "touchdown"]:
        for ax in ["pitch", "roll"]:
            sub = df[(df["window"] == win) & (df["axis"] == ax)]
            _print_freq_table(sub, f"[{win} / ankle_{ax}]")

    # ── 左右不对称摘要（real 端，joint/target 比值）────────────────────
    print("\n" + "─"*72)
    print("  real 端 joint/target 频率比值（比值>1.5 表示存在自激振荡）：")
    print(f"  {'场景':<28} {'left p50':>10} {'right p50':>10} {'差值':>8}")
    print("  " + "-"*60)
    real = df[df["dataset"] == "real"]
    for win in ["swing", "touchdown"]:
        for ax in ["pitch", "roll"]:
            sub = real[(real["window"]==win) & (real["axis"]==ax)]
            lv = sub[sub["side"]=="left"]["ratio_p50"].mean()
            rv = sub[sub["side"]=="right"]["ratio_p50"].mean()
            diff = lv - rv if not (np.isnan(lv) or np.isnan(rv)) else float("nan")
            flag = "  ★振荡" if (not np.isnan(lv) and lv > 1.5) or (not np.isnan(rv) and rv > 1.5) else ""
            print(f"  [{win}/ankle_{ax}]{'':<14} {lv:>10.2f} {rv:>10.2f} {diff:>+8.2f}{flag}")
        print()

    return df


# ══════════════════════════════════════════════════════════════════════════════
#  步骤 3：反推 J_eff，计算最优 Kp / Kd
# ══════════════════════════════════════════════════════════════════════════════
def step3_recommend(delay_df, freq_df, stance_df=None):
    print("\n" + "═"*72)
    print("  步骤3  反推 J_eff → 计算最优 Kp / Kd 范围")
    print("═"*72)

    # ── 3a. 从 freq 数据反推 J_eff（每条 case 独立计算）─────────────────────
    # 用 real + sim 合并，以 ankle_kp/ankle_kd 归组，取 p50 joint freq
    ankle = freq_df[
        freq_df["joint"].str.contains("ankle") &
        freq_df["role"].isin(["event_leg", "stance_leg"])
    ].copy()
    ankle["axis"] = ankle["joint"].apply(lambda j: "pitch" if "pitch" in j else "roll")

    j_eff_rows = []
    for (kp, kd, win, ax), g in ankle.groupby(
            ["ankle_kp", "ankle_kd", "window", "axis"], sort=True):
        jf_med = pct(g["joint_dominant_freq_hz"].values, 50)
        if np.isnan(jf_med) or jf_med <= 0: continue
        wn_obs = hz2rads(jf_med)          # 观测到的关节角频率 ≈ ωd ≈ ωn（ζ小时）
        j_eff  = kp / (wn_obs ** 2)
        j_eff_rows.append({
            "ankle_kp": kp, "ankle_kd": kd,
            "window": win, "axis": ax,
            "joint_freq_p50_hz": round(jf_med, 3),
            "omega_n_obs_rads":  round(wn_obs, 3),
            "j_eff":             round(j_eff, 6),
            "zeta_obs":          round(kd / (2 * math.sqrt(kp * j_eff)), 4),
        })
    j_eff_df = pd.DataFrame(j_eff_rows)

    print("\n  各案例反推的 J_eff（基于实测关节频率）：")
    print("  " + j_eff_df[["ankle_kp","ankle_kd","window","axis",
                             "joint_freq_p50_hz","omega_n_obs_rads","j_eff","zeta_obs"]
                            ].to_string(index=False).replace("\n","\n  "))

    # 每个 (window, axis) 的代表性 J_eff：取中位（过滤离群）
    j_eff_repr = (
        j_eff_df.groupby(["window","axis"])["j_eff"]
        .median().reset_index().rename(columns={"j_eff":"j_eff_median"})
    )
    print("\n  代表性 J_eff（按窗口/轴向中位）：")
    print("  " + j_eff_repr.to_string(index=False).replace("\n","\n  "))

    # ── 3b. 从 delay 数据取 real 端 p50/p75/p90（含支撑期）────────────
    delay_df2 = delay_df.copy()
    delay_df2["ankle_kp"] = delay_df2["case_label"].map(
        lambda c: CASE_KP_KD.get(c, (np.nan,))[0])
    delay_df2["ankle_kd"] = delay_df2["case_label"].map(
        lambda c: CASE_KP_KD.get(c, (np.nan, np.nan))[1])

    good_old = delay_df2[
        (delay_df2["corr"] >= CORR_THRESH) &
        (delay_df2["dataset"] == "real")
    ]
    tau_rows = []
    for (win, ax), g in good_old.groupby(["window","axis"]):
        tau_rows.append({
            "window": win, "axis": ax, "role": "—",
            "tau_p50": pct(g["lag_ms"].values, 50),
            "tau_p75": pct(g["lag_ms"].values, 75),
            "tau_p90": pct(g["lag_ms"].values, 90),
        })

    # 加入完整支撑期（分 stance_leg / swing_leg）
    if stance_df is not None and not stance_df.empty:
        good_st = stance_df[
            (stance_df["corr"] >= CORR_THRESH) &
            (stance_df["dataset"] == "real")
        ]
        for (ax, role), g in good_st.groupby(["axis","role"]):
            tau_rows.append({
                "window": "stance", "axis": ax, "role": role,
                "tau_p50": pct(g["lag_ms"].values, 50),
                "tau_p75": pct(g["lag_ms"].values, 75),
                "tau_p90": pct(g["lag_ms"].values, 90),
            })

    tau_stats = pd.DataFrame(tau_rows)
    tau_stats["tau_p50_s"] = tau_stats["tau_p50"] / 1000
    tau_stats["tau_p75_s"] = tau_stats["tau_p75"] / 1000
    tau_stats["tau_p90_s"] = tau_stats["tau_p90"] / 1000

    print("\n  real 端延迟统计（仅 corr≥0.2，含支撑期）：")
    print("  " + tau_stats[["window","role","axis","tau_p50","tau_p75","tau_p90"]
                            ].to_string(index=False).replace("\n","\n  "))

    # ── 3c. 汇合推荐 ─────────────────────────────────────────────────────
    # stance 窗口映射到 swing 的 J_eff（摆动期 J_eff 是最可靠的）
    stance_jeff_map = {"pitch": "swing", "roll": "swing"}

    rec_rows = []
    for _, tr in tau_stats.iterrows():
        win  = tr["window"]
        ax   = tr["axis"]
        role = tr.get("role", "—")
        # stance 用 swing 的 J_eff
        jwin = stance_jeff_map.get(ax, win) if win == "stance" else win
        j_row = j_eff_repr[(j_eff_repr["window"]==jwin) & (j_eff_repr["axis"]==ax)]
        if j_row.empty: continue
        j_eff = float(j_row["j_eff_median"].iloc[0])

        for pct_lbl, tau_s in [("p50", tr["tau_p50_s"]),
                                ("p75", tr["tau_p75_s"]),
                                ("p90", tr["tau_p90_s"])]:
            wmax = math.pi / (2 * tau_s)
            kp_max  = (wmax ** 2) * j_eff
            kp_opt  = (SAFETY * wmax) ** 2 * j_eff    # 80% 带宽
            kd_opt  = 2 * ZETA_TARGET * math.sqrt(kp_opt * j_eff)

            # 对当前各 Kp 诊断
            for kp_cand, kd_cand in [(25,0.4),(30,0.4),(35,0.5),(40,0.5),(40,0.8),(50,0.8)]:
                wn   = math.sqrt(kp_cand / j_eff)
                zeta = kd_cand / (2 * math.sqrt(kp_cand * j_eff))
                wd   = wn * math.sqrt(max(0, 1 - zeta**2))
                sm   = wmax - wn   # 正=稳定

                # 最小 Kd（相位补偿稳定）
                angle = wn * tau_s - math.pi / 2
                if angle <= 0:
                    kd_min = 0.0
                elif angle >= math.pi / 2 - 0.01:
                    kd_min = float("inf")
                else:
                    kd_min = kp_cand * math.tan(angle) / wn

                rec_rows.append({
                    "window": win, "axis": ax, "role": role, "delay_pct": pct_lbl,
                    "tau_ms": round(tau_s*1000, 1),
                    "j_eff": round(j_eff, 6),
                    "omega_max_rads": round(wmax, 3),
                    "kp_max_stable":  round(kp_max, 2),
                    "kp_opt_80pct":   round(kp_opt, 2),
                    "kd_opt_zeta07":  round(kd_opt, 4),
                    "kp_cand": kp_cand, "kd_cand": kd_cand,
                    "omega_n_rads":   round(wn, 3),
                    "zeta_current":   round(zeta, 3),
                    "omega_d_rads":   round(wd, 3),
                    "freq_d_hz":      round(rads2hz(wd), 3),
                    "stability_margin_rads": round(sm, 3),
                    "is_stable":      sm > 0,
                    "kd_min_for_stability": round(kd_min, 4) if math.isfinite(kd_min) else None,
                })

    rec_df = pd.DataFrame(rec_rows)

    # ── 打印核心表：swing × roll/pitch × p75（最苛刻）────────────────────
    print("\n" + "─"*72)
    print("  [摆动期 / p75 延迟] 各 Kp/Kd 稳定性诊断 + 推荐")
    print("─"*72)
    for ax in ["pitch", "roll"]:
        sub = rec_df[
            (rec_df["window"]=="swing") & (rec_df["axis"]==ax) &
            (rec_df["delay_pct"]=="p75")
        ].copy()
        if sub.empty: continue
        tau_ms = sub["tau_ms"].iloc[0]
        kp_max = sub["kp_max_stable"].iloc[0]
        kp_opt = sub["kp_opt_80pct"].iloc[0]
        kd_opt = sub["kd_opt_zeta07"].iloc[0]
        j_eff_v= sub["j_eff"].iloc[0]
        wmax_v = sub["omega_max_rads"].iloc[0]
        print(f"\n  ankle_{ax}  τ_p75={tau_ms}ms  J_eff={j_eff_v:.5f}  ωmax={wmax_v:.2f}rad/s")
        print(f"    ★ Kp_max（无Kd稳定上限） = {kp_max:.1f}")
        print(f"    ★ Kp_opt（80%安全裕度）  = {kp_opt:.1f}")
        print(f"    ★ Kd_opt（ζ=0.7@Kp_opt）= {kd_opt:.3f}")
        print(f"\n    当前各案例诊断：")
        print(f"    {'Kp':>5} {'Kd':>5} {'ωn':>8} {'ζ':>6} {'裕量(r/s)':>10} {'稳定?':>7} {'Kd_min':>8}")
        print("    " + "-"*55)
        for _, r in sub.iterrows():
            ok = "✓" if r["is_stable"] else "✗"
            kd_min_s = f"{r['kd_min_for_stability']:.3f}" if r["kd_min_for_stability"] is not None else " inf"
            print(f"    {r['kp_cand']:>5} {r['kd_cand']:>5.2f} {r['omega_n_rads']:>8.3f} "
                  f"{r['zeta_current']:>6.3f} {r['stability_margin_rads']:>10.3f} "
                  f"{ok:>7} {kd_min_s:>8}")

    # ── 支撑期 + 触地瞬间摘要 ───────────────────────────────────────────
    print(f"\n  [支撑期 stance / p75] 摘要（完整单腿支撑期）")
    for ax in ["pitch", "roll"]:
        for role in ["stance_leg", "swing_leg"]:
            sub = rec_df[
                (rec_df["window"]=="stance") & (rec_df["role"]==role) &
                (rec_df["axis"]==ax) & (rec_df["delay_pct"]=="p75")
            ]
            if sub.empty: continue
            r = sub.iloc[0]
            print(f"  ankle_{ax} [{role}]: τ={r['tau_ms']}ms  "
                  f"Kp_max={r['kp_max_stable']:.1f}  "
                  f"Kp_opt={r['kp_opt_80pct']:.1f}  Kd_opt={r['kd_opt_zeta07']:.3f}")

    print(f"\n  [触地瞬间 touchdown / p75] 摘要")
    for ax in ["pitch", "roll"]:
        sub = rec_df[(rec_df["window"]=="touchdown")&(rec_df["axis"]==ax)&(rec_df["delay_pct"]=="p75")]
        if sub.empty: continue
        r = sub.iloc[0]
        print(f"  ankle_{ax}: τ={r['tau_ms']}ms  Kp_max={r['kp_max_stable']:.0f}  "
              f"Kp_opt={r['kp_opt_80pct']:.0f}  Kd_opt={r['kd_opt_zeta07']:.2f}")

    # ── 综合最坏情况摘要 ────────────────────────────────────────────────
    print("\n" + "═"*72)
    print("  综合最坏情况（三窗口 p75 最大延迟）")
    print("═"*72)
    print(f"  {'场景':<30} {'τ_p75(ms)':>10} {'Kp_max':>8} {'Kp_opt':>8} {'Kd_opt':>8}")
    print("  " + "-"*68)
    scenarios = [
        ("swing", "—",          "摆动末期"),
        ("touchdown", "—",      "触地瞬间"),
        ("stance", "stance_leg","支撑期-站立腿"),
        ("stance", "swing_leg", "支撑期-摆动腿 ★最苛刻"),
    ]
    for ax in ["pitch", "roll"]:
        for win, role, label in scenarios:
            sub = rec_df[
                (rec_df["window"]==win) & (rec_df["axis"]==ax) &
                (rec_df["delay_pct"]=="p75") &
                (rec_df["role"]==role if "role" in rec_df.columns else True)
            ]
            if "role" in rec_df.columns:
                sub = rec_df[
                    (rec_df["window"]==win) & (rec_df["role"]==role) &
                    (rec_df["axis"]==ax) & (rec_df["delay_pct"]=="p75")
                ]
            if sub.empty: continue
            r = sub.iloc[0]
            print(f"  ankle_{ax} {label:<22} {r['tau_ms']:>10.0f} "
                  f"{r['kp_max_stable']:>8.1f} {r['kp_opt_80pct']:>8.1f} "
                  f"{r['kd_opt_zeta07']:>8.3f}")
        print()

    return rec_df, j_eff_df, tau_stats


# ══════════════════════════════════════════════════════════════════════════════
#  HTML 可视化
# ══════════════════════════════════════════════════════════════════════════════
def build_html(delay_table, freq_table, rec_df, j_eff_df, tau_stats):
    """生成交互式 HTML 可视化页面"""

    # 准备 JSON 数据
    data = {
        "delay": delay_table.fillna("").to_dict(orient="records"),
        "freq":  freq_table.fillna("").to_dict(orient="records"),
        "rec":   rec_df.fillna("").to_dict(orient="records"),
        "j_eff": j_eff_df.fillna("").to_dict(orient="records"),
        "tau_stats": tau_stats.fillna("").to_dict(orient="records"),
    }
    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>控制带宽分析 — 踝关节 Kp/Kd 推荐</title>
<style>
:root {{
  --bg:#0f1117; --panel:#1a1d26; --border:#2d3142;
  --text:#e8eaf0; --muted:#7c8499; --accent:#4f91f5;
  --green:#3ecf8e; --red:#f5655d; --orange:#f5a623; --blue:#4f91f5;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font:14px/1.6 'Segoe UI',sans-serif;padding:20px}}
h1{{font-size:1.4rem;margin-bottom:4px;color:var(--accent)}}
.subtitle{{color:var(--muted);font-size:.85rem;margin-bottom:20px}}
.tabs{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
.tab{{padding:7px 18px;border:1px solid var(--border);border-radius:20px;cursor:pointer;
      background:var(--panel);color:var(--muted);font-size:.85rem;transition:.2s}}
.tab.active{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.section{{display:none}}.section.active{{display:block}}
.controls{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;align-items:center}}
.controls label{{color:var(--muted);font-size:.82rem}}
select{{background:var(--panel);color:var(--text);border:1px solid var(--border);
        border-radius:6px;padding:4px 10px;font-size:.85rem;cursor:pointer}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}}
.card{{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:16px}}
.card h3{{font-size:.92rem;margin-bottom:12px;color:var(--accent);border-bottom:1px solid var(--border);padding-bottom:8px}}
table{{width:100%;border-collapse:collapse;font-size:.82rem}}
th{{background:#1e2130;color:var(--muted);text-transform:uppercase;font-size:.72rem;
    letter-spacing:.5px;padding:6px 8px;text-align:right;position:sticky;top:0}}
th:first-child{{text-align:left}}
td{{padding:5px 8px;border-bottom:1px solid var(--border);text-align:right}}
td:first-child{{text-align:left;color:var(--muted)}}
tr:hover td{{background:#1e2130}}
.stable{{color:var(--green)}} .unstable{{color:var(--red)}}
.highlight{{color:var(--orange);font-weight:600}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.75rem;font-weight:600}}
.badge-stable{{background:rgba(62,207,142,.15);color:var(--green)}}
.badge-unstable{{background:rgba(245,101,93,.15);color:var(--red)}}
.rec-box{{background:linear-gradient(135deg,rgba(79,145,245,.08),rgba(79,145,245,.03));
          border:1px solid rgba(79,145,245,.3);border-radius:10px;padding:20px;margin-bottom:16px}}
.rec-box h3{{color:var(--accent);margin-bottom:12px;font-size:1rem}}
.rec-row{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:8px}}
.rec-item{{background:var(--panel);border-radius:8px;padding:12px;text-align:center}}
.rec-item .val{{font-size:1.6rem;font-weight:700;color:var(--orange)}}
.rec-item .lbl{{font-size:.75rem;color:var(--muted);margin-top:4px}}
.bar-wrap{{height:8px;background:var(--border);border-radius:4px;overflow:hidden;margin-top:4px}}
.bar{{height:100%;border-radius:4px;transition:.4s}}
.info{{color:var(--muted);font-size:.8rem;margin-top:8px}}
</style>
</head>
<body>
<h1>踝关节控制带宽分析 & Kp/Kd 推荐</h1>
<p class="subtitle">基于 forward_x_failure 前6步 实测延迟 & 关节频率数据 · claude_control_bandwidth_analysis.py</p>

<div class="tabs">
  <div class="tab active" onclick="showTab('delay')">① 延迟统计</div>
  <div class="tab" onclick="showTab('freq')">② 频率统计</div>
  <div class="tab" onclick="showTab('rec')">③ Kp/Kd 推荐</div>
  <div class="tab" onclick="showTab('diag')">④ 稳定性诊断</div>
</div>

<!-- ① 延迟统计 -->
<div class="section active" id="sec-delay">
  <div class="controls">
    <label>Phase</label>
    <select id="dl-win" onchange="renderDelay()">
      <option value="swing">摆动期 swing</option>
      <option value="touchdown">支撑期 touchdown</option>
    </select>
    <label>Axis</label>
    <select id="dl-ax" onchange="renderDelay()">
      <option value="pitch">pitch</option>
      <option value="roll">roll</option>
    </select>
  </div>
  <div class="grid" id="delay-grid"></div>
</div>

<!-- ② 频率统计 -->
<div class="section" id="sec-freq">
  <div class="controls">
    <label>Phase</label>
    <select id="fq-win" onchange="renderFreq()">
      <option value="swing">摆动期 swing</option>
      <option value="touchdown">支撑期 touchdown</option>
    </select>
    <label>Axis</label>
    <select id="fq-ax" onchange="renderFreq()">
      <option value="pitch">pitch</option>
      <option value="roll">roll</option>
    </select>
  </div>
  <div class="grid" id="freq-grid"></div>
</div>

<!-- ③ Kp/Kd 推荐 -->
<div class="section" id="sec-rec">
  <div id="rec-container"></div>
</div>

<!-- ④ 稳定性诊断 -->
<div class="section" id="sec-diag">
  <div class="controls">
    <label>Phase</label>
    <select id="dg-win" onchange="renderDiag()">
      <option value="swing">摆动期 swing</option>
      <option value="touchdown">支撑期 touchdown</option>
    </select>
    <label>Axis</label>
    <select id="dg-ax" onchange="renderDiag()">
      <option value="pitch">pitch</option>
      <option value="roll">roll</option>
    </select>
    <label>Delay Pct</label>
    <select id="dg-pct" onchange="renderDiag()">
      <option value="p50">p50 (中位)</option>
      <option value="p75" selected>p75 (推荐基准)</option>
      <option value="p90">p90 (最保守)</option>
    </select>
  </div>
  <div id="diag-container"></div>
</div>

<script>
const DATA = {json_str};

function showTab(name) {{
  document.querySelectorAll('.tab').forEach((t,i) => {{
    const names=['delay','freq','rec','diag'];
    t.classList.toggle('active', names[i]===name);
  }});
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('sec-'+name).classList.add('active');
  if(name==='delay') renderDelay();
  if(name==='freq')  renderFreq();
  if(name==='rec')   renderRec();
  if(name==='diag')  renderDiag();
}}

/* ─── 延迟统计 ─────────────────────────────────────────────────────── */
function renderDelay() {{
  const win = document.getElementById('dl-win').value;
  const ax  = document.getElementById('dl-ax').value;
  const rows = DATA.delay.filter(r => r.window===win && r.axis===ax);

  // 按 dataset 分组
  const real = rows.filter(r=>r.dataset==='real').sort((a,b)=>a.ankle_kp-b.ankle_kp);
  const sim  = rows.filter(r=>r.dataset==='sim').sort((a,b)=>a.ankle_kp-b.ankle_kp);

  const maxTau = Math.max(...rows.map(r=>r.p90_ms||0), 1);

  function makeTable(arr, title) {{
    if(!arr.length) return '';
    let h = `<div class="card"><h3>${{title}}</h3><table>
      <tr><th>Kp/Kd</th><th>p25</th><th>p50</th><th>p75</th><th>p90</th><th>分布</th></tr>`;
    for(const r of arr) {{
      const pct = (r.p75_ms/maxTau*100).toFixed(0);
      const col = r.p75_ms>100?'var(--red)':r.p75_ms>60?'var(--orange)':'var(--green)';
      h += `<tr>
        <td>${{r.ankle_kp}}/${{r.ankle_kd}}</td>
        <td>${{r.p25_ms}}</td><td>${{r.p50_ms}}</td>
        <td class="highlight">${{r.p75_ms}}</td><td>${{r.p90_ms}}</td>
        <td style="width:80px"><div class="bar-wrap"><div class="bar" style="width:${{pct}}%;background:${{col}}"></div></div></td>
      </tr>`;
    }}
    h += '</table></div>';
    return h;
  }}

  document.getElementById('delay-grid').innerHTML =
    makeTable(real,'🔬 Real — 延迟 lag_ms') + makeTable(sim,'🖥️ Sim — 延迟 lag_ms');
}}

/* ─── 频率统计 ─────────────────────────────────────────────────────── */
function renderFreq() {{
  const win = document.getElementById('fq-win').value;
  const ax  = document.getElementById('fq-ax').value;
  const rows = DATA.freq.filter(r => r.window===win && r.axis===ax);

  const real = rows.filter(r=>r.dataset==='real').sort((a,b)=>a.ankle_kp-b.ankle_kp);
  const sim  = rows.filter(r=>r.dataset==='sim').sort((a,b)=>a.ankle_kp-b.ankle_kp);
  const maxF = Math.max(...rows.map(r=>r.joint_freq_p90_hz||0), 1);

  function makeTable(arr, title) {{
    if(!arr.length) return '';
    let h = `<div class="card"><h3>${{title}}</h3><table>
      <tr><th>Kp/Kd</th><th>target p50</th><th>joint p50</th><th>joint p75</th><th>分布</th></tr>`;
    for(const r of arr) {{
      const ratio = r.joint_freq_p50_hz/Math.max(r.target_freq_p50_hz,0.01);
      const col = ratio>1.5?'var(--red)':ratio>1.1?'var(--orange)':'var(--green)';
      const pct = (r.joint_freq_p50_hz/maxF*100).toFixed(0);
      h += `<tr>
        <td>${{r.ankle_kp}}/${{r.ankle_kd}}</td>
        <td>${{r.target_freq_p50_hz}}</td>
        <td class="highlight" style="color:${{col}}">${{r.joint_freq_p50_hz}}</td>
        <td>${{r.joint_freq_p75_hz}}</td>
        <td style="width:80px"><div class="bar-wrap"><div class="bar" style="width:${{pct}}%;background:${{col}}"></div></div></td>
      </tr>`;
    }}
    h += '</table></div>';
    return h;
  }}
  document.getElementById('freq-grid').innerHTML =
    makeTable(real,'🔬 Real — 频率 Hz') + makeTable(sim,'🖥️ Sim — 频率 Hz');
}}

/* ─── Kp/Kd 推荐 ───────────────────────────────────────────────────── */
function renderRec() {{
  const ts = DATA.tau_stats;
  const je = DATA.j_eff;

  let html = '';
  const cases = [
    {{win:'swing',   ax:'pitch', label:'摆动期 ankle_pitch'}},
    {{win:'swing',   ax:'roll',  label:'摆动期 ankle_roll'}},
    {{win:'touchdown',ax:'pitch',label:'支撑期 ankle_pitch'}},
    {{win:'touchdown',ax:'roll', label:'支撑期 ankle_roll'}},
  ];

  for(const c of cases) {{
    const trow = ts.find(r=>r.window===c.win&&r.axis===c.ax);
    const jrow = je.filter(r=>r.window===c.win&&r.axis===c.ax);
    if(!trow||!jrow.length) continue;
    const j_eff = jrow.reduce((s,r)=>s+r.j_eff,0)/jrow.length;
    const pi = Math.PI;
    function rec(tau_s) {{
      const wmax = pi/(2*tau_s);
      const kp_max = wmax*wmax*j_eff;
      const kp_opt = 0.64*kp_max;
      const kd_opt = 2*0.7*Math.sqrt(kp_opt*j_eff);
      return {{wmax:wmax.toFixed(2), kp_max:kp_max.toFixed(1), kp_opt:kp_opt.toFixed(1), kd_opt:kd_opt.toFixed(3)}};
    }}
    const r50=rec(trow.tau_p50_s), r75=rec(trow.tau_p75_s), r90=rec(trow.tau_p90_s);

    html += `<div class="rec-box">
      <h3>📐 ${{c.label}}</h3>
      <div class="info">J_eff ≈ ${{j_eff.toFixed(5)}} &nbsp;|&nbsp;
        τ: p50=${{trow.tau_p50}}ms · p75=${{trow.tau_p75}}ms · p90=${{trow.tau_p90}}ms</div>
      <table style="margin-top:12px">
        <tr><th>场景</th><th>τ(ms)</th><th>ωmax(r/s)</th>
            <th>Kp_max</th><th>Kp_opt(80%)</th><th>Kd_opt(ζ=0.7)</th></tr>
        <tr><td>p50</td><td>${{trow.tau_p50}}</td><td>${{r50.wmax}}</td>
            <td>${{r50.kp_max}}</td><td class="highlight">${{r50.kp_opt}}</td><td class="highlight">${{r50.kd_opt}}</td></tr>
        <tr><td>p75 ⭐</td><td>${{trow.tau_p75}}</td><td>${{r75.wmax}}</td>
            <td>${{r75.kp_max}}</td><td class="highlight">${{r75.kp_opt}}</td><td class="highlight">${{r75.kd_opt}}</td></tr>
        <tr><td>p90</td><td>${{trow.tau_p90}}</td><td>${{r90.wmax}}</td>
            <td>${{r90.kp_max}}</td><td class="highlight">${{r90.kp_opt}}</td><td class="highlight">${{r90.kd_opt}}</td></tr>
      </table>
    </div>`;
  }}
  document.getElementById('rec-container').innerHTML = html;
}}

/* ─── 稳定性诊断 ────────────────────────────────────────────────────── */
function renderDiag() {{
  const win = document.getElementById('dg-win').value;
  const ax  = document.getElementById('dg-ax').value;
  const pct = document.getElementById('dg-pct').value;

  const rows = DATA.rec.filter(r=>r.window===win&&r.axis===ax&&r.delay_pct===pct);
  if(!rows.length){{ document.getElementById('diag-container').innerHTML='<p style="color:var(--muted)">无数据</p>'; return; }}

  const info = rows[0];
  const maxWn = Math.max(...rows.map(r=>r.omega_n_rads),1);

  let html = `<div style="margin-bottom:12px;color:var(--muted);font-size:.85rem">
    τ=${{info.tau_ms}}ms &nbsp;|&nbsp; ωmax=${{info.omega_max_rads}} rad/s &nbsp;|&nbsp;
    Kp_max=${{info.kp_max_stable}} &nbsp;|&nbsp; Kp_opt(80%)=${{info.kp_opt_80pct}} &nbsp;|&nbsp;
    J_eff=${{info.j_eff}}
  </div>
  <div class="card"><table>
    <tr><th>Kp</th><th>Kd</th><th>ωn (r/s)</th><th>ζ</th><th>ωd (r/s)</th>
        <th>fd (Hz)</th><th>稳定裕量</th><th>Kd_min</th><th>状态</th><th>ωn分布</th></tr>`;

  for(const r of rows) {{
    const stable = r.is_stable;
    const pct2 = (r.omega_n_rads/info.omega_max_rads*100).toFixed(0);
    const col = stable?'var(--green)':r.stability_margin_rads>-2?'var(--orange)':'var(--red)';
    const badge = stable
      ? '<span class="badge badge-stable">✓ 稳定</span>'
      : '<span class="badge badge-unstable">✗ 不稳</span>';
    const kdm = r.kd_min_for_stability!=null ? r.kd_min_for_stability : '∞';
    html += `<tr>
      <td>${{r.kp_cand}}</td><td>${{r.kd_cand}}</td>
      <td style="color:${{col}}">${{r.omega_n_rads}}</td>
      <td>${{r.zeta_current}}</td>
      <td>${{r.omega_d_rads}}</td>
      <td>${{r.freq_d_hz}}</td>
      <td style="color:${{col}}">${{r.stability_margin_rads}}</td>
      <td>${{kdm}}</td>
      <td>${{badge}}</td>
      <td style="width:100px">
        <div class="bar-wrap"><div class="bar" style="width:${{Math.min(pct2,100)}}%;background:${{col}}"></div></div>
        <span style="font-size:.7rem;color:var(--muted)">${{pct2}}% of ωmax</span>
      </td>
    </tr>`;
  }}
  html += '</table></div>';
  document.getElementById('diag-container').innerHTML = html;
}}

// 初始化
renderDelay();
</script>
</body>
</html>"""
    return html


# ══════════════════════════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 72)
    print("  踝关节控制带宽分析  claude_control_bandwidth_analysis.py")
    print("=" * 72)

    delay_df  = pd.read_csv(DELAY_CSV)
    freq_df   = pd.read_csv(FREQ_CSV)
    stance_df = pd.read_csv(STANCE_CSV) if os.path.exists(STANCE_CSV) else None
    if stance_df is None:
        print("  [WARN] 未找到支撑期数据，请先运行 claude_stance_delay_extract.py")

    delay_table = step1_delay(delay_df, stance_df)
    freq_table  = step2_freq(freq_df)
    rec_df, j_eff_df, tau_stats = step3_recommend(delay_df, freq_df, stance_df)

    # 保存 CSV
    delay_table.to_csv(OUT_DELAY, index=False)
    freq_table.to_csv(OUT_FREQ, index=False)
    rec_df.to_csv(OUT_REC, index=False)

    # 生成 HTML
    html = build_html(delay_table, freq_table, rec_df, j_eff_df, tau_stats)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n[输出]")
    print(f"  {OUT_DELAY}")
    print(f"  {OUT_FREQ}")
    print(f"  {OUT_REC}")
    print(f"  {OUT_HTML}  ← 用浏览器打开查看可视化")
    print("\n  ✓ 完成。")
    print("=" * 72)


if __name__ == "__main__":
    main()
