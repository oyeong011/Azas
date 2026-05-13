#!/usr/bin/env python3
"""Supervised one-shot real cup side-pick gate.

This script prepares exactly one cup side pick from a live or manual base_link
cup reference pose. It refuses real motion unless the explicit real-motion gates
are present. When enabled, it plans approach/grasp/lift with MoveItPy and sends
only successful plan trajectories to MoveIt ExecuteTrajectory.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT_DIR / "tools"
SRC_MOTION = ROOT_DIR / "src" / "azas_motion"
for path in (TOOLS_DIR, SRC_MOTION):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

CONFIRM_PHRASE = "I_UNDERSTAND_THIS_WILL_MOVE_THE_ROBOT"
DEFAULT_SWEEP_JSON = Path("/tmp/azas_side_grasp_candidate_sweep.json")
DEFAULT_SWEEP_CSV = Path("/tmp/azas_side_grasp_candidate_sweep.csv")
MOVEIT_SUCCESS = 1


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
    parser.add_argument("--execute-action-name", default="/execute_trajectory")
    parser.add_argument("--move-action-name", default="/move_action")
    parser.add_argument("--action-timeout-sec", type=float, default=60.0)
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

    return execute_one_pick(args, best)


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
    print_stage("CHECK_SERVICES", "checking RG2 services, MoveIt planning, and execution actions")
    checks = [
        ("gripper open", args.gripper_open_service),
        ("gripper close", args.gripper_close_service),
        ("MoveIt plan", "/plan_kinematic_path"),
    ]
    service_list = command_output(["ros2", "service", "list"], timeout=5.0)
    if strict and not service_list:
        service_list = "\n".join(rclpy_graph_names("services"))
    ok = True
    for label, name in checks:
        found = name in service_list
        status = "OK" if found else ("FAIL" if strict else "WARN")
        print(f"[{status}] {label}: {name}")
        ok = ok and (found or not strict)
    move_group_nodes = command_output(["ros2", "node", "list", "--no-daemon"], timeout=5.0)
    if strict and not move_group_nodes:
        move_group_nodes = "\n".join(rclpy_graph_names("nodes"))
    move_group_found = "/move_group" in move_group_nodes
    status = "OK" if move_group_found else ("FAIL" if strict else "WARN")
    print(f"[{status}] move_group node: /move_group")
    action_text = command_output(["ros2", "action", "list", "-t"], timeout=5.0)
    if strict and not action_text:
        action_text = "\n".join(rclpy_action_names_and_types())
    execute_action_ok = f"{args.execute_action_name} [moveit_msgs/action/ExecuteTrajectory]" in action_text
    move_action_ok = f"{args.move_action_name} [moveit_msgs/action/MoveGroup]" in action_text
    execute_status = "OK" if execute_action_ok else ("FAIL" if strict else "WARN")
    move_status = "OK" if move_action_ok else "INFO"
    print(f"[{execute_status}] execute action: {args.execute_action_name} [moveit_msgs/action/ExecuteTrajectory]")
    print(f"[{move_status}] move action: {args.move_action_name} [moveit_msgs/action/MoveGroup]")
    return ok and (move_group_found or not strict) and (execute_action_ok or not strict)


def rclpy_graph_names(kind: str) -> list[str]:
    import rclpy

    initialized_here = False
    if not rclpy.ok():
        rclpy.init(args=None)
        initialized_here = True
    node = rclpy.create_node("azas_single_pick_graph_check")
    try:
        if kind == "services":
            return [name for name, _types in node.get_service_names_and_types()]
        if kind == "nodes":
            return list(node.get_node_names())
        raise ValueError(f"unsupported graph kind: {kind}")
    finally:
        node.destroy_node()
        if initialized_here and rclpy.ok():
            rclpy.shutdown()


def rclpy_action_names_and_types() -> list[str]:
    import rclpy

    initialized_here = False
    if not rclpy.ok():
        rclpy.init(args=None)
        initialized_here = True
    node = rclpy.create_node("azas_single_pick_action_check")
    try:
        return [
            f"{name} [{type_name}]"
            for name, type_names in node.get_action_names_and_types()
            for type_name in type_names
        ]
    finally:
        node.destroy_node()
        if initialized_here and rclpy.ok():
            rclpy.shutdown()


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
    print(f"motion_backend={args.execute_action_name} [moveit_msgs/action/ExecuteTrajectory]")
    print(f"speed_scale={args.velocity_scale:.3f} accel_scale={args.accel_scale:.3f}")
    print(f"confirm_required={CONFIRM_PHRASE}")
    if args.enable_real_motion and not best.get("all_success"):
        print("[FAIL] selected candidate is not all_success; execution prohibited")


def execute_one_pick(args: argparse.Namespace, candidate: dict[str, Any]) -> int:
    print_stage("EXECUTE_ONE_PICK", "one-shot ExecuteTrajectory backend")
    if not candidate.get("all_success"):
        print("[FAIL] selected candidate is not all_success; execution prohibited")
        return 1
    try:
        executor = MoveItExecuteTrajectoryBackend(args)
        executor.run(candidate)
    except Exception as exc:
        print(f"[FAIL] execution stopped: {exc}")
        return 1
    print_stage("DONE", "supervised one-shot side pick command sequence completed")
    return 0


class MoveItExecuteTrajectoryBackend:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        os.environ.setdefault("ROS_LOG_DIR", "/tmp/ros2_logs")
        Path(os.environ["ROS_LOG_DIR"]).mkdir(parents=True, exist_ok=True)
        import rclpy
        from rclpy.node import Node

        if not rclpy.ok():
            rclpy.init(args=None)
        self.rclpy = rclpy
        self.node: Node = rclpy.create_node("azas_supervised_real_single_cup_pick")
        self._select_action_backend()
        self.moveit_py = None
        self.planning_component = None

    def run(self, candidate: dict[str, Any]) -> None:
        try:
            self._init_moveit()
            self._call_gripper(self.args.gripper_open_service, "GRIPPER_OPEN")
            for label in ("approach", "grasp"):
                trajectory = self._plan_pose(label, candidate[f"{label}_pose"])
                self._execute_trajectory(label, trajectory)
            self._call_gripper(self.args.gripper_close_service, "GRIPPER_CLOSE")
            trajectory = self._plan_pose("lift", candidate["lift_pose"])
            self._execute_trajectory("lift", trajectory)
        finally:
            self.node.destroy_node()
            try:
                if self.rclpy.ok():
                    self.rclpy.shutdown()
            except Exception:
                pass

    def _select_action_backend(self) -> None:
        actions = dict(self.node.get_action_names_and_types())
        execute_types = actions.get(self.args.execute_action_name, [])
        move_types = actions.get(self.args.move_action_name, [])
        if "moveit_msgs/action/ExecuteTrajectory" in execute_types:
            self.action_name = self.args.execute_action_name
            self.action_type = "moveit_msgs/action/ExecuteTrajectory"
            print(f"[OK] using action backend: {self.action_name} [{self.action_type}]")
            return
        if "moveit_msgs/action/MoveGroup" in move_types:
            raise RuntimeError(
                f"{self.args.move_action_name} is available, but this script only executes "
                "already successful plan_result.trajectory via ExecuteTrajectory"
            )
        raise RuntimeError(
            f"{self.args.execute_action_name} [moveit_msgs/action/ExecuteTrajectory] not available"
        )

    def _init_moveit(self) -> None:
        from moveit.planning import MoveItPy
        from sweep_side_grasp_planning_candidates import moveit_config_dict

        self.moveit_py = MoveItPy(
            node_name="azas_supervised_single_pick_moveit",
            config_dict=moveit_config_dict("m0609", "dsr_moveit_config_m0609"),
            provide_planning_service=False,
        )
        self.planning_component = self.moveit_py.get_planning_component(
            self.args.planning_group
        )

    def _plan_pose(self, label: str, pose_dict_msg: dict[str, Any]):
        from geometry_msgs.msg import PoseStamped
        from moveit.planning import PlanRequestParameters

        print_stage(f"PLAN_{label.upper()}", "MoveItPy plan() before ExecuteTrajectory")
        pose_msg = PoseStamped()
        pose_msg.header.frame_id = self.args.base_frame
        pose_msg.pose.position.x = float(pose_dict_msg["position"]["x"])
        pose_msg.pose.position.y = float(pose_dict_msg["position"]["y"])
        pose_msg.pose.position.z = float(pose_dict_msg["position"]["z"])
        pose_msg.pose.orientation.x = float(pose_dict_msg["orientation"]["x"])
        pose_msg.pose.orientation.y = float(pose_dict_msg["orientation"]["y"])
        pose_msg.pose.orientation.z = float(pose_dict_msg["orientation"]["z"])
        pose_msg.pose.orientation.w = float(pose_dict_msg["orientation"]["w"])

        params = PlanRequestParameters(self.moveit_py)
        params.planning_time = float(self.args.planning_timeout_sec)
        params.planning_pipeline = "ompl"
        params.planner_id = "RRTConnectkConfigDefault"
        params.planning_attempts = 1
        params.max_velocity_scaling_factor = float(self.args.velocity_scale)
        params.max_acceleration_scaling_factor = float(self.args.accel_scale)
        self.planning_component.set_start_state_to_current_state()
        self.planning_component.set_goal_state(
            pose_stamped_msg=pose_msg,
            pose_link=self.args.ee_link,
        )
        plan_result = self.planning_component.plan(params)
        if not plan_result:
            raise RuntimeError(f"{label} planning failed; execution prohibited")
        trajectory = getattr(plan_result, "trajectory", None)
        if trajectory is None:
            raise RuntimeError(f"{label} plan_result has no trajectory; execution prohibited")
        print(f"[OK] {label} plan succeeded; trajectory ready for ExecuteTrajectory")
        return trajectory

    def _execute_trajectory(self, label: str, trajectory) -> None:
        from moveit_msgs.action import ExecuteTrajectory
        from rclpy.action import ActionClient

        print_stage(f"EXECUTE_{label.upper()}", self.action_name)
        client = ActionClient(self.node, ExecuteTrajectory, self.action_name)
        if not client.wait_for_server(timeout_sec=5.0):
            raise RuntimeError(f"ExecuteTrajectory action unavailable: {self.action_name}")
        goal = ExecuteTrajectory.Goal()
        goal.trajectory = trajectory
        send_future = client.send_goal_async(goal)
        self.rclpy.spin_until_future_complete(self.node, send_future, timeout_sec=5.0)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            raise RuntimeError(f"{label} ExecuteTrajectory goal rejected")
        result_future = goal_handle.get_result_async()
        self.rclpy.spin_until_future_complete(
            self.node,
            result_future,
            timeout_sec=float(self.args.action_timeout_sec),
        )
        result_wrapper = result_future.result()
        if result_wrapper is None:
            raise RuntimeError(f"{label} ExecuteTrajectory timed out")
        error_code = getattr(result_wrapper.result.error_code, "val", None)
        if error_code != MOVEIT_SUCCESS:
            raise RuntimeError(f"{label} ExecuteTrajectory failed with error_code={error_code}")
        print(f"[OK] {label} ExecuteTrajectory succeeded")

    def _call_gripper(self, service_name: str, label: str) -> None:
        from std_srvs.srv import Trigger

        print_stage(label, service_name)
        client = self.node.create_client(Trigger, service_name)
        if not client.wait_for_service(timeout_sec=5.0):
            raise RuntimeError(f"gripper service unavailable: {service_name}")
        future = client.call_async(Trigger.Request())
        self.rclpy.spin_until_future_complete(self.node, future, timeout_sec=10.0)
        response = future.result()
        if response is None or not response.success:
            message = getattr(response, "message", "<no response>")
            raise RuntimeError(f"gripper service failed: {service_name}: {message}")
        print(f"[OK] {label}: {response.message}")


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
