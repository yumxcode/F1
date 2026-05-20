#!/usr/bin/env python3
"""
t27 真机行走不稳综合分析脚本
分析维度:
  1. 基体稳定性 (base euler angles, angular velocity)
  2. 关节轨迹跟踪误差 (serial vs parallel joints)
  3. 电机响应延迟 & 扭矩跟踪
  4. 左右腿对称性
  5. 接触相序与步态稳定性
  6. 相位相关抖动分析
"""

import csv
import math
import statistics
from pathlib import Path
from collections import defaultdict

# ===== 关节定义 =====
JOINTS = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint",
    "left_knee_pitch_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_pitch_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
]

JOINT_LIMITS = {
    "left_hip_pitch_joint": (-1.0, 2.0), "left_hip_roll_joint": (-1.5, 0.2),
    "left_hip_yaw_joint": (-1.5, 1.5), "left_knee_pitch_joint": (0.0, 2.0),
    "left_ankle_pitch_joint": (-0.41, 0.35), "left_ankle_roll_joint": (-0.64, 0.64),
    "right_hip_pitch_joint": (-2.0, 1.0), "right_hip_roll_joint": (-0.2, 1.5),
    "right_hip_yaw_joint": (-1.5, 1.5), "right_knee_pitch_joint": (0.0, 2.0),
    "right_ankle_pitch_joint": (-0.41, 0.35), "right_ankle_roll_joint": (-0.64, 0.64),
}

LEFT_JOINTS = [j for j in JOINTS if j.startswith("left_")]
RIGHT_JOINTS = [j for j in JOINTS if j.startswith("right_")]

# Parallel joints (ankle roll + ankle pitch)
PARALLEL_JOINTS = {"left_ankle_pitch_joint", "left_ankle_roll_joint",
                   "right_ankle_pitch_joint", "right_ankle_roll_joint"}

# ===== 辅助函数 =====
def ffloat(v):
    if v is None: return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except: return None

def mean(vals):
    return statistics.fmean(vals) if vals else math.nan

def std(vals):
    return statistics.pstdev(vals) if vals else math.nan

def rms(vals):
    return math.sqrt(sum(v*v for v in vals)/len(vals)) if vals else math.nan

def pct(vals, p):
    if not vals: return math.nan
    s = sorted(vals)
    i = min(len(s)-1, max(0, round((len(s)-1)*p)))
    return s[i]

def corr(xs, ys):
    n = min(len(xs), len(ys))
    if n < 2: return math.nan
    x, y = xs[:n], ys[:n]
    mx, my = mean(x), mean(y)
    vx = [v-mx for v in x]
    vy = [v-my for v in y]
    d = math.sqrt(sum(v*v for v in vx)*sum(v*v for v in vy))
    return sum(a*b for a,b in zip(vx,vy))/d if d>1e-12 else math.nan

def load(csv_path):
    with open(csv_path, newline='') as f:
        return list(csv.DictReader(f))

def series(rows, key):
    return [v for r in rows if (v:=ffloat(r.get(key))) is not None]

