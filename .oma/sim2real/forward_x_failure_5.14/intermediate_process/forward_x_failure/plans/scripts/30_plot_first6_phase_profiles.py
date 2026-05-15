import csv
import math
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_repo_root(start_dir: str) -> str:
    cursor = start_dir
    while True:
        if os.path.isdir(os.path.join(cursor, "real2sim")) and os.path.isdir(os.path.join(cursor, "src")):
            return cursor
        parent = os.path.dirname(cursor)
        if parent == cursor:
            raise RuntimeError("Failed to locate repository root from plotting script path")
        cursor = parent


BASE_DIR = find_repo_root(SCRIPT_DIR)
INPUT_CSV = os.path.join(
    BASE_DIR,
    "real2sim",
    "table",
    "forward_x_failure_first6",
    "forward_x_failure_first6_phase_profiles.csv",
)
PLOT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "forward_x_failure_first6", "plots", "phase_profiles")
os.makedirs(PLOT_DIR, exist_ok=True)

JOINTS = ("hip_pitch", "knee_pitch", "ankle_pitch", "ankle_roll")
WINDOW_ROLES = (
    ("swing", "event_leg"),
    ("swing", "opposite_leg"),
    ("touchdown", "landing_leg"),
    ("touchdown", "stance_leg"),
)
COLORS = {"real": "#b33a3a", "sim": "#2d6f9f"}


