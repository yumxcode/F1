#!/usr/bin/env python3

import argparse
import csv
import json
import math
from pathlib import Path


def load_rows(csv_path):
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "time_sec": float(row["time_sec"]),
                    "phase": row["phase"],
                    "iteration": int(row["iteration"]),
                    "primary_joint": row["primary_joint"],
                    "coupled_joint": row["coupled_joint"],
                    "target_primary": float(row["target_primary"]),
                    "target_coupled": float(row["target_coupled"]),
                    "actual_primary": float(row["actual_primary"]),
                    "actual_coupled": float(row["actual_coupled"]),
                    "actual_primary_vel": float(row["actual_primary_vel"]),
                    "actual_coupled_vel": float(row["actual_coupled_vel"]),
                    "actual_primary_effort": float(row["actual_primary_effort"]),
                    "actual_coupled_effort": float(row["actual_coupled_effort"]),
                }
            )
    if not rows:
        raise ValueError(f"No data rows found in {csv_path}")
    return rows


def mean(values):
    return sum(values) / len(values) if values else 0.0


def infer_side_and_axis(primary_joint):
    if primary_joint.startswith("left_"):
        side = "left"
    elif primary_joint.startswith("right_"):
        side = "right"
    else:
        side = "unknown"

    if "roll" in primary_joint:
        axis = "roll"
    elif "pitch" in primary_joint:
        axis = "pitch"
    else:
        axis = "unknown"
    return side, axis


def infer_pose_name(csv_path_str):
    name = Path(csv_path_str).stem.lower()
    if "stand" in name:
        return "stand"
    if "zero" in name:
        return "zero"
    return "unknown"


def select_analysis_rows(rows):
    hold_rows = [row for row in rows if row["phase"] == "hold_target"]
    if hold_rows:
        return "hold_target", hold_rows

    active_rows = [row for row in rows if row["phase"] == "active"]
    if active_rows:
        return "active", active_rows

    raise ValueError("Neither hold_target nor active phase exists in csv.")


def summarize_rows(rows):
    return {
        "target_primary_mean": mean([row["target_primary"] for row in rows]),
        "target_coupled_mean": mean([row["target_coupled"] for row in rows]),
        "actual_primary_mean": mean([row["actual_primary"] for row in rows]),
        "actual_coupled_mean": mean([row["actual_coupled"] for row in rows]),
        "actual_primary_vel_abs_mean": mean([abs(row["actual_primary_vel"]) for row in rows]),
        "actual_coupled_vel_abs_mean": mean([abs(row["actual_coupled_vel"]) for row in rows]),
        "actual_primary_effort_abs_mean": mean([abs(row["actual_primary_effort"]) for row in rows]),
        "actual_coupled_effort_abs_mean": mean([abs(row["actual_coupled_effort"]) for row in rows]),
        "time_sec_start": rows[0]["time_sec"],
        "time_sec_end": rows[-1]["time_sec"],
        "sample_count": len(rows),
    }


def build_summary(
    csv_path,
    measured_angle_deg,
    pose_name=None,
    measurement_method="spirit_level",
    test_kp=None,
    test_kd=None,
):
    rows = load_rows(csv_path)
    phase_name, analysis_rows = select_analysis_rows(rows)
    stats = summarize_rows(analysis_rows)

    primary_joint = analysis_rows[0]["primary_joint"]
    coupled_joint = analysis_rows[0]["coupled_joint"]
    side, axis = infer_side_and_axis(primary_joint)
    pose_name = pose_name or infer_pose_name(str(csv_path))
    measured_angle_rad = math.radians(measured_angle_deg)

    if axis == "roll":
        commanded_ankle_roll_rad = stats["target_primary_mean"]
        commanded_ankle_pitch_rad = stats["target_coupled_mean"]
        logged_ankle_roll_rad = stats["actual_primary_mean"]
        logged_ankle_pitch_rad = stats["actual_coupled_mean"]
        measured_sole_roll_rad = measured_angle_rad
        measured_sole_pitch_rad = None
        axis_error_rad = logged_ankle_roll_rad - measured_sole_roll_rad
    elif axis == "pitch":
        commanded_ankle_roll_rad = stats["target_coupled_mean"]
        commanded_ankle_pitch_rad = stats["target_primary_mean"]
        logged_ankle_roll_rad = stats["actual_coupled_mean"]
        logged_ankle_pitch_rad = stats["actual_primary_mean"]
        measured_sole_roll_rad = None
        measured_sole_pitch_rad = measured_angle_rad
        axis_error_rad = logged_ankle_pitch_rad - measured_sole_pitch_rad
    else:
        raise ValueError(f"Cannot infer ankle axis from primary_joint={primary_joint}")

    return {
        "source_csv_path": str(csv_path),
        "case_id": Path(csv_path).stem,
        "phase": 1,
        "analysis_phase_used": phase_name,
        "side": side,
        "pose_name": pose_name,
        "primary_joint": primary_joint,
        "coupled_joint": coupled_joint,
        "commanded_ankle_roll_rad": commanded_ankle_roll_rad,
        "commanded_ankle_pitch_rad": commanded_ankle_pitch_rad,
        "logged_ankle_roll_rad": logged_ankle_roll_rad,
        "logged_ankle_pitch_rad": logged_ankle_pitch_rad,
        "measured_input_deg": measured_angle_deg,
        "measured_input_rad": measured_angle_rad,
        "measured_axis": axis,
        "measured_sole_roll_rad": measured_sole_roll_rad,
        "measured_sole_pitch_rad": measured_sole_pitch_rad,
        "measurement_method": measurement_method,
        "test_kp": test_kp,
        "test_kd": test_kd,
        "fk_body_name": f"link_{side}_ankle_roll" if side in {"left", "right"} else "",
        "time_sec_start": stats["time_sec_start"],
        "time_sec_end": stats["time_sec_end"],
        "sample_count": stats["sample_count"],
        "actual_primary_vel_abs_mean": stats["actual_primary_vel_abs_mean"],
        "actual_coupled_vel_abs_mean": stats["actual_coupled_vel_abs_mean"],
        "actual_primary_effort_abs_mean": stats["actual_primary_effort_abs_mean"],
        "actual_coupled_effort_abs_mean": stats["actual_coupled_effort_abs_mean"],
        "axis_error_rad": axis_error_rad,
    }


