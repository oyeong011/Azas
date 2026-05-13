from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

try:
    from lang_sam import LangSAM
    from PIL import Image as PilImage
except ImportError:  # pragma: no cover - depends on deployment environment
    LangSAM = None
    PilImage = None


class GroundedSam2TumblerMaskNode(Node):
    """Run an open-vocabulary segmentation model and publish a tumbler mask.

    This node is the model-facing half of the replacement vision path. It turns
    camera RGB images into a mono8 mask; `grounded_sam2_mask_detector_node` then
    fuses that mask with depth and CameraInfo to produce Azas `CupDetection`.
    """

    def __init__(self):
        super().__init__("grounded_sam2_tumbler_mask_node")
        self.declare_parameter("color_topic", "/camera/color/image_raw")
        self.declare_parameter("mask_topic", "/grounded_sam2/tumbler_mask")
        self.declare_parameter("prompt", "tumbler cup")
        self.declare_parameter("min_score", 0.25)
        self.declare_parameter("publish_empty_on_failure", True)

        self._bridge = CvBridge()
        self._model = self._load_model()
        self._pub = self.create_publisher(Image, str(self.get_parameter("mask_topic").value), 10)
        self.create_subscription(Image, str(self.get_parameter("color_topic").value), self._on_color, 10)
        self.get_logger().info("Grounded-SAM/SAM2 tumbler mask runner ready")

    def _load_model(self):
        if LangSAM is None or PilImage is None:
            self.get_logger().error(
                "lang-sam is not installed; install a Grounded-SAM/SAM2 runner before live mask inference"
            )
            return None
        try:
            return LangSAM()
        except Exception as exc:
            self.get_logger().error(f"failed to load Grounded-SAM model: {exc}")
            return None

    def _on_color(self, msg: Image) -> None:
        if self._model is None:
            self._publish_empty_if_enabled(msg, "model_not_loaded")
            return

        try:
            bgr = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().error(f"color conversion failed: {exc}")
            self._publish_empty_if_enabled(msg, "color_conversion_failed")
            return

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        prompt = str(self.get_parameter("prompt").value)
        try:
            mask = self._predict_best_mask(rgb, prompt)
        except Exception as exc:
            self.get_logger().error(f"Grounded-SAM inference failed: {exc}")
            self._publish_empty_if_enabled(msg, "inference_failed")
            return

        if mask is None:
            self._publish_empty_if_enabled(msg, "no_prompt_mask")
            return

        output = self._bridge.cv2_to_imgmsg(mask, encoding="mono8")
        output.header = msg.header
        self._pub.publish(output)

    def _predict_best_mask(self, rgb: np.ndarray, prompt: str) -> Optional[np.ndarray]:
        if PilImage is None:
            return None
        pil_image = PilImage.fromarray(rgb)
        prediction = self._model.predict(pil_image, prompt)
        masks, scores = self._extract_masks_and_scores(prediction)
        if masks.size == 0:
            return None

        min_score = float(self.get_parameter("min_score").value)
        best_index = 0
        best_score = -1.0
        for index, score in enumerate(scores):
            if score > best_score:
                best_index = index
                best_score = score
        if best_score < min_score:
            return None

        mask = np.asarray(masks[best_index])
        if mask.ndim > 2:
            mask = mask.squeeze()
        return np.where(mask > 0, 255, 0).astype(np.uint8)

    def _extract_masks_and_scores(self, prediction) -> tuple[np.ndarray, list[float]]:
        if isinstance(prediction, dict):
            masks_value = prediction.get("masks", [])
            scores_value = prediction.get("scores", prediction.get("logits", []))
        elif isinstance(prediction, tuple):
            masks_value = prediction[0] if len(prediction) > 0 else []
            scores_value = prediction[3] if len(prediction) > 3 else []
        else:
            masks_value = getattr(prediction, "masks", [])
            scores_value = getattr(prediction, "scores", getattr(prediction, "logits", []))

        masks = self._to_numpy(masks_value)
        raw_scores = self._to_numpy(scores_value).reshape(-1)
        scores = [float(score) for score in raw_scores.tolist()]
        if not scores and masks.ndim >= 3:
            scores = [1.0 for _ in range(masks.shape[0])]
        if masks.ndim == 2:
            masks = masks.reshape(1, masks.shape[0], masks.shape[1])
        return masks, scores

    @staticmethod
    def _to_numpy(value) -> np.ndarray:
        if hasattr(value, "detach"):
            value = value.detach()
        if hasattr(value, "cpu"):
            value = value.cpu()
        if hasattr(value, "numpy"):
            return np.asarray(value.numpy())
        return np.asarray(value)

    def _publish_empty_if_enabled(self, msg: Image, reason: str) -> None:
        if not bool(self.get_parameter("publish_empty_on_failure").value):
            return
        height = int(msg.height)
        width = int(msg.width)
        empty = np.zeros((height, width), dtype=np.uint8)
        output = self._bridge.cv2_to_imgmsg(empty, encoding="mono8")
        output.header = msg.header
        self._pub.publish(output)
        self.get_logger().warn(f"published empty mask: {reason}")


def main(args=None):
    rclpy.init(args=args)
    node = GroundedSam2TumblerMaskNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
