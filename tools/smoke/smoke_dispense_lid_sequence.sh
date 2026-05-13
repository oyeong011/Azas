#!/usr/bin/env bash
set -euo pipefail

# Fake-hardware smoke for the post-place sequence:
# extended dispenser press -> lid close press. No real robot is contacted.

STATUS_FILE="${STATUS_FILE:-/tmp/azas_smoke_dispense_lid_status.txt}"
LOG_FILE="${LOG_FILE:-/tmp/azas_smoke_dispense_lid_launch.log}"
FAKE_LOG_FILE="${FAKE_LOG_FILE:-/tmp/azas_smoke_dispense_lid_fake_services.log}"
SELECTED_DISPENSER_ID="${SELECTED_DISPENSER_ID:-2}"
SERVICE_PREFIX="${SERVICE_PREFIX:-}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/azas_ros_logs}"
FLOAT_660="(659\\.9+|660\\.0+)"
FLOAT_580="580\\.0+"
FLOAT_367="367\\.0+"
FLOAT_152="152\\.0+"

case "${SELECTED_DISPENSER_ID}" in
  1) EXPECTED_PLAN_Y="0.035"; EXPECTED_Y_MM="35\\.0" ;;
  2) EXPECTED_PLAN_Y="-0.065"; EXPECTED_Y_MM="-65\\.0" ;;
  3) EXPECTED_PLAN_Y="-0.165"; EXPECTED_Y_MM="-165\\.0" ;;
  4) EXPECTED_PLAN_Y="-0.265"; EXPECTED_Y_MM="-265\\.0" ;;
  *)
    echo "[FAIL] unsupported SELECTED_DISPENSER_ID=${SELECTED_DISPENSER_ID}"
    exit 1
    ;;
esac

rm -f "${STATUS_FILE}" "${LOG_FILE}" "${FAKE_LOG_FILE}"
mkdir -p "${ROS_LOG_DIR}"

set +u
source /opt/ros/humble/setup.bash
source /home/ssu/Azas/install/setup.bash
source /home/ssu/ros2_ws/install/setup.bash
set -u

assert_no_preexisting_fake_targets() {
  ros2 service list --no-daemon >/tmp/azas_smoke_dispense_lid_pre_services.txt 2>/tmp/azas_smoke_dispense_lid_pre_services.err || true
  for service in /jarvis/rg2/open /jarvis/rg2/close /jarvis/rg2/set_width; do
    if grep -qx "${service}" /tmp/azas_smoke_dispense_lid_pre_services.txt; then
      echo "[FAIL] refusing fake smoke: ${service} already exists before fake_hardware_services.py starts"
      echo "[FAIL] This smoke must only talk to the local fake/no-motion services."
      exit 1
    fi
  done
}

cleanup() {
  trap - EXIT
  if [[ -n "${LAUNCH_PID:-}" ]] && kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    kill "${LAUNCH_PID}" 2>/dev/null || true
  fi
  if [[ -n "${FAKE_PID:-}" ]] && kill -0 "${FAKE_PID}" 2>/dev/null; then
    kill "${FAKE_PID}" 2>/dev/null || true
  fi
  if [[ -n "${STATUS_PID:-}" ]] && kill -0 "${STATUS_PID}" 2>/dev/null; then
    kill "${STATUS_PID}" 2>/dev/null || true
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
assert_no_preexisting_fake_targets
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
    ros2 service list --no-daemon >/tmp/azas_smoke_dispense_lid_services.txt 2>/tmp/azas_smoke_dispense_lid_services.err || true
    if grep -q "/motion/move_line\\|/.*/motion/move_line" /tmp/azas_smoke_dispense_lid_services.txt; then
      exit 0
    fi
    sleep 0.2
  done
'

echo "[Azas] Starting dispenser/lid launch against fake services"
LAUNCH_ARGS=(
  selected_dispenser_id:="${SELECTED_DISPENSER_ID}"
  enable_hardware:=true
  hardware_confirm:=ENABLE_REAL_ROBOT_MOTION
  allow_service_control_without_moveit:=true
)
if [[ -n "${SERVICE_PREFIX}" ]]; then
  LAUNCH_ARGS+=(service_prefix:="${SERVICE_PREFIX}")
fi

ros2 launch jarvis dispense_lid_sequence.launch.py "${LAUNCH_ARGS[@]}" \
  >"${LOG_FILE}" 2>&1 &
LAUNCH_PID=$!

timeout 20s ros2 topic echo /jarvis/dispense_lid_sequence/status --field data --no-daemon >"${STATUS_FILE}" &
STATUS_PID=$!

echo "[Azas] Waiting for DONE status"
for _ in {1..40}; do
  if grep -q "DONE" "${STATUS_FILE}" 2>/dev/null || grep -q "dispense_lid_sequence_node.*DONE" "${LOG_FILE}" 2>/dev/null; then
    assert_log_contains "${LOG_FILE}" "plan extended_press_approach: x=0\\.660 y=${EXPECTED_PLAN_Y} z=0\\.472 hold=0\\.00" "press starts from an extended +X approach pose"
    assert_log_contains "${LOG_FILE}" "plan extended_press_top: x=0\\.660 y=${EXPECTED_PLAN_Y} z=0\\.392 hold=0\\.00" "press aligns with the dispenser top height"
    assert_log_contains "${LOG_FILE}" "plan extended_press_down: x=0\\.660 y=${EXPECTED_PLAN_Y} z=0\\.367 hold=0\\.50" "press travels down at extended reach"
    assert_log_contains "${LOG_FILE}" "plan lid_close_approach: x=0\\.580 y=${EXPECTED_PLAN_Y} z=0\\.240 hold=0\\.00" "lid close approaches above the placed cup"
    assert_log_contains "${LOG_FILE}" "plan lid_close_press: x=0\\.580 y=${EXPECTED_PLAN_Y} z=0\\.152 hold=0\\.40" "lid close presses down on the cup lid"
    assert_log_contains "${FAKE_LOG_FILE}" "fake move_line: pos=\\[(np\\.float64\\()?${FLOAT_660}\\)?, (np\\.float64\\()?${EXPECTED_Y_MM}\\)?, (np\\.float64\\()?${FLOAT_367}" "fake MoveLine received extended press-down waypoint in mm"
    assert_log_contains "${FAKE_LOG_FILE}" "fake move_line: pos=\\[(np\\.float64\\()?${FLOAT_580}\\)?, (np\\.float64\\()?${EXPECTED_Y_MM}\\)?, (np\\.float64\\()?${FLOAT_152}" "fake MoveLine received lid-close press waypoint in mm"
    echo "[OK] dispenser/lid fake hardware path reached DONE"
    exit 0
  fi
  if grep -q "FAILED" "${STATUS_FILE}" 2>/dev/null; then
    echo "[FAIL] dispenser/lid path reached FAILED"
    sed -n '1,160p' "${LOG_FILE}"
    sed -n '1,160p' "${FAKE_LOG_FILE}"
    exit 1
  fi
  sleep 0.5
done

echo "[FAIL] dispenser/lid path did not reach DONE"
echo "--- status ---"
sed -n '1,120p' "${STATUS_FILE}" 2>/dev/null || true
echo "--- launch log ---"
sed -n '1,180p' "${LOG_FILE}" 2>/dev/null || true
echo "--- fake service log ---"
sed -n '1,180p' "${FAKE_LOG_FILE}" 2>/dev/null || true
exit 1