# ===== 分析主函数 =====
def analyze(csv_path):
    rows = load(csv_path)
    N = len(rows)
    if N < 10:
        print(f"[WARN] 数据行数不足: {N}")
        return {}, [], {}, {}, {}

    # 时间戳
    ts = [int(r["timestamp_ns"]) for r in rows]
    dts = [(b-a)/1e9 for a,b in zip(ts,ts[1:]) if b>a]
    fs = 1.0/mean(dts) if dts else math.nan
    dur = (ts[-1]-ts[0])/1e9 if len(ts)>1 else 0

    # ----- 1. 基体稳定性 -----
    base_keys = ["base_euler_x","base_euler_y","base_euler_z",
                 "base_ang_vel_x","base_ang_vel_y","base_ang_vel_z"]
    base_stats = {}
    for k in base_keys:
        v = series(rows,k)
        if v:
            base_stats[k] = {"mean": mean(v), "std": std(v), "rms": rms(v),
                             "range": max(v)-min(v), "abs_p95": pct([abs(x) for x in v],0.95),
                             "abs_max": max(abs(x) for x in v)}

    # ----- 2. 接触状态 -----
    lc = [int(ffloat(r.get("left_contact")) or 0) for r in rows]
    rc = [int(ffloat(r.get("right_contact")) or 0) for r in rows]
    lc_trans = sum(1 for a,b in zip(lc,lc[1:]) if a!=b)
    rc_trans = sum(1 for a,b in zip(rc,rc[1:]) if a!=b)
    contact_stats = {"left_contact_frac": mean([float(x) for x in lc]),
                     "right_contact_frac": mean([float(x) for x in rc]),
                     "left_transitions": lc_trans, "right_transitions": rc_trans}

    # 步态相位检测
    phase_sin = series(rows, "phase_sin")
    phase_cos = series(rows, "phase_cos")
    phases = [math.atan2(s,c) for s,c in zip(phase_sin,phase_cos)] if phase_sin and phase_cos else []

    # ----- 3. 关节跟踪分析 -----
    joint_data = {}
    for j in JOINTS:
        pos = series(rows, f"pos_{j}")
        vel = series(rows, f"vel_{j}")
        effort = series(rows, f"effort_{j}")
        des_raw = series(rows, f"pos_des_raw_{j}")
        des_lpf = series(rows, f"pos_des_lpf_{j}")
        tau_raw = series(rows, f"tau_des_raw_{j}")
        tau_lpf = series(rows, f"tau_des_lpf_{j}")
        is_par = int(round(mean(series(rows, f"is_parallel_{j}")))) if series(rows, f"is_parallel_{j}") else 0
        action = series(rows, f"action_{j}")

        # 串行关节用 des_lpf, 并行关节用 des_raw 作为虚拟目标
        target = des_raw if is_par else des_lpf
        tname = "des_raw" if is_par else "des_lpf"
        n = min(len(target), len(pos))
        target, pos = target[:n], pos[:n]

        errors = [t-p for t,p in zip(target, pos)]
        delay, dc = 0.0, 0.0
        if n > 10:
            best_lag, best_c = 0, -2.0
            for lag in range(-20, 21):
                xs, ys = [], []
                for i in range(n):
                    jdx = i+lag
                    if 0 <= jdx < n:
                        xs.append(target[i])
                        ys.append(pos[jdx])
                if len(xs)>=10:
                    c = corr(xs,ys)
                    if not math.isnan(c) and c>best_c:
                        best_c=c; best_lag=lag
            delay = best_lag/fs*1000 if fs else 0
            dc = best_c

        lower, upper = JOINT_LIMITS[j]
        near_eps = 1e-3
        raw_series = des_raw[:n]
        tau_pair = list(zip(tau_lpf, effort)) if tau_lpf and effort else []

        jd = {
            "joint": j, "is_parallel": is_par, "target": tname,
            "rms_err": rms(errors), "mean_err": mean(errors), "std_err": std(errors),
            "max_abs_err": max(abs(e) for e in errors) if errors else math.nan,
            "pos_range": (max(pos)-min(pos)) if pos else math.nan,
            "tar_range": (max(target)-min(target)) if target else math.nan,
            "pos_over_tar": (max(pos)-min(pos))/(max(target)-min(target))
                if target and (max(target)-min(target))>1e-9 else math.nan,
            "corr_0lag": corr(target,pos),
            "delay_ms": delay, "delay_corr": dc,
            "vel_abs_p95": pct([abs(v) for v in vel],0.95),
            "effort_abs_p95": pct([abs(e) for e in effort],0.95),
            "effort_abs_max": max(abs(e) for e in effort) if effort else math.nan,
            "tau_lpf_abs_p95": pct([abs(t) for t in tau_lpf],0.95),
            "tau_raw_abs_p95": pct([abs(t) for t in tau_raw],0.95),
            "tau_effort_corr": corr(tau_lpf, effort) if tau_lpf and effort else math.nan,
            "lower_hit": mean([1.0 if v<=lower+near_eps else 0.0 for v in raw_series]),
            "upper_hit": mean([1.0 if v>=upper-near_eps else 0.0 for v in raw_series]),
            "action_range": (max(action)-min(action)) if action else math.nan,
            "action_rms": rms(action) if action else math.nan,
        }
        joint_data[j] = jd

    # ----- 4. 左右对称性分析 -----
    sym = {}
    for l,r in zip(LEFT_JOINTS, RIGHT_JOINTS):
        ld, rd = joint_data.get(l), joint_data.get(r)
        if ld and rd:
            sym[(l,r)] = {
                "rms_err_diff": abs(ld["rms_err"]-rd["rms_err"]),
                "pos_range_ratio": ld["pos_range"]/rd["pos_range"] if rd["pos_range"]>1e-9 else math.nan,
                "tar_range_ratio": ld["tar_range"]/rd["tar_range"] if rd["tar_range"]>1e-9 else math.nan,
                "delay_diff_ms": abs(ld["delay_ms"]-rd["delay_ms"]),
                "effort_p95_ratio": ld["effort_abs_p95"]/rd["effort_abs_p95"] if rd["effort_abs_p95"]>1e-9 else math.nan,
            }

    # ----- 5. Meta -----
    meta = {"rows": N, "duration_s": round(dur,3), "sample_hz": round(fs,1),
            "dt_min_ms": round(min(dts)*1000,3) if dts else math.nan,
            "dt_max_ms": round(max(dts)*1000,3) if dts else math.nan}

    return meta, base_stats, joint_data, contact_stats, sym, phases, rows

