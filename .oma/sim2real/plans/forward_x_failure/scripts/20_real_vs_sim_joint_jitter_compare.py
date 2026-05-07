import csv
import importlib.util
import math
import os
from collections import defaultdict


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_repo_root(start_dir: str) -> str:
    cursor = start_dir
    while True:
        if os.path.isdir(os.path.join(cursor, "real2sim")) and os.path.isdir(os.path.join(cursor, "src")):
            return cursor
        parent = os.path.dirname(cursor)
        if parent == cursor:
            raise RuntimeError("Failed to locate repository root from plan script path")
        cursor = parent


BASE_DIR = find_repo_root(SCRIPT_DIR)
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "compare")
RESULT_DIR = os.path.join(BASE_DIR, ".oma", "sim2real", "results", "forward_x_failure")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

SWING_PRE_SEC = 0.35
SWING_POST_SEC = 0.02
TOUCHDOWN_PRE_SEC = 0.05
TOUCHDOWN_POST_SEC = 0.10
EARLY_TOUCHDOWN_LIMIT = 4
MOVING_AVG_KERNEL = 5
DIFF_EPS_RAD = 5e-4
AXES = ("roll", "pitch")


def load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROUND3A = load_module(
    "round3a_plan",
    os.path.join(SCRIPT_DIR, "03a_round3_landing_window_analysis.py"),
)


REAL_CASES = [
    ("25/0.4 all_ankles", "t27_tracking_lag_b1_diag_20260430_100024.csv"),
    ("30/0.4 all_ankles", "t27_tracking_lag_b1_diag_20260430_100314.csv"),
    ("35/0.5 all_ankles", "t27_tracking_lag_b1_diag_20260430_100705.csv"),
    ("40/0.8 all_ankles", "t27_tracking_lag_b1_diag_20260430_101404.csv"),
]

SIM_CASES = [
    ("2504", "t27_tracking_lag_b1_diag_20260506_133905_2504.csv"),
    ("3505", "t27_tracking_lag_b1_diag_20260506_133024_3505.csv"),
    ("4005", "t27_tracking_lag_b1_diag_20260506_134153_4005.csv"),
    ("5008", "t27_tracking_lag_b1_diag_20260506_134417_5008.csv"),
]


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def rms(values):
    if not values:
        return math.nan
    return math.sqrt(sum(float(v) * float(v) for v in values) / len(values))


def stddev(values):
    if not values:
        return math.nan
    avg = mean(values)
    return math.sqrt(sum((float(v) - avg) ** 2 for v in values) / len(values))


