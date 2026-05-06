import csv
import math
import os
from collections import Counter, defaultdict


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
ROUND3_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
OUT_MD = os.path.join(ROUND3_DIR, "round3_execution_chain_disentanglement_cross_case_compare.md")
OUT_CSV = os.path.join(ROUND3_DIR, "round3_execution_chain_disentanglement_cross_case_compare.csv")
PROXY_CSV = os.path.join(ROUND3_DIR, "round3_t27_execution_chain_disentanglement_h2.csv")
ACTUATOR_CSV = os.path.join(ROUND3_DIR, "round3_execution_chain_disentanglement_actuator_20260429_161248.csv")


def load_csv(path):
    rows = []
    with open(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {}
            for key, value in raw.items():
                if value is None or value == "":
                    row[key] = math.nan
                    continue
                try:
                    row[key] = float(value)
                except ValueError:
                    row[key] = value
            rows.append(row)
    return rows


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    if not valid:
        return math.nan
    return sum(valid) / len(valid)


def fmt(value, digits=4):
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return "nan"
        return f"{value:.{digits}f}"
    return str(value)


def summarize_proxy(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["case_label"]].append(row)

    summaries = []
    for case_label, case_rows in grouped.items():
        summaries.append(
            {
                "case_label": case_label,
                "mode": "proxy",
                "events": len(case_rows),
                "mean_abs_sole_roll": mean([r["sole_mean_abs"] for r in case_rows]),
                "mean_output_to_sole_lag_ms": mean([r["raw_to_sole_lag_ms"] for r in case_rows]),
                "mean_exec_proxy_to_sole_lag_ms": mean([r["pos_to_sole_lag_ms"] for r in case_rows]),
                "mean_exec_internal_lag_ms": mean([r["lpf_to_pos_lag_ms"] for r in case_rows]),
                "execution_chain_support_mean": mean([r["h2_proxy_supported"] for r in case_rows]),
                "dominant_source": Counter(r["sole_source_guess"] for r in case_rows).most_common(1)[0][0],
                "notes": "proxy: pos_des_lpf->pos used as execution-chain surrogate",
            }
        )
    return sorted(summaries, key=lambda r: r["case_label"])


def summarize_actuator(rows):
    case_label = "25/0.5 all_ankles (actuator-state)"
    return [
        {
            "case_label": case_label,
            "mode": "actuator_state",
            "events": len(rows),
            "mean_abs_sole_roll": mean([r["sole_mean_abs"] for r in rows]),
            "mean_output_to_sole_lag_ms": mean([r["raw_to_sole_lag_ms"] for r in rows]),
            "mean_exec_proxy_to_sole_lag_ms": mean([r["joint_pos_to_sole_lag_ms"] for r in rows]),
            "mean_exec_internal_lag_ms": mean(
                [
                    mean([r["act_left_state_to_joint_lag_ms"], r["act_right_state_to_joint_lag_ms"]])
                    for r in rows
                ]
            ),
            "execution_chain_support_mean": mean([r["actuator_chain_support"] for r in rows]),
            "dominant_source": Counter(r["sole_source_guess"] for r in rows).most_common(1)[0][0],
            "notes": "actuator-state: actuator_cmd->actuator_state->joint_pos split available",
        }
    ]


def write_csv(path, rows):
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    proxy_rows = load_csv(PROXY_CSV)
    actuator_rows = load_csv(ACTUATOR_CSV)

    proxy_summary = summarize_proxy(proxy_rows)
    actuator_summary = summarize_actuator(actuator_rows)
    all_rows = proxy_summary + actuator_summary
    write_csv(OUT_CSV, all_rows)

    proxy_25_all = next((r for r in proxy_summary if r["case_label"] == "25/0.5 all_ankles"), None)
    act_25_all = actuator_summary[0]

    with open(OUT_MD, "w", encoding="utf-8") as handle:
        handle.write("# 11B Execution Chain Disentanglement Cross-Case Compare\n\n")
        handle.write("- Proxy source: `round3_t27_execution_chain_disentanglement_h2.csv`\n")
        handle.write("- Actuator-state source: `round3_execution_chain_disentanglement_actuator_20260429_161248.csv`\n")
        handle.write("- Scope: current repo only has one t27 log with `/actuator_cmd` + `/actuator_states`; cross-case compare therefore uses `5` proxy cases + `1` actuator-state case.\n\n")

        handle.write("## Case Summary\n\n")
        handle.write("| case | mode | events | mean_abs_sole_roll | mean output->sole lag (ms) | mean exec->sole lag (ms) | mean exec-internal lag (ms) | exec support | dominant source |\n")
        handle.write("|---|---|---:|---:|---:|---:|---:|---:|---|\n")
        for row in all_rows:
            handle.write(
                f"| {row['case_label']} | {row['mode']} | {int(row['events'])} | {fmt(row['mean_abs_sole_roll'])} | "
                f"{fmt(row['mean_output_to_sole_lag_ms'])} | {fmt(row['mean_exec_proxy_to_sole_lag_ms'])} | "
                f"{fmt(row['mean_exec_internal_lag_ms'])} | {fmt(row['execution_chain_support_mean'])} | {row['dominant_source']} |\n"
            )

        handle.write("\n## Consistency Check: 25/0.5 all_ankles\n\n")
        if proxy_25_all is not None:
            handle.write("| metric | proxy | actuator-state |\n")
            handle.write("|---|---:|---:|\n")
            handle.write(f"| mean_abs_sole_roll | {fmt(proxy_25_all['mean_abs_sole_roll'])} | {fmt(act_25_all['mean_abs_sole_roll'])} |\n")
            handle.write(f"| mean output->sole lag (ms) | {fmt(proxy_25_all['mean_output_to_sole_lag_ms'])} | {fmt(act_25_all['mean_output_to_sole_lag_ms'])} |\n")
            handle.write(f"| mean exec->sole lag (ms) | {fmt(proxy_25_all['mean_exec_proxy_to_sole_lag_ms'])} | {fmt(act_25_all['mean_exec_proxy_to_sole_lag_ms'])} |\n")
            handle.write(f"| mean exec-internal lag (ms) | {fmt(proxy_25_all['mean_exec_internal_lag_ms'])} | {fmt(act_25_all['mean_exec_internal_lag_ms'])} |\n")
            handle.write(f"| dominant source | {proxy_25_all['dominant_source']} | {act_25_all['dominant_source']} |\n")

        handle.write("\n## Interpretation\n\n")
        handle.write("- Across proxy cases, `sole_roll` is execution-chain-dominant in `4/5` parameter groups; only `40/0.8 right_roll` shifts toward `output_chain_dominant` under the proxy criterion.\n")
        handle.write("- The only currently available actuator-state case (`4 ankles = 25/0.5`) still lands on `execution_chain_dominant`, so the new actuator evidence is directionally consistent with the broader proxy dataset.\n")
        handle.write("- Current evidence supports: `output` is not the primary bottleneck; the execution chain remains the main source shaping `sole_roll`, while `coupled_geometry` stays as a concurrent underlying bias.\n")
        handle.write("- Limitation: there is only one actuator-state case. To close Phase B, actuator-state logs still need to be repeated for at least one higher-kp condition.\n")

    print(OUT_CSV)
    print(OUT_MD)


if __name__ == "__main__":
    main()
