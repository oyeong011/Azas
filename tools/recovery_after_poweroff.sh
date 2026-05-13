#!/usr/bin/env bash
set -euo pipefail

# Reboot/resume helper. This does not command robot motion or RG2 services.

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

run_step "Repository files present" test -f /home/ssu/Azas/docs/recovery_after_poweroff.md
run_step "Script syntax" bash -lc '
  bash -n /home/ssu/Azas/tools/verify_control_readiness.sh
  bash -n /home/ssu/Azas/tools/field_no_motion_report.sh
  bash -n /home/ssu/Azas/tools/robot_connection_acceptance.sh
  bash -n /home/ssu/Azas/tools/real_motion_measurement_report.sh
  bash -n /home/ssu/Azas/tools/check_live_hardware_gates.sh
  bash -n /home/ssu/Azas/tools/check_connection_stage.sh
  bash -n /home/ssu/Azas/tools/explain_real_robot_blockers.sh
  bash -n /home/ssu/Azas/tools/run_doosan_real_no_motion_m0609.sh
  bash -n /home/ssu/Azas/tools/run_connected_robot_control.sh
  bash -n /home/ssu/Azas/tools/run_robot_real.sh
'
run_step "Installed Azas package visibility" bash -lc '
  source /opt/ros/humble/setup.bash
  if [[ -f /home/ssu/Azas/install/setup.bash ]]; then
    source /home/ssu/Azas/install/setup.bash
  fi
  ros2 pkg prefix azas_bringup
  ros2 pkg prefix azas_task_manager
'
run_step "No-motion measurement blockers" /home/ssu/Azas/tools/real_motion_measurement_report.sh || true

{
  echo
  echo "## Next Safe Commands"
  echo "/home/ssu/Azas/tools/verify_control_readiness.sh"
  echo "/home/ssu/Azas/tools/explain_real_robot_blockers.sh"
  echo "ROBOT_HOST=<robot-ip> RG2_IP=<rg2-ip> /home/ssu/Azas/tools/run_connected_robot_control.sh  # connected no-motion field path"
  echo "ROBOT_HOST=<robot-ip> DOOSAN_NO_MOTION_CONFIRM=CONNECT_DOOSAN_NO_MOTION /home/ssu/Azas/tools/run_doosan_real_no_motion_m0609.sh  # after Doosan is connected"
  echo "/home/ssu/Azas/tools/field_no_motion_report.sh"
  echo "/home/ssu/Azas/tools/robot_connection_acceptance.sh  # after camera/Doosan/RG2 are connected"
  echo
  echo "Report: ${REPORT}"
} | tee -a "${REPORT}"
