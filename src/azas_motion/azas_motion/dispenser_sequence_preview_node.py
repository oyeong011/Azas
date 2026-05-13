#!/usr/bin/env python3
"""RViz-only dispenser sequence preview for Azas package structure.

This node is deliberately hardware-free. It subscribes to a base_link cup pose,
builds a readable sequential path, and publishes RViz markers plus a Path for
the optional IK preview node. It does not call MoveIt execution, Doosan
services, gripper services, or camera APIs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import rclpy
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion, Vector3
from nav_msgs.msg import Path
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from visualization_msgs.msg import Marker, MarkerArray


XYZ = Tuple[float, float, float]
RGBA = Tuple[float, float, float, float]


@dataclass(frozen=True)
class SequenceStep:
    label: str
    xyz: XYZ


def point(xyz: XYZ) -> Point:
    return Point(x=float(xyz[0]), y=float(xyz[1]), z=float(xyz[2]))


def quat_identity() -> Quaternion:
    return Quaternion(x=0.0, y=0.0, z=0.0, w=1.0)


def pose(xyz: XYZ, quat: Quaternion | None = None) -> Pose:
    msg = Pose()
    msg.position = point(xyz)
    msg.orientation = quat if quat is not None else quat_identity()
    return msg


def triples(values: Sequence[float]) -> List[XYZ]:
    if len(values) % 3 != 0:
        raise ValueError("flat XYZ array length must be a multiple of 3")
    return [
        (float(values[i]), float(values[i + 1]), float(values[i + 2]))
        for i in range(0, len(values), 3)
    ]


class DispenserSequencePreviewNode(Node):
    def __init__(self) -> None:
        super().__init__("dispenser_sequence_preview_node")
        self.declare_parameter("cup_pose_topic", "/azas/sim/tumbler_pose")
        self.declare_parameter("frame_id", "base_link")
        self.declare_parameter("selected_dispenser_id", 2)
        self.declare_parameter("cup_height_m", 0.17)
        self.declare_parameter("grasp_height_m", 0.085)
        self.declare_parameter("side_pre_grasp_offset_m", 0.10)
        self.declare_parameter("approach_height_m", 0.06)
        self.declare_parameter("shake_clearance_m", 0.13)
        self.declare_parameter("shake_swing_m", 0.075)
        self.declare_parameter("shake_lift_m", 0.055)
        self.declare_parameter("outlet_mouth_clearance_m", 0.0)
        self.declare_parameter("publish_rate_hz", 4.0)
        self.declare_parameter(
            "dispenser_bottle_positions",
            [
                0.55,
                0.18,
                0.1375,
                0.55,
                0.08,
                0.1375,
                0.55,
                -0.02,
                0.1375,
                0.55,
                -0.12,
                0.1375,
            ],
        )
        self.declare_parameter(
            "dispenser_outlet_positions",
            [
                0.43,
                0.18,
                0.392,
                0.43,
                0.08,
                0.392,
                0.43,
                -0.02,
                0.392,
                0.43,
                -0.12,
                0.392,
            ],
        )

        plan_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.path_pub = self.create_publisher(Path, "/azas/dispenser_sequence/plan", plan_qos)
        self.marker_pub = self.create_publisher(
            MarkerArray, "/azas/dispenser_sequence/markers", 10
        )
        self.target_pub = self.create_publisher(
            PoseStamped, "/azas/dispenser_sequence/target_pose", plan_qos
        )
        self.last_cup_pose: PoseStamped | None = None
        self.create_subscription(
            PoseStamped,
            str(self.get_parameter("cup_pose_topic").value),
            self.on_cup_pose,
            10,
        )
        period = 1.0 / max(float(self.get_parameter("publish_rate_hz").value), 0.2)
        self.create_timer(period, self.publish_preview)
        self.get_logger().info(
            "Azas RViz dispenser sequence preview ready; hardware and camera execution are disabled."
        )

    def on_cup_pose(self, msg: PoseStamped) -> None:
        expected = str(self.get_parameter("frame_id").value)
        if msg.header.frame_id != expected:
            self.get_logger().error(
                f"Rejected cup pose frame={msg.header.frame_id!r}; expected {expected!r}"
            )
            return
        self.last_cup_pose = msg

    def dispenser_layout(self) -> tuple[List[XYZ], List[XYZ], int]:
        bottles = triples(self.get_parameter("dispenser_bottle_positions").value)
        outlets = triples(self.get_parameter("dispenser_outlet_positions").value)
        if len(bottles) != len(outlets):
            raise ValueError("bottle/outlet count mismatch")
        selected = min(
            max(int(self.get_parameter("selected_dispenser_id").value), 1),
            len(outlets),
        )
        return bottles, outlets, selected - 1

    def build_steps(self, cup_pose: PoseStamped) -> List[SequenceStep]:
        _, outlets, selected_index = self.dispenser_layout()
        cup = cup_pose.pose.position
        cup_base = (float(cup.x), float(cup.y), float(cup.z))
        outlet = outlets[selected_index]
        cup_height = float(self.get_parameter("cup_height_m").value)
        grasp_height = float(self.get_parameter("grasp_height_m").value)
        side_offset = float(self.get_parameter("side_pre_grasp_offset_m").value)
        approach_height = float(self.get_parameter("approach_height_m").value)
        outlet_clearance = float(self.get_parameter("outlet_mouth_clearance_m").value)
        shake_clearance = float(self.get_parameter("shake_clearance_m").value)
        shake_swing = float(self.get_parameter("shake_swing_m").value)
        shake_lift = float(self.get_parameter("shake_lift_m").value)

        grasp = (cup_base[0], cup_base[1], cup_base[2] + grasp_height)
        side_pre_grasp = (grasp[0], grasp[1] - side_offset, grasp[2])
        target_base_z = outlet[2] - cup_height - outlet_clearance
        target_grasp = (outlet[0], outlet[1], target_base_z + grasp_height)
        pre_target = (target_grasp[0], target_grasp[1], target_grasp[2] + approach_height)
        shake_z = max(pre_target[2] + shake_clearance, grasp[2] + 0.24)
        lift = (grasp[0], grasp[1], shake_z)
        shake_left = (lift[0], lift[1] + shake_swing, lift[2] + shake_lift)
        shake_right = (lift[0], lift[1] - shake_swing, lift[2] - shake_lift * 0.45)
        shake_forward = (lift[0] + 0.045, lift[1], lift[2] + shake_lift * 0.75)
        shake_back = (lift[0] - 0.035, lift[1], lift[2] - shake_lift * 0.35)
        front_lane = (outlet[0] - 0.12, grasp[1], lift[2])
        front_of_outlet = (outlet[0] - 0.12, outlet[1], lift[2])

        return [
            SequenceStep("1 side_pre_grasp", side_pre_grasp),
            SequenceStep("2 side_grasp", grasp),
            SequenceStep("3 lift_high", lift),
            SequenceStep("4 shake_high_left", shake_left),
            SequenceStep("5 shake_high_right", shake_right),
            SequenceStep("6 shake_high_forward", shake_forward),
            SequenceStep("7 shake_high_back", shake_back),
            SequenceStep("8 shake_recenter", lift),
            SequenceStep("9 move_to_front_lane", front_lane),
            SequenceStep("10 front_of_dispenser", front_of_outlet),
            SequenceStep("11 mouth_under_outlet", pre_target),
            SequenceStep("12 dispense_alignment", target_grasp),
            SequenceStep("13 retreat", pre_target),
        ]

    def publish_preview(self) -> None:
        if self.last_cup_pose is None:
            return
        steps = self.build_steps(self.last_cup_pose)
        now = self.get_clock().now().to_msg()
        frame_id = str(self.get_parameter("frame_id").value)

        path = Path()
        path.header.stamp = now
        path.header.frame_id = frame_id
        for step in steps:
            stamped = PoseStamped()
            stamped.header = path.header
            stamped.pose = pose(step.xyz)
            path.poses.append(stamped)
        self.path_pub.publish(path)
        self.target_pub.publish(path.poses[-2])
        self.marker_pub.publish(self.make_markers(steps, now, frame_id))

    def marker(
        self,
        marker_id: int,
        marker_type: int,
        ns: str,
        xyz: XYZ,
        scale: Vector3,
        color: RGBA,
    ) -> Marker:
        marker = Marker()
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.header.frame_id = str(self.get_parameter("frame_id").value)
        marker.ns = ns
        marker.id = marker_id
        marker.type = marker_type
        marker.action = Marker.ADD
        marker.pose = pose(xyz)
        marker.scale = scale
        marker.color.r, marker.color.g, marker.color.b, marker.color.a = color
        return marker

    def make_markers(self, steps: Sequence[SequenceStep], stamp, frame_id: str) -> MarkerArray:
        markers: List[Marker] = []
        bottles, outlets, selected_index = self.dispenser_layout()
        for index, bottle in enumerate(bottles, start=1):
            selected = index - 1 == selected_index
            markers.append(
                self.marker(
                    100 + index,
                    Marker.CUBE,
                    "dispenser_bottle",
                    bottle,
                    Vector3(x=0.058, y=0.058, z=0.275),
                    (0.82, 0.96, 1.0, 0.38 if selected else 0.18),
                )
            )
            outlet = outlets[index - 1]
            markers.append(
                self.marker(
                    120 + index,
                    Marker.SPHERE,
                    "dispenser_outlet",
                    outlet,
                    Vector3(x=0.024, y=0.024, z=0.024),
                    (1.0, 0.85, 0.0, 1.0 if selected else 0.55),
                )
            )
            arrow = self.marker(
                140 + index,
                Marker.ARROW,
                "dispenser_faces_robot",
                (0.0, 0.0, 0.0),
                Vector3(x=0.012, y=0.020, z=0.020),
                (1.0, 0.85, 0.0, 1.0 if selected else 0.45),
            )
            arrow.points = [point(outlet), point((outlet[0] - 0.08, outlet[1], outlet[2]))]
            markers.append(arrow)

        line = self.marker(
            1,
            Marker.LINE_STRIP,
            "sequence_path",
            (0.0, 0.0, 0.0),
            Vector3(x=0.012, y=0.0, z=0.0),
            (0.8, 0.1, 1.0, 1.0),
        )
        line.points = [point(step.xyz) for step in steps]
        markers.append(line)

        for index, step in enumerate(steps, start=1):
            markers.append(
                self.marker(
                    10 + index,
                    Marker.SPHERE,
                    "sequence_waypoints",
                    step.xyz,
                    Vector3(x=0.026, y=0.026, z=0.026),
                    (0.8, 0.1, 1.0, 1.0),
                )
            )
            label = self.marker(
                30 + index,
                Marker.TEXT_VIEW_FACING,
                "sequence_labels",
                (step.xyz[0], step.xyz[1], step.xyz[2] + 0.04),
                Vector3(x=0.0, y=0.0, z=0.028),
                (1.0, 1.0, 1.0, 1.0),
            )
            label.text = step.label
            markers.append(label)

        status = self.marker(
            2,
            Marker.TEXT_VIEW_FACING,
            "preview_status",
            (0.18, 0.32, 0.46),
            Vector3(x=0.0, y=0.0, z=0.033),
            (0.2, 1.0, 0.35, 1.0),
        )
        status.text = "Azas RViz preview: side grasp -> high shake above obstacles -> dispenser alignment"
        markers.append(status)

        for marker in markers:
            marker.header.stamp = stamp
            marker.header.frame_id = frame_id
        return MarkerArray(markers=markers)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DispenserSequencePreviewNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
