#!/usr/bin/env bash
set -euo pipefail

# Code-only cup grasp pipeline smoke:
# simulated CupDetection -> pose bridge -> tumbler floor-place dry-run plan.
# This does NOT start RealSense, YOLO, RG2, Doosan, MoveIt execution, or hardware services.

STATUS_FILE="${STATUS_FILE:-/tmp/azas_code_only_cup_grasp_status.txt}"
PLAN_FILE="${PLAN_FILE:-/tmp/azas_code_only_cup_grasp_plan.txt}"
LOG_FILE="${LOG_FILE:-/tmp/azas_code_only_cup_grasp_launch.log}"
SELECTED_DISPENSER_ID="${SELECTED_DISPENSER_ID:-2}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/azas_ros_logs}"

case "${SELECTED_DISPENSER_ID}" in
  1) EXPECTED_PLACE_Y="0.035" ;;
  2) EXPECTED_PLACE_Y="-0.065" ;;
  3) EXPECTED_PLACE_Y="-0.165" ;;
  4) EXPECTED_PLACE_Y="-0.265" ;;
  *)
    echo "[FAIL] unsupported SELECTED_DISPENSER_ID=${SELECTED_DISPENSER_ID}"
    exit 1
    ;;
esac

rm -f "${STATUS_FILE}" "${PLAN_FILE}" "${LOG_FILE}"
mkdir -p "${ROS_LOG_DIR}"

set +u
source /opt/ros/humble/setup.bash
source /home/ssu/Azas/install/setup.bash
source /home/ssu/ros2_ws/install/setup.bash 2>/dev/null || true
set -u

cleanup() {
  if [[ -n "${LAUNCH_PID:-}" ]] && kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    kill "${LAUNCH_PID}" 2>/dev/null || true
    wait "${LAUNCH_PID}" 2>/dev/null || true
  fi
  if [[ -n "${STATUS_PID:-}" ]] && kill -0 "${STATUS_PID}" 2>/dev/null; then
    kill "${STATUS_PID}" 2>/dev/null || true
    wait "${STATUS_PID}" 2>/dev/null || true
  fi
  if [[ -n "${PLAN_PID:-}" ]] && kill -0 "${PLAN_PID}" 2>/dev/null; then
    kill "${PLAN_PID}" 2>/dev/null || true
    wait "${PLAN_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

assert_log_contains() {
  local pattern="$1"
  local description="$2"
  if grep -Eq "$pattern" "${LOG_FILE}"; then
    echo "[OK] ${description}"
    return 0
  fi
  echo "[FAIL] missing expected plan evidence: ${description}"
  echo "--- launch log ---"
  sed -n '1,220p' "${LOG_FILE}" 2>/dev/null || true
  exit 1
}

echo "[Azas] Starting CODE-ONLY cup grasp dry-run; robot/camera disabled."
ros2 launch azas_bringup simulated_cup_grasp_dryrun.launch.py \
  selected_dispenser_id:="${SELECTED_DISPENSER_ID}" \
  >"${LOG_FILE}" 2>&1 &
LAUNCH_PID=$!

timeout 20s ros2 topic echo /jarvis/tumbler_floor_place/status --field data --no-daemon >"${STATUS_FILE}" &
STATUS_PID=$!
timeout 20s ros2 topic echo /jarvis/tumbler_floor_place/plan --no-daemon >"${PLAN_FILE}" &
PLAN_PID=$!

for _ in {1..40}; do
  if grep -q "DONE" "${STATUS_FILE}" 2>/dev/null; then
    assert_log_contains "plan side_pre_grasp: x=0\\.238 y=-0\\.163 z=0\\.135 gripper=preopen width_m=0\\.095 force_n=8\\.0" "code-only path preopens for tapered cup before side approach"
    assert_log_contains "plan side_grasp_tumbler: x=0\\.320 y=-0\\.220 z=0\\.135 gripper=close width_m=0\\.064 force_n=12\\.0" "code-only path closes to tapered cup target width"
    assert_log_contains "plan lift_tumbler: x=0\\.320 y=-0\\.220 z=0\\.175 gripper=none" "code-only path uses slight lift after side grasp"
    assert_log_contains "plan pre_floor_place: x=0\\.580 y=${EXPECTED_PLACE_Y} z=0\\.145 gripper=none" "code-only path uses slight place approach clearance"
    assert_log_contains "plan floor_place: x=0\\.580 y=${EXPECTED_PLACE_Y} z=0\\.085 gripper=open" "code-only path targets fixed selected-dispenser position"
    echo "[OK] code-only cup grasp path reached DONE"
    echo "[Azas] plan file: ${PLAN_FILE}"
    exit 0
  fi
  if grep -q "FAILED" "${STATUS_FILE}" 2>/dev/null; then
    echo "[FAIL] code-only cup grasp path reached FAILED"
    sed -n '1,160p' "${STATUS_FILE}" 2>/dev/null || true
    sed -n '1,200p' "${LOG_FILE}" 2>/dev/null || true
    exit 1
  fi
  sleep 0.5
done

echo "[FAIL] code-only cup grasp path did not reach DONE"
echo "--- status ---"
sed -n '1,160p' "${STATUS_FILE}" 2>/dev/null || true
echo "--- plan ---"
sed -n '1,160p' "${PLAN_FILE}" 2>/dev/null || true
echo "--- launch log ---"
sed -n '1,220p' "${LOG_FILE}" 2>/dev/null || true
exit 1
