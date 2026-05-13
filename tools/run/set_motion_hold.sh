#!/usr/bin/env bash
set -euo pipefail

# Set a local real-motion hold. This does not command robot motion or RG2.

MOTION_HOLD_FILE="${MOTION_HOLD_FILE:-/tmp/azas_motion_hold}"
REASON="${*:-operator hold}"

{
  echo "motion_hold=true"
  echo "timestamp=$(date -Is)"
  echo "reason=${REASON}"
  echo "effect=tools/run_robot_real.sh refuses to launch while this file exists"
} >"${MOTION_HOLD_FILE}"

echo "[Azas] Motion hold set: ${MOTION_HOLD_FILE}"
sed -n '1,20p' "${MOTION_HOLD_FILE}"
