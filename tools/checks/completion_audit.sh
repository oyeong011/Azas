#!/usr/bin/env bash
set -euo pipefail

# Strict completion audit for the objective:
# "오픈소스를 찾아서 로봇이 제어까지 가능한 수준으로 구축하기"
#
# This is stricter than verify_control_readiness.sh. It fails while real
# hardware evidence is missing. No robot motion or RG2 service command is sent.

REPORT="${REPORT:-/tmp/azas_completion_audit.txt}"
CONTROL_REPORT="${CONTROL_REPORT:-/tmp/azas_control_readiness_report.txt}"
FIELD_REPORT="${FIELD_REPORT:-/tmp/azas_field_no_motion_report.txt}"
GATE_STAMP="${GATE_STAMP:-/tmp/azas_live_hardware_gates_passed}"
LIVE_GATE_MAX_AGE_SEC="${LIVE_GATE_MAX_AGE_SEC:-600}"
HAND_EYE_REPORT="${HAND_EYE_REPORT:-/tmp/azas_completion_hand_eye.out}"
missing=0

rm -f "${REPORT}"

section() {
  local title="$1"
  {
    echo
    echo "## ${title}"
  } | tee -a "${REPORT}"
}

ok() {
  echo "[OK] $1" | tee -a "${REPORT}"
}

missing_item() {
  echo "[MISSING] $1" | tee -a "${REPORT}"
  missing=$((missing + 1))
}

file_exists() {
  local path="$1"
  local label="$2"
  if [[ -s "${path}" ]]; then
    ok "${label}: ${path}"
  else
    missing_item "${label}: ${path}"
  fi
}

contains() {
  local path="$1"
  local pattern="$2"
  local label="$3"
  if [[ -s "${path}" ]] && grep -Eq "${pattern}" "${path}"; then
    ok "${label}"
  else
    missing_item "${label}"
  fi
}

fresh_file() {
  local path="$1"
  local label="$2"
  if [[ ! -s "${path}" ]]; then
    missing_item "${label}: ${path}"
    return 1
  fi

  local now_sec
  local file_sec
  local age_sec
  now_sec="$(date +%s)"
  file_sec="$(stat -c %Y "${path}")"
  age_sec=$((now_sec - file_sec))

  if (( age_sec <= LIVE_GATE_MAX_AGE_SEC )); then
    ok "${label}: ${path} age=${age_sec}s"
    return 0
  fi

  missing_item "${label}: ${path} age=${age_sec}s > ${LIVE_GATE_MAX_AGE_SEC}s"
  return 1
}

{
  echo "# Azas Completion Audit"
  date -Is
  echo
  echo "Objective: 오픈소스를 찾아서 로봇이 제어까지 가능한 수준으로 구축하기"
  echo "No motion commands are sent by this audit."
} | tee -a "${REPORT}"

section "Prompt-To-Artifact Checklist"
file_exists /home/ssu/Azas/docs/oss_robot_control_stack.md "OSS stack decision document"
file_exists /home/ssu/Azas/dependencies/ros2_sources.repos "Primary ROS source manifest"
file_exists /home/ssu/Azas/dependencies/experimental_sources.repos "Experimental ROS source manifest"
file_exists /home/ssu/Azas/dependencies/dsr_deeptree_sources.repos "DSR_DeepTree pinned demo manifest"
file_exists /home/ssu/Azas/docs/dsr_deeptree_integration.md "DSR_DeepTree integration note"
file_exists /home/ssu/Azas/docs/field_execution_commands.md "Field execution command sheet"
file_exists /home/ssu/Azas/src/azas_task_manager/azas_task_manager/cocktail_dryrun_sequence_node.py "Cocktail dry-run sequence node"
file_exists /home/ssu/Azas/tools/verify_control_readiness.sh "Non-hardware verifier"
file_exists /home/ssu/Azas/tools/field_no_motion_report.sh "Field no-motion report"
file_exists /home/ssu/Azas/tools/explain_real_robot_blockers.sh "Real robot blocker explainer"
file_exists /home/ssu/Azas/tools/run_doosan_real_no_motion_m0609.sh "Doosan real no-motion bringup entrypoint"
file_exists /home/ssu/Azas/tools/run_connected_robot_control.sh "Connected robot control orchestration entrypoint"
file_exists /home/ssu/Azas/tools/run_robot_real.sh "Real-motion gated entrypoint"
file_exists /home/ssu/Azas/docs/recovery_after_poweroff.md "Power-off recovery document"
file_exists /home/ssu/Azas/docs/current_handoff_2026-05-11.md "Current handoff document"

