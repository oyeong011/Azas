import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node


PDF_PICK_PLACE_STATES = (
    "HOME",
    "pick_approach",
    "pick",
    "pick_approach",
    "place_approach",
    "place",
    "place_approach",
)


class AlignmentExecutorNode(Node):
    """Planning-only MoveIt boundary for pose feasibility checks.

    This node intentionally does not contain confirmed EE_LINK/GROUP_NAME/outlet/TCP
    constants. Those must come from MoveIt config and calibration YAML after hardware
    verification.
    """

    def __init__(self):
        super().__init__("alignment_executor_node")
        self.declare_parameter("enable_planning_only", True)
        self.declare_parameter("allow_execute", False)
        self.declare_parameter("planning_group", "")
        self.declare_parameter("ee_link", "")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("approach_pose_topic", "")
        self.declare_parameter("grasp_pose_topic", "")
        self.declare_parameter("lift_pose_topic", "")
        self.declare_parameter("planning_timeout_sec", 5.0)
        self._approach_pose = None
        self._grasp_pose = None
        self._lift_pose = None
        self._configure_pose_subscriptions()
        self.get_logger().warn(
            "AlignmentExecutorNode is planning-only by default. It does not command "
            "Doosan motion, MoveIt execution, or RG2 hardware. Required sequence: "
            + " -> ".join(PDF_PICK_PLACE_STATES)
        )
        self.create_timer(1.0, self._report_planning_only_readiness)

    def _configure_pose_subscriptions(self) -> None:
        topics = (
            ("approach", "approach_pose_topic", self._on_approach_pose),
            ("grasp", "grasp_pose_topic", self._on_grasp_pose),
            ("lift", "lift_pose_topic", self._on_lift_pose),
        )
        for label, parameter_name, callback in topics:
            topic = str(self.get_parameter(parameter_name).value).strip()
            if not topic:
                self.get_logger().info(
                    f"No {label} pose topic configured; planning-only checker will wait idle"
                )
                continue
            self.create_subscription(PoseStamped, topic, callback, 10)
            self.get_logger().info(f"Subscribed to {label} pose topic for planning-only: {topic}")

    def _on_approach_pose(self, msg: PoseStamped) -> None:
        self._approach_pose = msg

    def _on_grasp_pose(self, msg: PoseStamped) -> None:
        self._grasp_pose = msg

    def _on_lift_pose(self, msg: PoseStamped) -> None:
        self._lift_pose = msg

    def _report_planning_only_readiness(self) -> None:
        if not bool(self.get_parameter("enable_planning_only").value):
            self.get_logger().warn("Planning-only checker disabled; no motion is commanded")
            return
        if bool(self.get_parameter("allow_execute").value):
            self.get_logger().error(
                "allow_execute=true is refused in this Azas planning-only boundary; "
                "no MoveIt execution or Doosan command is available here"
            )
            return

        planning_group = str(self.get_parameter("planning_group").value).strip()
        ee_link = str(self.get_parameter("ee_link").value).strip()
        base_frame = str(self.get_parameter("base_frame").value).strip()
        if not planning_group or not ee_link:
            self.get_logger().error(
                "Planning-only fail-closed: planning_group and ee_link must be set. "
                f"Current planning_group={planning_group!r}, ee_link={ee_link!r}. "
                "Source /opt/ros/humble/setup.bash and install/setup.bash, then pass "
                "verified MoveIt config values."
            )
            return
        if not base_frame:
            self.get_logger().error("Planning-only fail-closed: base_frame must be set")
            return

        moveit_ok, moveit_message = self._check_moveitpy_available()
        if not moveit_ok:
            self.get_logger().error(
                "Planning-only fail-closed: MoveItPy import failed. "
                f"{moveit_message}. Try: source /opt/ros/humble/setup.bash; "
                "source /home/ssu/Azas/install/setup.bash"
            )
            return

        if None in (self._approach_pose, self._grasp_pose, self._lift_pose):
            self.get_logger().warn(
                "Planning-only checker ready but waiting for approach/grasp/lift PoseStamped "
                "topics. No execution path exists in this node."
            )
            return

        self.get_logger().warn(
            "MoveItPy import is available, but planning request construction is not connected "
            "in this safety batch. approach/grasp/lift poses are held for planning-only "
            "integration; no execute call exists."
        )

    @staticmethod
    def _check_moveitpy_available() -> tuple[bool, str]:
        try:
            from moveit.planning import MoveItPy  # noqa: F401
        except Exception as exc:  # pragma: no cover - environment dependent
            return False, str(exc)
        return True, "MoveItPy import available"


def main(args=None):
    rclpy.init(args=args)
    node = AlignmentExecutorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
