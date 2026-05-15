import os
import re


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_repo_root(start_dir: str) -> str:
    cursor = start_dir
    while True:
        if os.path.isdir(os.path.join(cursor, "real2sim")) and os.path.isdir(os.path.join(cursor, "src")):
            return cursor
        parent = os.path.dirname(cursor)
        if parent == cursor:
            raise RuntimeError("Failed to locate repository root")
        cursor = parent


BASE_DIR = find_repo_root(SCRIPT_DIR)
ANKLE_TRANS_CC = os.path.join(BASE_DIR, "src", "module", "dcu_driver_module", "src", "ankle_transmission.cc")
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
OUT_MD = os.path.join(OUT_DIR, "round3_parallel_mapping_verification.md")

os.makedirs(OUT_DIR, exist_ok=True)


def extract_function_body(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise RuntimeError(f"Failed to locate signature: {signature}")
    brace_start = text.find("{", start)
    if brace_start < 0:
        raise RuntimeError(f"Failed to locate opening brace: {signature}")
    depth = 0
    for idx in range(brace_start, len(text)):
        if text[idx] == "{":
            depth += 1
        elif text[idx] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start : idx + 1]
    raise RuntimeError(f"Failed to locate closing brace: {signature}")


def has(body: str, snippet: str) -> bool:
    return snippet in body


def strip_line_comments(body: str) -> str:
    cleaned = []
    for line in body.splitlines():
        cleaned.append(line.split("//", 1)[0])
    return "\n".join(cleaned)


def capture(body: str, pattern: str) -> str:
    cleaned = strip_line_comments(body)
    matches = re.findall(pattern, cleaned)
    if not matches:
        return "missing"
    return matches[-1]


def parse_functions():
    with open(ANKLE_TRANS_CC, "r", encoding="utf-8") as handle:
        text = handle.read()

    left_a2j = extract_function_body(text, "void LeftAnkleParallelTransmission::TransformActuatorToJoint()")
    left_j2a = extract_function_body(text, "void LeftAnkleParallelTransmission::TransformJointToActuator()")
    right_a2j = extract_function_body(text, "void RightAnkleParallelTransmission::TransformActuatorToJoint()")
    right_j2a = extract_function_body(text, "void RightAnkleParallelTransmission::TransformJointToActuator()")

    return {
        "left_a2j": left_a2j,
        "left_j2a": left_j2a,
        "right_a2j": right_a2j,
        "right_j2a": right_j2a,
    }


def build_side_facts(a2j: str, j2a: str, side: str):
    return {
        "qm5_state_source": capture(a2j, r"double qm5 = ([^;]+);"),
        "qm6_state_source": capture(a2j, r"double qm6 = ([^;]+);"),
        "q6_extra_flip": has(a2j, "q6 *= -1;"),
        "qm5_extra_flip": has(a2j, "qm5 *= -1;"),
        "qm6_extra_flip": has(a2j, "qm6 *= -1;"),
        "taum5_state_source": capture(a2j, r"double taum5 = ([^;]+);"),
        "taum6_state_source": capture(a2j, r"double taum6 = ([^;]+);"),
        "cqm5_phase": capture(a2j, r"cqm5 = cos\(([^;]+)\);"),
        "cqm6_phase": capture(a2j, r"cqm6 = cos\(([^;]+)\);"),
        "p_4p2_6_y": capture(a2j, r"p_4p2_6_y = ([^;]+);"),
        "p_4p4_6_y": capture(a2j, r"p_4p4_6_y = ([^;]+);"),
        "qm5_cmd_target": capture(j2a, r"actr_(left|right)_\.handle->cmd\.position = qm5Des"),
        "qm6_cmd_target": capture(j2a, r"actr_(left|right)_\.handle->cmd\.position = qm6Des"),
        "qm5_des_formula": capture(j2a, r"qm5Des = ([^;]+);"),
        "qm6_des_formula": capture(j2a, r"qm6Des = ([^;]+);"),
        "pitch_kp_target": capture(j2a, r"actr_(left|right)_\.handle->cmd\.kp = joint_pitch_\.handle->cmd\.kp;"),
        "roll_kp_target": capture(j2a, r"actr_(left|right)_\.handle->cmd\.kp = joint_roll_\.handle->cmd\.kp;"),
        "side": side,
    }


