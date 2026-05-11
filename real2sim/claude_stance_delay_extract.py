"""
claude_stance_delay_extract.py
=================================
补充"完整支撑期"的踝关节延迟统计。

现有 delay_detail.csv 的窗口定义：
  swing     = 触地前350ms → 触地前20ms  （摆动末期330ms）
  touchdown = 触地前50ms  → 触地后100ms  （触地瞬间150ms）

本脚本新增：
  stance    = 触地[i] → 触地[i+1]         （完整单腿支撑期，约300~500ms）

支撑期定义：
  - 按时间排列所有 touchdown 事件 e[0..N]
  - e[i] 落地后直到 e[i+1] 落地前，即为 e[i].side 的支撑期
  - 在此窗口内对两条腿（支撑腿/摆动腿）各计算 ankle pitch/roll 的 lag_ms

输出：
  claude_stance_delay_detail.csv   — 与 delay_detail.csv 同格式，window="stance"
"""

import os, sys, csv, math, importlib.util
import numpy as np

# ─── 路径配置 ──────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)   # repo root（real2sim 的上级）
OMA_SCRIPTS = os.path.join(BASE_DIR, ".oma", "sim2real", "plans",
                            "forward_x_failure", "scripts")
TABLE_DIR  = os.path.join(SCRIPT_DIR, "table", "forward_x_failure_first6")
OUT_CSV    = os.path.join(SCRIPT_DIR, "claude_stance_delay_detail.csv")

# ─── Case 定义（与 script 28 完全一致）────────────────────────────────────
REAL_CASES = [
    ("real", "25/0.4 all_ankles", 25.0, 0.4,
     "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100024.csv"),
    ("real", "30/0.4 all_ankles", 30.0, 0.4,
     "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100314.csv"),
    ("real", "35/0.5 all_ankles", 35.0, 0.5,
     "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_100705.csv"),
    ("real", "40/0.8 all_ankles", 40.0, 0.8,
     "test_logs/data_csv/t27_tracking_lag_b1_diag_20260430_101404.csv"),
]
SIM_CASES = [
    ("sim", "2504", 25.0, 0.4,
     "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133905_2504.csv"),
    ("sim", "3505", 35.0, 0.5,
     "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_133024_3505.csv"),
    ("sim", "4005", 40.0, 0.5,
     "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134153_4005.csv"),
    ("sim", "5008", 50.0, 0.8,
     "test_logs/data_csv/sim/t27_tracking_lag_b1_diag_20260506_134417_5008.csv"),
]
STEP_LIMIT = 6    # 只取前6步

# ─── 参数（与 script 28 一致）─────────────────────────────────────────────
STANCE_MAX_LAG_SEC   = 0.20   # lag 搜索上限
MIN_SAMPLE_POINTS    = 8
DIFF_EPS_RAD         = 1e-4
CORR_THRESHOLD       = 0.20

# ─── 加载 ROUND3A 模块 ─────────────────────────────────────────────────────
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

ROUND3A = load_module(
    "round3a_plan",
    os.path.join(OMA_SCRIPTS, "03a_round3_landing_window_analysis.py"),
)

# ─── 工具函数（复制自 script 28）──────────────────────────────────────────
def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    return sum(valid) / len(valid) if valid else math.nan