def fmt(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def write_csv(path, rows):
    if not rows:
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def select_window_rows(rows, event_time, window_name):
    if window_name == "swing":
        start_t = event_time - SWING_PRE_SEC
        end_t = event_time - SWING_POST_SEC
    elif window_name == "touchdown":
        start_t = event_time - TOUCHDOWN_PRE_SEC
        end_t = event_time + TOUCHDOWN_POST_SEC
    else:
        raise ValueError(window_name)
    return [row for row in rows if start_t <= row["time_sec"] <= end_t]


def moving_average(signal, kernel_size: int):
    if not signal:
        return []
    kernel_size = max(1, min(kernel_size, len(signal)))
    half = kernel_size // 2
    out = []
    for idx in range(len(signal)):
        start = max(0, idx - half)
        end = min(len(signal), idx + half + 1)
        out.append(mean(signal[start:end]))
    return out


def sign_flip_count(signal, eps: float):
    if len(signal) < 3:
        return 0
    diffs = [signal[i + 1] - signal[i] for i in range(len(signal) - 1)]
    signs = []
    for value in diffs:
        if abs(value) <= eps:
            continue
        signs.append(1 if value > 0.0 else -1)
    if len(signs) < 2:
        return 0
    return sum(1 for i in range(len(signs) - 1) if signs[i] != signs[i + 1])


def sign_flip_rate(signal, eps: float):
    if len(signal) < 3:
        return math.nan
    diffs = [signal[i + 1] - signal[i] for i in range(len(signal) - 1)]
    signs = []
    for value in diffs:
        if abs(value) <= eps:
            continue
        signs.append(1 if value > 0.0 else -1)
    if len(signs) < 2:
        return 0.0
    flips = sum(1 for i in range(len(signs) - 1) if signs[i] != signs[i + 1])
    return flips / (len(signs) - 1)


def local_extrema_count(signal, eps: float):
    if len(signal) < 3:
        return 0
    count = 0
    for idx in range(1, len(signal) - 1):
        prev_delta = signal[idx] - signal[idx - 1]
        next_delta = signal[idx + 1] - signal[idx]
        if abs(prev_delta) <= eps or abs(next_delta) <= eps:
            continue
        if prev_delta * next_delta < 0:
            count += 1
    return count


def dominant_frequency_hz(signal, dt_sec):
    if len(signal) < 6 or dt_sec <= 0:
        return math.nan
    avg = mean(signal)
    centered = [float(value) - avg for value in signal]
    n = len(centered)
    best_freq = math.nan
    best_power = 0.0
    # Small touchdown/swing windows only; direct DFT is sufficient and dependency-free.
    for k in range(1, n // 2 + 1):
        real = 0.0
        imag = 0.0
        for idx, value in enumerate(centered):
            angle = 2.0 * math.pi * k * idx / n
            real += value * math.cos(angle)
            imag -= value * math.sin(angle)
        power = real * real + imag * imag
        if power > best_power:
            best_power = power
            best_freq = k / (n * dt_sec)
    return best_freq


def jitter_metrics(values, dt_sec):
    signal = [float(value) for value in values]
    if len(signal) < 5:
        return {
            "mean_abs": math.nan,
            "range": math.nan,
            "std": math.nan,
            "net_delta_abs": math.nan,
            "path_length": math.nan,
            "hp_rms": math.nan,
            "vel_rms": math.nan,
            "flip_rate": math.nan,
            "direction_change_rate_hz": math.nan,
            "extrema_rate_hz": math.nan,
            "dominant_freq_hz": math.nan,
        }
    baseline = moving_average(signal, MOVING_AVG_KERNEL)
    residual = [value - base for value, base in zip(signal, baseline)]
    diffs = [(signal[i + 1] - signal[i]) / max(dt_sec, 1e-6) for i in range(len(signal) - 1)]
    raw_diffs = [signal[i + 1] - signal[i] for i in range(len(signal) - 1)]
    duration_sec = max((len(signal) - 1) * dt_sec, 1e-6)
    flips = sign_flip_count(signal, DIFF_EPS_RAD)
    extrema = local_extrema_count(signal, DIFF_EPS_RAD)
    return {
        "mean_abs": mean([abs(value) for value in signal]),
        "range": max(signal) - min(signal),
        "std": stddev(signal),
        "net_delta_abs": abs(signal[-1] - signal[0]),
        "path_length": sum(abs(value) for value in raw_diffs),
        "hp_rms": rms(residual),
        "vel_rms": rms(diffs),
        "flip_rate": sign_flip_rate(signal, DIFF_EPS_RAD),
        "direction_change_rate_hz": flips / duration_sec,
        "extrema_rate_hz": extrema / duration_sec,
        "dominant_freq_hz": dominant_frequency_hz(signal, dt_sec),
    }


def analyze_case(stage, case_label, csv_path):
    rows = ROUND3A.load_csv(csv_path)
    ROUND3A.attach_fk_metrics(rows)
    events = sorted(ROUND3A.detect_touchdowns(rows), key=lambda e: e.timestamp_sec)[:EARLY_TOUCHDOWN_LIMIT]
    if len(rows) < 2:
        return [], []
    dt_sec = mean([rows[i + 1]["time_sec"] - rows[i]["time_sec"] for i in range(len(rows) - 1)])
    detail_rows = []
    for event in events:
        for window_name in ("swing", "touchdown"):
            window_rows = select_window_rows(rows, event.timestamp_sec, window_name)
            if len(window_rows) < 5:
                continue
            for side in ("left", "right"):
                for axis in AXES:
                    output_values = [row[f"pos_des_raw_{side}_ankle_{axis}_joint"] for row in window_rows]
                    joint_values = [row[f"pos_{side}_ankle_{axis}_joint"] for row in window_rows]
                    output_metrics = jitter_metrics(output_values, dt_sec)
                    joint_metrics = jitter_metrics(joint_values, dt_sec)
                    track_err = [a - b for a, b in zip(output_values, joint_values)]
                    detail_rows.append(
                        {
                            "stage": stage,
                            "case_label": case_label,
                            "diag_csv": os.path.basename(csv_path),
                            "side": side,
                            "axis": axis,
                            "window": window_name,
                            "touchdown_time_sec": event.timestamp_sec,
                            "sample_count": len(window_rows),
                            "dt_ms": dt_sec * 1000.0,
                            "output_mean_abs_rad": output_metrics["mean_abs"],
                            "output_range_rad": output_metrics["range"],
                            "output_std_rad": output_metrics["std"],
                            "output_net_delta_abs_rad": output_metrics["net_delta_abs"],
                            "output_path_length_rad": output_metrics["path_length"],
                            "output_hp_rms_rad": output_metrics["hp_rms"],
                            "output_vel_rms_radps": output_metrics["vel_rms"],
                            "output_flip_rate": output_metrics["flip_rate"],
                            "output_direction_change_rate_hz": output_metrics["direction_change_rate_hz"],
                            "output_extrema_rate_hz": output_metrics["extrema_rate_hz"],
                            "output_dominant_freq_hz": output_metrics["dominant_freq_hz"],
                            "joint_mean_abs_rad": joint_metrics["mean_abs"],
                            "joint_range_rad": joint_metrics["range"],
                            "joint_std_rad": joint_metrics["std"],
                            "joint_net_delta_abs_rad": joint_metrics["net_delta_abs"],
                            "joint_path_length_rad": joint_metrics["path_length"],
                            "joint_hp_rms_rad": joint_metrics["hp_rms"],
                            "joint_vel_rms_radps": joint_metrics["vel_rms"],
                            "joint_flip_rate": joint_metrics["flip_rate"],
                            "joint_direction_change_rate_hz": joint_metrics["direction_change_rate_hz"],
                            "joint_extrema_rate_hz": joint_metrics["extrema_rate_hz"],
                            "joint_dominant_freq_hz": joint_metrics["dominant_freq_hz"],
                            "tracking_err_rms_rad": rms(track_err),
                            "joint_to_output_hp_rms_ratio": (
                                joint_metrics["hp_rms"] / output_metrics["hp_rms"]
                                if output_metrics["hp_rms"] and not math.isnan(output_metrics["hp_rms"])
                                else math.nan
                            ),
                        }
                    )

    summary_rows = []
    grouped = defaultdict(list)
    for row in detail_rows:
        grouped[(row["stage"], row["case_label"], row["side"], row["axis"], row["window"])].append(row)
    for (row_stage, row_case, row_side, row_axis, row_window), items in sorted(grouped.items()):
        summary_rows.append(
            {
                "stage": row_stage,
                "case_label": row_case,
                "side": row_side,
                "axis": row_axis,
                "window": row_window,
                "events": len(items),
                "mean_output_hp_rms_rad": mean([r["output_hp_rms_rad"] for r in items]),
                "mean_joint_hp_rms_rad": mean([r["joint_hp_rms_rad"] for r in items]),
                "mean_output_range_rad": mean([r["output_range_rad"] for r in items]),
                "mean_joint_range_rad": mean([r["joint_range_rad"] for r in items]),
                "mean_output_path_length_rad": mean([r["output_path_length_rad"] for r in items]),
                "mean_joint_path_length_rad": mean([r["joint_path_length_rad"] for r in items]),
                "mean_output_direction_change_rate_hz": mean([r["output_direction_change_rate_hz"] for r in items]),
                "mean_joint_direction_change_rate_hz": mean([r["joint_direction_change_rate_hz"] for r in items]),
                "mean_output_dominant_freq_hz": mean([r["output_dominant_freq_hz"] for r in items]),
                "mean_joint_dominant_freq_hz": mean([r["joint_dominant_freq_hz"] for r in items]),
                "mean_output_flip_rate": mean([r["output_flip_rate"] for r in items]),
                "mean_joint_flip_rate": mean([r["joint_flip_rate"] for r in items]),
                "mean_tracking_err_rms_rad": mean([r["tracking_err_rms_rad"] for r in items]),
                "mean_joint_to_output_hp_rms_ratio": mean([r["joint_to_output_hp_rms_ratio"] for r in items]),
            }
        )
    return detail_rows, summary_rows


def stage_window_side_summary(detail_rows):
    grouped = defaultdict(list)
    for row in detail_rows:
        grouped[(row["stage"], row["window"], row["side"], row["axis"])].append(row)
    out = []
    for (stage, window, side, axis), items in sorted(grouped.items()):
        out.append(
            {
                "stage": stage,
                "window": window,
                "side": side,
                "axis": axis,
                "events": len(items),
                "mean_output_hp_rms_rad": mean([r["output_hp_rms_rad"] for r in items]),
                "mean_joint_hp_rms_rad": mean([r["joint_hp_rms_rad"] for r in items]),
                "mean_output_range_rad": mean([r["output_range_rad"] for r in items]),
                "mean_joint_range_rad": mean([r["joint_range_rad"] for r in items]),
                "mean_output_path_length_rad": mean([r["output_path_length_rad"] for r in items]),
                "mean_joint_path_length_rad": mean([r["joint_path_length_rad"] for r in items]),
                "mean_output_direction_change_rate_hz": mean([r["output_direction_change_rate_hz"] for r in items]),
                "mean_joint_direction_change_rate_hz": mean([r["joint_direction_change_rate_hz"] for r in items]),
                "mean_output_dominant_freq_hz": mean([r["output_dominant_freq_hz"] for r in items]),
                "mean_joint_dominant_freq_hz": mean([r["joint_dominant_freq_hz"] for r in items]),
                "mean_output_flip_rate": mean([r["output_flip_rate"] for r in items]),
                "mean_joint_flip_rate": mean([r["joint_flip_rate"] for r in items]),
                "mean_tracking_err_rms_rad": mean([r["tracking_err_rms_rad"] for r in items]),
                "mean_joint_to_output_hp_rms_ratio": mean([r["joint_to_output_hp_rms_ratio"] for r in items]),
            }
        )
    return out


def stage_window_summary(detail_rows):
    grouped = defaultdict(list)
    for row in detail_rows:
        grouped[(row["stage"], row["window"], row["axis"])].append(row)
    out = []
    for (stage, window, axis), items in sorted(grouped.items()):
        out.append(
            {
                "stage": stage,
                "window": window,
                "axis": axis,
                "events": len(items),
                "mean_output_hp_rms_rad": mean([r["output_hp_rms_rad"] for r in items]),
                "mean_joint_hp_rms_rad": mean([r["joint_hp_rms_rad"] for r in items]),
                "mean_output_range_rad": mean([r["output_range_rad"] for r in items]),
                "mean_joint_range_rad": mean([r["joint_range_rad"] for r in items]),
                "mean_output_path_length_rad": mean([r["output_path_length_rad"] for r in items]),
                "mean_joint_path_length_rad": mean([r["joint_path_length_rad"] for r in items]),
                "mean_output_direction_change_rate_hz": mean([r["output_direction_change_rate_hz"] for r in items]),
                "mean_joint_direction_change_rate_hz": mean([r["joint_direction_change_rate_hz"] for r in items]),
                "mean_output_dominant_freq_hz": mean([r["output_dominant_freq_hz"] for r in items]),
                "mean_joint_dominant_freq_hz": mean([r["joint_dominant_freq_hz"] for r in items]),
                "mean_output_flip_rate": mean([r["output_flip_rate"] for r in items]),
                "mean_joint_flip_rate": mean([r["joint_flip_rate"] for r in items]),
                "mean_tracking_err_rms_rad": mean([r["tracking_err_rms_rad"] for r in items]),
                "mean_joint_to_output_hp_rms_ratio": mean([r["joint_to_output_hp_rms_ratio"] for r in items]),
            }
        )
    return out


def build_result_markdown(path, stage_window_rows, stage_window_side_rows, case_rows):
    def find_row(rows, **query):
        for row in rows:
            if all(row.get(k) == v for k, v in query.items()):
                return row
        return None

    def safe_ratio(numerator, denominator):
        if denominator is None or denominator == 0 or math.isnan(denominator):
            return math.nan
        return numerator / denominator

    def max_row(rows, key, **query):
        matches = [row for row in rows if all(row.get(k) == v for k, v in query.items())]
        if not matches:
            return None
        return max(matches, key=lambda row: row.get(key, -math.inf))

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# 20 Real vs Sim Swing/Touchdown Joint Adjustment/Jitter Compare\n\n")
        handle.write("- Scope: real `t27` all-ankle 4 cases vs sim `t27` 4 cases.\n")
        handle.write("- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.\n")
        handle.write("- Signal pair: `pos_des_raw_<side>_ankle_<axis>_joint` as joint output proxy, `pos_<side>_ankle_<axis>_joint` as realized joint.\n")
        handle.write("- Axes: ankle `roll` and `pitch`; sides: left and right.\n")
        handle.write("- High-frequency metric: `hp_rms = signal - 5-sample moving average` RMS, emphasizing local shake.\n")
        handle.write("- Adjustment-size metrics: `range`, `path_length`, `net_delta_abs`; these capture large corrections even when not high-frequency.\n")
        handle.write("- Adjustment-frequency metrics: `direction_change_rate_hz`, `dominant_freq_hz`, `flip_rate`; these capture how often the correction direction changes.\n\n")

        handle.write("## Metric Dictionary\n\n")
        handle.write("| column | meaning | unit / reading |\n")
        handle.write("|---|---|---|\n")
        handle.write("| `stage` | Data source group. `real` is hardware log, `sim` is simulation log. | category |\n")
        handle.write("| `window` | Touchdown-relative phase window. `swing` is `touchdown-350ms .. touchdown-20ms`; `touchdown` is `touchdown-50ms .. touchdown+100ms`. | category |\n")
        handle.write("| `axis` | Ankle axis being evaluated. | `roll` or `pitch` |\n")
        handle.write("| `events` | Number of touchdown-window samples after aggregation. Stage summary aggregates 4 cases x 4 early touchdowns x 2 sides = 32 events per stage/window/axis. | count |\n")
        handle.write("| `out hp` | High-pass RMS of policy/raw joint output proxy `pos_des_raw`. Computed as RMS of `signal - 5-sample moving_average(signal)`. | rad; larger means output has stronger local high-frequency shake |\n")
        handle.write("| `joint hp` | High-pass RMS of realized joint position `pos`. Same computation as `out hp`. | rad; larger means actual joint has stronger local high-frequency shake |\n")
        handle.write("| `hp ratio` | `joint hp / out hp`. | dimensionless; larger than 1 means realized joint high-frequency residual exceeds output residual |\n")
        handle.write("| `out range` | `max(output) - min(output)` inside the window. | rad; output adjustment amplitude |\n")
        handle.write("| `joint range` | `max(joint) - min(joint)` inside the window. | rad; realized joint adjustment amplitude |\n")
        handle.write("| `out path` | Sum of absolute frame-to-frame output changes: `sum(abs(diff(output)))`. | rad; cumulative output adjustment distance |\n")
        handle.write("| `joint path` | Sum of absolute frame-to-frame realized joint changes: `sum(abs(diff(joint)))`. | rad; cumulative realized joint adjustment distance |\n")
        handle.write("| `out dir hz` | Direction-change rate of output, based on sign flips of first differences after a small epsilon filter. | Hz; larger means output reverses correction direction more often |\n")
        handle.write("| `joint dir hz` | Direction-change rate of realized joint, same method as `out dir hz`. | Hz; larger means actual joint reverses correction direction more often |\n")
        handle.write("| `out dom hz` | Dominant frequency of the output signal in the local window, estimated by direct DFT after mean removal. | Hz; main low/window-scale oscillation component, not alone a jitter verdict |\n")
        handle.write("| `joint dom hz` | Dominant frequency of the realized joint signal in the local window, same method as `out dom hz`. | Hz; main realized-joint oscillation component |\n")
        handle.write("| `track err` | RMS tracking error between output and realized joint: `rms(output - joint)`. | rad; larger means output-to-joint realization gap is larger |\n\n")

        handle.write("## Stage Summary\n\n")
        handle.write("| stage | window | axis | events | out hp | joint hp | hp ratio | out range | joint range | out path | joint path | out dir hz | joint dir hz | out dom hz | joint dom hz | track err |\n")
        handle.write("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in stage_window_rows:
            handle.write(
                f"| {row['stage']} | {row['window']} | {row['axis']} | {int(row['events'])} | {fmt(row['mean_output_hp_rms_rad'])} | "
                f"{fmt(row['mean_joint_hp_rms_rad'])} | {fmt(row['mean_joint_to_output_hp_rms_ratio'])} | "
                f"{fmt(row['mean_output_range_rad'])} | {fmt(row['mean_joint_range_rad'])} | "
                f"{fmt(row['mean_output_path_length_rad'])} | {fmt(row['mean_joint_path_length_rad'])} | "
                f"{fmt(row['mean_output_direction_change_rate_hz'])} | {fmt(row['mean_joint_direction_change_rate_hz'])} | "
                f"{fmt(row['mean_output_dominant_freq_hz'])} | {fmt(row['mean_joint_dominant_freq_hz'])} | "
                f"{fmt(row['mean_tracking_err_rms_rad'])} |\n"
            )

        handle.write("\n### Stage Summary Analysis\n\n")
        handle.write("- `real` 的问题不是单一高频抖动。新 kinematic touchdown 窗口下，real 的 `joint range/joint path/track err` 仍整体高于 sim，说明主要差异仍是更大的真实关节调整负担和更差的 output-to-joint 兑现。\n")
        handle.write("- `swing` 阶段主要表现为“调整更大”，不是“所有高频都更大”。例如 `pitch swing` 的 `joint hp` real/sim 为 "
                     f"`{fmt(safe_ratio(find_row(stage_window_rows, stage='real', window='swing', axis='pitch')['mean_joint_hp_rms_rad'], find_row(stage_window_rows, stage='sim', window='swing', axis='pitch')['mean_joint_hp_rms_rad']))}`x，"
                     "但 `joint range` 和 `joint path` 仍分别为 "
                     f"`{fmt(safe_ratio(find_row(stage_window_rows, stage='real', window='swing', axis='pitch')['mean_joint_range_rad'], find_row(stage_window_rows, stage='sim', window='swing', axis='pitch')['mean_joint_range_rad']))}`x / "
                     f"`{fmt(safe_ratio(find_row(stage_window_rows, stage='real', window='swing', axis='pitch')['mean_joint_path_length_rad'], find_row(stage_window_rows, stage='sim', window='swing', axis='pitch')['mean_joint_path_length_rad']))}`x，"
                     "说明 swing 更像过量姿态修正。\n")
        handle.write("- `touchdown` 才是差异最集中的窗口。`roll touchdown` 的 `joint hp/range/path/dir-rate` real 相对 sim 分别为 "
                     f"`{fmt(safe_ratio(find_row(stage_window_rows, stage='real', window='touchdown', axis='roll')['mean_joint_hp_rms_rad'], find_row(stage_window_rows, stage='sim', window='touchdown', axis='roll')['mean_joint_hp_rms_rad']))}`x / "
                     f"`{fmt(safe_ratio(find_row(stage_window_rows, stage='real', window='touchdown', axis='roll')['mean_joint_range_rad'], find_row(stage_window_rows, stage='sim', window='touchdown', axis='roll')['mean_joint_range_rad']))}`x / "
                     f"`{fmt(safe_ratio(find_row(stage_window_rows, stage='real', window='touchdown', axis='roll')['mean_joint_path_length_rad'], find_row(stage_window_rows, stage='sim', window='touchdown', axis='roll')['mean_joint_path_length_rad']))}`x / "
                     f"`{fmt(safe_ratio(find_row(stage_window_rows, stage='real', window='touchdown', axis='roll')['mean_joint_direction_change_rate_hz'], find_row(stage_window_rows, stage='sim', window='touchdown', axis='roll')['mean_joint_direction_change_rate_hz']))}`x，"
                     "这是当前最重的异常点。\n")
        handle.write("- `pitch touchdown` 的读法需要降级：real 的 `joint hp` 不高于 sim，但 `joint range/path/track err` 仍高于 sim，因此它更像接触窗口内的大幅姿态兑现问题，而不是 pitch 高频抖动问题。\n")
        handle.write("- `hp ratio` 在 real 全部小于 `1`，说明真实 joint 没有把输出高频进一步放大成更大的高频噪声，反而滤掉了一部分高频；但 real 的 `joint range/joint path/track err` 仍明显更大，说明问题更像“大幅度、长路径的纠偏 + 更差的输出兑现”，而不是纯高频抖振。\n")

        handle.write("\n## Stage-Side Summary\n\n")
        handle.write("| stage | window | side | axis | events | joint hp | joint range | joint path | joint dir hz | joint dom hz | track err |\n")
        handle.write("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in stage_window_side_rows:
            handle.write(
                f"| {row['stage']} | {row['window']} | {row['side']} | {row['axis']} | {int(row['events'])} | "
                f"{fmt(row['mean_joint_hp_rms_rad'])} | {fmt(row['mean_joint_range_rad'])} | "
                f"{fmt(row['mean_joint_path_length_rad'])} | {fmt(row['mean_joint_direction_change_rate_hz'])} | "
                f"{fmt(row['mean_joint_dominant_freq_hz'])} | {fmt(row['mean_tracking_err_rms_rad'])} |\n"
            )

        handle.write("\n### Stage-Side Summary Analysis\n\n")
        for stage in ("real", "sim"):
            for window in ("swing", "touchdown"):
                for axis in AXES:
                    left_row = find_row(stage_window_side_rows, stage=stage, window=window, side="left", axis=axis)
                    right_row = find_row(stage_window_side_rows, stage=stage, window=window, side="right", axis=axis)
                    if not left_row or not right_row:
                        continue
                    range_heavier = "left" if left_row["mean_joint_range_rad"] >= right_row["mean_joint_range_rad"] else "right"
                    path_heavier = "left" if left_row["mean_joint_path_length_rad"] >= right_row["mean_joint_path_length_rad"] else "right"
                    dir_heavier = "left" if left_row["mean_joint_direction_change_rate_hz"] >= right_row["mean_joint_direction_change_rate_hz"] else "right"
                    track_heavier = "left" if left_row["mean_tracking_err_rms_rad"] >= right_row["mean_tracking_err_rms_rad"] else "right"
                    handle.write(
                        f"- {stage} {window} {axis}: `range/path` 更重的是 `{range_heavier}` / `{path_heavier}`，"
                        f"`dir-rate` 更高的是 `{dir_heavier}`，`track err` 更大的是 `{track_heavier}`。"
                        f" 左右数值分别为 range `{fmt(left_row['mean_joint_range_rad'])}` / `{fmt(right_row['mean_joint_range_rad'])}`，"
                        f"path `{fmt(left_row['mean_joint_path_length_rad'])}` / `{fmt(right_row['mean_joint_path_length_rad'])}`，"
                        f"dir-rate `{fmt(left_row['mean_joint_direction_change_rate_hz'])}` / `{fmt(right_row['mean_joint_direction_change_rate_hz'])}`。\n"
                    )
        handle.write("- 从 `real` 侧读法看，`swing roll` 和 `touchdown roll` 都不是完全对称问题：左侧更偏“大幅修正”，右侧更偏“频繁反向修正”。这更像左右脚在不同子阶段承担了不同的补偿方式，而不是单脚统一高频炸掉。\n")
        handle.write("- `real touchdown pitch` 在新窗口下左侧 `range/path/dir-rate/track err` 均略高，说明 pitch 接触窗更偏左侧兑现负担，而不是左右脚完全对称。\n")
        handle.write("- `sim` 侧虽然也有左右差异，但 real 的 roll `joint range/path/track err` 仍明显更高，说明 real 仍存在更重的 touchdown 调整负担。\n")

        handle.write("\n## Per-case Side Summary\n\n")
        handle.write("| stage | case | side | axis | window | events | joint hp | joint range | joint path | joint dir hz | track err |\n")
        handle.write("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|\n")
        for row in case_rows:
            handle.write(
                f"| {row['stage']} | {row['case_label']} | {row['side']} | {row['axis']} | {row['window']} | {int(row['events'])} | "
                f"{fmt(row['mean_joint_hp_rms_rad'])} | {fmt(row['mean_joint_range_rad'])} | "
                f"{fmt(row['mean_joint_path_length_rad'])} | {fmt(row['mean_joint_direction_change_rate_hz'])} | "
                f"{fmt(row['mean_tracking_err_rms_rad'])} |\n"
            )

        real_path_peak = max_row(case_rows, "mean_joint_path_length_rad", stage="real")
        real_track_peak = max_row(case_rows, "mean_tracking_err_rms_rad", stage="real")
        real_hp_peak = max_row(case_rows, "mean_joint_hp_rms_rad", stage="real")
        sim_path_peak = max_row(case_rows, "mean_joint_path_length_rad", stage="sim")
        sim_track_peak = max_row(case_rows, "mean_tracking_err_rms_rad", stage="sim")
        sim_hp_peak = max_row(case_rows, "mean_joint_hp_rms_rad", stage="sim")

        handle.write("\n### Per-case Side Summary Analysis\n\n")
        if real_path_peak:
            handle.write(
                f"- `real` 最大累计调整路径出现在 `{real_path_peak['case_label']}` / `{real_path_peak['side']}` / "
                f"`{real_path_peak['axis']}` / `{real_path_peak['window']}`，`joint path = {fmt(real_path_peak['mean_joint_path_length_rad'])}`。"
                " 这说明 real 的问题不是所有 case 平均一致，而是部分工况在局部窗口会出现明显更重的反复修正。\n"
            )
        if real_track_peak:
            handle.write(
                f"- `real` 最大兑现误差出现在 `{real_track_peak['case_label']}` / `{real_track_peak['side']}` / "
                f"`{real_track_peak['axis']}` / `{real_track_peak['window']}`，`track err = {fmt(real_track_peak['mean_tracking_err_rms_rad'])}`。"
                " 这说明某些 real case 不只是调得多，而且 `output -> joint` 落地更差。\n"
            )
        if real_hp_peak:
            handle.write(
                f"- `real` 最大局部高频出现在 `{real_hp_peak['case_label']}` / `{real_hp_peak['side']}` / "
                f"`{real_hp_peak['axis']}` / `{real_hp_peak['window']}`，`joint hp = {fmt(real_hp_peak['mean_joint_hp_rms_rad'])}`。"
                " 高频峰值并不总和最大路径、最大兑现误差落在同一行，再次说明不能只用 `hp_rms` 代表全部现象。\n"
            )
        if sim_path_peak and sim_track_peak and sim_hp_peak:
            handle.write(
                f"- `sim` 的对应峰值分别是：最大 `joint path` `{fmt(sim_path_peak['mean_joint_path_length_rad'])}`，"
                f"最大 `track err` `{fmt(sim_track_peak['mean_tracking_err_rms_rad'])}`，最大 `joint hp` `{fmt(sim_hp_peak['mean_joint_hp_rms_rad'])}`。"
                " sim 也存在局部峰值，但总体仍低于 real 的 failure 级别窗口，说明 sim 的局部 realization 偏差尚未跨过可前走边界。\n"
            )
        handle.write("- 按 case 读，这批数据不支持“只有一个特定 `kp/kd` 工况坏掉”的说法。多个 real case 都能在不同侧、不同轴、不同窗口上拉高 `path/track err/hp`，更像系统性 sim2real 差异，而不是单一参数点异常。\n")

        handle.write("\n## Interpretation\n\n")
        for axis in AXES:
            for window in ("swing", "touchdown"):
                real_row = find_row(stage_window_rows, stage="real", window=window, axis=axis)
                sim_row = find_row(stage_window_rows, stage="sim", window=window, axis=axis)
                if not real_row or not sim_row:
                    continue
                handle.write(
                    f"- {axis} {window}: joint hp real/sim `{fmt(real_row['mean_joint_hp_rms_rad'])}` / `{fmt(sim_row['mean_joint_hp_rms_rad'])}` "
                    f"= `{fmt(safe_ratio(real_row['mean_joint_hp_rms_rad'], sim_row['mean_joint_hp_rms_rad']))}`x; "
                    f"joint range `{fmt(real_row['mean_joint_range_rad'])}` / `{fmt(sim_row['mean_joint_range_rad'])}` "
                    f"= `{fmt(safe_ratio(real_row['mean_joint_range_rad'], sim_row['mean_joint_range_rad']))}`x; "
                    f"joint path `{fmt(real_row['mean_joint_path_length_rad'])}` / `{fmt(sim_row['mean_joint_path_length_rad'])}` "
                    f"= `{fmt(safe_ratio(real_row['mean_joint_path_length_rad'], sim_row['mean_joint_path_length_rad']))}`x; "
                    f"joint dir-rate `{fmt(real_row['mean_joint_direction_change_rate_hz'])}` / `{fmt(sim_row['mean_joint_direction_change_rate_hz'])}` Hz "
                    f"= `{fmt(safe_ratio(real_row['mean_joint_direction_change_rate_hz'], sim_row['mean_joint_direction_change_rate_hz']))}`x; "
                    f"tracking err `{fmt(real_row['mean_tracking_err_rms_rad'])}` / `{fmt(sim_row['mean_tracking_err_rms_rad'])}`.\n"
                )
        handle.write("- 判定逻辑不再把 `jitter` 等同于单一高频残差：`hp_rms` 只回答局部高频抖动，`range/path_length` 回答调整幅值和总调整量，`direction_change_rate_hz/dominant_freq_hz` 回答调整频率。\n")
        handle.write("- 如果 real 的 joint 指标显著高于 output 指标，说明抖动/调整主要在执行层、关节跟踪或结构响应中被引入或放大；如果 output 已经高，则需要回查策略输出或状态输入。\n")
        handle.write("- Use the side summary to check whether the excess adjustment is left-right symmetric or concentrated on one ankle.\n")


def main():
    all_detail = []
    all_case_summary = []

    for case_label, filename in REAL_CASES:
        csv_path = os.path.join(BASE_DIR, "test_logs", "data_csv", filename)
        detail_rows, summary_rows = analyze_case("real", case_label, csv_path)
        all_detail.extend(detail_rows)
        all_case_summary.extend(summary_rows)

    for case_label, filename in SIM_CASES:
        csv_path = os.path.join(BASE_DIR, "test_logs", "data_csv", "sim", filename)
        detail_rows, summary_rows = analyze_case("sim", case_label, csv_path)
        all_detail.extend(detail_rows)
        all_case_summary.extend(summary_rows)

    stage_window_rows = stage_window_summary(all_detail)
    stage_window_side_rows = stage_window_side_summary(all_detail)

    detail_csv = os.path.join(OUT_DIR, "real_vs_sim_joint_jitter_detail.csv")
    case_csv = os.path.join(OUT_DIR, "real_vs_sim_joint_jitter_case_summary.csv")
    stage_csv = os.path.join(OUT_DIR, "real_vs_sim_joint_jitter_stage_summary.csv")
    side_csv = os.path.join(OUT_DIR, "real_vs_sim_joint_jitter_stage_side_summary.csv")
    result_md = os.path.join(RESULT_DIR, "20_real_vs_sim_joint_jitter_compare.md")

    write_csv(detail_csv, all_detail)
    write_csv(case_csv, all_case_summary)
    write_csv(stage_csv, stage_window_rows)
    write_csv(side_csv, stage_window_side_rows)
    build_result_markdown(result_md, stage_window_rows, stage_window_side_rows, all_case_summary)

    print(detail_csv)
    print(case_csv)
    print(stage_csv)
    print(side_csv)
    print(result_md)


if __name__ == "__main__":
    main()
