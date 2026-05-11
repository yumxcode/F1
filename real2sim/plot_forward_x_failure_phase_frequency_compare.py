#!/usr/bin/env python3
"""Draw real-vs-sim comparison charts for phase frequency overview CSV."""

from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = (
    ROOT
    / "table"
    / "forward_x_failure_first6"
    / "forward_x_failure_first6_complete_phase_frequency_kp_side_overview.csv"
)
OUT_DIR = ROOT / "table" / "forward_x_failure_first6" / "plots"
OUT_SVG = OUT_DIR / "forward_x_failure_first6_kp_phase_side_joint_real_sim_compare.svg"
OUT_CSV = (
    ROOT
    / "table"
    / "forward_x_failure_first6"
    / "forward_x_failure_first6_kp_phase_side_joint_real_sim_compare.csv"
)

METRICS = [
    ("joint dominant hz", "mean_joint_dominant_freq_hz", "Hz"),
    ("joint dir hz", "mean_joint_direction_change_rate_hz", "Hz"),
    ("joint path/s", "mean_joint_path_rate_radps", "rad/s"),
    ("joint range", "mean_joint_range_rad", "rad"),
]

PHASE_ORDER = ["complete_support", "complete_swing"]
SIDE_ORDER = ["left", "right"]
JOINT_ORDER = ["hip_pitch", "hip_roll", "knee_pitch", "ankle_pitch", "ankle_roll"]


def sort_key(row: dict[str, object]) -> tuple[int, int, int]:
    return (
        PHASE_ORDER.index(str(row["phase"])),
        SIDE_ORDER.index(str(row["side"])),
        JOINT_ORDER.index(str(row["joint"])),
    )


