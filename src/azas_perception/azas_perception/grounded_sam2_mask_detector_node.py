from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
import rclpy
from azas_interfaces.msg import CupDetection
from cv_bridge import CvBridge
from geometry_msgs.msg import Pose
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image

from azas_perception.depth_projection import CameraIntrinsics, pixel_depth_to_camera_point


class GroundedSam2MaskDetectorNode(Node):
    """Convert Grounded-SAM2 segmentation masks into Azas CupDetection messages.

    The heavy open-vocabulary model is intentionally kept outside this node. A
    GroundingDINO+SAM2/Grounded-SAM-2 runner publishes a binary tumbler mask;
    this adapter fuses that mask with aligned depth and CameraInfo so downstream
    Azas nodes can keep using the stable /azas/cup_detection contract.
    """

    def __init__(self):
        super().__init__("grounded_sam2_mask_detector_node")
        self.declare_parameter("mask_topic", "/grounded_sam2/tumbler_mask")
        self.declare_parameter("depth_topic", "/camera/aligned_depth_to_color/image_raw")
        self.declare_parameter("camera_info_topic", "/camera/color/camera_info")
        self.declare_parameter("depth_scale", 0.001)
        self.declare_parameter("mask_threshold", 1)
        self.declare_parameter("min_mask_pixels", 80)
        self.declare_parameter("cup_height_m", 0.17)
        self.declare_parameter("default_confidence", 0.75)
        self.declare_parameter("target_prompt", "tumbler cup")
        self.declare_parameter("source", "grounded_sam2_mask_detector")

        self._bridge = CvBridge()
        self._latest_depth: Optional[np.ndarray] = None
        self._latest_info: Optional[CameraInfo] = None

        self._pub = self.create_publisher(CupDetection, "/azas/cup_detection", 10)
        self.create_subscription(Image, str(self.get_parameter("mask_topic").value), self._on_mask, 10)
        self.create_subscription(Image, str(self.get_parameter("depth_topic").value), self._on_depth, 10)
        self.create_subscription(
            CameraInfo,
            str(self.get_parameter("camera_info_topic").value),
            self._on_camera_info,
            10,
        )
        self.get_logger().info("Grounded-SAM2 mask detector adapter ready")

    def _on_depth(self, msg: Image) -> None:
        try:
            self._latest_depth = self._bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as exc:
            self.get_logger().error(f"depth conversion failed: {exc}")

    def _on_camera_info(self, msg: CameraInfo) -> None:
        self._latest_info = msg

    def _on_mask(self, msg: Image) -> None:
        if self._latest_depth is None or self._latest_info is None:
            self._publish_invalid(msg, "waiting_for_depth_and_camera_info")
            return

        try:
            mask_image = self._bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as exc:
            self.get_logger().error(f"mask conversion failed: {exc}")
            self._publish_invalid(msg, "mask_conversion_failed")
            return

        component = self._largest_valid_component(mask_image)
        if component is None:
            self._publish_invalid(msg, "no_valid_tumbler_mask")
            return

        center_u, center_v, pixel_count, component_mask = component
        depth_raw = self._median_depth(component_mask)
        if depth_raw is None:
            self._publish_invalid(msg, "invalid_depth_inside_mask")
            return

        info = self._latest_info
        intrinsics = CameraIntrinsics(fx=info.k[0], fy=info.k[4], cx=info.k[2], cy=info.k[5])
        try:
            x, y, z = pixel_depth_to_camera_point(
                center_u,
                center_v,
                depth_raw,
                intrinsics,
                float(self.get_parameter("depth_scale").value),
            )
        except ValueError:
            self._publish_invalid(msg, "invalid_projected_depth")
            return

        output = CupDetection()
        output.header.stamp = msg.header.stamp
        output.header.frame_id = info.header.frame_id or msg.header.frame_id
        output.grasp_pose = self._pose_at(x, y, z)
        output.cup_mouth_center = self._pose_at(x, y, z + float(self.get_parameter("cup_height_m").value))
        output.confidence = float(self.get_parameter("default_confidence").value)
        output.status = (
            f"detected:grounded_sam2 prompt={self.get_parameter('target_prompt').value!r} "
            f"mask_pixels={pixel_count} depth_raw={depth_raw:.1f}"
        )
        output.source = str(self.get_parameter("source").value)
        self._pub.publish(output)

    def _largest_valid_component(self, mask_image: np.ndarray) -> Optional[tuple[int, int, int, np.ndarray]]:
        mask = np.asarray(mask_image)
        if mask.ndim == 3:
            mask = mask[:, :, 0]
        binary = (mask > int(self.get_parameter("mask_threshold").value)).astype(np.uint8)
        min_pixels = int(self.get_parameter("min_mask_pixels").value)
        if int(binary.sum()) < min_pixels:
            return None

        count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        if count <= 1:
            return None

        best_label = 0
        best_area = 0
        for label in range(1, count):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if area > best_area:
                best_label = label
                best_area = area
        if best_area < min_pixels:
            return None

        center_u = int(round(float(centroids[best_label][0])))
        center_v = int(round(float(centroids[best_label][1])))
        return center_u, center_v, best_area, labels == best_label

    def _median_depth(self, component_mask: np.ndarray) -> Optional[float]:
        depth = self._latest_depth
        if depth is None or depth.size == 0:
            return None
        if component_mask.shape != depth.shape[:2]:
            self.get_logger().warn(
                f"mask/depth shape mismatch: mask={component_mask.shape} depth={depth.shape[:2]}"
            )
            return None
        depth_values = np.asarray(depth, dtype=np.float32)[component_mask]
        valid = depth_values[np.isfinite(depth_values) & (depth_values > 0)]
        if valid.size == 0:
            return None
        return float(np.median(valid))

    def _publish_invalid(self, msg: Image, status: str) -> None:
        output = CupDetection()
        output.header.stamp = msg.header.stamp
        output.header.frame_id = msg.header.frame_id
        output.grasp_pose = Pose()
        output.cup_mouth_center = Pose()
        output.confidence = 0.0
        output.status = status
        output.source = str(self.get_parameter("source").value)
        self._pub.publish(output)

    @staticmethod
    def _pose_at(x: float, y: float, z: float) -> Pose:
        pose = Pose()
        pose.position.x = x
        pose.position.y = y
        pose.position.z = z
        pose.orientation.w = 1.0
        return pose


def main(args=None):
    rclpy.init(args=args)
    node = GroundedSam2MaskDetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
