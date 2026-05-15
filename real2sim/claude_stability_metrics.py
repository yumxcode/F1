"""
踝关节 PD 控制稳定性指标分析  v5
====================================
系统模型：J_eff·q̈ + Kd·q̇ + Kp·q = 0（闭环二阶系统）
  ωn = √(Kp/J_eff)          自然角频率
  ζ  = Kd / (2√(Kp·J_eff))  阻尼比

【适用前提 — 必须满足，否则公式失效】
  |H(fn)|=1/(2ζ) 仅对「无零点」G_CL 成立：
    τ = Kp·e（纯比例误差 + 速度反馈 Kd·q̇ 打在输出侧）
    G_CL = ωn² / (s²+2ζωns+ωn²)
  若控制器为「有零点」形式（τ = Kp·e + Kd·ė），
    G_CL = (Kd·s+Kp)/(J·s²+Kd·s+Kp)，
    |G_CL(jωn)| = √(1+1/4ζ²) ≥ 1，公式不再成立！

【v5 新增 — 摆动相专用FRF】
─────────────────────────────────────────────────────────────────
背景：
  步行中 G_fn = |H(fn_th)| 通常远低于 0.5（理论 ζ→∞），
  但阶跃响应实验（摆动相 ζ_step = 0.07-0.25）显示系统欠阻尼！
  矛盾根源：支撑相 J_eff_stance >> J_EFF_DEFAULT，
            fn_eff_stance << fn_th，在 fn_th 处 Welch FRF 已在
            滚降区，|H| 低不是因为过阻尼，而是因为惯量被污染！

解决方案：
  仅用摆动相片段计算 FRF（contact=0 时，J_eff ≈ J_EFF_DEFAULT）
  分段累积 Sxy/Sxx/Syy → 对全局估计的摆动相分量求 H_sw

新增指标：
  G_fn_sw     摆动相 |H(fn_th)|（去除支撑相惯量污染）
  zeta_frf_sw 摆动相 ζ = 1/(2·G_fn_sw)
  coh_fn_sw   摆动相 fn 处相干
  fn_frf_sw   摆动相 FRF 相位法 fn
  e_rms_swing 摆动相跟踪误差RMS
  e_rms_stance 支撑相跟踪误差RMS

预测（用于验证）：
  若 G_fn_sw > 0.5 → 摆动相欠阻尼，确认全步态G_fn低是J_eff_stance效应
  若 G_fn_sw < 0.5 → 系统真正过阻尼（不因摆动相过滤而改变）

【v4 方法论（继承）】
─────────────────────────────────────────────────────────────────
v3 存在的三个缺陷：
  缺陷1：fn_swing 用误差PSD主峰估计fn（步态谐波主导，非系统fn）
  缺陷2：halfpower_zeta 用半功率带宽法（过阻尼无峰，输出混乱值）
  缺陷3：csd(jnt,des) 顺序导致相位取反（∠G_CL* 非 ∠G_CL）
  → v4全部修复：FRF相位法 + |H(fn)|=1/(2ζ) + csd(des,jnt)

【输出指标】
─────────────────────────────────────────────────────────────────
  全步态（含支撑相）：
    fn_th_hz, fn_frf_hz, fn_err_hz, fn_stance_hz
    G_fn, zeta_th, zeta_frf, coh_at_fn
    e_rms_rad, tau_th_ms, tau_frf_ms, delay_ms, A_peak, DeltaLR

  摆动相专用（v5新增）：
    G_fn_sw, zeta_frf_sw, coh_fn_sw, fn_frf_sw
    e_rms_swing, e_rms_stance
    n_swing_segs（用于计算摆动相FRF的片段数）
"""

import numpy as np
import pandas as pd
from scipy.signal import welch, csd, correlate, correlation_lags
from scipy.signal import butter, filtfilt, find_peaks, hilbert
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# 全局配置
# ═══════════════════════════════════════════════════════════════════════════════

BASE_REAL = '/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/'
BASE_SIM  = '/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/sim/'

# 默认等效转动惯量（摆动相估计值，用于理论值计算）
J_EFF_DEFAULT = 0.0965   # kg·m²

AXES  = ['ankle_pitch', 'ankle_roll']
SIDES = ['left', 'right']

MIN_TD_GAP   = 0.25   # 接地/离地去抖门限 [s]
TD_POST      = 1.50   # 接地后全局分析窗口 [s]（fn_stance用）
TD_POST_ZETA = 0.50   # 接地后ζ分析窗口 [s]（短窗降低步态污染）
SWING_PRE    = 0.35   # xcorr: 接地前截取窗口 [s]
SWING_POST   = 0.02   # xcorr: 接地前结束偏移 [s]
MAX_DELAY_MS = 150    # xcorr: 最大可信延迟 [ms]

# 摆动相FRF参数
SWING_BUF_S   = 0.05  # 摆动相首尾边缘缓冲 [s]（避免接地冲击污染）
SWING_MIN_S   = 0.15  # 摆动相最短有效片段 [s]
SWING_NPERSEG = 2.0   # 摆动相Welch nperseg [s]（较短，适应短片段）

# v5.2: FRF 可信度门限
COH_SW_MIN = 0.30   # 摆动相相干函数最低门限（v5.2: 0.40→0.30）
N_SW_MIN   = 5      # 摆动相 FRF 最少片段数

# ζ_ld 峰值间距校验：有效间距范围 = [LO, HI] × T_osc
ZETA_PEAK_TOL_LO = 0.5
ZETA_PEAK_TOL_HI = 2.0
DES_CHANGE_THRESH = 0.20  # des变化量门限 [rad]

