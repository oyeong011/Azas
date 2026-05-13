#!/usr/bin/env bash
set -euo pipefail

# Reboot/resume helper. This does not command robot motion or RG2 services.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKS_DIR="${ROOT_DIR}/tools/checks"
RUN_DIR="${ROOT_DIR}/tools/run"
REPORT="${REPORT:-/tmp/azas_recovery_after_poweroff_report.txt}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/azas_ros_logs}"

mkdir -p "${ROS_LOG_DIR}"
rm -f "${REPORT}"

section() {
  local title="$1"
  {
    echo
    echo "## ${title}"
  } | tee -a "${REPORT}"
}

run_step() {
  local label="$1"
  shift
  section "${label}"
  if "$@" 2>&1 | tee -a "${REPORT}"; then
    echo "[RESULT] ${label}: PASS" | tee -a "${REPORT}"
  else
    echo "[RESULT] ${label}: FAIL" | tee -a "${REPORT}"
    return 1
  fi
}

{
  echo "# Azas Recovery After Poweroff Report"
  date -Is
  echo
  echo "Scope: non-motion resume diagnostics."
} | tee -a "${REPORT}"

run_step "Repository files present" test -f "${ROOT_DIR}/docs/recovery_after_poweroff.md"
run_step "Script syntax" bash -lc '
  for script in "$@"; do
    bash -n "${script}"
  done
' bash \
  "${CHECKS_DIR}/verify_control_readiness.sh" \
  "${RUN_DIR}/field_no_motion_report.sh" \
  "${CHECKS_DIR}/robot_connection_acceptance.sh" \
  "${RUN_DIR}/real_motion_measurement_report.sh" \
  "${CHECKS_DIR}/check_live_hardware_gates.sh" \
  "${CHECKS_DIR}/check_connection_stage.sh" \
  "${CHECKS_DIR}/explain_real_robot_blockers.sh" \
  "${RUN_DIR}/run_doosan_real_no_motion_m0609.sh" \
  "${RUN_DIR}/run_connected_robot_control.sh" \
  "${RUN_DIR}/run_robot_real.sh"
run_step "Installed Azas package visibility" env ROOT_DIR="${ROOT_DIR}" bash -lc '
  source /opt/ros/humble/setup.bash
  if [[ -f "${ROOT_DIR}/install/setup.bash" ]]; then
    source "${ROOT_DIR}/install/setup.bash"
  fi
  ros2 pkg prefix azas_bringup
  ros2 pkg prefix azas_task_manager
'
run_step "No-motion measurement blockers" "${RUN_DIR}/real_motion_measurement_report.sh" || true

{
  echo
  echo "## Next Safe Commands"
  echo "${CHECKS_DIR}/verify_control_readiness.sh"
  echo "${CHECKS_DIR}/explain_real_robot_blockers.sh"
  echo "ROBOT_HOST=<robot-ip> RG2_IP=<rg2-ip> ${RUN_DIR}/run_connected_robot_control.sh  # connected no-motion field path"
  echo "ROBOT_HOST=<robot-ip> DOOSAN_NO_MOTION_CONFIRM=CONNECT_DOOSAN_NO_MOTION ${RUN_DIR}/run_doosan_real_no_motion_m0609.sh  # after Doosan is connected"
  echo "${RUN_DIR}/field_no_motion_report.sh"
  echo "${CHECKS_DIR}/robot_connection_acceptance.sh  # after camera/Doosan/RG2 are connected"
  echo
  echo "Report: ${REPORT}"
} | tee -a "${REPORT}"