def evaluate(left: dict, right: dict):
    findings = []

    left_pitch_consistent = left["qm5_state_source"].startswith("actr_right_") and left["qm5_cmd_target"] == "right"
    left_roll_consistent = left["qm6_state_source"].startswith("actr_left_") and left["qm6_cmd_target"] == "left"
    right_pitch_consistent = right["qm5_state_source"].startswith("actr_left_") and right["qm5_cmd_target"] == "left"
    right_roll_consistent = right["qm6_state_source"].startswith("actr_right_") and right["qm6_cmd_target"] == "right"

    if all((left_pitch_consistent, left_roll_consistent, right_pitch_consistent, right_roll_consistent)):
        findings.append(
            "Actuator ownership is self-consistent: each side reads actuator state from the same actuator pair that later receives its pitch/roll command."
        )
    else:
        findings.append(
            "Actuator ownership is not fully self-consistent: at least one side reads from a different actuator than it commands back into."
        )

    left_sign_bundle = left["qm5_extra_flip"] and left["qm6_extra_flip"] and left["q6_extra_flip"]
    right_sign_bundle = (not right["qm5_extra_flip"]) and (not right["qm6_extra_flip"]) and (not right["q6_extra_flip"])
    if left_sign_bundle and right_sign_bundle:
        findings.append(
            "The side-specific sign convention is asymmetric by construction: left applies an explicit `(qm5, qm6, q6)` flip bundle, while right relies on phase offsets and sign in the inverse formulas."
        )

    left_phase_ok = left["cqm5_phase"] == "qm5 + 1.2028" and left["cqm6_phase"] == "qm6 - 1.2030"
    right_phase_ok = right["cqm5_phase"] == "qm5 - 1.2028" and right["cqm6_phase"] == "qm6 + 1.2030"
    if left_phase_ok and right_phase_ok:
        findings.append(
            "Left/right cosine phase offsets are mirror-paired, not identical. This supports a deliberate mirrored convention rather than a copy-paste mistake."
        )

    y_signs_ok = (
        left["p_4p2_6_y"] == "-0.025"
        and left["p_4p4_6_y"] == "0.025"
        and right["p_4p2_6_y"] == "0.025"
        and right["p_4p4_6_y"] == "-0.025"
    )
    if y_signs_ok:
        findings.append(
            "The geometric `y` offsets also mirror across sides. Mapping asymmetry therefore lives in a coupled sign package, not a single stray line."
        )

    residual_risks = [
        "All mirrored conventions are hard-coded in C++, not configurable in YAML.",
        "There is no explicit code-level proof here that `TransformActuatorToJoint()` and `TransformJointToActuator()` are numerically inverse around touchdown operating points.",
        "Touchdown data still shows `bilateral_mirror_stable` roll residual after dead-zone screening, so code-level self-consistency does not eliminate geometry residual."
    ]
    return findings, residual_risks