REAL_CASES = [
    ('25/0.4', 25, 0.4, BASE_REAL + 't27_tracking_lag_b1_diag_20260430_100024.csv'),
    ('30/0.4', 30, 0.4, BASE_REAL + 't27_tracking_lag_b1_diag_20260430_100314.csv'),
    ('35/0.5', 35, 0.5, BASE_REAL + 't27_tracking_lag_b1_diag_20260430_100705.csv'),
    ('40/0.8', 40, 0.8, BASE_REAL + 't27_tracking_lag_b1_diag_20260430_101404.csv'),
]
SIM_CASES = [
    ('25/0.4', 25, 0.4, BASE_SIM + 't27_tracking_lag_b1_diag_20260506_133905_2504.csv'),
    ('35/0.5', 35, 0.5, BASE_SIM + 't27_tracking_lag_b1_diag_20260506_133024_3505.csv'),
    ('40/0.5', 40, 0.5, BASE_SIM + 't27_tracking_lag_b1_diag_20260506_134153_4005.csv'),
    ('50/0.8', 50, 0.8, BASE_SIM + 't27_tracking_lag_b1_diag_20260506_134417_5008.csv'),
]


# ═══════════════════════════════════════════════════════════════════════════════
# 数据加载
# ═══════════════════════════════════════════════════════════════════════════════
def load(path):
    """读取CSV，返回 (df, t_s, dt_s, fs_Hz)。时间戳纳秒→秒。"""
    df   = pd.read_csv(path)
    t_ns = df['timestamp_ns'].values
    t    = (t_ns - t_ns[0]) / 1e9
    dt   = np.nanmedian(np.diff(t))
    fs   = 1.0 / dt
    return df, t, dt, fs


# ═══════════════════════════════════════════════════════════════════════════════
# 接地/离地事件检测（去抖）
# ═══════════════════════════════════════════════════════════════════════════════
def debounce_td(df, t, side, min_gap=MIN_TD_GAP):
    """检测接触上升沿（0→1）并去抖，返回 (接地时刻[s], 样本索引)。"""
    contact = np.nan_to_num(df[f'{side}_contact'].values.astype(float), nan=0.0).astype(int)
    edges   = np.where(np.diff(contact) > 0)[0] + 1
    if len(edges) == 0:
        return np.array([]), np.array([], dtype=int)
    times = t[edges]
    kt, ki = [times[0]], [edges[0]]
    for i, tt in enumerate(times[1:], 1):
        if tt - kt[-1] >= min_gap:
            kt.append(tt); ki.append(edges[i])
    return np.array(kt), np.array(ki)


def detect_liftoff(df, t, side, min_gap=MIN_TD_GAP):
    """
    检测离地事件（接触信号下降沿 1→0）并去抖。
    返回：(离地时刻[s], 样本索引)

    离地定义：contact 从1变为0的时刻即为摆动相起点。
    去抖逻辑与 debounce_td 相同，防止接触信号毛刺。
    """
    contact = np.nan_to_num(df[f'{side}_contact'].values.astype(float), nan=0.0).astype(int)
    edges   = np.where(np.diff(contact) < 0)[0] + 1  # 下降沿：1→0
    if len(edges) == 0:
        return np.array([]), np.array([], dtype=int)
    times = t[edges]
    kt, ki = [times[0]], [edges[0]]
    for i, tt in enumerate(times[1:], 1):
        if tt - kt[-1] >= min_gap:
            kt.append(tt); ki.append(edges[i])
    return np.array(kt), np.array(ki)


