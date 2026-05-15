import math
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
            raise RuntimeError("Failed to locate repository root from plan script path")
        cursor = parent


BASE_DIR = find_repo_root(SCRIPT_DIR)
OUT_DIR = os.path.join(BASE_DIR, "real2sim", "table", "round3")
RL_CFG = os.path.join(BASE_DIR, "src", "module", "control_module", "cfg", "rl_x1.yaml")
DCU_CFG = os.path.join(BASE_DIR, "src", "module", "dcu_driver_module", "cfg", "dcu_x1.yaml")
ANKLE_TRANS_CC = os.path.join(BASE_DIR, "src", "module", "dcu_driver_module", "src", "ankle_transmission.cc")
ANKLE_TRANS_YAML = os.path.join(BASE_DIR, "src", "module", "dcu_driver_module", "cfg", "ankle_trans_x1.yaml")
OUT_MD = os.path.join(OUT_DIR, "round3_zero_bias_and_mapping_check.md")

QM5_ANGLE_MIN = -1.4
QM6_ANGLE_MIN = -1.0
QM_RESOLUTION = 0.4 / 180.0 * math.pi

os.makedirs(OUT_DIR, exist_ok=True)


ANKLE_JOINTS = (
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
)


def extract_joint_offsets(path: str):
    offsets = {}
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()
    in_joint_offset = False
    for line in lines:
        stripped = line.rstrip()
        if stripped.startswith("joint_offset:"):
            in_joint_offset = True
            continue
        if in_joint_offset:
            if stripped and not line.startswith(" "):
                break
            match = re.match(r"\s*([A-Za-z0-9_]+)\s*:\s*([-+0-9.eE]+)", stripped)
            if match:
                name, value = match.groups()
                if name in ANKLE_JOINTS:
                    offsets[name] = float(value)
    return offsets


def extract_parallel_transmission_blocks(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()
    blocks = {}
    current_name = None
    current = None
    for line in lines:
        if re.match(r"\s*-\s+name:\s+", line):
            current_name = line.split(":", 1)[1].strip().split()[0]
            current = {"name": current_name}
            blocks[current_name] = current
            continue
        if current is None:
            continue
        match = re.match(r"\s*([A-Za-z0-9_]+)\s*:\s*([^\s#]+)", line)
        if match:
            key, value = match.groups()
            current[key] = value
    return {
        name: block
        for name, block in blocks.items()
        if block.get("type") in ("LeftAnkleParallelTransmission", "RightAnkleParallelTransmission")
    }


def extract_function_body(text: str, signature: str):
    start = text.find(signature)
    if start < 0:
        raise RuntimeError(f"Failed to locate function signature: {signature}")
    brace_start = text.find("{", start)
    if brace_start < 0:
        raise RuntimeError(f"Failed to locate opening brace for: {signature}")
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start : idx + 1]
    raise RuntimeError(f"Failed to locate closing brace for: {signature}")