def fmt(value: float) -> str:
    if value != value:
        return ""
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_pairs() -> tuple[list[dict[str, object]], list[str]]:
    rows = []
    with INPUT.open(newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    by_key: dict[tuple[str, str, str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    datasets_by_kp: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        key = (row["kp_case"], row["phase"], row["side"], row["joint"])
        by_key[key][row["dataset"]] = row
        datasets_by_kp[row["kp_case"]].add(row["dataset"])

    paired_rows = []
    for key, dataset_rows in by_key.items():
        if "real" not in dataset_rows or "sim" not in dataset_rows:
            continue
        kp_case, phase, side, joint = key
        out: dict[str, object] = {
            "kp_case": kp_case,
            "phase": phase,
            "side": side,
            "joint": joint,
        }
        for label, col, _unit in METRICS:
            real = float(dataset_rows["real"][col])
            sim = float(dataset_rows["sim"][col])
            out[f"{label} real"] = real
            out[f"{label} sim"] = sim
            out[f"{label} sim-real"] = sim - real
            out[f"{label} sim/real"] = sim / real if real else float("nan")
        paired_rows.append(out)

    paired_kp = sorted({str(r["kp_case"]) for r in paired_rows})
    unpaired_kp = [
        kp for kp, datasets in sorted(datasets_by_kp.items()) if datasets != {"real", "sim"}
    ]
    paired_rows.sort(key=lambda r: (str(r["kp_case"]), *sort_key(r)))
    return paired_rows, unpaired_kp


def write_csv(rows: list[dict[str, object]]) -> None:
    fields = ["kp_case", "phase", "side", "joint"]
    for label, _col, _unit in METRICS:
        fields.extend(
            [
                f"{label} real",
                f"{label} sim",
                f"{label} sim-real",
                f"{label} sim/real",
            ]
        )
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_svg(rows: list[dict[str, object]], unpaired_kp: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_kp: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_kp[str(row["kp_case"])].append(row)

    margin_l = 360
    margin_r = 50
    title_h = 120
    metric_w = 315
    row_h = 24
    kp_gap = 58
    header_h = 42
    width = margin_l + len(METRICS) * metric_w + margin_r
    height = title_h + sum(header_h + len(v) * row_h + kp_gap for v in by_kp.values()) + 40
    max_by_metric = {
        label: max(float(r[f"{label} real"]) for r in rows)
        if max(float(r[f"{label} real"]) for r in rows)
        > max(float(r[f"{label} sim"]) for r in rows)
        else max(float(r[f"{label} sim"]) for r in rows)
        for label, _col, _unit in METRICS
    }

    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Arial,Helvetica,sans-serif;fill:#18212f}",
        ".title{font-size:26px;font-weight:700}",
        ".subtitle{font-size:13px;fill:#526174}",
        ".section{font-size:18px;font-weight:700}",
        ".head{font-size:13px;font-weight:700;fill:#334155}",
        ".label{font-size:12px;fill:#334155}",
        ".small{font-size:10px;fill:#526174}",
        ".grid{stroke:#d8dee8;stroke-width:1}",
        ".real{fill:#2563eb}",
        ".sim{fill:#dc2626}",
        ".bg{fill:#f8fafc}",
        ".band{fill:#eef2f7}",
        "</style>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="34" y="42" class="title">Real vs Sim joint metrics at identical kp/kd</text>',
        f'<text x="34" y="66" class="subtitle">Source: {esc(INPUT.relative_to(ROOT.parent))}</text>',
        '<text x="34" y="84" class="subtitle">Dominant Hz uses FFT/PSD on joint_pos after demeaning and Hann windowing; DC is ignored.</text>',
        '<rect x="34" y="100" width="14" height="8" class="real"/>',
        '<text x="54" y="108" class="subtitle">real</text>',
        '<rect x="104" y="100" width="14" height="8" class="sim"/>',
        '<text x="124" y="108" class="subtitle">sim</text>',
    ]
    if unpaired_kp:
        svg.append(
            f'<text x="205" y="108" class="subtitle">Skipped unpaired kp_case: '
            f'{esc(", ".join(unpaired_kp))}</text>'
        )

    y = title_h
    for kp_case, kp_rows in by_kp.items():
        svg.append(f'<text x="34" y="{y}" class="section">{esc(kp_case)}</text>')
        y += 24
        for i, (label, _col, unit) in enumerate(METRICS):
            x = margin_l + i * metric_w
            svg.append(f'<text x="{x}" y="{y}" class="head">{esc(label)} ({esc(unit)})</text>')
            svg.append(f'<line x1="{x}" y1="{y + 8}" x2="{x + metric_w - 28}" y2="{y + 8}" class="grid"/>')
        y += 18

        last_group = None
        for row in kp_rows:
            group = (row["phase"], row["side"])
            if group != last_group:
                svg.append(
                    f'<rect x="28" y="{y - 13}" width="{width - 56}" height="{row_h}" class="band"/>'
                )
                svg.append(
                    f'<text x="34" y="{y + 4}" class="head">{esc(row["phase"])} | {esc(row["side"])}</text>'
                )
                last_group = group
            svg.append(f'<text x="205" y="{y + 4}" class="label">{esc(row["joint"])}</text>')
            for i, (label, _col, _unit) in enumerate(METRICS):
                x = margin_l + i * metric_w
                max_value = max_by_metric[label] or 1.0
                real = float(row[f"{label} real"])
                sim = float(row[f"{label} sim"])
                bar_max = metric_w - 116
                real_w = max(1, real / max_value * bar_max)
                sim_w = max(1, sim / max_value * bar_max)
                svg.append(f'<rect x="{x}" y="{y - 8}" width="{bar_max}" height="8" class="bg"/>')
                svg.append(f'<rect x="{x}" y="{y - 8}" width="{real_w:.1f}" height="8" class="real"/>')
                svg.append(f'<rect x="{x}" y="{y + 2}" width="{bar_max}" height="8" class="bg"/>')
                svg.append(f'<rect x="{x}" y="{y + 2}" width="{sim_w:.1f}" height="8" class="sim"/>')
                svg.append(f'<text x="{x + bar_max + 8}" y="{y - 1}" class="small">{fmt(real)}</text>')
                svg.append(f'<text x="{x + bar_max + 8}" y="{y + 9}" class="small">{fmt(sim)}</text>')
            y += row_h
        y += kp_gap

    svg.append("</svg>")
    OUT_SVG.write_text("\n".join(svg) + "\n")


def main() -> None:
    rows, unpaired_kp = load_pairs()
    if not rows:
        raise SystemExit("No real/sim pairs found for identical kp_case/phase/side/joint.")
    write_csv(rows)
    write_svg(rows, unpaired_kp)
    print(f"paired rows: {len(rows)}")
    print(f"wrote: {OUT_CSV}")
    print(f"wrote: {OUT_SVG}")
    if unpaired_kp:
        print("skipped unpaired kp_case:", ", ".join(unpaired_kp))


if __name__ == "__main__":
    main()
