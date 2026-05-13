import rclpy
from azas_interfaces.msg import CupDetection
from geometry_msgs.msg import Pose
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo


class TumblerDetectorNode(Node):
    """Placeholder detector boundary for depth-camera tumbler detection.

    Real detections must be computed from color/depth/CameraInfo plus TF. This
    placeholder publishes confidence 0.0 so downstream code cannot treat it as a
    valid robot target.
    """

    def __init__(self):
        super().__init__("tumbler_detector_node")
        self.publisher = self.create_publisher(CupDetection, "/azas/cup_detection", 10)
        self.declare_parameter("camera_info_topic", "/camera/color/camera_info")
        topic = self.get_parameter("camera_info_topic").value
        self.create_subscription(CameraInfo, topic, self.on_info, 10)
        self.get_logger().warn(
            "Tumbler detector is a boundary skeleton: camera topics/frame/depth scale require confirmation."
        )

    def on_info(self, msg: CameraInfo) -> None:
        cup = CupDetection()
        cup.header.stamp = self.get_clock().now().to_msg()
        cup.header.frame_id = msg.header.frame_id or "확인 필요"
        cup.grasp_pose = Pose()
        cup.cup_mouth_center = Pose()
        cup.confidence = 0.0
        cup.status = "확인 필요: detector not implemented"
        cup.source = "placeholder_waiting_for_depth_pipeline"
        self.publisher.publish(cup)


def main(args=None):
    rclpy.init(args=args)
    node = TumblerDetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