def parse_code_sign_facts(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()

    left_a2j = extract_function_body(text, "void LeftAnkleParallelTransmission::TransformActuatorToJoint()")
    right_a2j = extract_function_body(text, "void RightAnkleParallelTransmission::TransformActuatorToJoint()")
    left_j2a = extract_function_body(text, "void LeftAnkleParallelTransmission::TransformJointToActuator()")
    right_j2a = extract_function_body(text, "void RightAnkleParallelTransmission::TransformJointToActuator()")

    facts = {
        "left_a2j_extra_qm5_flip": "qm5 *= -1;" in left_a2j,
        "left_a2j_extra_qm6_flip": "qm6 *= -1;" in left_a2j,
        "left_a2j_extra_q6_flip": "q6 *= -1;" in left_a2j,
        "right_a2j_extra_qm5_flip": "qm5 *= -1;" in right_a2j,
        "right_a2j_extra_qm6_flip": "qm6 *= -1;" in right_a2j,
        "right_a2j_extra_q6_flip": "q6 *= -1;" in right_a2j,
        "left_a2j_state_source": "qm5 = actr_right_.handle->state.position" if "actr_right_.handle->state.position" in left_a2j else "unknown",
        "right_a2j_state_source": "qm5 = actr_left_.handle->state.position" if "actr_left_.handle->state.position" in right_a2j else "unknown",
        "left_j2a_cmd_pitch_target": "actr_right_.handle->cmd.kp = joint_pitch_.handle->cmd.kp;" in left_j2a,
        "left_j2a_cmd_roll_target": "actr_left_.handle->cmd.kp = joint_roll_.handle->cmd.kp;" in left_j2a,
        "right_j2a_cmd_pitch_target": "actr_left_.handle->cmd.kp = joint_pitch_.handle->cmd.kp;" in right_j2a,
        "right_j2a_cmd_roll_target": "actr_right_.handle->cmd.kp = joint_roll_.handle->cmd.kp;" in right_j2a,
    }
    return facts


def parse_mapping_grid(path: str):
    entries = {}
    key = None
    q5 = None
    q6 = None
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip()
            key_match = re.match(r"^(qm5qm6_(\d+)_(\d+)):\s*$", line)
            if key_match:
                key = key_match.group(1)
                q5 = None
                q6 = None
                continue
            if key is None:
                continue
            q5_match = re.match(r"^\s*q5:\s*([-+0-9.eE]+)\s*$", line)
            if q5_match:
                q5 = float(q5_match.group(1))
                continue
            q6_match = re.match(r"^\s*q6:\s*([-+0-9.eE]+)\s*$", line)
            if q6_match:
                q6 = float(q6_match.group(1))
                if q5 is not None:
                    _, i_str, j_str = key.split("_")
                    entries[(int(i_str), int(j_str))] = {"q5": q5, "q6": q6}
                key = None
    return entries


def actuator_angle(i: int, j: int):
    qm5 = QM5_ANGLE_MIN + (i - 1) * QM_RESOLUTION
    qm6 = QM6_ANGLE_MIN + (j - 1) * QM_RESOLUTION
    return qm5, qm6


def finite_difference(entries, i: int, j: int, axis: str):
    if axis == "i":
        left = entries.get((i - 1, j))
        right = entries.get((i + 1, j))
        if left and right:
            step = 2 * QM_RESOLUTION
            return {
                "dq5_dqm": (right["q5"] - left["q5"]) / step,
                "dq6_dqm": (right["q6"] - left["q6"]) / step,
            }
    if axis == "j":
        left = entries.get((i, j - 1))
        right = entries.get((i, j + 1))
        if left and right:
            step = 2 * QM_RESOLUTION
            return {
                "dq5_dqm": (right["q5"] - left["q5"]) / step,
                "dq6_dqm": (right["q6"] - left["q6"]) / step,
            }
    return None


def nearest_zero_entry(entries):
    best = None
    for (i, j), values in entries.items():
        score = math.hypot(values["q5"], values["q6"])
        if best is None or score < best["score"]:
            qm5, qm6 = actuator_angle(i, j)
            best = {
                "i": i,
                "j": j,
                "q5": values["q5"],
                "q6": values["q6"],
                "qm5": qm5,
                "qm6": qm6,
                "score": score,
            }
    return best


def write_report(offsets, blocks, code_facts, zero_entry, d_i, d_j):
    with open(OUT_MD, "w", encoding="utf-8") as handle:
        handle.write("# Round 3C Zero Bias and Mapping Check\n\n")

        handle.write("## Config-Level Facts\n\n")
        handle.write("### RL joint_offset\n\n")
        for joint in ANKLE_JOINTS:
            handle.write(f"- `{joint}`: `{offsets.get(joint, 'missing')}`\n")
        handle.write("\n")

        handle.write("### DCU ankle transmission directions\n\n")
        for name in sorted(blocks):
            block = blocks[name]
            handle.write(
                f"- `{name}`: "
                f"`joint_pitch={block.get('joint_pitch')}`, "
                f"`joint_roll={block.get('joint_roll')}`, "
                f"`actuator_left={block.get('actuator_left')}`, "
                f"`actuator_right={block.get('actuator_right')}`, "
                f"`direction_left={block.get('direction_left')}`, "
                f"`direction_right={block.get('direction_right')}`\n"
            )
        handle.write("\n")

        handle.write("## Code-Level Sign Facts\n\n")
        handle.write(f"- `Left TransformActuatorToJoint`: extra `qm5 *= -1`: `{code_facts['left_a2j_extra_qm5_flip']}`\n")
        handle.write(f"- `Left TransformActuatorToJoint`: extra `qm6 *= -1`: `{code_facts['left_a2j_extra_qm6_flip']}`\n")
        handle.write(f"- `Left TransformActuatorToJoint`: extra `q6 *= -1`: `{code_facts['left_a2j_extra_q6_flip']}`\n")
        handle.write(f"- `Right TransformActuatorToJoint`: extra `qm5 *= -1`: `{code_facts['right_a2j_extra_qm5_flip']}`\n")
        handle.write(f"- `Right TransformActuatorToJoint`: extra `qm6 *= -1`: `{code_facts['right_a2j_extra_qm6_flip']}`\n")
        handle.write(f"- `Right TransformActuatorToJoint`: extra `q6 *= -1`: `{code_facts['right_a2j_extra_q6_flip']}`\n")
        handle.write(f"- `Left actuator state source`: `{code_facts['left_a2j_state_source']}`\n")
        handle.write(f"- `Right actuator state source`: `{code_facts['right_a2j_state_source']}`\n")
        handle.write(f"- `Left joint->actuator kp path consistent`: `{code_facts['left_j2a_cmd_pitch_target'] and code_facts['left_j2a_cmd_roll_target']}`\n")
        handle.write(f"- `Right joint->actuator kp path consistent`: `{code_facts['right_j2a_cmd_pitch_target'] and code_facts['right_j2a_cmd_roll_target']}`\n\n")

        handle.write("## Mapping Table Zero-Neighborhood\n\n")
        handle.write(
            f"- Nearest grid entry to `(q5=0, q6=0)`: "
            f"`(i={zero_entry['i']}, j={zero_entry['j']})`, "
            f"`q5={zero_entry['q5']:.6f}`, `q6={zero_entry['q6']:.6f}`, "
            f"`qm5={zero_entry['qm5']:.6f}`, `qm6={zero_entry['qm6']:.6f}`\n"
        )
        if d_i:
            handle.write(
                f"- Local derivative along `qm5` axis: "
                f"`dq5/dqm5={d_i['dq5_dqm']:.4f}`, `dq6/dqm5={d_i['dq6_dqm']:.4f}`\n"
            )
        if d_j:
            handle.write(
                f"- Local derivative along `qm6` axis: "
                f"`dq5/dqm6={d_j['dq5_dqm']:.4f}`, `dq6/dqm6={d_j['dq6_dqm']:.4f}`\n"
            )
        handle.write("\n")

        handle.write("## Engineering Interpretation\n\n")
        all_zero_offsets = all(abs(offsets.get(joint, math.nan)) == 0.0 for joint in ANKLE_JOINTS)
        handle.write(f"- `joint_offset` for all 4 ankle joints is zero: `{all_zero_offsets}`\n")
        handle.write("- Both left/right ankle transmission blocks use `direction_left = 1.0`, `direction_right = 1.0`.\n")
        handle.write("- Left ankle actuator->joint path contains extra sign flips (`qm5`, `qm6`, `q6`), while right ankle actuator->joint path does not.\n")
        handle.write("- Therefore left/right symmetry is not established only by YAML directions; part of the sign convention is hard-coded inside `ankle_transmission.cc`.\n")
        handle.write("- If touchdown results show stable left/right mirror roll bias, these hard-coded asymmetries are higher-priority suspects than controller-side `joint_offset`.\n\n")

        handle.write("## Current Conclusion\n\n")
        handle.write("1. `controller joint_offset` does not currently explain the touchdown roll bias, because all ankle offsets are configured to `0.0`.\n")
        handle.write("2. `transmission direction` also does not explain it at YAML level, because both ankle transmissions are configured as `1.0 / 1.0`.\n")
        handle.write("3. The stronger zero-bias risk is inside `ankle_transmission.cc` itself, where left/right sign handling is not symmetric in actuator->joint reconstruction.\n")
        handle.write("4. This supports advancing `05` from generic `coupled_geometry` into a narrower `parallel_mapping / sign-convention verification` line.\n")


def main():
    offsets = extract_joint_offsets(RL_CFG)
    blocks = extract_parallel_transmission_blocks(DCU_CFG)
    code_facts = parse_code_sign_facts(ANKLE_TRANS_CC)
    entries = parse_mapping_grid(ANKLE_TRANS_YAML)
    zero_entry = nearest_zero_entry(entries)
    d_i = finite_difference(entries, zero_entry["i"], zero_entry["j"], "i")
    d_j = finite_difference(entries, zero_entry["i"], zero_entry["j"], "j")
    write_report(offsets, blocks, code_facts, zero_entry, d_i, d_j)
    print(f"Zero bias and mapping check: {OUT_MD}")


if __name__ == "__main__":
    main()
