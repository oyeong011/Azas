import rclpy
from azas_interfaces.msg import GraspCandidate, GraspCandidateArray
from geometry_msgs.msg import PoseArray
from rclpy.node import Node


class ExternalGraspAdapterNode(Node):
    """Adapter boundary for external grasp generators.

    External packages such as AnyGrasp may publish or return grasp poses, but
    they must not command Azas motion directly. This adapter converts a simple
    PoseArray into the Azas GraspCandidateArray contract so downstream code can
    apply TF, workspace, collision, and gripper checks before planning.
    """

    def __init__(self):
        super().__init__("external_grasp_adapter_node")
        self.declare_parameter("input_pose_array_topic", "/external/grasp_poses")
        self.declare_parameter("source", "external_grasp_generator")
        input_topic = self.get_parameter("input_pose_array_topic").value
        self.source = self.get_parameter("source").value
        self.publisher = self.create_publisher(
            GraspCandidateArray, "/azas/grasp_candidates", 10
        )
        self.create_subscription(PoseArray, input_topic, self.on_pose_array, 10)
        self.get_logger().warn(
            "External grasp adapter publishes candidates only; motion requires TF, "
            "workspace, collision, and MoveIt checks."
        )

    def on_pose_array(self, msg: PoseArray) -> None:
        output = GraspCandidateArray()
        output.header = msg.header
        output.source = self.source
        output.status = "unverified_external_candidates"
        for index, pose in enumerate(msg.poses):
            candidate = GraspCandidate()
            candidate.header = msg.header
            candidate.pose = pose
            candidate.score = 0.0
            candidate.source = self.source
            candidate.external_id = str(index)
            candidate.status = "requires_tf_workspace_collision_gripper_checks"
            output.candidates.append(candidate)
        self.publisher.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = ExternalGraspAdapterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
