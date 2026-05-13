#!/usr/bin/env bash
set -euo pipefail

# Regression smoke for the post-connection acceptance wrapper.
# The check must fail closed when live camera/robot/RG2 evidence is absent.
# It sends no Doosan motion command and no RG2 open/close request.

OUT="/tmp/azas_smoke_robot_connection_acceptance.out"
ERR="/tmp/azas_smoke_robot_connection_acceptance.err"

set +e
RUN_DEPTH_SAMPLE=false \
RUN_LID_STABILITY=false \
RUN_CUP_STABILITY=false \
RUN_HAND_EYE=false \
RUN_COMPLETION_AUDIT=false \
REPORT=/tmp/azas_smoke_robot_connection_acceptance_report.txt \
/home/ssu/Azas/tools/checks/robot_connection_acceptance.sh >"${OUT}" 2>"${ERR}"
status=$?
set -e

if [[ "${status}" -eq 0 ]]; then
  echo "[FAIL] robot_connection_acceptance.sh passed without live evidence"
  sed -n '1,160p' "${OUT}" || true
  exit 1
fi

if grep -q '^\[BLOCKED\] Robot connection acceptance failed:' "${OUT}"; then
  echo "[PASS] robot_connection_acceptance.sh fails closed without live evidence"
  exit 0
fi

echo "[FAIL] robot_connection_acceptance.sh failed, but did not report the expected BLOCKED verdict"
sed -n '1,180p' "${OUT}" || true
sed -n '1,80p' "${ERR}" || true
exit 1
