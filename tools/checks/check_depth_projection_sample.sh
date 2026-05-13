#!/usr/bin/env bash
set -euo pipefail

# Live camera depth-projection gate. This does not command robot motion.

DEPTH_TOPIC="${DEPTH_TOPIC:-/camera/aligned_depth_to_color/image_raw}"
CAMERA_INFO_TOPIC="${CAMERA_INFO_TOPIC:-/camera/color/camera_info}"
TIMEOUT="${TIMEOUT:-10.0}"
PATCH_RADIUS="${PATCH_RADIUS:-3}"

set +u
source /opt/ros/humble/setup.bash
source /home/ssu/Azas/install/setup.bash
set -u

exec python3 /home/ssu/Azas/tools/checks/check_depth_projection_sample.py \
  --depth-topic "${DEPTH_TOPIC}" \
  --camera-info-topic "${CAMERA_INFO_TOPIC}" \
  --timeout "${TIMEOUT}" \
  --patch-radius "${PATCH_RADIUS}"

