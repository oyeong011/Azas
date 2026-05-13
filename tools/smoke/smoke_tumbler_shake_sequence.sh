#!/usr/bin/env bash
set -euo pipefail

# Fake-hardware smoke for the safe-space tumbler shake path. No real robot is contacted.

STATUS_FILE="${STATUS_FILE:-/tmp/azas_smoke_tumbler_shake_status.txt}"
LOG_FILE="${LOG_FILE:-/tmp/azas_smoke_tumbler_shake_launch.log}"
FAKE_LOG_FILE="${FAKE_LOG_FILE:-/tmp/azas_smoke_tumbler_shake_fake_services.log}"
BAD_LOG_FILE="${BAD_LOG_FILE:-/tmp/azas_smoke_tumbler_shake_bad_launch.log}"
BAD_STATUS_FILE="${BAD_STATUS_FILE:-/tmp/azas_smoke_tumbler_shake_bad_status.txt}"
SERVICE_PREFIX="${SERVICE_PREFIX:-}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/azas_ros_logs}"

rm -f "${STATUS_FILE}" "${LOG_FILE}" "${FAKE_LOG_FILE}" "${BAD_LOG_FILE}" "${BAD_STATUS_FILE}"
mkdir -p "${ROS_LOG_DIR}"

set +u
source /opt/ros/humble/setup.bash
source /home/ssu/Azas/install/setup.bash
source /home/ssu/ros2_ws/install/setup.bash
set -u

cleanup() {
  trap - EXIT
  if [[ -n "${LAUNCH_PID:-}" ]] && kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    kill "${LAUNCH_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BAD_LAUNCH_PID:-}" ]] && kill -0 "${BAD_LAUNCH_PID}" 2>/dev/null; then
    kill "${BAD_LAUNCH_PID}" 2>/dev/null || true
  fi
  if [[ -n "${FAKE_PID:-}" ]] && kill -0 "${FAKE_PID}" 2>/dev/null; then
    kill "${FAKE_PID}" 2>/dev/null || true
  fi
  if [[ -n "${STATUS_PID:-}" ]] && kill -0 "${STATUS_PID}" 2>/dev/null; then
    kill "${STATUS_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BAD_STATUS_PID:-}" ]] && kill -0 "${BAD_STATUS_PID}" 2>/dev/null; then
    kill "${BAD_STATUS_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

assert_log_contains() {
  local file="$1"
  local pattern="$2"
  local description="$3"
  if grep -Eq "$pattern" "${file}"; then
    echo "[OK] ${description}"
    return 0
  fi
  echo "[FAIL] missing expected evidence: ${description}"
  echo "--- ${file} ---"
  sed -n '1,220p' "${file}" 2>/dev/null || true
  exit 1
}

echo "[Azas] Starting fake hardware services"
if [[ -n "${SERVICE_PREFIX}" ]]; then
  python3 /home/ssu/Azas/tools/smoke/fake_hardware_services.py \
    --ros-args -p service_prefix:="${SERVICE_PREFIX}" \
    >"${FAKE_LOG_FILE}" 2>&1 &
else
  python3 /home/ssu/Azas/tools/smoke/fake_hardware_services.py \
    >"${FAKE_LOG_FILE}" 2>&1 &
fi
FAKE_PID=$!

timeout 12s bash -lc '
  while true; do
    ros2 service list --no-daemon >/tmp/azas_smoke_tumbler_shake_services.txt 2>/tmp/azas_smoke_tumbler_shake_services.err || true
    if grep -q "/motion/move_line\\|/.*/motion/move_line" /tmp/azas_smoke_tumbler_shake_services.txt; then
      exit 0
    fi
    sleep 0.2
  done
'

echo "[Azas] Starting safe shake launch against fake services"
LAUNCH_ARGS=(
  enable_hardware:=true
  hardware_confirm:=ENABLE_REAL_ROBOT_MOTION
  allow_service_control_without_moveit:=true
)
if [[ -n "${SERVICE_PREFIX}" ]]; then
  LAUNCH_ARGS+=(service_prefix:="${SERVICE_PREFIX}")
fi

ros2 launch jarvis tumbler_shake_sequence.launch.py "${LAUNCH_ARGS[@]}" \
  >"${LOG_FILE}" 2>&1 &
LAUNCH_PID=$!

timeout 20s ros2 topic echo /jarvis/tumbler_shake_sequence/status --field data --no-daemon >"${STATUS_FILE}" 2>/tmp/azas_smoke_tumbler_shake_topic.err &
STATUS_PID=$!