# ═══════════════════════════════════════════════════════════════════════════════
# ① 全步态FRF：H(f) = Sxy/Sxx，des→jnt
# ═══════════════════════════════════════════════════════════════════════════════
def compute_frf(jnt, des, fs, nperseg_s=4.0):
    """
    计算前向FRF：H(f) = G_CL(f)，des为输入，jnt为输出。

    使用 csd(des, jnt) = E[des*(f)·jnt(f)] = G_CL·Sxx_des
    → H = csd(des, jnt) / welch(des) = G_CL

    相位：∠H = ∠G_CL（正确，未取共轭）
    幅值：|H| = |G_CL|（不受纯时延影响）

    同时计算相干函数 γ²(f) = |Sxy|²/(Sxx·Syy)，衡量线性拟合质量。
    """
    jnt_c = np.where(np.isnan(jnt), 0.0, jnt)
    des_c = np.where(np.isnan(des), 0.0, des)
    nperseg = min(int(nperseg_s * fs), len(jnt_c) // 2)
    if nperseg < 32:
        return None, None, None

    # csd(des, jnt): Pxy = des* · jnt → 前向FRF（des→jnt）
    f, Sxy = csd(des_c, jnt_c, fs=fs, nperseg=nperseg,
                 noverlap=nperseg // 2, window='hann')
    _, Sxx = welch(des_c, fs=fs, nperseg=nperseg,
                   noverlap=nperseg // 2, window='hann')
    _, Syy = welch(jnt_c, fs=fs, nperseg=nperseg,
                   noverlap=nperseg // 2, window='hann')

    # FRF H(f) = Sxy / Sxx
    H = np.zeros(len(f), dtype=complex)
    valid = Sxx > 1e-14
    H[valid] = Sxy[valid] / Sxx[valid]

    # 相干函数 γ²(f)
    denom = np.maximum(Sxx * Syy, 1e-20)
    coh   = np.abs(Sxy) ** 2 / denom

    return f, H, coh


# ═══════════════════════════════════════════════════════════════════════════════
# ② 摆动相FRF（v5新增）：仅用 contact=0 片段，消除支撑相惯量污染
# ═══════════════════════════════════════════════════════════════════════════════
def compute_swing_frf(jnt, des, t, fs, td_times, lo_times,
                      buf_s=SWING_BUF_S, min_len_s=SWING_MIN_S,
                      nperseg_s=SWING_NPERSEG):
    """
    仅用摆动相片段计算分段平均FRF。

    【为何要分摆动相？】
    步行中 J_eff_stance >> J_EFF_DEFAULT（支撑相人体/地面惯量加入）
    → fn_eff_stance << fn_th（系统实际谐振频率下移）
    → Welch FRF 在 fn_th 处的幅值被支撑相拉低 → G_fn < 0.5 → ζ估计偏高
    摆动相 contact=0，J_eff ≈ J_EFF_DEFAULT，fn_eff ≈ fn_th，可信！

    【分段累积法（避免片段拼接谱泄漏）】
    对每个摆动相片段 [离地+buf, 接地-buf]（长度≥min_len_s）：
      计算该片段的 Sxy, Sxx, Syy（同一nperseg）
      累加到全局 Sxy_sum, Sxx_sum, Syy_sum
    最终：H_sw = Sxy_sum / Sxx_sum
          coh_sw = |Sxy_sum|² / (Sxx_sum · Syy_sum)

    此方法等价于加权 Welch 估计，各片段信噪比作为隐式权重。

    参数：
      td_times: 接地时刻[s]（摆动相终点）
      lo_times: 离地时刻[s]（摆动相起点）

    返回：(f, H_sw, coh_sw, n_segs)
    """
    if len(lo_times) == 0 or len(td_times) == 0:
        return None, None, None, 0

    nperseg = max(32, int(nperseg_s * fs))

    Sxy_sum = None
    Sxx_sum = None
    Syy_sum = None
    n_segs  = 0

    # 为每个离地时刻找其后第一个接地时刻（构成一个摆动相）
    for lo_t in lo_times:
        # 找离地后的第一个接地时刻
        after = td_times[td_times > lo_t]
        if len(after) == 0:
            continue
        td_t = after[0]

        # 加缓冲（避开接触冲击瞬态）
        t0 = lo_t + buf_s
        t1 = td_t - buf_s
        if t1 - t0 < min_len_s:
            continue  # 摆动相太短，跳过

        mask = (t >= t0) & (t <= t1)
        if mask.sum() < nperseg:
            # 片段比 nperseg 短时，用片段本身长度（至少32点）
            nperseg_local = max(32, mask.sum() // 2)
        else:
            nperseg_local = nperseg

        seg_des = np.where(np.isnan(des[mask]), 0.0, des[mask])
        seg_jnt = np.where(np.isnan(jnt[mask]), 0.0, jnt[mask])

        if len(seg_des) < 32:
            continue

        # 计算该片段的互功率谱和自功率谱
        try:
            f_seg, Sxy_seg = csd(seg_des, seg_jnt, fs=fs,
                                  nperseg=min(nperseg_local, len(seg_des)),
                                  noverlap=min(nperseg_local, len(seg_des)) // 2,
                                  window='hann')
            _, Sxx_seg = welch(seg_des, fs=fs,
                               nperseg=min(nperseg_local, len(seg_des)),
                               noverlap=min(nperseg_local, len(seg_des)) // 2,
                               window='hann')
            _, Syy_seg = welch(seg_jnt, fs=fs,
                               nperseg=min(nperseg_local, len(seg_des)),
                               noverlap=min(nperseg_local, len(seg_des)) // 2,
                               window='hann')
        except Exception:
            continue

        # 累积（需要频率轴一致）
        if Sxy_sum is None:
            Sxy_sum = Sxy_seg.copy()
            Sxx_sum = Sxx_seg.copy()
            Syy_sum = Syy_seg.copy()
            f_out   = f_seg
        elif len(Sxy_seg) == len(Sxy_sum):
            Sxy_sum += Sxy_seg
            Sxx_sum += Sxx_seg
            Syy_sum += Syy_seg
        # 频率轴不一致（nperseg不同）时跳过
        n_segs += 1

    if Sxy_sum is None or n_segs == 0:
        return None, None, None, 0

    # 由累积谱计算 H_sw 和 coh_sw
    H_sw  = np.zeros(len(f_out), dtype=complex)
    valid = Sxx_sum > 1e-14
    H_sw[valid] = Sxy_sum[valid] / Sxx_sum[valid]

    denom   = np.maximum(Sxx_sum * Syy_sum, 1e-20)
    coh_sw  = np.abs(Sxy_sum) ** 2 / denom

    return f_out, H_sw, coh_sw, n_segs


# ═══════════════════════════════════════════════════════════════════════════════
# ③ fn 估计：FRF 相位 = -90° 处（延迟补偿后）
# ═══════════════════════════════════════════════════════════════════════════════
def estimate_fn_frf(f, H, coh, fn_th, delay_ms, search_bw=2.0, coh_min=0.10):
    """
    从延迟补偿后的 FRF 相位估计自然频率。

    理论依据：∠G_CL(jωn) = -90°（对任意ζ，无零点G_CL严格成立）

    步骤：
      1. 补偿观测到的相位延迟：H_comp = H · exp(+j2πf·τ_delay)
      2. 在 [fn_th ± search_bw] Hz 范围内找相位最接近 -90° 的点
      3. 检查该点的相干函数是否达标（γ² >= coh_min）
    """
    if f is None or H is None:
        return np.nan, np.nan

    # 延迟补偿（幅值不变，相位校正）
    tau = np.clip(delay_ms, 0, MAX_DELAY_MS) / 1000.0 \
          if not np.isnan(delay_ms) else 0.0
    H_comp = H * np.exp(1j * 2 * np.pi * f * tau)

    # 搜索范围
    flo = max(0.5, fn_th - search_bw)
    fhi = min(f[-1] - 0.1, fn_th + search_bw)
    mask = (f >= flo) & (f <= fhi)
    if not mask.any():
        return np.nan, np.nan

    phase_deg = np.angle(H_comp[mask], deg=True)
    f_sub     = f[mask]
    coh_sub   = coh[mask] if coh is not None else np.ones(mask.sum())

    # 找最接近 -90° 的点
    idx    = np.argmin(np.abs(phase_deg + 90.0))
    fn_frf = float(f_sub[idx])
    coh_fn = float(coh_sub[idx])

    # 相干不足时标记为不可靠
    if coh_fn < coh_min:
        fn_frf = np.nan

    return fn_frf, coh_fn


# ═══════════════════════════════════════════════════════════════════════════════
# ④ ζ 估计：|H(fn)| = 1/(2ζ)（核心公式）
# ═══════════════════════════════════════════════════════════════════════════════
def estimate_zeta_frf(f, H, coh, fn, bw_hz=0.75, coh_min=0.10):
    """
    从 FRF 幅值在 fn 处估计阻尼比。

    严格推导（无零点G_CL，对任意ζ成立）：
      G_CL(jωn) = ωn² / (−ωn²+2jζωn²+ωn²) = 1/(2jζ)
      |G_CL(jωn)| = 1/(2ζ)  →  ζ = 1/(2|H(fn)|)

    幅值不受纯时延影响（|e^(-jωτ)| = 1），无需延迟补偿。
    在 [fn±bw_hz/2] 范围取相干加权均值，降低谱估计噪声。

    解读：
      G_fn > 0.5 → ζ < 1.0  欠阻尼（有谐振放大）
      G_fn = 0.5 → ζ = 1.0  临界阻尼
      G_fn < 0.5 → ζ > 1.0  过阻尼 OR fn_eff偏离fn_th（惯量效应）
    """
    if f is None or H is None or np.isnan(fn):
        return np.nan, np.nan, np.nan

    mask = (f >= fn - bw_hz / 2) & (f <= fn + bw_hz / 2)
    if not mask.any():
        return np.nan, np.nan, np.nan

    H_mag    = np.abs(H[mask])
    coh_vals = coh[mask] if coh is not None else np.ones(mask.sum())

    # 用相干函数加权平均（高相干点权重更高）
    weights  = np.maximum(coh_vals, 1e-3)
    G_fn     = float(np.average(H_mag, weights=weights))
    coh_mean = float(np.mean(coh_vals))

    if G_fn < 1e-6:
        return G_fn, np.nan, coh_mean

    zeta_frf = float(np.clip(1.0 / (2.0 * G_fn), 0.01, 10.0))
    return G_fn, zeta_frf, coh_mean


# ═══════════════════════════════════════════════════════════════════════════════
# ⑤ fn 参考：误差 PSD 主峰（受步态谐波主导，非系统fn）
# ═══════════════════════════════════════════════════════════════════════════════
def estimate_fn_err(err, fs, fmin=2.0, fmax=7.0, nperseg_s=4.0):
    """
    误差PSD主峰频率（参考值）。
    ⚠️  等于 argmax[|S(f)|²·Prr(f)]，受步态输入谱影响，非真实fn。
    """
    err_c   = err[~np.isnan(err)]
    n       = len(err_c)
    nperseg = min(int(nperseg_s * fs), n // 2)
    if nperseg < 32:
        return np.nan
    f, P = welch(err_c, fs=fs, nperseg=nperseg, noverlap=nperseg // 2, window='hann')
    mask = (f >= fmin) & (f <= fmax)
    if not mask.any():
        return np.nan
    return float(f[mask][np.argmax(P[mask])])


# ═══════════════════════════════════════════════════════════════════════════════
# ⑥ fn_stance：接地后振铃 FFT（短窗，3-20Hz）
# ═══════════════════════════════════════════════════════════════════════════════
def estimate_fn_stance(seg, fs, fmin=3.0, fmax=20.0):
    """
    接地冲击激励下的振铃主频，通过短窗 FFT 估计。
    与 fn_th 互补：fn_stance 捕捉接地后实际振铃频率。
    """
    seg_c = seg[~np.isnan(seg)]
    if len(seg_c) < 16:
        return np.nan
    n     = len(seg_c)
    fft_f = np.fft.rfftfreq(n, 1 / fs)
    fft_m = np.abs(np.fft.rfft(seg_c * np.hanning(n)))
    mask  = (fft_f >= fmin) & (fft_f <= fmax)
    if not mask.any():
        return np.nan
    return float(fft_f[mask][np.argmax(fft_m[mask])])


# ═══════════════════════════════════════════════════════════════════════════════
# ⑦ ζ 参考：对数递减法（步行中通常无效，需自由衰减）
# ═══════════════════════════════════════════════════════════════════════════════
def log_decrement_zeta(seg, des_seg, fs, fn_guess, win_s=TD_POST_ZETA):
    """
    对数递减法估计 ζ。
    ⚠️  前提：系统处于自由衰减（无持续外力驱动）
    步行数据通常不满足此前提，v5 中仅作参考指标。

    双重校验：
      1. des 变化量 < DES_CHANGE_THRESH（排除强迫振动场景）
      2. 峰值间距 ∈ [0.5, 2.0]·T_osc（排除步态周期误识别）

    公式：δ = median{ln(A_k/A_{k+1})}，ζ = δ/√(4π²+δ²)
    """
    n     = min(len(seg), int(win_s * fs))
    seg_c = np.where(np.isnan(seg[:n]), 0.0, seg[:n])
    des_c = np.where(np.isnan(des_seg[:n]), np.nanmean(des_seg[:n]), des_seg[:n])

    # 校验1：des 是否稳定（目标不动才能自由衰减）
    des_change = float(np.nanmax(des_c) - np.nanmin(des_c))
    if des_change > DES_CHANGE_THRESH:
        return np.nan, 0, f'forced(Δ={des_change:.2f}rad)'

    # 高通 + 带通滤波
    nyq = fs / 2
    flo = max(0.5, fn_guess - 3.0)
    fhi = min(nyq - 0.5, fn_guess + 3.0)
    if flo >= fhi:
        return np.nan, 0, 'filter_err'
    try:
        b_hp, a_hp = butter(2, 1.0 / nyq, btype='high')
        seg_hp = filtfilt(b_hp, a_hp, seg_c)
        b_bp, a_bp = butter(2, [flo / nyq, fhi / nyq], btype='band')
        filtered = filtfilt(b_bp, a_bp, seg_hp)
    except Exception:
        return np.nan, 0, 'filter_err'

    # Hilbert 包络 + 峰值检测
    env = np.abs(hilbert(filtered))
    min_dist = max(1, int(0.5 * fs / fn_guess))
    peaks, _ = find_peaks(env, distance=min_dist, height=np.mean(env) * 0.3)
    if len(peaks) < 2:
        return np.nan, 0, 'too_few'

    # 校验2：峰值间距是否匹配系统振荡周期
    T_osc    = 1.0 / fn_guess
    spacings = np.diff(peaks / fs)
    if not all((ZETA_PEAK_TOL_LO * T_osc <= s <= ZETA_PEAK_TOL_HI * T_osc)
               for s in spacings):
        return np.nan, 0, f'gait_peaks(gap={np.median(spacings):.2f}s)'

    # 对数递减
    amps   = env[peaks]
    deltas = [np.log(amps[i] / amps[i + 1])
              for i in range(len(amps) - 1) if amps[i + 1] > 1e-9]
    if not deltas or any(d <= 0 for d in deltas):
        return np.nan, 0, 'non_decay'

    delta = float(np.median(deltas))
    zeta  = delta / np.sqrt(4 * np.pi ** 2 + delta ** 2)
    return float(zeta), len(peaks), 'ok'


# ═══════════════════════════════════════════════════════════════════════════════
# ⑧ 控制延迟：摆动相拼接 xcorr
# ═══════════════════════════════════════════════════════════════════════════════
def xcorr_delay(tgt_segs, jnt_segs, dt, max_lag_ms=MAX_DELAY_MS):
    """
    拼接摆动相片段，归一化互相关估计控制延迟。
    搜索范围：[-20ms, +max_lag_ms]（正滞后 = jnt 落后于 des）。
    返回：(delay_ms, xcorr_peak)
    """
    tgt_all, jnt_all = [], []
    for t_seg, j_seg in zip(tgt_segs, jnt_segs):
        t_c = t_seg[~np.isnan(t_seg)]
        j_c = j_seg[~np.isnan(j_seg)]
        if len(t_c) != len(j_c) or len(t_c) < 8:
            continue
        ts, js = t_c.std(), j_c.std()
        if ts < 1e-6 or js < 1e-6:
            continue
        tgt_all.append((t_c - t_c.mean()) / ts)
        jnt_all.append((j_c - j_c.mean()) / js)
    if not tgt_all:
        return np.nan, np.nan

    tc = np.concatenate(tgt_all)
    jc = np.concatenate(jnt_all)
    n  = len(tc)
    cc   = correlate(jc, tc, mode='full')
    lags = correlation_lags(len(jc), len(tc), mode='full')
    cc_n = cc / n

    # 搜索范围：-2样本 到 max_lag_ms/dt 样本
    max_lag_samp = int(max_lag_ms / (dt * 1000))
    mask = (lags >= -2) & (lags <= max_lag_samp)
    best = lags[mask][np.argmax(cc_n[mask])]
    return float(best * dt * 1000), float(cc_n[mask].max())


# ═══════════════════════════════════════════════════════════════════════════════
# 单轴全套指标计算（v5）
# ═══════════════════════════════════════════════════════════════════════════════
def compute_axis_metrics(df, t, dt, fs, side, axis, kp, kd):
    """
    计算单侧、单轴的全套稳定性指标（v5新增摆动相FRF）。

    计算顺序：
      1. 基础量：eRMS, err, jnt, des, 理论值
      2. 接地/离地事件：td_times, lo_times
      3. 相位分离eRMS：e_rms_swing, e_rms_stance
      4. xcorr 延迟（摆动相）
      5. 全步态FRF（含支撑相）
      6. 摆动相专用FRF（v5新增）
      7. fn_frf（全步态 + 摆动相）
      8. ζ_frf（全步态 + 摆动相）
      9. 接地后逐帧：fn_stance, ζ_ld, A_peak
    """
    jnt_col = f'pos_{side}_{axis}_joint'
    des_col = f'pos_des_raw_{side}_{axis}_joint'
    if jnt_col not in df.columns or des_col not in df.columns:
        return {}

    jnt = df[jnt_col].values.astype(float)
    des = df[des_col].values.astype(float)
    err = jnt - des

    # ── 理论值 ──────────────────────────────────────────────────────────────
    wn_th   = np.sqrt(kp / J_EFF_DEFAULT)
    fn_th   = wn_th / (2 * np.pi)
    zeta_th = kd / (2 * np.sqrt(kp * J_EFF_DEFAULT))
    tau_th  = 2 * J_EFF_DEFAULT / kd * 1000    # ms
    Mr_th   = 1.0 / (2 * zeta_th * np.sqrt(max(1 - zeta_th**2, 1e-6))) \
              if zeta_th < 1 / np.sqrt(2) else np.nan
    PM_th   = 100 * zeta_th                    # 相位裕度近似 [deg]

    # ── 1. eRMS（全步态） ────────────────────────────────────────────────────
    e_rms = float(np.sqrt(np.nanmean(err ** 2)))

    # ── 2. 接地/离地事件 ─────────────────────────────────────────────────────
    td_times, _ = debounce_td(df, t, side)
    lo_times, _ = detect_liftoff(df, t, side)

    # ── 3. 分相位eRMS（v5新增） ───────────────────────────────────────────────
    #    contact_col: {side}_contact（0=摆动, 1=支撑）
    if f'{side}_contact' in df.columns:
        contact_bool = (np.nan_to_num(df[f'{side}_contact'].values.astype(float)) > 0.5)
        e_rms_swing  = float(np.sqrt(np.nanmean(err[~contact_bool]**2))) \
                       if (~contact_bool).any() else np.nan
        e_rms_stance = float(np.sqrt(np.nanmean(err[contact_bool]**2))) \
                       if contact_bool.any() else np.nan
    else:
        e_rms_swing  = np.nan
        e_rms_stance = np.nan

    # ── 4. xcorr 延迟（摆动相片段） ─────────────────────────────────────────
    sw_tgt, sw_jnt = [], []
    for t_td in td_times:
        t0, t1 = t_td - SWING_PRE, t_td - SWING_POST
        mask = (t >= t0) & (t <= t1)
        if mask.sum() >= 8:
            sw_tgt.append(des[mask])
            sw_jnt.append(jnt[mask])
    delay_ms, xcorr_pk = xcorr_delay(sw_tgt, sw_jnt, dt)
    safe_delay = delay_ms if (not np.isnan(delay_ms) and delay_ms <= MAX_DELAY_MS) \
                 else 0.0

    # ── 5. 全步态FRF ─────────────────────────────────────────────────────────
    f_frf, H_frf, coh_frf = compute_frf(jnt, des, fs)

    # fn_frf（全步态，延迟补偿后相位-90°）
    fn_frf, coh_at_fn = estimate_fn_frf(f_frf, H_frf, coh_frf, fn_th, safe_delay)

    # G_fn + ζ_frf（全步态，|H(fn_th)|法，fn_th更稳定）
    G_fn, zeta_frf, coh_at_fn2 = estimate_zeta_frf(f_frf, H_frf, coh_frf, fn_th)
    coh_at_fn = coh_at_fn2 if not np.isnan(coh_at_fn2) else coh_at_fn

    # ── 6. 摆动相专用FRF（v5新增） ────────────────────────────────────────────
    f_sw, H_sw, coh_sw, n_swing_segs = compute_swing_frf(
        jnt, des, t, fs, td_times, lo_times
    )

    # 摆动相 fn_frf_sw（延迟补偿后相位-90°）
    fn_frf_sw, coh_fn_sw_fn = estimate_fn_frf(
        f_sw, H_sw, coh_sw, fn_th, safe_delay
    ) if f_sw is not None else (np.nan, np.nan)

    # 摆动相 G_fn_sw + ζ_frf_sw（关键：去除J_eff_stance污染）
    G_fn_sw, zeta_frf_sw, coh_fn_sw = estimate_zeta_frf(
        f_sw, H_sw, coh_sw, fn_th
    ) if f_sw is not None else (np.nan, np.nan, np.nan)

    # 用摆动相相干更新
    if not np.isnan(coh_fn_sw):
        coh_fn_sw = coh_fn_sw

    # ── 7. 误差PSD主峰（参考，受步态谐波影响） ──────────────────────────────
    fn_err = estimate_fn_err(err, fs)

    # ── 8. 接地后逐帧分析 ────────────────────────────────────────────────────
    fn_stance_list = []
    zeta_ld_list   = []
    apeak_list     = []

    for t_td in td_times:
        mask_d = (t >= t_td) & (t <= t_td + TD_POST)
        if mask_d.sum() < 20:
            continue
        seg     = err[mask_d]
        des_seg = des[mask_d]

        # fn_stance：接地振铃FFT
        fns = estimate_fn_stance(seg, fs)
        if not np.isnan(fns):
            fn_stance_list.append(fns)

        # A_peak：接地过冲幅度（前150ms峰值 / 400ms后稳态均值）
        n_early = int(0.15 * fs)
        n_late0 = int(0.40 * fs)
        if len(seg) > n_late0 + 10:
            early_pk = np.nanmax(np.abs(seg[:n_early]))
            late_mu  = np.nanmean(np.abs(seg[n_late0:]))
            if late_mu > 1e-5:
                apeak_list.append(early_pk / late_mu)

        # ζ_ld：对数递减（双重校验，步行中通常无效）
        z, npks, _ = log_decrement_zeta(seg, des_seg, fs, fn_th)
        if not np.isnan(z) and 0.01 < z < 0.90 and npks >= 2:
            zeta_ld_list.append(z)

    fn_stance = float(np.median(fn_stance_list)) if fn_stance_list else np.nan
    zeta_ld   = float(np.median(zeta_ld_list))   if zeta_ld_list   else np.nan
    a_peak    = float(np.median(apeak_list))      if apeak_list     else np.nan

    # ── 9. 由 ζ_frf 推导 ──────────────────────────────────────────────────
    jeff_hat = kp / (2 * np.pi * fn_frf) ** 2 \
               if not np.isnan(fn_frf) and fn_frf > 0 else np.nan
    tau_frf  = 1.0 / (zeta_frf * wn_th) * 1000 \
               if not np.isnan(zeta_frf) and zeta_frf > 0 else np.nan
    PM_frf   = 100 * zeta_frf if not np.isnan(zeta_frf) else np.nan
    PM_frf_sw = 100 * zeta_frf_sw if not np.isnan(zeta_frf_sw) else np.nan

    def _r(v, n=4):
        return round(float(v), n) \
               if v is not None and not (isinstance(v, float) and np.isnan(v)) \
               else None

    return {
        'side':             side,
        'axis':             axis,
        # ── 全步态误差 ─────────────────────────────────────────
        'e_rms_rad':        _r(e_rms,       5),
        'e_rms_swing':      _r(e_rms_swing, 5),   # v5新增：摆动相eRMS
        'e_rms_stance':     _r(e_rms_stance,5),   # v5新增：支撑相eRMS
        # ── 全步态自然频率 ────────────────────────────────────
        'fn_th_hz':         _r(fn_th,       3),   # 理论fn
        'fn_frf_hz':        _r(fn_frf,      3),   # FRF相位法（全步态）
        'fn_err_hz':        _r(fn_err,      3),   # 误差PSD主峰（参考）
        'fn_stance_hz':     _r(fn_stance,   3),   # 接地振铃FFT
        'jeff_hat':         _r(jeff_hat,    5),   # 由fn_frf推算的J_eff
        # ── 全步态阻尼比 ──────────────────────────────────────
        'zeta_th':          _r(zeta_th,     4),   # 理论ζ
        'G_fn':             _r(G_fn,        4),   # |H(fn_th)|全步态
        'zeta_frf':         _r(zeta_frf,    4),   # 1/(2G_fn) 全步态（含惯量污染）
        'coh_at_fn':        _r(coh_at_fn,   3),   # fn处相干函数
        'zeta_ld':          _r(zeta_ld,     4),   # 对数递减（参考）
        # ── 摆动相专用FRF（v5新增，去除J_eff_stance污染） ────
        'G_fn_sw':          _r(G_fn_sw,     4),   # 摆动相|H(fn_th)|（关键！）
        'zeta_frf_sw':      _r(zeta_frf_sw, 4),   # 摆动相ζ = 1/(2·G_fn_sw)
        'coh_fn_sw':        _r(coh_fn_sw,   3),   # 摆动相fn处相干
        'fn_frf_sw':        _r(fn_frf_sw,   3),   # 摆动相FRF相位法fn
        'PM_frf_sw_deg':    _r(PM_frf_sw,   2),   # 摆动相相位裕度估计
        'n_swing_segs':     n_swing_segs,          # 摆动相有效片段数
        # ── 时域/延迟 ────────────────────────────────────────
        'tau_th_ms':        _r(tau_th,      1),   # 理论衰减时间常数
        'tau_frf_ms':       _r(tau_frf,     1),   # 由ζ_frf推算τ
        'delay_ms':         _r(delay_ms,    1),   # xcorr控制延迟
        'xcorr_peak':       _r(xcorr_pk,    3),   # xcorr峰值（质量）
        # ── 其他 ─────────────────────────────────────────────
        'Mr_th':            _r(Mr_th,       3),   # 理论谐振增益
        'PM_th_deg':        _r(PM_th,       2),   # 理论相位裕度
        'PM_frf_deg':       _r(PM_frf,      2),   # 全步态相位裕度估计
        'A_peak':           _r(a_peak,      3),   # 接地过冲幅度
        'n_td':             len(td_times),
        'n_lo':             len(lo_times),
        'n_zeta_ld_ok':     len(zeta_ld_list),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 单次实验运行
# ═══════════════════════════════════════════════════════════════════════════════
def run_case(label, kp, kd, path, source):
    print(f"  [{source:4s}] Kp/Kd={label}  {path.split('/')[-1]}")
    df, t, dt, fs = load(path)
    print(f"    {len(df)} 行, {t[-1]:.1f}s, fs={fs:.1f}Hz")

    rows = []
    for side in SIDES:
        for axis in AXES:
            res = compute_axis_metrics(df, t, dt, fs, side, axis, kp, kd)
            if not res:
                continue
            res.update({'source': source, 'kpkd': label, 'kp': kp, 'kd': kd})
            rows.append(res)

            # 阻尼状态判断（优先使用摆动相指标）
            z_sw = res.get('zeta_frf_sw')
            z_all = res.get('zeta_frf')
            z_show = z_sw if (z_sw is not None) else z_all
            if z_show is not None:
                if z_show > 1.15:
                    status = '过阻尼'
                elif abs(z_show - 1.0) < 0.15:
                    status = '临界'
                else:
                    status = '欠阻尼'
            else:
                status = '未知'

            print(f"    [{side:5s}|{axis:12s}]  "
                  f"eRMS={res['e_rms_rad']}(sw={res['e_rms_swing']})  "
                  f"fn_th={res['fn_th_hz']}Hz  "
                  f"G_fn={res['G_fn']}(sw={res['G_fn_sw']})  "
                  f"ζ_frf={res['zeta_frf']}|ζ_sw={res['zeta_frf_sw']}[{status}]  "
                  f"coh_sw={res['coh_fn_sw']}  "
                  f"n_sw={res['n_swing_segs']}  "
                  f"delay={res['delay_ms']}ms")

    for axis in AXES:
        lft = next((r for r in rows if r['side'] == 'left'  and r['axis'] == axis), None)
        rgt = next((r for r in rows if r['side'] == 'right' and r['axis'] == axis), None)
        if lft and rgt:
            el, er = lft.get('e_rms_rad'), rgt.get('e_rms_rad')
            if el is not None and er is not None and er > 0:
                dlr = el / er
                lft['DeltaLR'] = rgt['DeltaLR'] = round(dlr, 3)
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════════════════════════════════════════
all_rows = []

print("=" * 95)
print("REAL DATA")
print("=" * 95)
for args in REAL_CASES:
    all_rows.extend(run_case(*args, 'real'))
    print()

print("=" * 95)
print("SIM DATA")
print("=" * 95)
for args in SIM_CASES:
    all_rows.extend(run_case(*args, 'sim'))
    print()

df_all = pd.DataFrame(all_rows)

# ─── 汇总表（左右平均） ────────────────────────────────────────────────────────
SUMMARY_COLS = ['kpkd',
                'e_rms_rad', 'e_rms_swing', 'e_rms_stance',
                'fn_th_hz', 'fn_frf_hz', 'fn_err_hz', 'fn_stance_hz',
                'zeta_th', 'G_fn', 'zeta_frf', 'coh_at_fn',
                'G_fn_sw', 'zeta_frf_sw', 'coh_fn_sw', 'fn_frf_sw',
                'tau_th_ms', 'tau_frf_ms', 'delay_ms',
                'PM_th_deg', 'PM_frf_deg', 'PM_frf_sw_deg',
                'A_peak', 'DeltaLR', 'n_swing_segs']

pd.set_option('display.float_format', '{:.4f}'.format)
pd.set_option('display.max_columns', 30)
pd.set_option('display.width', 300)

for axis in AXES:
    print("\n" + "=" * 120)
    print(f"汇总 — {axis.upper()}  （左右均值）")
    print("=" * 120)
    for src in ['real', 'sim']:
        sub = df_all[(df_all['source'] == src) & (df_all['axis'] == axis)].copy()
        if sub.empty:
            continue
        agg_dict = {c: ('first' if c in ('kpkd', 'DeltaLR') else 'mean')
                    for c in SUMMARY_COLS if c in sub.columns}
        agg = sub.groupby('kpkd').agg(agg_dict).reset_index(drop=True)
        print(f"\n  [{src.upper()}]")
        print(agg[[c for c in SUMMARY_COLS if c in agg.columns]].to_string(index=False))

# ─── Real vs Sim 核心对比（包含摆动相指标） ────────────────────────────────────
print("\n\n" + "=" * 130)
print("REAL vs SIM 核心对比 — 摆动相FRF揭示真实阻尼状态")
print("=" * 130)
print("\n【解读键】:")
print("  G_fn   = |H(fn_th)| 全步态（含支撑相J_eff污染）")
print("  G_fn_sw= |H(fn_th)| 摆动相专用（J_eff≈设计值，无污染）")
print("  ζ_frf  = 1/(2·G_fn)    全步态阻尼比估计（可能偏高）")
print("  ζ_sw   = 1/(2·G_fn_sw) 摆动相阻尼比估计（可信！）")
print("  诊断：G_fn_sw>0.5 → 欠阻尼（全步态G_fn低=支撑相惯量效应）")
print("        G_fn_sw<0.5 → 真正过阻尼（非惯量效应）")
print()

for axis in AXES:
    print(f"\n  [{axis}]")
    hdr = (f"  {'Kp/Kd':>8}  {'Src':>4}  {'eRMS':>6}  "
           f"{'eRMS_sw':>7}  {'eRMS_st':>7}  "
           f"{'fn_th':>5}  {'G_fn':>5}  {'ζ_frf':>6}  "
           f"{'G_fn_sw':>7}  {'ζ_sw':>6}  {'coh_sw':>6}  "
           f"{'n_sw':>4}  {'delay':>6}  {'A_pk':>5}")
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))
    for label in sorted(set(df_all['kpkd'].tolist())):
        for src in ['real', 'sim']:
            sub = df_all[(df_all['kpkd'] == label) &
                         (df_all['source'] == src) &
                         (df_all['axis'] == axis)]
            if sub.empty:
                continue
            def m(c):
                return sub[c].mean() if c in sub.columns and sub[c].notna().any() else float('nan')
            def f(v, fmt='.3f'):
                return format(v, fmt) if not np.isnan(v) else '---'
            nsw = int(sub['n_swing_segs'].mean()) if 'n_swing_segs' in sub.columns else 0
            print(f"  {label:>8}  {src:>4}  {f(m('e_rms_rad')):>6}  "
                  f"{f(m('e_rms_swing')):>7}  {f(m('e_rms_stance')):>7}  "
                  f"{f(m('fn_th_hz'), '.2f'):>5}  {f(m('G_fn')):>5}  {f(m('zeta_frf')):>6}  "
                  f"{f(m('G_fn_sw')):>7}  {f(m('zeta_frf_sw')):>6}  {f(m('coh_fn_sw')):>6}  "
                  f"{nsw:>4}  {f(m('delay_ms'), '.0f'):>6}  {f(m('A_peak')):>5}")

# ─── 结论性诊断 ────────────────────────────────────────────────────────────────
print("\n\n" + "=" * 130)
print("诊断结论")
print("=" * 130)

for axis in AXES:
    print(f"\n  [{axis}]")
    for src in ['real', 'sim']:
        sub = df_all[(df_all['source'] == src) & (df_all['axis'] == axis)].copy()
        if sub.empty:
            continue
        g_sw_vals  = sub['G_fn_sw'].dropna()
        g_all_vals = sub['G_fn'].dropna()
        z_th_val   = sub['zeta_th'].mean() if 'zeta_th' in sub.columns else float('nan')

        if len(g_sw_vals) == 0:
            print(f"    [{src.upper()}] 摆动相FRF数据不足")
            continue

        g_sw_mean  = g_sw_vals.mean()
        g_all_mean = g_all_vals.mean() if len(g_all_vals) > 0 else float('nan')
        z_sw_mean  = 1/(2*g_sw_mean) if g_sw_mean > 0 else float('nan')

        if g_sw_mean > 0.5:
            diagnosis = f"摆动相欠阻尼 (ζ_sw≈{z_sw_mean:.2f}<1.0)"
            if not np.isnan(g_all_mean) and g_all_mean < 0.5:
                reason = f"全步态G_fn={g_all_mean:.3f}<0.5 是支撑相高惯量导致fn_eff下移，非过阻尼！"
            else:
                reason = f"全步态G_fn={g_all_mean:.3f}，结果一致"
        elif g_sw_mean < 0.35:
            diagnosis = f"摆动相真正过阻尼 (ζ_sw≈{z_sw_mean:.2f}>1.0)"
            reason = "G_fn_sw低不因惯量效应，系统参数需调整"
        else:
            diagnosis = f"接近临界阻尼 (ζ_sw≈{z_sw_mean:.2f}≈1.0)"
            reason = f"G_fn_sw={g_sw_mean:.3f}≈0.5"

        print(f"    [{src.upper()}] {diagnosis}")
        print(f"           {reason}")
        print(f"           理论ζ_th={z_th_val:.3f}, G_fn_sw={g_sw_mean:.3f}, G_fn={g_all_mean:.3f}")

# ─── 保存 ─────────────────────────────────────────────────────────────────────
SAVE_COLS = ['source', 'kpkd', 'kp', 'kd', 'side', 'axis',
             'e_rms_rad', 'e_rms_swing', 'e_rms_stance',
             'fn_th_hz', 'fn_frf_hz', 'fn_err_hz', 'fn_stance_hz', 'jeff_hat',
             'zeta_th', 'G_fn', 'zeta_frf', 'coh_at_fn', 'zeta_ld',
             'G_fn_sw', 'zeta_frf_sw', 'coh_fn_sw', 'fn_frf_sw',
             'tau_th_ms', 'tau_frf_ms', 'delay_ms', 'xcorr_peak',
             'Mr_th', 'PM_th_deg', 'PM_frf_deg', 'PM_frf_sw_deg',
             'A_peak', 'DeltaLR', 'n_td', 'n_lo', 'n_swing_segs', 'n_zeta_ld_ok']
SAVE_COLS = [c for c in SAVE_COLS if c in df_all.columns]
out = '/Users/yumx/code/X1/agibot_x1_infer/real2sim/claude_stability_metrics_results.csv'
df_all[SAVE_COLS].to_csv(out, index=False)
print(f"\n\n保存完成 → {out}  ({len(df_all)} 行)")
