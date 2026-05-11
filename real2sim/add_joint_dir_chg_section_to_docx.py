#!/usr/bin/env python3
"""Append joint_dir_chg multi-metric interpretation to the ankle report docx."""

from __future__ import annotations

import csv
import math
import shutil
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "real2sim" / "sim2real_ankle_control_report.docx"
BACKUP = ROOT / "real2sim" / "sim2real_ankle_control_report.before_joint_dir_chg.docx"
TABLE_DIR = ROOT / "real2sim" / "table" / "forward_x_failure_first6"
VIB_CSV = TABLE_DIR / "forward_x_failure_first6_ankle_vibration_frequency_detail.csv"
DIR_GAIN_CSV = TABLE_DIR / "forward_x_failure_first6_ankle_window_dir_gain_summary.csv"
DETAIL_CSV = TABLE_DIR / "forward_x_failure_first6_joint_change_frequency_detail.csv"
OUT_CSV = TABLE_DIR / "forward_x_failure_first6_ankle_multi_metric_interpretation.csv"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
ET.register_namespace("w", W_NS)


def qn(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as f:
        return list(csv.DictReader(f))


def as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def mean(values: list[float]) -> float:
    valid = [v for v in values if not math.isnan(v)]
    return sum(valid) / len(valid) if valid else math.nan


def median(values: list[float]) -> float:
    valid = [v for v in values if not math.isnan(v)]
    return statistics.median(valid) if valid else math.nan


def fmt(value: float, digits: int = 2) -> str:
    if value is None or math.isnan(value):
        return "-"
    return f"{value:.{digits}f}"


def level(value: float, threshold: float) -> str:
    if math.isnan(value) or math.isnan(threshold):
        return "NA"
    return "高" if value >= threshold else "低"


def gain_level(value: float) -> str:
    if math.isnan(value):
        return "NA"
    if value < 0.5:
        return "低"
    if value > 1.2:
        return "高"
    return "适中"


def classify(psd_level: str, dir_level: str, gain: float, rms_level: str) -> tuple[str, int]:
    if psd_level == "高" and dir_level == "高":
        base = "真抖风险：频域振荡能量高，且时域折返频繁"
        score = 4
    elif psd_level == "高" and dir_level == "低":
        base = "低频/集中振荡：能量高但轨迹折返不碎，优先看幅值与残余包络"
        score = 3
    elif psd_level == "低" and dir_level == "高":
        base = "碎动/chatter：频域峰不强但折返多，可能是接触碎动、噪声或传动间隙"
        score = 3
    else:
        base = "低振荡风险：频域能量和折返活跃度均低"
        score = 1

    g_level = gain_level(gain)
    if g_level == "低":
        base += "；但 gain 低，可能偏软或未跟上 target"
        score += 1
    elif g_level == "高":
        base += "；gain 高，存在过放大/过冲风险"
        score += 1

    if rms_level == "高":
        base += "；tracking RMS 高，整体跟踪误差偏大"
        score += 1
    return base, score


def build_rows() -> list[dict[str, object]]:
    vib_groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(VIB_CSV):
        vib_groups[(row["kp_case"], row["dataset"], row["joint"])].append(row)

    vib_summary = {}
    for key, items in vib_groups.items():
        vib_summary[key] = {
            "psd_peak_hz": mean([as_float(r["vibration_peak_hz"]) for r in items]),
            "psd_peak_power": mean([as_float(r["vibration_peak_power"]) for r in items]),
            "psd_band_power": mean([as_float(r["vibration_band_power"]) for r in items]),
        }

    rms_groups: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in read_csv(DETAIL_CSV):
        if row["joint"] not in ("ankle_pitch", "ankle_roll"):
            continue
        key = (row["kp_case"], row["dataset"], row["window"], row["joint"])
        rms_groups[key].append(as_float(row["tracking_err_rms_rad"]))
    rms_summary = {key: mean(vals) for key, vals in rms_groups.items()}

    dir_rows = []
    for row in read_csv(DIR_GAIN_CSV):
        if row["joint"] not in ("ankle_pitch", "ankle_roll"):
            continue
        key = (row["kp_case"], row["dataset"], row["window"], row["joint"])
        vib = vib_summary.get((row["kp_case"], row["dataset"], row["joint"]), {})
        dir_rows.append(
            {
                "kp_case": row["kp_case"],
                "dataset": row["dataset"],
                "window": row["window"],
                "joint": row["joint"],
                "psd_peak_hz": vib.get("psd_peak_hz", math.nan),
                "psd_peak_power": vib.get("psd_peak_power", math.nan),
                "psd_band_power": vib.get("psd_band_power", math.nan),
                "target_dir_chg_hz": as_float(row["mean_target_dir_chg_hz"]),
                "joint_dir_chg_hz": as_float(row["mean_joint_dir_chg_hz"]),
                "amplitude_gain": as_float(row["mean_amplitude_gain"]),
                "tracking_rms_rad": rms_summary.get(key, math.nan),
                "curve_count": int(float(row["curve_count"])),
            }
        )

    psd_threshold = {
        joint: median([r["psd_band_power"] for r in dir_rows if r["joint"] == joint])
        for joint in ("ankle_pitch", "ankle_roll")
    }
    dir_threshold = {
        (joint, window): median(
            [r["joint_dir_chg_hz"] for r in dir_rows if r["joint"] == joint and r["window"] == window]
        )
        for joint in ("ankle_pitch", "ankle_roll")
        for window in ("swing", "touchdown")
    }
    rms_threshold = {
        (joint, window): median(
            [r["tracking_rms_rad"] for r in dir_rows if r["joint"] == joint and r["window"] == window]
        )
        for joint in ("ankle_pitch", "ankle_roll")
        for window in ("swing", "touchdown")
    }

    out = []
    for row in dir_rows:
        psd_l = level(row["psd_band_power"], psd_threshold[row["joint"]])
        dir_l = level(row["joint_dir_chg_hz"], dir_threshold[(row["joint"], row["window"])])
        rms_l = level(row["tracking_rms_rad"], rms_threshold[(row["joint"], row["window"])])
        diagnosis, score = classify(psd_l, dir_l, row["amplitude_gain"], rms_l)
        out.append(
            {
                **row,
                "psd_power_level": psd_l,
                "joint_dir_level": dir_l,
                "gain_level": gain_level(row["amplitude_gain"]),
                "tracking_rms_level": rms_l,
                "risk_score": score,
                "interpretation": diagnosis,
            }
        )
    out.sort(key=lambda r: (-int(r["risk_score"]), r["dataset"], r["kp_case"], r["window"], r["joint"]))
    return out


def write_interpretation_csv(rows: list[dict[str, object]]) -> None:
    fieldnames = list(rows[0].keys())
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def text_of_paragraph(p: ET.Element) -> str:
    return "".join((t.text or "") for t in p.findall(".//w:t", NS))


def make_p(text: str, style: str | None = None, bold: bool = False) -> ET.Element:
    p = ET.Element(qn("p"))
    if style:
        ppr = ET.SubElement(p, qn("pPr"))
        pstyle = ET.SubElement(ppr, qn("pStyle"))
        pstyle.set(qn("val"), style)
    r = ET.SubElement(p, qn("r"))
    if bold:
        rpr = ET.SubElement(r, qn("rPr"))
        ET.SubElement(rpr, qn("b"))
    t = ET.SubElement(r, qn("t"))
    t.text = text
    return p


def make_table(headers: list[str], rows: list[list[str]]) -> ET.Element:
    tbl = ET.Element(qn("tbl"))
    tbl_pr = ET.SubElement(tbl, qn("tblPr"))
    tbl_style = ET.SubElement(tbl_pr, qn("tblStyle"))
    tbl_style.set(qn("val"), "TableGrid")
    tbl_w = ET.SubElement(tbl_pr, qn("tblW"))
    tbl_w.set(qn("w"), "0")
    tbl_w.set(qn("type"), "auto")
    borders = ET.SubElement(tbl_pr, qn("tblBorders"))
    for name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = ET.SubElement(borders, qn(name))
        b.set(qn("val"), "single")
        b.set(qn("sz"), "4")
        b.set(qn("space"), "0")
        b.set(qn("color"), "BFBFBF")

    def add_row(values: list[str], header: bool = False) -> None:
        tr = ET.SubElement(tbl, qn("tr"))
        for value in values:
            tc = ET.SubElement(tr, qn("tc"))
            tc_pr = ET.SubElement(tc, qn("tcPr"))
            tc_w = ET.SubElement(tc_pr, qn("tcW"))
            tc_w.set(qn("w"), "0")
            tc_w.set(qn("type"), "auto")
            tc.append(make_p(value, bold=header))

    add_row(headers, header=True)
    for row in rows:
        add_row(row)
    return tbl


def append_section_to_docx(rows: list[dict[str, object]]) -> None:
    if not BACKUP.exists():
        shutil.copy2(DOCX, BACKUP)

    top_rows = rows[:12]
    summary_counts = defaultdict(int)
    for row in rows:
        summary_counts[(row["psd_power_level"], row["joint_dir_level"])] += 1

    front_note = [
        make_p("本次新增摘要：joint_dir_chg 联合判读", "Heading1"),
        make_p(
            "本次补充把 joint_dir_chg 定义为时域抖动/折返指标，并与 PSD peak/band power、"
            "amplitude_gain、tracking RMS 联合判读。新增完整章节见文末 § 9，完整明细见 "
            f"{OUT_CSV.relative_to(ROOT)}。",
        ),
        make_table(
            ["判读组合", "样本数", "含义"],
            [
                [
                    "PSD 高 + joint_dir_chg 高",
                    str(summary_counts[("高", "高")]),
                    "频域振荡能量高，且时域频繁折返，优先视为真抖风险",
                ],
                [
                    "PSD 高 + joint_dir_chg 低",
                    str(summary_counts[("高", "低")]),
                    "能量集中但轨迹较平滑，优先检查低频大幅振荡与残余包络",
                ],
                [
                    "PSD 低 + joint_dir_chg 高",
                    str(summary_counts[("低", "高")]),
                    "峰值能量不强但折返多，可能是 chatter、噪声或传动碎动",
                ],
                [
                    "joint_dir_chg 低 + amplitude_gain 低",
                    "-",
                    "不能直接判稳，可能只是偏软或没有跟上 target",
                ],
            ],
        ),
    ]

    section = [
        make_p("§ 9  joint_dir_chg 多指标联合判读", "Heading1"),
        make_p(
            "本节把 joint_dir_chg 作为时域抖动/折返指标，和 full-log residual Welch PSD、amplitude_gain、tracking RMS 联合解释。"
            "joint_dir_chg 不用于估计自然频率，也不单独判断稳定性。",
        ),
        make_p("9.1  指标含义", "Heading2"),
        make_table(
            ["指标", "回答的问题", "报告用途"],
            [
                ["PSD peak frequency", "振荡主要在哪个频段", "定位 residual 的主要频带"],
                ["PSD peak/band power", "该频段能量有多大", "判断振荡强度"],
                ["joint_dir_chg", "时域轨迹有多碎、折返多不多", "识别 chatter / 碎动 / 频繁修正"],
                ["amplitude_gain", "joint 是否跟上 target 幅值", "区分真稳定和偏软/未跟随"],
                ["tracking error RMS", "整体跟踪误差多大", "衡量跟踪质量"],
            ],
        ),
        make_p("9.2  联合判读规则", "Heading2"),
        make_table(
            ["PSD power", "joint_dir_chg", "典型解释"],
            [
                ["高", "高", "频域能量高且时域折返频繁：真抖 / 接触 chatter 风险高"],
                ["高", "低", "能量集中但折返不碎：可能是低频大幅振荡或平滑残余"],
                ["低", "高", "峰值能量不强但折返多：可能是宽频小噪声、接触碎动、编码器噪声或传动间隙"],
                ["低", "低", "低振荡风险；若 amplitude_gain 也低，则可能只是偏软或未跟上 target"],
            ],
        ),
        make_p("9.3  本次数据分布", "Heading2"),
        make_table(
            ["PSD power", "joint_dir_chg", "样本数"],
            [[k[0], k[1], str(v)] for k, v in sorted(summary_counts.items())],
        ),
        make_p("9.4  Top 风险样本", "Heading2"),
        make_p(f"完整明细已写入：{OUT_CSV.relative_to(ROOT)}。下表按 risk_score 降序展示前 12 条。"),
        make_table(
            ["Kp/Kd", "数据", "窗口", "关节", "PSD Hz", "PSD band", "joint dir", "gain", "RMS", "判读"],
            [
                [
                    str(r["kp_case"]).replace("_", "/"),
                    str(r["dataset"]),
                    str(r["window"]),
                    str(r["joint"]).replace("ankle_", ""),
                    fmt(float(r["psd_peak_hz"])),
                    f"{fmt(float(r['psd_band_power']), 1)}({r['psd_power_level']})",
                    f"{fmt(float(r['joint_dir_chg_hz']))}({r['joint_dir_level']})",
                    f"{fmt(float(r['amplitude_gain']))}({r['gain_level']})",
                    f"{fmt(float(r['tracking_rms_rad']), 3)}({r['tracking_rms_level']})",
                    str(r["interpretation"]),
                ]
                for r in top_rows
            ],
        ),
        make_p("9.5  结论", "Heading2"),
        make_p(
            "joint_dir_chg 的价值是补足 PSD：PSD 告诉我们能量集中在哪个频段、能量有多强；"
            "joint_dir_chg 告诉我们时域轨迹是否频繁折返。两者同时高时才更接近“真抖”。"
            "若 joint_dir_chg 低但 amplitude_gain 低，不能简单判断为稳定，应同时检查 tracking RMS 和 target 跟随幅值。",
        ),
    ]

    with zipfile.ZipFile(DOCX, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    root = ET.fromstring(files["word/document.xml"])
    body = root.find("w:body", NS)
    if body is None:
        raise RuntimeError("word/document.xml has no body")

    children = list(body)
    sect_pr = body.find("w:sectPr", NS)

    # Remove previous generated front note and section if this script is rerun.
    front_remove_from = None
    front_remove_to = None
    for idx, child in enumerate(children):
        if child.tag == qn("p") and text_of_paragraph(child).startswith("本次新增摘要：joint_dir_chg 联合判读"):
            front_remove_from = idx
            break
    if front_remove_from is not None:
        for idx in range(front_remove_from + 1, len(children)):
            child = children[idx]
            if child.tag == qn("p") and text_of_paragraph(child).startswith("§ 1  延迟统计"):
                front_remove_to = idx
                break
        if front_remove_to is None:
            front_remove_to = front_remove_from + len(front_note)
        for child in children[front_remove_from:front_remove_to]:
            body.remove(child)

    children = list(body)
    sect_pr = body.find("w:sectPr", NS)
    remove_from = None
    for idx, child in enumerate(children):
        if child.tag == qn("p") and text_of_paragraph(child).startswith("§ 9  joint_dir_chg 多指标联合判读"):
            remove_from = idx
            break
    if remove_from is not None:
        for child in children[remove_from:]:
            if child is sect_pr:
                break
            body.remove(child)

    children = list(body)
    front_insert_at = None
    for idx, child in enumerate(children):
        if child.tag == qn("p") and text_of_paragraph(child).startswith("§ 1  延迟统计"):
            front_insert_at = idx
            break
    if front_insert_at is None:
        front_insert_at = min(10, len(children))
    for offset, element in enumerate(front_note):
        body.insert(front_insert_at + offset, element)

    insert_at = len(list(body))
    if sect_pr is not None:
        insert_at = list(body).index(sect_pr)
    for offset, element in enumerate(section):
        body.insert(insert_at + offset, element)

    files["word/document.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    tmp = DOCX.with_suffix(".tmp.docx")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    tmp.replace(DOCX)


def main() -> None:
    rows = build_rows()
    write_interpretation_csv(rows)
    append_section_to_docx(rows)
    print(OUT_CSV)
    print(DOCX)
    print(BACKUP)


if __name__ == "__main__":
    main()