echo "[Azas] Waiting for DONE status"
for _ in {1..40}; do
  if grep -q "DONE" "${STATUS_FILE}" 2>/dev/null || grep -q "tumbler_shake_sequence_node.*DONE" "${LOG_FILE}" 2>/dev/null; then
    assert_log_contains "${LOG_FILE}" "Shake safety validated: min_z=0\\.250 keepout_radius=0\\.200 workspace=ok" "shake path passed min-height and dispenser keepout validation"
    assert_log_contains "${LOG_FILE}" "plan shake_safe_approach: x=0\\.300 y=-0\\.280 z=0\\.370 hold=0\\.00" "shake starts at a high safe approach pose"
    assert_log_contains "${LOG_FILE}" "plan shake_center_start: x=0\\.300 y=-0\\.280 z=0\\.320 hold=0\\.00" "shake center stays high and away from dispensers"
    assert_log_contains "${LOG_FILE}" "plan shake_cycle_1_x_plus: x=0\\.335 y=-0\\.280 z=0\\.320 hold=0\\.00" "shake x-plus waypoint is bounded"
    assert_log_contains "${LOG_FILE}" "plan shake_cycle_1_y_minus: x=0\\.300 y=-0\\.300 z=0\\.320 hold=0\\.00" "shake y-minus waypoint remains inside workspace"
    assert_log_contains "${FAKE_LOG_FILE}" "fake move_line: pos=\\[(np\\.float64\\()?300\\.0+\\)?, (np\\.float64\\()?-280\\.0+\\)?, (np\\.float64\\()?370\\.0+" "fake MoveLine received safe approach waypoint in mm"
    assert_log_contains "${FAKE_LOG_FILE}" "fake move_line: pos=\\[(np\\.float64\\()?33[45]\\.[0-9]+\\)?, (np\\.float64\\()?-280\\.0+\\)?, (np\\.float64\\()?320\\.0+" "fake MoveLine received bounded shake waypoint in mm"
    echo "[OK] tumbler shake fake hardware path reached DONE"
    kill "${LAUNCH_PID}" 2>/dev/null || true
    kill "${STATUS_PID}" 2>/dev/null || true
    break
  fi
  if grep -q "FAILED" "${STATUS_FILE}" 2>/dev/null; then
    echo "[FAIL] tumbler shake path reached FAILED"
    sed -n '1,160p' "${LOG_FILE}"
    sed -n '1,160p' "${FAKE_LOG_FILE}"
    exit 1
  fi
  sleep 0.5
done

if ! grep -q "DONE" "${STATUS_FILE}" 2>/dev/null && ! grep -q "tumbler_shake_sequence_node.*DONE" "${LOG_FILE}" 2>/dev/null; then
  echo "[FAIL] tumbler shake path did not reach DONE"
  echo "--- status ---"
  sed -n '1,120p' "${STATUS_FILE}" 2>/dev/null || true
  echo "--- launch log ---"
  sed -n '1,180p' "${LOG_FILE}" 2>/dev/null || true
  echo "--- fake service log ---"
  sed -n '1,180p' "${FAKE_LOG_FILE}" 2>/dev/null || true
  exit 1
fi

echo "[Azas] Checking that unsafe shake space fails closed"
ros2 launch jarvis tumbler_shake_sequence.launch.py \
  shake_center_x:=0.58 \
  shake_center_y:=-0.12 \
  >"${BAD_LOG_FILE}" 2>&1 &
BAD_LAUNCH_PID=$!

timeout 12s ros2 topic echo /jarvis/tumbler_shake_sequence/status --field data --no-daemon >"${BAD_STATUS_FILE}" 2>/tmp/azas_smoke_tumbler_shake_bad_topic.err &
BAD_STATUS_PID=$!

for _ in {1..24}; do
  if grep -q "FAILED" "${BAD_STATUS_FILE}" 2>/dev/null || grep -q "tumbler_shake_sequence_node.*FAILED" "${BAD_LOG_FILE}" 2>/dev/null; then
    assert_log_contains "${BAD_LOG_FILE}" "too close to dispenser" "unsafe dispenser-overlap shake plan fails closed"
    echo "[OK] unsafe shake space was rejected"
    exit 0
  fi
  sleep 0.5
done

echo "[FAIL] unsafe shake space did not fail closed"
sed -n '1,180p' "${BAD_LOG_FILE}" 2>/dev/null || true
exit 1
