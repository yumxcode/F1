#!/usr/bin/env python3
"""Update ankle identifier YAML for the next kp/kd test.

Primary use: run locally, commit, push, then let the lab machine pull and
execute the updated config. If generated runtime copies already exist, patch
them too so the script is also safe to run directly on the lab machine.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CFG = REPO_ROOT / "src/module/ankle_identifier_module/cfg/ankle_identifier.yaml"


def format_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def patch_yaml_lines(lines: List[str], updates: Dict[str, object]) -> List[str]:
    patched = list(lines)
    seen = set()
    for idx, line in enumerate(patched):
        stripped = line.strip()
        if ":" not in stripped or stripped.startswith("#"):
            continue
        key, _ = stripped.split(":", 1)
        key = key.strip()
        if key in updates:
            patched[idx] = f"{key}: {format_value(updates[key])}\n"
            seen.add(key)

    missing = [key for key in updates if key not in seen]
    if missing:
        raise ValueError(f"Missing YAML keys: {', '.join(missing)}")

    return patched


def candidate_paths() -> Iterable[Path]:
    yield SOURCE_CFG

    build_root = REPO_ROOT / "build"
    if build_root.exists():
        yield from build_root.rglob("ankle_identifier.yaml")

    install_root = REPO_ROOT / "src/install/linux/bin"
    if install_root.exists():
        yield from install_root.rglob("ankle_identifier.yaml")


def update_file(path: Path, updates: Dict[str, object]) -> None:
    original = path.read_text().splitlines(keepends=True)
    patched = patch_yaml_lines(original, updates)
    path.write_text("".join(patched))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--side", choices=["left", "right"], required=True)
    parser.add_argument("--axis", choices=["pitch", "roll"], required=True)
    parser.add_argument("--mode", choices=["step", "sine"], default="step")
    parser.add_argument("--contact", choices=["air", "ground"], default=None)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--kp", type=float, required=True)
    parser.add_argument("--kd", type=float, required=True)
    parser.add_argument("--step-amplitude", type=float, default=0.015)
    parser.add_argument("--sine-amplitude", type=float, default=0.004)
    parser.add_argument("--sine-frequency", type=float, default=1.0)
    parser.add_argument("--csv-path", default=None)
    args = parser.parse_args()

    auto_name = f"{args.side}_{args.axis}_{args.mode}"
    if args.contact:
        auto_name += f"_{args.contact}"
    auto_name += f"_kp{args.kp:g}_kd{args.kd:g}"
    if args.tag:
        auto_name += f"_{args.tag}"

    csv_path = args.csv_path or f"./log/{auto_name}.csv"
    updates = {
        "mode": args.mode,
        "test_side": args.side,
        "test_axis": args.axis,
        "step_amplitude_rad": args.step_amplitude,
        "sine_amplitude_rad": args.sine_amplitude,
        "sine_frequency_hz": args.sine_frequency,
        "test_kp": args.kp,
        "test_kd": args.kd,
        "csv_path": csv_path,
    }

    updated_paths = []
    for path in dict.fromkeys(candidate_paths()):
        if path.exists():
            update_file(path, updates)
            updated_paths.append(path)

    if not updated_paths:
        raise FileNotFoundError("No ankle_identifier.yaml files found to update.")

    print("Updated ankle identifier config:")
    for path in updated_paths:
        print(f"  - {path}")
    print("Test tuple:")
    print(f"  mode={args.mode}")
    print(f"  side={args.side}")
    print(f"  axis={args.axis}")
    if args.contact:
        print(f"  contact={args.contact}")
    print(f"  kp={args.kp:g}")
    print(f"  kd={args.kd:g}")
    print(f"  step_amplitude_rad={args.step_amplitude:g}")
    print(f"  csv_path={csv_path}")
    print("Next step:")
    print("  commit/push locally, then pull/build/run on the lab machine")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
