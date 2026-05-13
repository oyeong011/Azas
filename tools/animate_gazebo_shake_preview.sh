#!/usr/bin/env bash
set -euo pipefail

model_name="${1:-tumbler_shaker_start}"
gripper_name="${GRIPPER_MODEL_NAME:-rg2_preview}"
center_x="${SHAKE_CENTER_X:-0.42}"
center_y="${SHAKE_CENTER_Y:--0.28}"
z="${SHAKE_MODEL_Z:-0.0}"
amp_x="${SHAKE_AMPLITUDE_X:-0.035}"
amp_y="${SHAKE_AMPLITUDE_Y:-0.020}"

while true; do
  gz model -m "${model_name}" -x "${center_x}" -y "${center_y}" -z "${z}" >/dev/null 2>&1 || true
  gz model -m "${gripper_name}" -x "${center_x}" -y "${center_y}" -z "${z}" >/dev/null 2>&1 || true
  sleep 0.20
  gz model -m "${model_name}" -x "$(awk "BEGIN {print ${center_x}+${amp_x}}")" -y "${center_y}" -z "${z}" >/dev/null 2>&1 || true
  gz model -m "${gripper_name}" -x "$(awk "BEGIN {print ${center_x}+${amp_x}}")" -y "${center_y}" -z "${z}" >/dev/null 2>&1 || true
  sleep 0.20
  gz model -m "${model_name}" -x "$(awk "BEGIN {print ${center_x}-${amp_x}}")" -y "${center_y}" -z "${z}" >/dev/null 2>&1 || true
  gz model -m "${gripper_name}" -x "$(awk "BEGIN {print ${center_x}-${amp_x}}")" -y "${center_y}" -z "${z}" >/dev/null 2>&1 || true
  sleep 0.20
  gz model -m "${model_name}" -x "${center_x}" -y "$(awk "BEGIN {print ${center_y}+${amp_y}}")" -z "${z}" >/dev/null 2>&1 || true
  gz model -m "${gripper_name}" -x "${center_x}" -y "$(awk "BEGIN {print ${center_y}+${amp_y}}")" -z "${z}" >/dev/null 2>&1 || true
  sleep 0.20
  gz model -m "${model_name}" -x "${center_x}" -y "$(awk "BEGIN {print ${center_y}-${amp_y}}")" -z "${z}" >/dev/null 2>&1 || true
  gz model -m "${gripper_name}" -x "${center_x}" -y "$(awk "BEGIN {print ${center_y}-${amp_y}}")" -z "${z}" >/dev/null 2>&1 || true
  sleep 0.20
done
