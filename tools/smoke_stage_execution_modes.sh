#!/usr/bin/env bash
set -euo pipefail

# Verifies real-field stage limiting without starting camera, RG2, or Doosan hardware.

export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/azas_ros_logs}"
mkdir -p "${ROS_LOG_DIR}"

set +u
source /opt/ros/humble/setup.bash
source /home/ssu/Azas/install/setup.bash
source /home/ssu/ros2_ws/install/setup.bash
set -u

cleanup() {
  if [[ -n "${LAUNCH_PID:-}" ]] && kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    kill "${LAUNCH_PID}" 2>/dev/null || true
    wait "${LAUNCH_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

wait_done() {
  local log_file="$1"
  for _ in {1..30}; do
    if grep -q "DONE" "${log_file}" 2>/dev/null; then
      return 0
    fi
    if grep -q "FAILED" "${log_file}" 2>/dev/null; then
      echo "[FAIL] stage launch reached FAILED"
      sed -n '1,220p' "${log_file}"
      return 1
    fi
    sleep 0.5
  done
  echo "[FAIL] stage launch did not reach DONE"
  sed -n '1,220p' "${log_file}"
  return 1
}

assert_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if grep -Eq "${pattern}" "${file}"; then
    echo "[OK] ${label}"
    return 0
  fi
  echo "[FAIL] missing ${label}"
  sed -n '1,220p' "${file}"
  return 1
}

assert_not_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if grep -Eq "${pattern}" "${file}"; then
    echo "[FAIL] unexpected ${label}"
    sed -n '1,220p' "${file}"
    return 1
  fi
  echo "[OK] ${label}"
}

run_floor_stage() {
  local stage="$1"
  local log_file="/tmp/azas_stage_floor_${stage}.log"
  rm -f "${log_file}"
  LAUNCH_PID=""
  ros2 launch jarvis tumbler_floor_place.launch.py \
    selected_dispenser_id:=2 \
    use_tumbler_pose_topic:=false \
    execution_stage:="${stage}" \
    >"${log_file}" 2>&1 &
  LAUNCH_PID=$!
  wait_done "${log_file}"
  cleanup
  LAUNCH_PID=""
  echo "${log_file}"
}

run_dispense_stage() {
  local stage="$1"
  local log_file="/tmp/azas_stage_dispense_${stage}.log"
  rm -f "${log_file}"
  LAUNCH_PID=""
  ros2 launch jarvis dispense_lid_sequence.launch.py \
    selected_dispenser_id:=2 \
    execution_stage:="${stage}" \
    >"${log_file}" 2>&1 &
  LAUNCH_PID=$!
  wait_done "${log_file}"
  cleanup
  LAUNCH_PID=""
  echo "${log_file}"
}

lift_log="$(run_floor_stage lift)"
assert_contains "${lift_log}" "execution_stage=lift: stopping plan at lift_tumbler" "floor stage lift stop marker"
assert_contains "${lift_log}" "plan lift_tumbler:" "floor stage lift includes lift waypoint"
assert_not_contains "${lift_log}" "plan floor_place:" "floor stage lift excludes floor placement"

place_log="$(run_floor_stage place)"
assert_contains "${place_log}" "execution_stage=place: stopping plan at floor_place" "floor stage place stop marker"
assert_contains "${place_log}" "plan floor_place:" "floor stage place includes placement waypoint"
assert_not_contains "${place_log}" "plan retreat_after_place:" "floor stage place excludes retreat"

press_log="$(run_dispense_stage press)"
assert_contains "${press_log}" "execution_stage=press: generated 4 of 7 sequence steps" "dispense stage press stop marker"
assert_contains "${press_log}" "plan extended_press_down:" "dispense stage press includes press down"
assert_not_contains "${press_log}" "plan lid_close_press:" "dispense stage press excludes lid close"

lid_log="$(run_dispense_stage lid)"
assert_contains "${lid_log}" "execution_stage=lid: generated 3 of 7 sequence steps" "dispense stage lid stop marker"
assert_contains "${lid_log}" "plan lid_close_press:" "dispense stage lid includes lid close"
assert_not_contains "${lid_log}" "plan extended_press_down:" "dispense stage lid excludes dispenser press"

echo "[PASS] stage execution modes are limited as expected"
