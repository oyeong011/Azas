import rclpy
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
    """MoveItPy boundary skeleton for the PDF pick-and-place sequence.

    This node intentionally does not contain confirmed EE_LINK/GROUP_NAME/outlet/TCP
    constants. Those must come from MoveIt config and calibration YAML after hardware
    verification.
    """

    def __init__(self):
        super().__init__("alignment_executor_node")
        self.declare_parameter("planning_group", "확인 필요")
        self.declare_parameter("ee_link", "확인 필요")
        self.get_logger().warn(
            "MoveItPy execution pending confirmed planning_group, EE_LINK, "
            "gripper_tcp, dispenser_outlet, and cup offset. Required sequence: "
            + " -> ".join(PDF_PICK_PLACE_STATES)
        )


def main(args=None):
    rclpy.init(args=args)
    node = AlignmentExecutorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
