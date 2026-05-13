#!/usr/bin/env python3
"""Move only HOME -> OBSERVE joint targets for cup observation.

This script is intentionally limited to the camera observation posture path.
It does not read cup poses, run perception, touch the gripper, sweep side grasp
candidates, or execute a pick.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[0]
TOOLS_DIR = ROOT_DIR / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

CONFIRM_PHRASE = "I_UNDERSTAND_THIS_WILL_MOVE_THE_ROBOT"
MOVEIT_SUCCESS = 1
JOINT_TARGET_TOLERANCE_RAD = 0.03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home-joint-1-deg", type=float, default=0.0)
    parser.add_argument("--home-joint-2-deg", type=float, default=0.0)
    parser.add_argument("--home-joint-3-deg", type=float, default=90.0)
    parser.add_argument("--home-joint-4-deg", type=float, default=0.0)
    parser.add_argument("--home-joint-5-deg", type=float, default=90.0)
    parser.add_argument("--home-joint-6-deg", type=float, default=0.0)
    parser.add_argument("--observe-joint-1-deg", type=float, default=0.0)
    parser.add_argument("--observe-joint-2-deg", type=float, default=-15.0)
    parser.add_argument("--observe-joint-3-deg", type=float, default=45.0)
    parser.add_argument("--observe-joint-4-deg", type=float, default=0.0)
    parser.add_argument("--observe-joint-5-deg", type=float, default=75.0)
    parser.add_argument("--observe-joint-6-deg", type=float, default=0.0)
    parser.add_argument("--planning-group", default="manipulator")
    parser.add_argument("--execute-action-name", default="/execute_trajectory")
    parser.add_argument("--planning-timeout-sec", type=float, default=3.0)
    parser.add_argument("--velocity-scale", type=float, default=0.02)
    parser.add_argument("--accel-scale", type=float, default=0.02)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--enable-real-motion", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--one-shot", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--action-timeout-sec", type=float, default=60.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print_stage("START", "observe-only HOME -> OBSERVE joint target motion")
    print("scope=observe_cup_pose_only")
    print(f"real_motion={args.enable_real_motion} dry_run={dry_run_only(args)} one_shot={args.one_shot}")

    home_target = home_joint_target_degrees(args)
    observe_target = observe_joint_target_degrees(args)
    print_joint_target("HOME", home_target)
    print_joint_target("OBSERVE", observe_target)
    print(f"planning_group={args.planning_group}")
    print(f"motion_backend={args.execute_action_name} [moveit_msgs/action/ExecuteTrajectory]")
    print(f"speed_scale={args.velocity_scale:.3f} accel_scale={args.accel_scale:.3f}")
    print(f"target_tolerance_rad={JOINT_TARGET_TOLERANCE_RAD:.3f}")

    if not validate_motion_gates(args):
        return 2
    if not validate_speed_scales(args):
        return 2

    if dry_run_only(args):
        countdown(5)
        print_stage("DRY_RUN_DONE", "HOME and OBSERVE targets were not executed")
        print("No real robot motion was commanded.")
        return 0

    if not check_real_motion_ready(args):
        return 1

    countdown(5)
    try:
        executor = ObserveJointExecutor(args)
    except Exception as exc:
        print("HOME_PLAN_FAILED")
        print(f"[FAIL] ROS node setup failed before HOME planning: {exc}")
        return 1
    try:
        if not executor.execute_target("HOME", home_target):
            return 1
        if not executor.wait_for_target("HOME", home_target):
            print("HOME_TARGET_NOT_REACHED")
            return 1
        if not executor.execute_target("OBSERVE", observe_target):
            return 1
        if not executor.wait_for_target("OBSERVE", observe_target):
            print("OBSERVE_TARGET_NOT_REACHED")
            return 1
    finally:
        executor.shutdown()

    print("OBSERVE_CUP_POSE_REACHED")
    return 0


def validate_motion_gates(args: argparse.Namespace) -> bool:
    print_stage("SAFETY_GATE", "checking real-motion flags")
    if not args.one_shot:
        print("[FAIL] --one-shot must remain true; repeated execution is not allowed")
        return False
    if not args.enable_real_motion:
        print("[OK] dry-run mode; real motion disabled")
        return True
    if args.confirm != CONFIRM_PHRASE:
        print(f"[FAIL] real motion requires --confirm {CONFIRM_PHRASE}")
        print("No real robot motion was commanded.")
        return False
    print("[OK] real-motion confirmation phrase accepted")
    return True


def validate_speed_scales(args: argparse.Namespace) -> bool:
    ok = 0.0 < args.velocity_scale <= 0.05 and 0.0 < args.accel_scale <= 0.05
    status = "OK" if ok else "FAIL"
    print(f"[{status}] velocity_scale={args.velocity_scale:.3f} accel_scale={args.accel_scale:.3f}")
    return ok


def check_real_motion_ready(args: argparse.Namespace) -> bool:
    print_stage("CHECK_REAL_MOTION_READY", "checking MoveIt node, ExecuteTrajectory action, and controller")
    move_group_nodes = command_output(["ros2", "node", "list", "--no-daemon"], timeout=5.0)
    if not move_group_nodes:
        move_group_nodes = "\n".join(rclpy_graph_names("nodes"))
    if "/move_group" not in move_group_nodes:
        print("MOVE_GROUP_NOT_READY")
        print("[FAIL] move_group node missing: /move_group")
        return False
    print("[OK] move_group node: /move_group")

    action_text = command_output(["ros2", "action", "list", "-t"], timeout=5.0)
    if not action_text:
        action_text = "\n".join(rclpy_action_names_and_types())
    expected_action = f"{args.execute_action_name} [moveit_msgs/action/ExecuteTrajectory]"
    if expected_action not in action_text:
        print("EXECUTE_TRAJECTORY_NOT_AVAILABLE")
        print(f"[FAIL] execute action missing: {expected_action}")
        return False
    print(f"[OK] execute action: {expected_action}")

    return check_controller_if_available()


def check_controller_if_available() -> bool:
    controllers = command_output(["ros2", "control", "list_controllers"], timeout=5.0)
    if not controllers:
        print("[WARN] controller_manager did not answer; dsr_moveit_controller active state was not verified")
        return True
    if any("dsr_moveit_controller" in line and "active" in line for line in controllers.splitlines()):
        print("[OK] dsr_moveit_controller is active")
        return True
    print("MOVE_GROUP_NOT_READY")
    print("[FAIL] dsr_moveit_controller is not active")
    return False


class ObserveJointExecutor:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        os.environ.setdefault("ROS_LOG_DIR", "/tmp/ros2_logs")
        Path(os.environ["ROS_LOG_DIR"]).mkdir(parents=True, exist_ok=True)

        import rclpy
        from rclpy.node import Node

        if not rclpy.ok():
            rclpy.init(args=None)
        self.rclpy = rclpy
        self.node: Node = rclpy.create_node("azas_observe_cup_pose_only")
        self.moveit_py = None
        self.planning_component = None

    def shutdown(self) -> None:
        self.node.destroy_node()
        try:
            if self.rclpy.ok():
                self.rclpy.shutdown()
        except Exception:
            pass

    def execute_target(self, label: str, joint_degrees: dict[str, float]) -> bool:
        try:
            trajectory = self._plan_joint_target(label, joint_degrees)
        except Exception as exc:
            print(f"{label}_PLAN_FAILED")
            print(f"[FAIL] {label} planning failed: {exc}")
            return False
        try:
            self._execute_trajectory(label, trajectory)
        except Exception as exc:
            print(f"{label}_EXECUTE_FAILED")
            print(f"[FAIL] {label} ExecuteTrajectory failed: {exc}")
            return False
        return True

    def wait_for_target(self, label: str, joint_degrees: dict[str, float]) -> bool:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            error = self.joint_target_error(joint_degrees, timeout_sec=1.0)
            if error is not None:
                print(f"[INFO] {label} joint target max_error_rad={error:.6f}")
                if error <= JOINT_TARGET_TOLERANCE_RAD:
                    print(f"[OK] {label} joint state reached target")
                    return True
            time.sleep(0.2)
        error = self.joint_target_error(joint_degrees, timeout_sec=1.0)
        if error is None:
            print(f"[FAIL] {label} /joint_states did not contain all target joints")
        else:
            print(f"[FAIL] {label} max_error_rad={error:.6f}")
        return False

    def _init_moveit(self) -> None:
        from moveit.planning import MoveItPy

        self.moveit_py = MoveItPy(
            node_name="azas_observe_cup_pose_only_moveit",
            config_dict=moveit_config_dict("m0609", "dsr_moveit_config_m0609"),
            provide_planning_service=False,
        )
        time.sleep(2.0)
        self.planning_component = self.moveit_py.get_planning_component(
            self.args.planning_group
        )

    def _plan_joint_target(self, label: str, joint_degrees: dict[str, float]):
        from moveit.core.robot_state import RobotState
        from moveit.planning import PlanRequestParameters

        print_stage(f"PLAN_{label}", "MoveItPy joint target plan before ExecuteTrajectory")
        print_joint_target(label, joint_degrees)
        if self.moveit_py is None or self.planning_component is None:
            self._init_moveit()
        robot_model = self.moveit_py.get_robot_model()
        robot_state = RobotState(robot_model)
        robot_state.joint_positions = {
            name: math.radians(float(degrees))
            for name, degrees in joint_degrees.items()
        }
        robot_state.update()

        params = PlanRequestParameters(self.moveit_py)
        params.planning_time = float(self.args.planning_timeout_sec)
        params.planning_pipeline = "ompl"
        params.planner_id = "RRTConnectkConfigDefault"
        params.planning_attempts = 1
        params.max_velocity_scaling_factor = float(self.args.velocity_scale)
        params.max_acceleration_scaling_factor = float(self.args.accel_scale)
        self.planning_component.set_start_state_to_current_state()
        self.planning_component.set_goal_state(robot_state=robot_state)
        plan_result = self.planning_component.plan(params)
        if not plan_result:
            raise RuntimeError("plan_result was empty")
        trajectory = getattr(plan_result, "trajectory", None)
        if trajectory is None:
            raise RuntimeError("plan_result has no trajectory")
        if hasattr(trajectory, "get_robot_trajectory_msg"):
            trajectory = trajectory.get_robot_trajectory_msg()
        print(f"[OK] {label} joint target plan succeeded; trajectory ready")
        return trajectory

    def _execute_trajectory(self, label: str, trajectory: Any) -> None:
        from moveit_msgs.action import ExecuteTrajectory
        from rclpy.action import ActionClient

        print_stage(f"EXECUTE_{label}", self.args.execute_action_name)
        before_joints = self.read_joint_positions(timeout_sec=3.0)
        client = ActionClient(self.node, ExecuteTrajectory, self.args.execute_action_name)
        if not client.wait_for_server(timeout_sec=5.0):
            raise RuntimeError("ExecuteTrajectory action server unavailable")
        goal = ExecuteTrajectory.Goal()
        goal.trajectory = trajectory
        send_future = client.send_goal_async(goal)
        self.rclpy.spin_until_future_complete(self.node, send_future, timeout_sec=5.0)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            raise RuntimeError("ExecuteTrajectory goal rejected")
        result_future = goal_handle.get_result_async()
        self.rclpy.spin_until_future_complete(
            self.node,
            result_future,
            timeout_sec=float(self.args.action_timeout_sec),
        )
        result_wrapper = result_future.result()
        if result_wrapper is None:
            raise RuntimeError("ExecuteTrajectory timed out")
        error_code = getattr(result_wrapper.result.error_code, "val", None)
        if error_code != MOVEIT_SUCCESS:
            raise RuntimeError(f"MoveIt error_code={error_code}")
        after_joints = self.read_joint_positions(timeout_sec=3.0)
        max_delta = max_joint_delta(before_joints, after_joints)
        if max_delta is None:
            print(f"[WARN] {label} max_delta_rad could not be computed from /joint_states")
        else:
            print(f"[INFO] {label} max_delta_rad={max_delta:.6f}")
        print(f"[OK] {label} ExecuteTrajectory succeeded")

    def read_joint_positions(self, timeout_sec: float) -> list[float] | None:
        state = self.read_joint_state_map(timeout_sec=timeout_sec)
        if state is None:
            return None
        return [state[name] for name in sorted(state)]

    def read_joint_state_map(self, timeout_sec: float) -> dict[str, float] | None:
        from sensor_msgs.msg import JointState

        latest: dict[str, float] | None = None

        def callback(msg: JointState) -> None:
            nonlocal latest
            if msg.name and len(msg.name) == len(msg.position):
                latest = dict(zip(msg.name, msg.position))

        subscription = self.node.create_subscription(JointState, "/joint_states", callback, 10)
        deadline = time.monotonic() + timeout_sec
        try:
            while latest is None and time.monotonic() < deadline:
                self.rclpy.spin_once(self.node, timeout_sec=0.1)
            return latest
        finally:
            self.node.destroy_subscription(subscription)

    def joint_target_error(self, joint_degrees: dict[str, float], timeout_sec: float) -> float | None:
        current = self.read_joint_state_map(timeout_sec=timeout_sec)
        if current is None:
            return None
        errors: list[float] = []
        for name, degrees in joint_degrees.items():
            if name not in current:
                return None
            errors.append(abs(current[name] - math.radians(float(degrees))))
        return max(errors) if errors else None


def home_joint_target_degrees(args: argparse.Namespace) -> dict[str, float]:
    return {
        "joint_1": float(args.home_joint_1_deg),
        "joint_2": float(args.home_joint_2_deg),
        "joint_3": float(args.home_joint_3_deg),
        "joint_4": float(args.home_joint_4_deg),
        "joint_5": float(args.home_joint_5_deg),
        "joint_6": float(args.home_joint_6_deg),
    }


def observe_joint_target_degrees(args: argparse.Namespace) -> dict[str, float]:
    return {
        "joint_1": float(args.observe_joint_1_deg),
        "joint_2": float(args.observe_joint_2_deg),
        "joint_3": float(args.observe_joint_3_deg),
        "joint_4": float(args.observe_joint_4_deg),
        "joint_5": float(args.observe_joint_5_deg),
        "joint_6": float(args.observe_joint_6_deg),
    }


def moveit_config_dict(robot_model: str, moveit_config_package: str) -> dict[str, Any]:
    from moveit_configs_utils import MoveItConfigsBuilder

    config = (
        MoveItConfigsBuilder(robot_model, "robot_description", moveit_config_package)
        .robot_description(file_path=f"config/{robot_model}.urdf.xacro")
        .robot_description_semantic(file_path="config/dsr.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(
            pipelines=["ompl", "chomp", "pilz_industrial_motion_planner"],
            default_planning_pipeline="ompl",
            load_all=False,
        )
        .to_moveit_configs()
        .to_dict()
    )
    pipeline_names = config.get("planning_pipelines", ["ompl"])
    if isinstance(pipeline_names, list):
        config["planning_pipelines"] = {"pipeline_names": pipeline_names}
    config["plan_request_params"] = {
        "planning_attempts": 1,
        "planning_pipeline": "ompl",
        "planner_id": "RRTConnectkConfigDefault",
        "max_velocity_scaling_factor": 0.1,
        "max_acceleration_scaling_factor": 0.1,
        "planning_time": 1.0,
    }
    return config


def print_joint_target(label: str, joint_degrees: dict[str, float]) -> None:
    joint_radians = {
        name: math.radians(float(degrees))
        for name, degrees in joint_degrees.items()
    }
    print(f"{label.lower()}_joint_target_deg={json.dumps(joint_degrees, sort_keys=True)}")
    print(f"{label.lower()}_joint_target_rad={json.dumps(joint_radians, sort_keys=True)}")


def dry_run_only(args: argparse.Namespace) -> bool:
    return args.dry_run and not args.enable_real_motion


def countdown(seconds: int) -> None:
    print_stage("COUNTDOWN", f"waiting {seconds} seconds before continuing")
    for remaining in range(seconds, 0, -1):
        print(f"{remaining}...")
        time.sleep(1.0)


def print_stage(name: str, detail: str) -> None:
    print(f"\n=== {name} ===")
    print(detail)


def max_joint_delta(before: list[float] | None, after: list[float] | None) -> float | None:
    if before is None or after is None or len(before) != len(after):
        return None
    return max(abs(a - b) for a, b in zip(after, before))


def rclpy_graph_names(kind: str) -> list[str]:
    import rclpy

    initialized_here = False
    if not rclpy.ok():
        rclpy.init(args=None)
        initialized_here = True
    node = rclpy.create_node("azas_observe_graph_check")
    try:
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
    node = rclpy.create_node("azas_observe_action_check")
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
    try:
        return subprocess.run(command, **kwargs)
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return subprocess.CompletedProcess(command, 124, output)
    except FileNotFoundError:
        return subprocess.CompletedProcess(command, 127, "")


if __name__ == "__main__":
    raise SystemExit(main())
