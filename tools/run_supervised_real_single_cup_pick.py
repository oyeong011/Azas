#!/usr/bin/env python3
"""Supervised one-shot real cup side-pick gate.

This script prepares exactly one cup side pick from a live or manual base_link
cup reference pose. It refuses real motion unless the explicit real-motion gates
are present, and this batch still stops before execution because Azas does not
yet contain an accepted MoveIt execution backend.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIRM_PHRASE = "I_UNDERSTAND_THIS_WILL_MOVE_THE_ROBOT"
DEFAULT_SWEEP_JSON = Path("/tmp/azas_side_grasp_candidate_sweep.json")
DEFAULT_SWEEP_CSV = Path("/tmp/azas_side_grasp_candidate_sweep.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--enable-real-motion", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--one-shot", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-live-pose", type=str_to_bool, default=False)
    parser.add_argument("--tumbler-pose-topic", default="/jarvis/tumbler_dispenser/tumbler_pose")
    parser.add_argument("--cup-reference-x", type=float, default=None)
    parser.add_argument("--cup-reference-y", type=float, default=None)
    parser.add_argument("--cup-reference-z", type=float, default=None)
    parser.add_argument("--planning-group", default="manipulator")
    parser.add_argument("--ee-link", default="tool0")
    parser.add_argument("--base-frame", default="base_link")
    parser.add_argument("--max-candidates", type=int, default=300)
    parser.add_argument("--planning-timeout-sec", type=float, default=1.0)
    parser.add_argument("--velocity-scale", type=float, default=0.03)
    parser.add_argument("--accel-scale", type=float, default=0.03)
    parser.add_argument("--gripper-open-service", default="/jarvis/rg2/open")
    parser.add_argument("--gripper-close-service", default="/jarvis/rg2/close")
    parser.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP_JSON)
    parser.add_argument("--sweep-csv", type=Path, default=DEFAULT_SWEEP_CSV)
    parser.add_argument("--skip-sweep", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print_stage("START", "supervised one-shot cup side pick")
    print(f"real_motion={args.enable_real_motion} one_shot={args.one_shot}")

    if not validate_motion_gates(args):
        return 2
    if not validate_speed_scales(args):
        return 2
    if not check_services(args, strict=args.enable_real_motion):
        return 1

    cup_pose = read_cup_pose(args)
    if cup_pose is None:
        return 1

    best = sweep_and_select(args, cup_pose, run=not args.skip_sweep and not dry_run_only(args))
    if best is None:
        return 1

    print_pick_poses(best)
    print_confirm_summary(args, cup_pose, best)
    print("[INFO] Waiting 5 seconds before the execution gate.")
    time.sleep(5.0)

    if not args.enable_real_motion:
        print_stage("DONE", "dry-run stop before GRIPPER_OPEN")
        print("No real robot motion or RG2 command was sent.")
        return 0

    return execute_one_pick_stub(args)


def str_to_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid bool value: {value!r}")


def print_stage(name: str, detail: str) -> None:
    print(f"\n=== {name} ===")
    print(detail)


def validate_motion_gates(args: argparse.Namespace) -> bool:
    print_stage("SAFETY_GATE", "checking real-motion flags")
    if not args.one_shot:
        print("[FAIL] --one-shot must remain true; repeated pick is not allowed")
        return False
    if not args.enable_real_motion:
        print("[OK] dry-run mode; real motion disabled")
        return True
    if args.confirm != CONFIRM_PHRASE:
        print(f"[FAIL] real motion requires --confirm {CONFIRM_PHRASE}")
        print("No real robot motion or RG2 command was sent.")
        return False
    print("[OK] real-motion confirmation phrase accepted")
    return True


def validate_speed_scales(args: argparse.Namespace) -> bool:
    ok = 0.0 < args.velocity_scale <= 0.05 and 0.0 < args.accel_scale <= 0.05
    status = "OK" if ok else "FAIL"
    print(f"[{status}] velocity_scale={args.velocity_scale:.3f} accel_scale={args.accel_scale:.3f}")
    return ok


def check_services(args: argparse.Namespace, strict: bool) -> bool:
    print_stage("CHECK_SERVICES", "checking RG2 and MoveIt planning services")
    checks = [
        ("gripper open", args.gripper_open_service),
        ("gripper close", args.gripper_close_service),
        ("MoveIt plan", "/plan_kinematic_path"),
    ]
    service_list = command_output(["ros2", "service", "list"], timeout=5.0)
    ok = True
    for label, name in checks:
        found = name in service_list
        status = "OK" if found else ("FAIL" if strict else "WARN")
        print(f"[{status}] {label}: {name}")
        ok = ok and (found or not strict)
    move_group_nodes = command_output(["ros2", "node", "list", "--no-daemon"], timeout=5.0)
    move_group_found = "/move_group" in move_group_nodes
    status = "OK" if move_group_found else ("FAIL" if strict else "WARN")
    print(f"[{status}] move_group node: /move_group")
    return ok and (move_group_found or not strict)


def read_cup_pose(args: argparse.Namespace) -> dict[str, float] | None:
    print_stage("WAIT_OR_READ_CUP_POSE", "base_link pose only")
    if args.use_live_pose:
        pose = read_live_pose(args.tumbler_pose_topic)
        if pose is None:
            return None
        print(f"[OK] live pose: {pose}")
        return pose
    if None in (args.cup_reference_x, args.cup_reference_y, args.cup_reference_z):
        print("[FAIL] provide --use-live-pose true or --cup-reference-x/y/z")
        return None
    pose = {
        "frame_id": args.base_frame,
        "x": float(args.cup_reference_x),
        "y": float(args.cup_reference_y),
        "z": float(args.cup_reference_z),
    }
    if pose["frame_id"] != "base_link":
        print(f"[FAIL] frame_id must be base_link, got {pose['frame_id']!r}")
        return None
    print(f"[OK] manual cup reference: {pose}")
    return pose


def read_live_pose(topic: str) -> dict[str, float] | None:
    result = run_command(["ros2", "topic", "echo", "--once", topic], timeout=8.0, capture=True)
    if result.returncode != 0:
        print(f"[FAIL] timed out or failed reading live pose topic: {topic}")
        return None
    frame_id = extract_scalar(result.stdout, "frame_id:")
    if frame_id != "base_link":
        print(f"[FAIL] live pose frame_id must be base_link, got {frame_id!r}")
        return None
    values = extract_position_xyz(result.stdout)
    if values is None:
        print("[FAIL] could not parse live pose position")
        return None
    return {"frame_id": frame_id, "x": values[0], "y": values[1], "z": values[2]}


def extract_scalar(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped.split(":", 1)[1].strip().strip("'\"")
    return None


def extract_position_xyz(text: str) -> tuple[float, float, float] | None:
    in_position = False
    values: dict[str, float] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "position:":
            in_position = True
            continue
        if stripped == "orientation:":
            in_position = False
        if in_position and any(stripped.startswith(f"{axis}:") for axis in ("x", "y", "z")):
            axis, raw = stripped.split(":", 1)
            values[axis] = float(raw.strip())
    if {"x", "y", "z"} <= values.keys():
        return values["x"], values["y"], values["z"]
    return None


def sweep_and_select(
    args: argparse.Namespace,
    cup_pose: dict[str, float],
    run: bool,
) -> dict[str, Any] | None:
    print_stage("SWEEP_SIDE_GRASP_CANDIDATES", "planning-only all_success candidates required")
    command = [
        sys.executable,
        str(ROOT_DIR / "tools" / "sweep_side_grasp_planning_candidates.py"),
        "--planning-group",
        args.planning_group,
        "--ee-link",
        args.ee_link,
        "--base-frame",
        args.base_frame,
        "--cup-reference-x",
        str(cup_pose["x"]),
        "--cup-reference-y",
        str(cup_pose["y"]),
        "--cup-reference-z",
        str(cup_pose["z"]),
        "--planning-timeout-sec",
        str(args.planning_timeout_sec),
        "--max-candidates",
        str(args.max_candidates),
        "--json-output",
        str(args.sweep_json),
        "--csv-output",
        str(args.sweep_csv),
    ]
    if run:
        result = run_command(command, timeout=240.0, capture=False)
        if result.returncode != 0:
            print("[FAIL] candidate sweep failed; execution prohibited")
            return None
    else:
        print("[DRY-RUN] would run:", " ".join(command))

    best = load_best_candidate(args.sweep_json)
    if best is None:
        if args.enable_real_motion:
            print("[FAIL] all_success candidate missing; execution prohibited")
            return None
        print("[DRY-RUN] no all_success sweep output found; using preview candidate only")
        return preview_candidate(cup_pose)
    print(f"[OK] selected all_success candidate_id={best.get('candidate_id')}")
    return best


def load_best_candidate(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    results = json.loads(path.read_text(encoding="utf-8"))
    successes = [item for item in results if item.get("all_success")]
    if not successes:
        return None
    return sorted(
        successes,
        key=lambda item: (
            abs(float(item.get("height", 999.0)) - 0.06),
            -float(item.get("approach_distance_m", 0.0)),
            {"-x": 0, "+x": 1, "-y": 2, "+y": 3}.get(str(item.get("axis")), 99),
        ),
    )[0]


def preview_candidate(cup_pose: dict[str, float]) -> dict[str, Any]:
    grasp_z = cup_pose["z"] + 0.05
    return {
        "candidate_id": "dry_run_preview_not_planned",
        "axis": "-x",
        "height": 0.05,
        "qx": 0.0,
        "qy": 0.0,
        "qz": 0.0,
        "qw": 1.0,
        "approach_pose": pose_dict(cup_pose["x"] + 0.175, cup_pose["y"], grasp_z),
        "grasp_pose": pose_dict(cup_pose["x"], cup_pose["y"], grasp_z),
        "lift_pose": pose_dict(cup_pose["x"], cup_pose["y"], grasp_z + 0.12),
        "all_success": False,
        "failure_code": "DRY_RUN_NOT_PLANNED",
    }


def pose_dict(x: float, y: float, z: float) -> dict[str, Any]:
    return {
        "position": {"x": x, "y": y, "z": z},
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
    }


def print_pick_poses(candidate: dict[str, Any]) -> None:
    print_stage("PRINT_APPROACH_GRASP_LIFT_POSES", "review selected candidate")
    print(f"candidate_id={candidate.get('candidate_id')}")
    print(f"axis={candidate.get('axis')} height={candidate.get('height')}")
    print(
        "quaternion="
        f"[{candidate.get('qx')}, {candidate.get('qy')}, {candidate.get('qz')}, {candidate.get('qw')}]"
    )
    print(f"approach_pose={json.dumps(candidate.get('approach_pose'), sort_keys=True)}")
    print(f"grasp_pose={json.dumps(candidate.get('grasp_pose'), sort_keys=True)}")
    print(f"lift_pose={json.dumps(candidate.get('lift_pose'), sort_keys=True)}")
    print(f"all_success={candidate.get('all_success')} failure_code={candidate.get('failure_code')}")


def print_confirm_summary(args: argparse.Namespace, cup_pose: dict[str, float], best: dict[str, Any]) -> None:
    print_stage("USER_CONFIRM", "final review before any real command")
    print(f"cup_pose={cup_pose}")
    print(f"gripper_open={args.gripper_open_service}")
    print(f"gripper_close={args.gripper_close_service}")
    print(f"motion_backend=missing")
    print(f"speed_scale={args.velocity_scale:.3f} accel_scale={args.accel_scale:.3f}")
    print(f"confirm_required={CONFIRM_PHRASE}")
    if args.enable_real_motion and not best.get("all_success"):
        print("[FAIL] selected candidate is not all_success; execution prohibited")


def execute_one_pick_stub(args: argparse.Namespace) -> int:
    print_stage("EXECUTE_ONE_PICK", "blocked before GRIPPER_OPEN")
    print("Current repo has MoveItPy plan() only; no accepted execution backend exists.")
    print("Required backend: execute the exact planned trajectory via MoveIt ExecuteTrajectory")
    print("or MoveGroup action after proving it consumes the successful plan result.")
    print("No gripper open/close was called because motion backend is missing.")
    print("No real robot motion or RG2 command was sent.")
    return 1


def dry_run_only(args: argparse.Namespace) -> bool:
    return not args.enable_real_motion


def command_output(command: list[str], timeout: float) -> str:
    result = run_command(command, timeout=timeout, capture=True)
    return result.stdout if result.returncode == 0 else ""


def run_command(
    command: list[str],
    timeout: float,
    capture: bool,
) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, Any] = {
        "cwd": str(ROOT_DIR),
        "timeout": timeout,
        "check": False,
        "text": True,
    }
    if capture:
        kwargs.update({"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT})
    return subprocess.run(command, **kwargs)


if __name__ == "__main__":
    raise SystemExit(main())
