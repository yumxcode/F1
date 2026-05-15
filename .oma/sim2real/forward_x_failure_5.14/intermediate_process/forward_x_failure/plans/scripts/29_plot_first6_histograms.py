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
    "forward_x_failure_first6_cycle_histograms.csv",
)
PLOT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "forward_x_failure_first6", "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

FREQUENCY_BINS = [
    "[0.00,1.00)",
    "[1.00,2.50)",
    "[2.50,5.00)",
    "[5.00,8.00)",
    "[8.00,12.00)",
    "[12.00,20.00)",
    "[20.00,1000.00)",
]
AMPLITUDE_BINS = [
    "[0.000,0.005)",
    "[0.005,0.010)",
    "[0.010,0.020)",
    "[0.020,0.040)",
    "[0.040,0.080)",
    "[0.080,1.000)",
]
BIN_LABELS = {
    "frequency": ["0-1", "1-2.5", "2.5-5", "5-8", "8-12", "12-20", "20+"],
    "amplitude": ["0-.005", ".005-.01", ".01-.02", ".02-.04", ".04-.08", ".08+"],
}
BIN_ORDER = {"frequency": FREQUENCY_BINS, "amplitude": AMPLITUDE_BINS}


def read_rows():
    with open(INPUT_CSV, newline="") as handle:
        return list(csv.DictReader(handle))


def float_or_nan(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def aggregate_counts(rows, hist_type, dataset, window, axis):
    counts = {label: 0 for label in BIN_ORDER[hist_type]}
    for row in rows:
        if (
            row["hist_type"] == hist_type
            and row["dataset"] == dataset
            and row["window"] == window
            and row["axis"] == axis
        ):
            counts[row["bin_label"]] += int(row["count"])
    return [counts[label] for label in BIN_ORDER[hist_type]]


def aggregate_metric(rows, hist_type, dataset, window, axis, metric_name):
    sums = {label: 0.0 for label in BIN_ORDER[hist_type]}
    weights = {label: 0 for label in BIN_ORDER[hist_type]}
    for row in rows:
        if (
            row["hist_type"] == hist_type
            and row["dataset"] == dataset
            and row["window"] == window
            and row["axis"] == axis
        ):
            count = int(row["count"])
            value = float_or_nan(row[metric_name])
            if count > 0 and not math.isnan(value):
                sums[row["bin_label"]] += value * count
                weights[row["bin_label"]] += count
    return [sums[label] / weights[label] if weights[label] else math.nan for label in BIN_ORDER[hist_type]]


def save_grouped_bar(rows, hist_type, metric_name=None):
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
    fig.suptitle(
        f"{hist_type.title()} Histogram: real vs sim"
        if metric_name is None
        else f"{hist_type.title()} Histogram Metric: {metric_name}",
        fontsize=16,
        fontweight="bold",
    )
    x = np.arange(len(BIN_ORDER[hist_type]))
    width = 0.36
    colors = {"real": "#b33a3a", "sim": "#2d6f9f"}

    for ax, (window, axis) in zip(axes.flat, [(w, a) for w in ("swing", "touchdown") for a in ("pitch", "roll")]):
        if metric_name is None:
            real_values = aggregate_counts(rows, hist_type, "real", window, axis)
            sim_values = aggregate_counts(rows, hist_type, "sim", window, axis)
            ylabel = "cycle count"
        else:
            real_values = aggregate_metric(rows, hist_type, "real", window, axis, metric_name)
            sim_values = aggregate_metric(rows, hist_type, "sim", window, axis, metric_name)
            ylabel = metric_name
        ax.bar(x - width / 2, real_values, width, label="real", color=colors["real"], alpha=0.88)
        ax.bar(x + width / 2, sim_values, width, label="sim", color=colors["sim"], alpha=0.88)
        ax.set_title(f"{window} {axis}")
        ax.set_xticks(x)
        ax.set_xticklabels(BIN_LABELS[hist_type], rotation=25, ha="right")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(frameon=False)

    suffix = "count" if metric_name is None else metric_name.replace("mean_", "").replace("_", "-")
    out_path = os.path.join(PLOT_DIR, f"{hist_type}_{suffix}_real_vs_sim.png")
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def step_heatmap_matrix(rows, hist_type, dataset, window, axis, bin_label):
    matrix = np.zeros((6, 4), dtype=float)
    case_labels = sorted({row["case_label"] for row in rows if row["dataset"] == dataset})
    for case_idx, case_label in enumerate(case_labels):
        for step in range(1, 7):
            total = 0
            for row in rows:
                if (
                    row["hist_type"] == hist_type
                    and row["dataset"] == dataset
                    and row["case_label"] == case_label
                    and row["step_index"] == str(step)
                    and row["window"] == window
                    and row["axis"] == axis
                    and row["bin_label"] == bin_label
                ):
                    total += int(row["count"])
            matrix[step - 1, case_idx] = total
    return matrix, case_labels


def save_step_heatmap(rows, hist_type, window, axis, bin_label):
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.2), constrained_layout=True)
    vmax = 1.0
    matrices = []
    labels = []
    for dataset in ("real", "sim"):
        matrix, case_labels = step_heatmap_matrix(rows, hist_type, dataset, window, axis, bin_label)
        matrices.append(matrix)
        labels.append(case_labels)
        vmax = max(vmax, float(np.max(matrix)))

    for ax, dataset, matrix, case_labels in zip(axes, ("real", "sim"), matrices, labels):
        image = ax.imshow(matrix, aspect="auto", cmap="magma", vmin=0, vmax=vmax)
        ax.set_title(dataset)
        ax.set_xlabel("case")
        ax.set_ylabel("step")
        ax.set_xticks(np.arange(len(case_labels)))
        ax.set_xticklabels(case_labels, rotation=25, ha="right")
        ax.set_yticks(np.arange(6))
        ax.set_yticklabels([str(i) for i in range(1, 7)])
        for row_idx in range(matrix.shape[0]):
            for col_idx in range(matrix.shape[1]):
                ax.text(col_idx, row_idx, f"{int(matrix[row_idx, col_idx])}", ha="center", va="center", color="white", fontsize=9)
    fig.colorbar(image, ax=axes, shrink=0.85, label="cycle count")
    clean_bin = (
        bin_label.replace("[", "")
        .replace(")", "")
        .replace(",", "_")
        .replace(".", "p")
        .replace(" ", "")
    )
    out_path = os.path.join(PLOT_DIR, f"{hist_type}_{window}_{axis}_{clean_bin}_step_heatmap.png")
    fig.suptitle(f"{hist_type.title()} bin {bin_label}: {window} {axis}", fontsize=15, fontweight="bold")
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def main():
    rows = read_rows()
    outputs = []
    for hist_type in ("frequency", "amplitude"):
        outputs.append(save_grouped_bar(rows, hist_type))
        outputs.append(save_grouped_bar(rows, hist_type, "mean_joint_amplitude_rad"))
        outputs.append(save_grouped_bar(rows, hist_type, "mean_tracking_err_rms_rad"))

    outputs.append(save_step_heatmap(rows, "amplitude", "touchdown", "roll", "[0.080,1.000)"))
    outputs.append(save_step_heatmap(rows, "amplitude", "swing", "roll", "[0.080,1.000)"))
    outputs.append(save_step_heatmap(rows, "frequency", "touchdown", "roll", "[20.00,1000.00)"))
    outputs.append(save_step_heatmap(rows, "frequency", "swing", "roll", "[20.00,1000.00)"))

    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