def maybe_write_json(path, payload):
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def maybe_write_csv_row(path, summary):
    if not path:
        return

    fieldnames = [
        "case_id",
        "phase",
        "side",
        "pose_name",
        "commanded_ankle_roll_rad",
        "commanded_ankle_pitch_rad",
        "logged_ankle_roll_rad",
        "logged_ankle_pitch_rad",
        "fk_body_name",
        "fk_sole_roll_rad",
        "fk_sole_pitch_rad",
        "fk_sole_normal_z",
        "measured_sole_roll_rad",
        "measured_sole_pitch_rad",
        "measurement_method",
        "contact_edge_label",
        "contact_mark_evidence",
        "video_evidence",
        "evidence_file",
        "operator_note",
    ]

    row = {
        "case_id": summary["case_id"],
        "phase": summary["phase"],
        "side": summary["side"],
        "pose_name": summary["pose_name"],
        "commanded_ankle_roll_rad": summary["commanded_ankle_roll_rad"],
        "commanded_ankle_pitch_rad": summary["commanded_ankle_pitch_rad"],
        "logged_ankle_roll_rad": summary["logged_ankle_roll_rad"],
        "logged_ankle_pitch_rad": summary["logged_ankle_pitch_rad"],
        "fk_body_name": summary["fk_body_name"],
        "fk_sole_roll_rad": "",
        "fk_sole_pitch_rad": "",
        "fk_sole_normal_z": "",
        "measured_sole_roll_rad": "" if summary["measured_sole_roll_rad"] is None else summary["measured_sole_roll_rad"],
        "measured_sole_pitch_rad": "" if summary["measured_sole_pitch_rad"] is None else summary["measured_sole_pitch_rad"],
        "measurement_method": summary["measurement_method"],
        "contact_edge_label": "",
        "contact_mark_evidence": "",
        "video_evidence": "",
        "evidence_file": summary["source_csv_path"],
        "operator_note": (
            f"analysis_phase={summary['analysis_phase_used']}; "
            f"sample_count={summary['sample_count']}; "
            f"axis_error_rad={summary['axis_error_rad']:.6f}; "
            f"test_kp={summary['test_kp']}; "
            f"test_kd={summary['test_kd']}"
        ),
    }

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


def print_summary(summary):
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze a 05D static ankle scan csv and combine it with a manual angle measurement."
    )
    parser.add_argument("csv_path", help="Path to ankle_identifier_module output csv.")
    parser.add_argument(
        "measured_angle_deg",
        type=float,
        help="Measured sole angle from the level meter, in degrees. The script converts it to radians.",
    )
    parser.add_argument(
        "--pose-name",
        default=None,
        help="Optional override for pose_name in the output, e.g. zero or stand.",
    )
    parser.add_argument(
        "--measurement-method",
        default="spirit_level",
        help="Label written into the summary, default: spirit_level.",
    )
    parser.add_argument(
        "--test-kp",
        type=float,
        default=None,
        help="Optional explicit kp label for this test.",
    )
    parser.add_argument(
        "--test-kd",
        type=float,
        default=None,
        help="Optional explicit kd label for this test.",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path to save the full summary as json.",
    )
    parser.add_argument(
        "--csv-row-out",
        default=None,
        help="Optional path to save one 05D template-compatible csv row.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    summary = build_summary(
        csv_path=args.csv_path,
        measured_angle_deg=args.measured_angle_deg,
        pose_name=args.pose_name,
        measurement_method=args.measurement_method,
        test_kp=args.test_kp,
        test_kd=args.test_kd,
    )
    maybe_write_json(args.json_out, summary)
    maybe_write_csv_row(args.csv_row_out, summary)
    print_summary(summary)


if __name__ == "__main__":
    main()