section "Fresh Non-Hardware Evidence"
if /home/ssu/Azas/tools/verify_control_readiness.sh >/tmp/azas_completion_verify.out 2>&1; then
  ok "verify_control_readiness.sh passes"
else
  missing_item "verify_control_readiness.sh passes"
fi
cat /tmp/azas_completion_verify.out >>"${REPORT}" || true

section "Existing Report Evidence"
contains "${CONTROL_REPORT}" '\[RESULT\] Cocktail dry-run sequence smoke: PASS' "Control report includes cocktail dry-run PASS"
contains "${CONTROL_REPORT}" '\[RESULT\] Real-motion entrypoint fail-closed smoke: PASS' "Control report includes real-motion entrypoint fail-closed PASS"
contains "${CONTROL_REPORT}" '\[RESULT\] Real-motion config gate smoke: PASS' "Control report includes config gate smoke PASS"

section "Real Hardware Readiness Evidence"
if [[ -f "${GATE_STAMP}" ]] && grep -qx "strict=true" "${GATE_STAMP}"; then
  now_sec="$(date +%s)"
  stamp_sec="$(stat -c %Y "${GATE_STAMP}")"
  age_sec=$((now_sec - stamp_sec))
  if (( age_sec <= LIVE_GATE_MAX_AGE_SEC )); then
    ok "Fresh strict live gate stamp exists: ${GATE_STAMP} age=${age_sec}s"
  else
    missing_item "Fresh strict live gate stamp exists: ${GATE_STAMP} age=${age_sec}s > ${LIVE_GATE_MAX_AGE_SEC}s"
  fi
else
  missing_item "Fresh strict live gate stamp exists: ${GATE_STAMP}"
fi

if /home/ssu/Azas/tools/check_real_motion_config.sh >/tmp/azas_completion_config.out 2>&1; then
  ok "Production calibration/safety config gate passes"
else
  missing_item "Production calibration/safety config gate passes"
fi
cat /tmp/azas_completion_config.out >>"${REPORT}" || true

if fresh_file "${FIELD_REPORT}" "Fresh field no-motion report"; then
  contains "${FIELD_REPORT}" '\[RESULT\] Cup detection stability: PASS' "Fresh field report includes cup/tumbler-body stability PASS"
  contains "${FIELD_REPORT}" '\[RESULT\] Lid detection stability: PASS' "Fresh field report includes lid stability PASS"
  contains "${FIELD_REPORT}" '\[RESULT\] Live hardware gate: PASS' "Fresh field report includes live hardware gate PASS"
fi

if /home/ssu/Azas/tools/check_hand_eye_readiness.sh >"${HAND_EYE_REPORT}" 2>&1; then
  ok "Hand-eye/base-camera transform readiness check passes"
else
  missing_item "Hand-eye/base-camera transform readiness check passes"
fi
cat "${HAND_EYE_REPORT}" >>"${REPORT}" || true

contains /home/ssu/Azas/docs/control_readiness_audit.md 'RG2 actuation verified.*\| Done \|' "RG2 actuation marked done"
contains /home/ssu/Azas/docs/control_readiness_audit.md 'Real robot hardware gate verified.*\| Done \|' "Real robot hardware gate marked done"

section "Verdict"
if [[ "${missing}" -eq 0 ]]; then
  echo "[COMPLETE] Objective evidence is complete." | tee -a "${REPORT}"
else
  echo "[NOT COMPLETE] missing=${missing}. Real robot-control readiness is not fully verified." | tee -a "${REPORT}"
  echo "Report: ${REPORT}" | tee -a "${REPORT}"
  exit 1
fi

echo "Report: ${REPORT}" | tee -a "${REPORT}"
