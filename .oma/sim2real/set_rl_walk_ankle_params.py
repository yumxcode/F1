#!/usr/bin/env python3
"""Patch rl_walk_leg ankle kp/kd in source and generated runtime configs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CFG = REPO_ROOT / "src/module/control_module/cfg/rl_x1.yaml"
TARGET_BLOCK = "  rl_walk_leg:"


def candidate_paths() -> Iterable[Path]:
    yield SOURCE_CFG

    build_root = REPO_ROOT / "build"
    if build_root.exists():
        yield from build_root.rglob("rl_x1.yaml")

    install_root = REPO_ROOT / "src/install/linux/bin"
    if install_root.exists():
        yield from install_root.rglob("rl_x1.yaml")


def replace_block(lines: List[str], key: str, replacement: str) -> List[str]:
    in_target = False
    for idx, line in enumerate(lines):
        if line.startswith(TARGET_BLOCK):
            in_target = True
            continue
        if in_target and line.startswith("  ") and not line.startswith("    "):
            break
        if in_target and line.lstrip().startswith(f"{key}:"):
            indent = line[: len(line) - len(line.lstrip())]
            lines[idx] = f"{indent}{key}: {replacement}\n"
            return lines
    raise ValueError(f"Key '{key}' not found under rl_walk_leg block")


def update_file(
    path: Path,
    left_pitch_kp: float,
    left_roll_kp: float,
    right_pitch_kp: float,
    right_roll_kp: float,
    ankle_kd: float,
) -> None:
    lines = path.read_text().splitlines(keepends=True)
    stiffness = (
        "[30.0, 40.0, 35.0,  100.0, "
        f"{left_pitch_kp:.1f}, {left_roll_kp:.1f},\n"
        "                 30.0, 40.0,  35.0, 100.0, "
        f"{right_pitch_kp:.1f}, {right_roll_kp:.1f}]"
    )
    damping = (
        "[3.0,  3.0,  4.0,   10.0,  "
        f"{ankle_kd:.1f},   {ankle_kd:.1f},\n"
        "                 3.0,  3.0,   4.0,  10.0,  "
        f"{ankle_kd:.1f},   {ankle_kd:.1f}]"
    )
    lines = replace_block(lines, "stiffness", stiffness)
    lines = replace_block(lines, "damping", damping)
    path.write_text("".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left-pitch-kp", type=float, default=100.0)
    parser.add_argument("--left-roll-kp", type=float, default=80.0)
    parser.add_argument("--right-pitch-kp", type=float, default=100.0)
    parser.add_argument("--right-roll-kp", type=float, default=60.0)
    parser.add_argument("--ankle-kd", type=float, default=0.8)
    args = parser.parse_args()

    updated_paths = []
    for path in dict.fromkeys(candidate_paths()):
        if path.exists():
            update_file(
                path,
                left_pitch_kp=args.left_pitch_kp,
                left_roll_kp=args.left_roll_kp,
                right_pitch_kp=args.right_pitch_kp,
                right_roll_kp=args.right_roll_kp,
                ankle_kd=args.ankle_kd,
            )
            updated_paths.append(path)

    if not updated_paths:
        raise FileNotFoundError("No rl_x1.yaml files found to update.")

    print("Updated rl_walk_leg ankle params:")
    for path in updated_paths:
        print(f"  - {path}")
    print("Applied values:")
    print(f"  left_pitch_kp={args.left_pitch_kp:g}")
    print(f"  left_roll_kp={args.left_roll_kp:g}")
    print(f"  right_pitch_kp={args.right_pitch_kp:g}")
    print(f"  right_roll_kp={args.right_roll_kp:g}")
    print(f"  ankle_kd={args.ankle_kd:g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