def median(values):
    valid = sorted(v for v in values if isinstance(v, (int, float)) and not math.isnan(v))
    if not valid: return math.nan
    n = len(valid)
    return (valid[n // 2 - 1] + valid[n // 2]) / 2.0 if n % 2 == 0 else valid[n // 2]

def rms(values):
    valid = [float(v) for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    return math.sqrt(mean([v * v for v in valid])) if valid else math.nan

def zscore(values):
    valid = [v for v in values if not math.isnan(v)]
    if not valid: return values
    mu = mean(valid)
    sd = math.sqrt(mean([(v - mu) ** 2 for v in valid]))
    if sd == 0 or math.isnan(sd): return [0.0 for _ in values]
    return [(v - mu) / sd if not math.isnan(v) else 0.0 for v in values]

def first_differences(values):
    return [values[i + 1] - values[i] for i in range(len(values) - 1)]

def dominant_frequency_hz(signal, dt_sec):
    if len(signal) < 6 or dt_sec <= 0: return math.nan
    avg = mean(signal)
    centered = [float(v) - avg for v in signal]
    n = len(centered)
    best_freq, best_power = math.nan, 0.0
    for k in range(1, n // 2 + 1):
        real = sum(centered[i] * math.cos(2 * math.pi * k * i / n) for i in range(n))
        imag = sum(-centered[i] * math.sin(2 * math.pi * k * i / n) for i in range(n))
        power = real * real + imag * imag
        if power > best_power:
            best_power, best_freq = power, k / (n * dt_sec)
    return best_freq

def sign_flip_count(signal, eps):
    diffs = [signal[i+1] - signal[i] for i in range(len(signal)-1)]
    signs = [1 if d > eps else -1 if d < -eps else 0 for d in diffs]
    signs = [s for s in signs if s != 0]
    return sum(1 for i in range(len(signs)-1) if signs[i] != signs[i+1])

def local_extrema_count(signal, eps):
    count = 0
    for i in range(1, len(signal)-1):
        pd = signal[i] - signal[i-1]
        nd = signal[i+1] - signal[i]
        if abs(pd) > eps and abs(nd) > eps and pd * nd < 0:
            count += 1
    return count

def best_lag_samples(x, y, max_lag_samples):
    """交叉相关求最优延迟（与 script 28 完全相同）"""
    x = zscore(first_differences(x))
    y = zscore(first_differences(y))
    n = min(len(x), len(y))
    if n < MIN_SAMPLE_POINTS:
        return math.nan, math.nan
    x, y = x[:n], y[:n]
    best_lag, best_corr = 0, -1.0
    for lag in range(0, min(max_lag_samples + 1, n)):
        if lag == 0:
            pairs = list(zip(x, y))
        else:
            pairs = list(zip(x[:-lag], y[lag:]))
        if not pairs: continue
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        mx, my = mean(xs), mean(ys)
        num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        den = math.sqrt(sum((a - mx)**2 for a in xs) * sum((b - my)**2 for b in ys))
        corr = num / den if den > 1e-12 else 0.0
        if corr > best_corr:
            best_corr, best_lag = corr, lag
    return float(best_lag), float(best_corr)

def other_side(side):
    return "right" if side == "left" else "left"

# ─── 主提取函数 ────────────────────────────────────────────────────────────
def extract_stance_delays(dataset, case_label, ankle_kp, ankle_kd, csv_path):
    rows = ROUND3A.load_csv(csv_path)
    ROUND3A.attach_fk_metrics(rows)
    events = sorted(ROUND3A.detect_touchdowns(rows),
                    key=lambda e: e.timestamp_sec)[:STEP_LIMIT + 1]  # 多取1个，保证最后一步有终点

    if len(events) < 2:
        print(f"  [WARN] {case_label}: only {len(events)} events, skipping")
        return []

    dt_sec = median([rows[i+1]["time_sec"] - rows[i]["time_sec"]
                     for i in range(min(100, len(rows)-1))])
    max_lag_samples = max(1, int(round(STANCE_MAX_LAG_SEC / max(dt_sec, 1e-6))))
    diag_csv = os.path.basename(csv_path)

    out_rows = []

    # 取前 STEP_LIMIT 个步骤：事件 i → i+1 定义第 i+1 步的支撑期
    for step_idx, i in enumerate(range(min(STEP_LIMIT, len(events) - 1)), start=1):
        e_start = events[i]       # 当前触地 → 支撑期开始
        e_end   = events[i + 1] if i + 1 < len(events) else None  # 下一触地 → 支撑期结束

        stance_side = e_start.side           # 支撑腿
        swing_side  = other_side(stance_side) # 摆动腿（空中）

        t_start = e_start.timestamp_sec
        t_end   = e_end.timestamp_sec if e_end else rows[-1]["time_sec"]

        stance_rows = [row for row in rows if t_start <= row["time_sec"] <= t_end]
        if len(stance_rows) < MIN_SAMPLE_POINTS:
            continue

        duration_sec = t_end - t_start

        # 对支撑腿和摆动腿各计算 pitch / roll 延迟
        for side, role in [(stance_side, "stance_leg"), (swing_side, "swing_leg")]:
            for axis in ("pitch", "roll"):
                target_key = f"pos_des_raw_{side}_ankle_{axis}_joint"
                joint_key  = f"pos_{side}_ankle_{axis}_joint"

                try:
                    target = [row[target_key] for row in stance_rows]
                    joint  = [row[joint_key]  for row in stance_rows]
                    times  = [row["time_sec"] for row in stance_rows]
                except KeyError:
                    continue

                lag_samples, corr = best_lag_samples(target, joint, max_lag_samples)
                lag_ms = lag_samples * dt_sec * 1000.0 if not math.isnan(lag_samples) else math.nan

                # 关节运动指标
                duration = max((len(joint) - 1) * dt_sec, 1e-6)
                j_range = max(joint) - min(joint)
                j_path  = sum(abs(joint[k+1] - joint[k]) for k in range(len(joint)-1))
                j_dfreq = dominant_frequency_hz(joint, dt_sec)
                j_dcr   = sign_flip_count(joint, DIFF_EPS_RAD) / duration
                j_er    = local_extrema_count(joint, DIFF_EPS_RAD) / duration
                t_range = max(target) - min(target)
                t_path  = sum(abs(target[k+1] - target[k]) for k in range(len(target)-1))

                # 对齐后的跟踪误差
                lag_s = 0 if math.isnan(lag_samples) else int(max(0, lag_samples))
                if lag_s > 0 and lag_s < len(target):
                    err = [target[k] - joint[k + lag_s] for k in range(len(target) - lag_s)]
                    tracking_err_rms = rms(err)
                else:
                    err = [target[k] - joint[k] for k in range(len(joint))]
                    tracking_err_rms = rms(err)

                out_rows.append({
                    "dataset":        dataset,
                    "case_label":     case_label,
                    "ankle_kp":       ankle_kp,
                    "ankle_kd":       ankle_kd,
                    "diag_csv":       diag_csv,
                    "step_index":     step_idx,
                    "stance_side":    stance_side,   # 哪条腿在支撑
                    "window":         "stance",
                    "side":           side,
                    "role":           role,
                    "axis":           axis,
                    "stance_start_sec": round(t_start, 4),
                    "stance_end_sec":   round(t_end,   4),
                    "duration_sec":     round(duration_sec, 4),
                    "sample_count":     len(stance_rows),
                    "lag_ms":           round(lag_ms, 2) if not math.isnan(lag_ms) else float("nan"),
                    "corr":             round(corr,   4) if not math.isnan(corr)   else float("nan"),
                    "target_range_rad": round(t_range, 6),
                    "joint_range_rad":  round(j_range, 6),
                    "target_path_rad":  round(t_path,  6),
                    "joint_path_rad":   round(j_path,  6),
                    "joint_dominant_freq_hz":         round(j_dfreq, 4) if not math.isnan(j_dfreq) else float("nan"),
                    "joint_direction_change_rate_hz": round(j_dcr,   4),
                    "joint_extrema_rate_hz":          round(j_er,    4),
                    "tracking_err_rms_rad":           round(tracking_err_rms, 6) if not math.isnan(tracking_err_rms) else float("nan"),
                })

    return out_rows


# ─── 打印统计摘要 ──────────────────────────────────────────────────────────
def print_summary(all_rows):
    import pandas as pd
    df = pd.DataFrame(all_rows)
    good = df[df["corr"] >= CORR_THRESHOLD].copy()

    print("\n" + "═"*72)
    print("  支撑期延迟统计（lag_ms，仅 corr≥0.2）")
    print("  分 Kp/Kd × dataset × role × axis")
    print("═"*72)

    for role in ["stance_leg", "swing_leg"]:
        for axis in ["pitch", "roll"]:
            sub = good[(good["role"]==role) & (good["axis"]==axis)]
            if sub.empty: continue
            sub = sub.copy()
            sub["case"] = sub["ankle_kp"].astype(int).astype(str) + "/" + sub["ankle_kd"].astype(str)
            pivot = sub.pivot_table(
                index="case", columns="dataset",
                values="lag_ms",
                aggfunc=lambda x: f"p50={int(round(x.quantile(.5)))}  p75={int(round(x.quantile(.75)))}"
            )
            print(f"\n  [stance / {role} / {axis}]")
            print("  " + pivot.to_string().replace("\n", "\n  "))

    print("\n  支撑期 vs 摆动期 延迟对比（real端 p75）：")
    print(f"  {'场景':<30} {'摆动期p75':>12} {'支撑期stance_leg p75':>22} {'支撑期swing_leg p75':>22}")
    print("  " + "-"*88)

    # 加载旧的 delay_detail.csv 做对比
    old_csv = os.path.join(TABLE_DIR, "forward_x_failure_first6_delay_detail.csv")
    if os.path.exists(old_csv):
        old_df = pd.read_csv(old_csv)
        old_real = old_df[
            (old_df["dataset"]=="real") & (old_df["corr"]>=CORR_THRESHOLD) &
            (old_df["window"]=="swing")
        ]
        new_real = good[good["dataset"]=="real"]
        for axis in ["pitch", "roll"]:
            old_p75 = old_real[old_real["axis"]==axis]["lag_ms"].quantile(.75) if not old_real.empty else float("nan")
            new_st  = new_real[(new_real["role"]=="stance_leg")&(new_real["axis"]==axis)]["lag_ms"].quantile(.75)
            new_sw  = new_real[(new_real["role"]=="swing_leg") &(new_real["axis"]==axis)]["lag_ms"].quantile(.75)
            print(f"  {'ankle_'+axis+' (real全案例)':<30} {old_p75:>12.1f} ms {new_st:>22.1f} ms {new_sw:>22.1f} ms")


# ─── 主入口 ────────────────────────────────────────────────────────────────
def main():
    print("=" * 72)
    print("  支撑期延迟提取  claude_stance_delay_extract.py")
    print("=" * 72)

    all_rows = []
    for dataset, case_label, kp, kd, rel_path in REAL_CASES + SIM_CASES:
        csv_path = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(csv_path):
            print(f"  [SKIP] 找不到文件: {csv_path}")
            continue
        print(f"  处理: {dataset} / {case_label} ...", end="", flush=True)
        rows = extract_stance_delays(dataset, case_label, kp, kd, csv_path)
        all_rows.extend(rows)
        print(f" {len(rows)} 行")

    if not all_rows:
        print("  [ERROR] 未提取到任何数据")
        return

    # 写 CSV
    fieldnames = list(all_rows[0].keys())
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n  已保存: {OUT_CSV}  ({len(all_rows)} 行)")
    print_summary(all_rows)
    print("\n  ✓ 完成。")
    print("=" * 72)


if __name__ == "__main__":
    main()