def read_rows():
    with open(INPUT_CSV, newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["step_index_int"] = int(row["step_index"])
        row["phase_bin_int"] = int(row["phase_bin"])
        row["norm_phase_float"] = float(row["norm_phase"])
        row["pos_target_float"] = float(row["pos_target_rad"])
        row["joint_pos_float"] = float(row["joint_pos_rad"])
        row["tracking_err_float"] = row["pos_target_float"] - row["joint_pos_float"]
    return rows


def mean(values):
    return sum(values) / len(values) if values else math.nan


def rms(values):
    return math.sqrt(sum(value * value for value in values) / len(values)) if values else math.nan


def profile_mean(rows, dataset, window, role, joint, signal):
    grouped = defaultdict(list)
    for row in rows:
        if row["dataset"] == dataset and row["window"] == window and row["role"] == role and row["joint"] == joint:
            grouped[row["phase_bin_int"]].append(row[signal])
    phases = []
    values = []
    for phase_bin in sorted(grouped):
        phases.append(phase_bin / 20.0)
        values.append(mean(grouped[phase_bin]))
    return phases, values


def save_mean_profile_grid(rows, signal, filename, ylabel):
    fig, axes = plt.subplots(4, 4, figsize=(17, 12), constrained_layout=True, sharex=True)
    fig.suptitle(f"Phase Profile Mean: {ylabel}", fontsize=16, fontweight="bold")
    for row_idx, (window, role) in enumerate(WINDOW_ROLES):
        for col_idx, joint in enumerate(JOINTS):
            ax = axes[row_idx, col_idx]
            for dataset in ("real", "sim"):
                phases, values = profile_mean(rows, dataset, window, role, joint, signal)
                ax.plot(phases, values, label=dataset, color=COLORS[dataset], linewidth=2.0)
            ax.set_title(f"{window} | {role} | {joint}", fontsize=10)
            ax.grid(alpha=0.25)
            if col_idx == 0:
                ax.set_ylabel(ylabel)
            if row_idx == len(WINDOW_ROLES) - 1:
                ax.set_xlabel("normalized phase")
            ax.legend(frameon=False, fontsize=8)
    out_path = os.path.join(PLOT_DIR, filename)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def curve_stats(rows):
    curves = defaultdict(list)
    for row in rows:
        key = (
            row["dataset"],
            row["case_label"],
            row["step_index"],
            row["touchdown_side"],
            row["window"],
            row["role"],
            row["joint"],
        )
        curves[key].append(row)

    stats = []
    for key, points in curves.items():
        points = sorted(points, key=lambda item: item["phase_bin_int"])
        targets = [point["pos_target_float"] for point in points]
        joints = [point["joint_pos_float"] for point in points]
        errs = [target - joint for target, joint in zip(targets, joints)]
        stats.append(
            {
                "dataset": key[0],
                "case_label": key[1],
                "step_index": int(key[2]),
                "touchdown_side": key[3],
                "window": key[4],
                "role": key[5],
                "joint": key[6],
                "target_range": max(targets) - min(targets),
                "joint_range": max(joints) - min(joints),
                "tracking_err_rms": rms(errs),
                "target_delta": targets[-1] - targets[0],
                "joint_delta": joints[-1] - joints[0],
            }
        )
    return stats


def save_metric_bar(stats, metric, filename, ylabel):
    grouped = defaultdict(list)
    for row in stats:
        grouped[(row["dataset"], row["window"], row["role"], row["joint"])].append(row[metric])

    labels = [f"{window}\n{role}\n{joint}" for window, role in WINDOW_ROLES for joint in JOINTS]
    x = np.arange(len(labels))
    width = 0.36
    real_values = []
    sim_values = []
    for window, role in WINDOW_ROLES:
        for joint in JOINTS:
            real_values.append(mean(grouped[("real", window, role, joint)]))
            sim_values.append(mean(grouped[("sim", window, role, joint)]))

    fig, ax = plt.subplots(figsize=(18, 6.2), constrained_layout=True)
    ax.bar(x - width / 2, real_values, width, label="real", color=COLORS["real"], alpha=0.88)
    ax.bar(x + width / 2, sim_values, width, label="sim", color=COLORS["sim"], alpha=0.88)
    ax.set_title(f"Phase Profile Curve Metric: {ylabel}", fontsize=15, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    out_path = os.path.join(PLOT_DIR, filename)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def heatmap_matrix(stats, dataset, window, role, joint, metric):
    case_labels = sorted({row["case_label"] for row in stats if row["dataset"] == dataset})
    matrix = np.full((6, len(case_labels)), np.nan)
    for row in stats:
        if row["dataset"] == dataset and row["window"] == window and row["role"] == role and row["joint"] == joint:
            case_idx = case_labels.index(row["case_label"])
            matrix[row["step_index"] - 1, case_idx] = row[metric]
    return matrix, case_labels


def save_focus_heatmap(stats, window, role, joint, metric):
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.2), constrained_layout=True)
    matrices = []
    labels = []
    vmax = 0.0
    for dataset in ("real", "sim"):
        matrix, case_labels = heatmap_matrix(stats, dataset, window, role, joint, metric)
        matrices.append(matrix)
        labels.append(case_labels)
        vmax = max(vmax, float(np.nanmax(matrix)))

    image = None
    for ax, dataset, matrix, case_labels in zip(axes, ("real", "sim"), matrices, labels):
        image = ax.imshow(matrix, aspect="auto", cmap="viridis", vmin=0.0, vmax=max(vmax, 1e-6))
        ax.set_title(dataset)
        ax.set_xlabel("case")
        ax.set_ylabel("step")
        ax.set_xticks(np.arange(len(case_labels)))
        ax.set_xticklabels(case_labels, rotation=25, ha="right")
        ax.set_yticks(np.arange(6))
        ax.set_yticklabels([str(step) for step in range(1, 7)])
        for row_idx in range(matrix.shape[0]):
            for col_idx in range(matrix.shape[1]):
                value = matrix[row_idx, col_idx]
                if not math.isnan(value):
                    ax.text(col_idx, row_idx, f"{value:.2f}", ha="center", va="center", color="white", fontsize=8)

    fig.colorbar(image, ax=axes, shrink=0.85, label=metric)
    fig.suptitle(f"{window} | {role} | {joint} | {metric}", fontsize=15, fontweight="bold")
    out_name = f"{window}_{role}_{joint}_{metric}_step_heatmap.png"
    out_path = os.path.join(PLOT_DIR, out_name)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def raw_profile_map(rows, dataset, window, role, joint, signal):
    grouped = defaultdict(list)
    for row in rows:
        if row["dataset"] == dataset and row["window"] == window and row["role"] == role and row["joint"] == joint:
            grouped[(row["case_label"], row["step_index"])].append(row)
    out = {}
    for key, points in grouped.items():
        points = sorted(points, key=lambda item: item["phase_bin_int"])
        out[key] = (
            [point["norm_phase_float"] for point in points],
            [point[signal] for point in points],
        )
    return out


