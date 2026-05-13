from dataclasses import dataclass


@dataclass(frozen=True)
class CameraIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float


def pixel_depth_to_camera_point(
    u: int,
    v: int,
    depth_raw: float,
    intrinsics: CameraIntrinsics,
    depth_scale: float = 0.001,
) -> tuple[float, float, float]:
    """Project aligned depth pixel to camera-frame metric point."""
    if depth_raw <= 0:
        raise ValueError("depth_raw must be positive")
    if depth_scale <= 0:
        raise ValueError("depth_scale must be positive")

    z = depth_raw * depth_scale
    x = (u - intrinsics.cx) * z / intrinsics.fx
    y = (v - intrinsics.cy) * z / intrinsics.fy
    return x, y, z
