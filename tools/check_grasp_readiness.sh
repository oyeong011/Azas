#!/usr/bin/env bash
set -euo pipefail

# No-motion readiness check for the first real cup grasp attempt.
# This script does not launch hardware, command Doosan motion, or call RG2.
# It only verifies the evidence needed before a supervised grasp can be planned:
#   1. live cup detection stability,
#   2. camera/depth projection,
#   3. camera-frame to base_link TF evidence,
#   4. visible Doosan/RG2 service gates and measured config gate status.

EXPECT_CLASS="${EXPECT_CLASS:-cup}"
BASE_FRAME="${BASE_FRAME:-base_link}"
CAMERA_FRAME="${CAMERA_FRAME:-}"
ROS2_DAEMON_FLAG="${ROS2_DAEMON_FLAG:---no-daemon}"

ROOT="/home/ssu/Azas"

echo "[Azas] Grasp readiness check. No motion commands will be sent."
echo "[Azas] expect_class=${EXPECT_CLASS} base_frame=${BASE_FRAME} camera_frame=${CAMERA_FRAME:-<from CameraInfo>}"
echo

failures=0

run_step() {
  local label="$1"
  shift
  echo
  echo "== ${label} =="
  if "$@"; then
    echo "[PASS] ${label}"
  else
    echo "[FAIL] ${label}"
    failures=$((failures + 1))
  fi
}

run_step "depth projection sample" "${ROOT}/tools/check_depth_projection_sample.sh"
run_step "cup detection stability" "${ROOT}/tools/check_detection_stability.sh" --expect-class "${EXPECT_CLASS}"

if [[ -n "${CAMERA_FRAME}" ]]; then
  run_step "camera-to-base TF readiness" env \
    BASE_FRAME="${BASE_FRAME}" CAMERA_FRAME="${CAMERA_FRAME}" ROS2_DAEMON_FLAG="${ROS2_DAEMON_FLAG}" \
    "${ROOT}/tools/check_hand_eye_readiness.sh"
else
  run_step "camera-to-base TF readiness" env \
    BASE_FRAME="${BASE_FRAME}" ROS2_DAEMON_FLAG="${ROS2_DAEMON_FLAG}" \
    "${ROOT}/tools/check_hand_eye_readiness.sh"
fi

run_step "connection/service/config stage" env \
  ROS2_DAEMON_FLAG="${ROS2_DAEMON_FLAG}" "${ROOT}/tools/check_connection_stage.sh"

echo
echo "[Azas] Result: failures=${failures}"
if [[ "${failures}" -ne 0 ]]; then
  echo "[Azas] NOT READY TO GRASP: fix the failed no-motion gates before any real pick."
  exit 1
fi

echo "[Azas] READY FOR SUPERVISED GRASP PLANNING: live cup pose is in ${BASE_FRAME} and gates are visible."
