from dataclasses import dataclass

from geometry_msgs.msg import Point, Pose, Quaternion, Vector3


@dataclass(frozen=True)
class AlignmentConfig:
    outlet_clearance_m: float


def compute_alignment_tcp_pose(
    dispenser_outlet: Point,
    offset_tcp_to_cup_mouth: Vector3,
    orientation: Quaternion,
    config: AlignmentConfig,
) -> Pose:
    """Compute TCP pose so cup_mouth_center sits below dispenser_outlet.

    Inputs must be measured/calibrated. The function only applies the wiki equation;
    it does not define outlet coordinates, EE_LINK, GROUP_NAME, or TCP offset.
    """
    if config.outlet_clearance_m < 0.0:
        raise ValueError("outlet_clearance_m must be non-negative")

    pose = Pose()
    pose.position.x = dispenser_outlet.x - offset_tcp_to_cup_mouth.x
    pose.position.y = dispenser_outlet.y - offset_tcp_to_cup_mouth.y
    pose.position.z = (
        dispenser_outlet.z - config.outlet_clearance_m - offset_tcp_to_cup_mouth.z
    )
    pose.orientation = orientation
    return pose