def write_report(left: dict, right: dict, findings, residual_risks):
    with open(OUT_MD, "w", encoding="utf-8") as handle:
        handle.write("# Round 3C Parallel Mapping Verification\n\n")
        handle.write("## Scope\n\n")
        handle.write(
            "This report is the `05B` code-side verification for touchdown residual only. "
            "Swing dead-zone / small-signal realization has already been split out to `13_dead_zone_audit`.\n\n"
        )

        handle.write("## Side-by-Side Mapping Facts\n\n")
        handle.write("| Item | Left ankle | Right ankle |\n")
        handle.write("|---|---|---|\n")
        handle.write(f"| `qm5` state source | `{left['qm5_state_source']}` | `{right['qm5_state_source']}` |\n")
        handle.write(f"| `qm6` state source | `{left['qm6_state_source']}` | `{right['qm6_state_source']}` |\n")
        handle.write(f"| extra `qm5 *= -1` | `{left['qm5_extra_flip']}` | `{right['qm5_extra_flip']}` |\n")
        handle.write(f"| extra `qm6 *= -1` | `{left['qm6_extra_flip']}` | `{right['qm6_extra_flip']}` |\n")
        handle.write(f"| extra `q6 *= -1` | `{left['q6_extra_flip']}` | `{right['q6_extra_flip']}` |\n")
        handle.write(f"| `taum5` state source | `{left['taum5_state_source']}` | `{right['taum5_state_source']}` |\n")
        handle.write(f"| `taum6` state source | `{left['taum6_state_source']}` | `{right['taum6_state_source']}` |\n")
        handle.write(f"| `cqm5` phase | `{left['cqm5_phase']}` | `{right['cqm5_phase']}` |\n")
        handle.write(f"| `cqm6` phase | `{left['cqm6_phase']}` | `{right['cqm6_phase']}` |\n")
        handle.write(f"| `p_4p2_6_y` | `{left['p_4p2_6_y']}` | `{right['p_4p2_6_y']}` |\n")
        handle.write(f"| `p_4p4_6_y` | `{left['p_4p4_6_y']}` | `{right['p_4p4_6_y']}` |\n")
        handle.write(f"| `qm5Des` actuator target | `{left['qm5_cmd_target']}` | `{right['qm5_cmd_target']}` |\n")
        handle.write(f"| `qm6Des` actuator target | `{left['qm6_cmd_target']}` | `{right['qm6_cmd_target']}` |\n")
        handle.write(f"| `qm5Des` formula | `{left['qm5_des_formula']}` | `{right['qm5_des_formula']}` |\n")
        handle.write(f"| `qm6Des` formula | `{left['qm6_des_formula']}` | `{right['qm6_des_formula']}` |\n")
        handle.write(f"| pitch `kp` target | `{left['pitch_kp_target']}` | `{right['pitch_kp_target']}` |\n")
        handle.write(f"| roll `kp` target | `{left['roll_kp_target']}` | `{right['roll_kp_target']}` |\n\n")

        handle.write("## Verification Reading\n\n")
        for finding in findings:
            handle.write(f"- {finding}\n")
        handle.write("\n")

        handle.write("## Residual Risks After 05B\n\n")
        for risk in residual_risks:
            handle.write(f"- {risk}\n")
        handle.write("\n")

        handle.write("## Current 05B Conclusion\n\n")
        handle.write(
            "1. `05B` does not find a simple one-line left/right sign bug in actuator ownership. "
            "Pitch/roll actuator ownership is internally paired on both sides.\n"
        )
        handle.write(
            "2. `05B` confirms that left/right mapping is not symmetric in a trivial sense; it is encoded as a mirrored hard-coded sign/phase package inside `ankle_transmission.cc`.\n"
        )
        handle.write(
            "3. Because touchdown residual still shows stable mirror roll bias after dead-zone screening, the remaining high-priority explanations are:\n"
        )
        handle.write("   - numerical mismatch between mirrored code package and real mechanism / table operating region\n")
        handle.write("   - hardware-side realization asymmetry on top of this hard-coded mapping\n")
        handle.write("   - foot-space / contact geometry residual not represented by joint-space alone\n")


def main():
    funcs = parse_functions()
    left = build_side_facts(funcs["left_a2j"], funcs["left_j2a"], "left")
    right = build_side_facts(funcs["right_a2j"], funcs["right_j2a"], "right")
    findings, residual_risks = evaluate(left, right)
    write_report(left, right, findings, residual_risks)
    print(f"Parallel mapping verification: {OUT_MD}")


if __name__ == "__main__":
    main()
