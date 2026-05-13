#!/usr/bin/env bash
set -euo pipefail

# Summarize the measured-value blockers that keep real robot motion disabled.
# This script sends no ROS command and does not touch hardware.

REPORT="${REPORT:-/tmp/azas_real_motion_measurement_report.txt}"
CALIBRATION_FILE="${CALIBRATION_FILE:-/home/ssu/Azas/src/azas_bringup/config/calibration.yaml}"
SAFETY_FILE="${SAFETY_FILE:-/home/ssu/Azas/src/azas_bringup/config/safety.yaml}"
CHECKER="${CHECKER:-/home/ssu/Azas/tools/checks/check_real_motion_config.sh}"

rm -f "${REPORT}"

section() {
  local title="$1"
  {
    echo
    echo "## ${title}"
  } | tee -a "${REPORT}"
}

{
  echo "# Azas Real-Motion Measurement Report"
  date -Is
  echo
  echo "Scope: measured-value audit only. No robot, gripper, or ROS motion command is sent."
  echo "calibration=${CALIBRATION_FILE}"
  echo "safety=${SAFETY_FILE}"
} | tee -a "${REPORT}"

section "Config Gate"
if CALIBRATION_FILE="${CALIBRATION_FILE}" SAFETY_FILE="${SAFETY_FILE}" "${CHECKER}" 2>&1 | tee -a "${REPORT}"; then
  echo "[RESULT] Config gate: PASS" | tee -a "${REPORT}"
else
  echo "[RESULT] Config gate: BLOCKED" | tee -a "${REPORT}"
fi

section "Required Measurement Worksheet"
cat <<'EOF' | tee -a "${REPORT}"
- Camera frame from live CameraInfo.
- MoveIt planning group and EE link from the actual M0609 config.
- RG2 TCP frame and TCP-to-cup-mouth offset measured with the real gripper/cup.
- Hand-eye transform from base_link to the camera frame.
- Fixed dispenser outlet pose and rim/outlet clearance in base_link.
- Workspace bounds and minimum safe Z from the physical cell.
- RG2 default width/force values after unit/limit confirmation.
EOF

section "Next Command"
cat <<'EOF' | tee -a "${REPORT}"
After the measured values are filled:

STRICT_LIVE_GATE=true RUN_LID_STABILITY=true RUN_CUP_STABILITY=true /home/ssu/Azas/tools/run/field_no_motion_report.sh

Real motion remains blocked until that strict report writes /tmp/azas_live_hardware_gates_passed.
EOF

echo | tee -a "${REPORT}"
echo "Report: ${REPORT}" | tee -a "${REPORT}"