def save_raw_step_case_grid(rows, window, role, joint, signal, ylabel):
    real_map = raw_profile_map(rows, "real", window, role, joint, signal)
    sim_map = raw_profile_map(rows, "sim", window, role, joint, signal)
    real_cases = sorted({case for case, _ in real_map})
    sim_cases = sorted({case for case, _ in sim_map})

    fig, axes = plt.subplots(6, 4, figsize=(18, 16), constrained_layout=True, sharex=True, sharey=True)
    fig.suptitle(f"Raw Phase Profiles: {window} | {role} | {joint} | {ylabel}", fontsize=16, fontweight="bold")

    for step in range(1, 7):
        for col_idx in range(4):
            ax = axes[step - 1, col_idx]
            if col_idx < len(real_cases):
                key = (real_cases[col_idx], str(step))
                if key in real_map:
                    phases, values = real_map[key]
                    ax.plot(phases, values, color=COLORS["real"], linewidth=1.8, label=f"real {real_cases[col_idx]}")
            if col_idx < len(sim_cases):
                key = (sim_cases[col_idx], str(step))
                if key in sim_map:
                    phases, values = sim_map[key]
                    ax.plot(phases, values, color=COLORS["sim"], linewidth=1.8, label=f"sim {sim_cases[col_idx]}")
            ax.set_title(f"step {step} | pair {col_idx + 1}", fontsize=9)
            ax.grid(alpha=0.25)
            if col_idx == 0:
                ax.set_ylabel(ylabel)
            if step == 6:
                ax.set_xlabel("normalized phase")
            ax.legend(frameon=False, fontsize=7, loc="best")

    safe_signal = signal.replace("_float", "")
    out_name = f"raw_step_case_{window}_{role}_{joint}_{safe_signal}_real_vs_sim.png"
    out_path = os.path.join(PLOT_DIR, out_name)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def save_raw_step_case_target_joint_overlay(rows, window, role, joint):
    grouped = defaultdict(list)
    for row in rows:
        if row["window"] == window and row["role"] == role and row["joint"] == joint:
            grouped[(row["dataset"], row["case_label"], row["step_index"])].append(row)

    real_cases = sorted({case for dataset, case, _ in grouped if dataset == "real"})
    sim_cases = sorted({case for dataset, case, _ in grouped if dataset == "sim"})

    fig, axes = plt.subplots(6, 4, figsize=(18, 16), constrained_layout=True, sharex=True, sharey=True)
    fig.suptitle(f"Raw Target vs Joint Overlay: {window} | {role} | {joint}", fontsize=16, fontweight="bold")
    style = {
        ("real", "target"): {"color": COLORS["real"], "linestyle": "--", "linewidth": 1.5, "label": "real target"},
        ("real", "joint"): {"color": COLORS["real"], "linestyle": "-", "linewidth": 2.0, "label": "real joint"},
        ("sim", "target"): {"color": COLORS["sim"], "linestyle": "--", "linewidth": 1.5, "label": "sim target"},
        ("sim", "joint"): {"color": COLORS["sim"], "linestyle": "-", "linewidth": 2.0, "label": "sim joint"},
    }

    for step in range(1, 7):
        for col_idx in range(4):
            ax = axes[step - 1, col_idx]
            for dataset, cases in (("real", real_cases), ("sim", sim_cases)):
                if col_idx >= len(cases):
                    continue
                key = (dataset, cases[col_idx], str(step))
                points = sorted(grouped.get(key, []), key=lambda item: item["phase_bin_int"])
                if not points:
                    continue
                phases = [point["norm_phase_float"] for point in points]
                target = [point["pos_target_float"] for point in points]
                joint_pos = [point["joint_pos_float"] for point in points]
                ax.plot(phases, target, **style[(dataset, "target")])
                ax.plot(phases, joint_pos, **style[(dataset, "joint")])
            ax.set_title(f"step {step} | pair {col_idx + 1}", fontsize=9)
            ax.grid(alpha=0.25)
            if col_idx == 0:
                ax.set_ylabel("rad")
            if step == 6:
                ax.set_xlabel("normalized phase")
            ax.legend(frameon=False, fontsize=6, loc="best")

    out_name = f"raw_step_case_{window}_{role}_{joint}_target_joint_overlay_real_vs_sim.png"
    out_path = os.path.join(PLOT_DIR, out_name)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def main():
    rows = read_rows()
    stats = curve_stats(rows)
    overlay_specs = [
        (window, role, joint)
        for window, role in WINDOW_ROLES
        for joint in ("ankle_roll", "ankle_pitch")
    ]
    outputs = [
        save_mean_profile_grid(rows, "pos_target_float", "phase_mean_pos_target_real_vs_sim.png", "pos_target_rad"),
        save_mean_profile_grid(rows, "joint_pos_float", "phase_mean_joint_pos_real_vs_sim.png", "joint_pos_rad"),
        save_mean_profile_grid(rows, "tracking_err_float", "phase_mean_tracking_err_real_vs_sim.png", "pos_target - joint_pos rad"),
        save_metric_bar(stats, "target_range", "phase_curve_target_range_real_vs_sim.png", "target range rad"),
        save_metric_bar(stats, "joint_range", "phase_curve_joint_range_real_vs_sim.png", "joint range rad"),
        save_metric_bar(stats, "tracking_err_rms", "phase_curve_tracking_err_rms_real_vs_sim.png", "tracking err RMS rad"),
        save_focus_heatmap(stats, "touchdown", "landing_leg", "ankle_roll", "joint_range"),
        save_focus_heatmap(stats, "touchdown", "landing_leg", "ankle_roll", "tracking_err_rms"),
        save_focus_heatmap(stats, "swing", "event_leg", "ankle_roll", "joint_range"),
        save_focus_heatmap(stats, "swing", "event_leg", "ankle_roll", "tracking_err_rms"),
        save_focus_heatmap(stats, "touchdown", "landing_leg", "ankle_pitch", "joint_range"),
        save_focus_heatmap(stats, "touchdown", "landing_leg", "ankle_pitch", "tracking_err_rms"),
        save_raw_step_case_grid(rows, "touchdown", "landing_leg", "ankle_roll", "pos_target_float", "pos_target_rad"),
        save_raw_step_case_grid(rows, "swing", "event_leg", "ankle_roll", "pos_target_float", "pos_target_rad"),
        save_raw_step_case_grid(rows, "touchdown", "landing_leg", "ankle_pitch", "pos_target_float", "pos_target_rad"),
        save_raw_step_case_grid(rows, "swing", "event_leg", "ankle_pitch", "pos_target_float", "pos_target_rad"),
        save_raw_step_case_grid(rows, "touchdown", "landing_leg", "ankle_roll", "joint_pos_float", "joint_pos_rad"),
        save_raw_step_case_grid(rows, "swing", "event_leg", "ankle_roll", "joint_pos_float", "joint_pos_rad"),
        save_raw_step_case_grid(rows, "touchdown", "landing_leg", "ankle_pitch", "joint_pos_float", "joint_pos_rad"),
        save_raw_step_case_grid(rows, "swing", "event_leg", "ankle_pitch", "joint_pos_float", "joint_pos_rad"),
    ]
    outputs.extend(
        save_raw_step_case_target_joint_overlay(rows, window, role, joint)
        for window, role, joint in overlay_specs
    )
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
