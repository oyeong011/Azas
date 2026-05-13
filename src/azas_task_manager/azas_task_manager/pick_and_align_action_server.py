import rclpy
from azas_interfaces.action import PickAndAlign
from rclpy.action import ActionServer
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


class PickAndAlignActionServer(Node):
    """MVP-1 orchestration boundary.

    The action owns sequence state only. Perception/calibration provide robot-frame
    poses, azas_motion plans/executes MoveItPy motions, and azas_gripper controls RG2.
    LLM/VLA output is intentionally excluded from coordinate generation.
    """

    def __init__(self):
        super().__init__("pick_and_align_action_server")
        self._server = ActionServer(
            self,
            PickAndAlign,
            "/azas/pick_and_align",
            self.execute_callback,
        )

    def execute_callback(self, goal_handle):
        feedback = PickAndAlign.Feedback()
        for state in PDF_PICK_PLACE_STATES:
            feedback.state = state
            feedback.detail = "skeleton state; subsystem execution pending"
            goal_handle.publish_feedback(feedback)

        result = PickAndAlign.Result()
        result.success = False
        result.error_code = "SKELETON_ONLY"
        result.message = (
            "PickAndAlign action contract is present, but calibrated perception, RG2, "
            "and MoveItPy execution are not yet connected."
        )
        goal_handle.succeed()
        return result


def main(args=None):
    rclpy.init(args=args)
    node = PickAndAlignActionServer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