# ===== 报告生成 =====
def report(meta, base_stats, joint_data, contact_stats, sym, phases, rows, out_dir, src):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = []
    L = lines.append

    L(f"# t27 真机行走不稳分析报告")
    L(f"")
    L(f"- **数据源**: `{src}`")
    L(f"- **数据行数**: {meta['rows']}")
    L(f"- **时长**: {meta['duration_s']} s")
    L(f"- **采样率**: {meta['sample_hz']} Hz")
    L(f"- **dt min/max**: {meta['dt_min_ms']}/{meta['dt_max_ms']} ms")
    L(f"- **平台**: 智元X1 (F1) | R52/R86-2/R86-3, 12DOF")
    L(f"")

    # ===== 1. 基体稳定性 =====
    L("## 1. 基体姿态稳定性")
    L("")
    L("| 指标 | mean | std | RMS | range | abs_p95 | abs_max |")
    L("|---|---:|---:|---:|---:|---:|---:|")
    for k in ["base_euler_x","base_euler_y","base_euler_z",
              "base_ang_vel_x","base_ang_vel_y","base_ang_vel_z"]:
        s = base_stats.get(k,{})
        label = {"base_euler_x":"roll_x(rad)","base_euler_y":"pitch_y(rad)","base_euler_z":"yaw_z(rad)",
                 "base_ang_vel_x":"gyro_x(rad/s)","base_ang_vel_y":"gyro_y(rad/s)","base_ang_vel_z":"gyro_z(rad/s)"}
        L(f"| {label.get(k,k)} | {s.get('mean','N/A'):.5f} | {s.get('std','N/A'):.5f} | "
          f"{s.get('rms','N/A'):.5f} | {s.get('range','N/A'):.5f} | {s.get('abs_p95','N/A'):.5f} | {s.get('abs_max','N/A'):.5f} |")

    roll_std = base_stats.get("base_euler_x",{}).get("std",0)
    pitch_std = base_stats.get("base_euler_y",{}).get("std",0)
    gyro_p95 = base_stats.get("base_ang_vel_x",{}).get("abs_p95",0)
    L("")
    L(f"> **评判**: roll std={roll_std:.4f} rad, pitch std={pitch_std:.4f} rad. "
      f"人形机器人稳定行走的参考阈值: roll std < 0.02 rad, pitch std < 0.03 rad. "
      f"{'⚠ 超过阈值' if roll_std>0.02 or pitch_std>0.03 else '✓ 在阈值内'}")
    L(f"> gyro_x abs_p95={gyro_p95:.4f} rad/s, 反映侧向摆动剧烈程度。")
    L("")

    # ===== 2. 接触状态 =====
    L("## 2. 接触状态与步态相")
    L("")
    L(f"| 指标 | 左足 | 右足 |")
    L(f"|---|---|---:|")
    L(f"| 接触占比 | {contact_stats['left_contact_frac']:.3f} | {contact_stats['right_contact_frac']:.3f} |")
    L(f"| 接触切换次数 | {contact_stats['left_transitions']} | {contact_stats['right_transitions']} |")
    L("")
    L(f"> 单足支撑相过多(>0.7)表示双足支撑不足，行走不稳。期望双足支撑占比≈0.2~0.3。")

    # ===== 3. 关节跟踪误差 =====
    L("## 3. 关节跟踪误差分析")
    L("")
    L("### 3.1 按RMS误差排序")
    L("")
    L("| 关节 | 类型 | 目标 | RMS_err | mean_err | std_err | max_abs_err | 目标范围 | 实际范围 | Pos/目标 | 零滞相关 | 延迟ms | 延迟相关 |")
    L("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    sorted_j = sorted(joint_data.values(), key=lambda x: x["rms_err"], reverse=True)
    for jd in sorted_j:
        jt = "并行" if jd["is_parallel"] else "串行"
        L(f"| {jd['joint']} | {jt} | {jd['target']} | {jd['rms_err']:.4f} | {jd['mean_err']:.4f} | "
          f"{jd['std_err']:.4f} | {jd['max_abs_err']:.4f} | {jd['tar_range']:.4f} | {jd['pos_range']:.4f} | "
          f"{jd['pos_over_tar']:.3f} | {jd['corr_0lag']:.3f} | {jd['delay_ms']:.1f} | {jd['delay_corr']:.3f} |")

    L("")
    L("### 3.2 关节扭矩跟踪 (tau_lpf vs actual effort)")
    L("")
    L("| 关节 | tau_lpf p95 | effort p95 | 最大effort | tau-effort相关 |")
    L("|---|---:|---:|---:|---:|")
    for jd in sorted_j:
        L(f"| {jd['joint']} | {jd['tau_lpf_abs_p95']:.3f} | {jd['effort_abs_p95']:.3f} | "
          f"{jd['effort_abs_max']:.3f} | {jd['tau_effort_corr']:.3f} |")

    L("")
    L("### 3.3 并行关节限位触碰分析")
    L("")
    L("| 关节 | 下限触碰率 | 上限触碰率 |")
    L("|---|---:|---:|")
    for jd in sorted_j:
        if jd["is_parallel"]:
            L(f"| {jd['joint']} | {jd['lower_hit']:.1%} | {jd['upper_hit']:.1%} |")

    # ===== 4. 左右对称性 =====
    L("")
    L("## 4. 左右腿对称性分析")
    L("")
    L("| 左关节 | 右关节 | RMS误差差 | 位置范围比(L/R) | 目标范围比(L/R) | 延迟差(ms) | 力矩p95比(L/R) |")
    L("|---|---:|---:|---:|---:|---:|")
    for (l,r),sd in sym.items():
        L(f"| {l} | {r} | {sd['rms_err_diff']:.4f} | {sd['pos_range_ratio']:.3f} | "
          f"{sd['tar_range_ratio']:.3f} | {sd['delay_diff_ms']:.1f} | {sd['effort_p95_ratio']:.3f} |")

    # ===== 5. 相关性统计 =====
    L("")
    L("## 5. 最严重问题汇总")
    L("")

    # 找出最大的几个问题
    worst_tracking = sorted_j[:3]
    L("### 5.1 Top 3 最大RMS跟踪误差")
    for jd in worst_tracking:
        L(f"- **{jd['joint']}**: RMS={jd['rms_err']:.4f} rad, 延迟={jd['delay_ms']:.1f}ms, 相关={jd['delay_corr']:.3f}")

    worst_delay = sorted(joint_data.values(), key=lambda x: abs(x["delay_ms"]), reverse=True)[:3]
    L("### 5.2 Top 3 最大延迟")
    for jd in worst_delay:
        L(f"- **{jd['joint']}**: 延迟={jd['delay_ms']:.1f}ms, 相关={jd['delay_corr']:.3f}, RMS={jd['rms_err']:.4f}")

    worst_effort = sorted(joint_data.values(), key=lambda x: abs(x["effort_abs_max"]), reverse=True)[:3]
    L("### 5.3 Top 3 最大力矩输出")
    for jd in worst_effort:
        L(f"- **{jd['joint']}**: max effort={jd['effort_abs_max']:.3f} Nm, p95={jd['effort_abs_p95']:.3f}")

    # ===== 6. 结论 =====
    L("")
    L("## 6. 结论与建议")
    L("")

    # 汇总关键问题
    issues = []

    # 基体稳定性
    if roll_std > 0.02:
        issues.append(f"**基体侧向摆动过大**: roll std={roll_std:.4f} rad (阈值0.02)")
    if pitch_std > 0.03:
        issues.append(f"**基体俯仰摆动过大**: pitch std={pitch_std:.4f} rad (阈值0.03)")

    # 跟踪误差最大的关节
    for jd in worst_tracking[:2]:
        issues.append(f"**{jd['joint']}跟踪不良**: RMS={jd['rms_err']:.4f} rad, 延迟={jd['delay_ms']:.1f}ms")

    # 左右不对称
    for (l,r),sd in sym.items():
        if sd.get("rms_err_diff",0) > 0.03:
            issues.append(f"**左右不对称**: {l}/{r} RMS误差差={sd['rms_err_diff']:.4f} rad")

    # 扭矩跟踪
    poor_torque = [jd for jd in joint_data.values() if not math.isnan(jd.get("tau_effort_corr",0)) and abs(jd.get("tau_effort_corr",0)) < 0.5]
    if poor_torque:
        names = ", ".join(jd["joint"] for jd in poor_torque[:3])
        issues.append(f"**扭矩跟踪差**: {names} 的tau-effort相关<0.5，电机力矩响应异常")

    if not issues:
        L("未发现显著异常。")
    else:
        L("### 发现的问题")
        for i, iss in enumerate(issues, 1):
            L(f"{i}. {iss}")

    L("")
    L("### 建议")
    L("")
    if roll_std > 0.02:
        L("1. **降低侧向(roll)晃动**: 检查hip_roll关节的PD增益，增加Kp或Kd抑制侧向摆动；考虑增加踝关节roll方向刚度。")
    if pitch_std > 0.03:
        L("2. **抑制俯仰(pitch)摆动**: 增大hip_pitch和knee_pitch关节阻尼系数；检查躯干IMU数据是否正常。")
    laggy_joints = [jd for jd in joint_data.values() if abs(jd["delay_ms"]) > 30]
    if laggy_joints:
        names = ", ".join(jd["joint"] for jd in laggy_joints[:3])
        L(f"3. **减小执行延迟**: {names} 延迟>{abs(laggy_joints[0]['delay_ms']):.0f}ms，检查通信延迟或关节伺服响应设置。")
    asym_issues = [(l,r,sd) for (l,r),sd in sym.items() if sd.get("rms_err_diff",0) > 0.03]
    if asym_issues:
        L("4. **修正左右不对称**: 检查机械装配是否水平，左右电机参数是否一致。")
    if poor_torque:
        L("5. **校准电机力矩环**: 对扭矩跟踪差的关节进行力矩环参数整定，检查电流反馈是否正常。")

    out_path = out_dir / "t27_instability_analysis_report.md"
    out_path.write_text("\n".join(lines) + "\n")
    print(f"[OK] 报告已写入: {out_path}")
    return lines

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="test_logs/data_csv/t27_joint_20260518_1_real.csv", type=Path)
    parser.add_argument("--out-dir", default="test_logs/analysis_output", type=Path)
    args = parser.parse_args()

    meta, base_stats, joint_data, contact_stats, sym, phases, rows = analyze(args.csv)
    report(meta, base_stats, joint_data, contact_stats, sym, phases, rows, args.out_dir, args.csv)

if __name__ == "__main__":
    main()
